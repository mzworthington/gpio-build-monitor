#include <Arduino.h>
#include <GxEPD2_BW.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <cstring>
#include <esp_sleep.h>
#include <esp_wifi.h>

#include "duty_cycle.hpp"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.h.example"
#endif

// Xteink X4 panel pins (open-x4-epaper/sample-firmware).
#define EPD_SCLK 8
#define EPD_MOSI 10
#define EPD_CS 21
#define EPD_DC 4
#define EPD_RST 5
#define EPD_BUSY 6
#define BAT_GPIO 0
#define USB_DETECT_GPIO 20
#define POWER_BUTTON_GPIO 3

#define USER_AGENT "gpio-build-monitor-x4/0.1 (+https://github.com/mzworthington/gpio-build-monitor)"
#define WIFI_TIMEOUT_MS 15000
#define HTTP_TIMEOUT_MS 10000

GxEPD2_BW<GxEPD2_426_GDEQ0426T82, GxEPD2_426_GDEQ0426T82::HEIGHT> display(
    GxEPD2_426_GDEQ0426T82(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

RTC_DATA_ATTR char last_etag[x4::kEtagCap] = "";
RTC_DATA_ATTR uint8_t fail_streak = 0;
RTC_DATA_ATTR uint8_t updates_since_full = 0;

static bool is_charging() { return digitalRead(USB_DETECT_GPIO) == HIGH; }

static void radio_off() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

static void enter_deep_sleep(uint32_t seconds) {
  radio_off();
  Serial.printf("deep sleep %u s\n", seconds);
  Serial.flush();
  esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(seconds) * 1000000ULL);
  esp_deep_sleep_enable_gpio_wakeup(1ULL << POWER_BUTTON_GPIO, ESP_GPIO_WAKEUP_GPIO_LOW);
  // Do not gpio_deep_sleep_hold_en(): non-RTC pins leak on ESP32-C3.
  esp_deep_sleep_start();
}

static bool wifi_connect() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(200);
  }
  return WiFi.status() == WL_CONNECTED;
}

static void draw_status(const x4::CyclePlan& plan) {
  display.setRotation(3);
  display.setTextColor(GxEPD_BLACK);
  if (plan.panel == x4::PanelAction::Full) {
    display.setFullWindow();
  } else {
    display.setPartialWindow(0, 0, display.width(), display.height());
  }
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setCursor(16, 48);
    display.setTextSize(3);
    if (plan.snapshot.is_running) {
      display.print("RUN ");
    }
    display.print(plan.snapshot.status);
    display.setTextSize(1);
    int y = 90;
    for (uint8_t i = 0; i < plan.snapshot.build_count; ++i) {
      display.setCursor(16, y);
      display.printf("%s %s", plan.snapshot.builds[i].status, plan.snapshot.builds[i].workflow);
      y += 18;
      if (y > 450) {
        break;
      }
    }
    for (uint8_t i = 0; i < plan.snapshot.open_pr_count; ++i) {
      if (y > 450) {
        break;
      }
      display.setCursor(16, y);
      display.printf("%u PRs %s", static_cast<unsigned>(plan.snapshot.open_prs[i].pr_count),
                     plan.snapshot.open_prs[i].repo);
      y += 18;
    }
  } while (display.nextPage());
}

static int fetch_snapshot(String* body, String* etag, String* retry_after) {
  HTTPClient http;
  WiFiClient client;
  WiFiClientSecure secure;
#if STATUS_HTTPS
  // Bring-up only: replace with the Worker certificate for a real install.
  secure.setInsecure();
  WiFiClient& stream = secure;
#else
  WiFiClient& stream = client;
#endif
  String url;
#if STATUS_HTTPS
  url = String("https://") + STATUS_HOST + STATUS_PATH;
#else
  url = String("http://") + STATUS_HOST + STATUS_PATH;
#endif
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);
  http.begin(stream, url);
  http.addHeader("Accept", "application/json");
  http.addHeader("User-Agent", USER_AGENT);
  const char* header_keys[] = {"ETag", "Retry-After"};
  http.collectHeaders(header_keys, 2);
  if (last_etag[0] != '\0') {
    http.addHeader("If-None-Match", last_etag);
  }
  const int code = http.GET();
  *retry_after = http.header("Retry-After");
  *etag = http.header("ETag");
  if (code == 200) {
    *body = http.getString();
  }
  http.end();
  return code;
}

static void apply_plan(const x4::CyclePlan& plan, const char* etag) {
  fail_streak = plan.fail_streak;
  updates_since_full = plan.updates_since_full;
  if (plan.store_etag) {
    x4::copy_etag(last_etag, sizeof(last_etag), etag);
  }
  if (plan.panel != x4::PanelAction::Leave) {
    draw_status(plan);
  }
  enter_deep_sleep(plan.sleep_seconds);
}

void setup() {
  pinMode(POWER_BUTTON_GPIO, INPUT);
  pinMode(USB_DETECT_GPIO, INPUT);
  pinMode(BAT_GPIO, INPUT);
  Serial.begin(115200);

  SPI.begin(EPD_SCLK, /*miso=*/-1, EPD_MOSI, EPD_CS);
  SPISettings spi_settings(40000000, MSBFIRST, SPI_MODE0);
  display.init(115200, true, 2, false, SPI, spi_settings);

  const bool charging = is_charging();
  if (!wifi_connect()) {
    apply_plan(x4::plan_cycle(fail_streak, updates_since_full, {0, nullptr, nullptr, nullptr}, charging),
               nullptr);
  }

  String body;
  String etag;
  String retry_after;
  const int code = fetch_snapshot(&body, &etag, &retry_after);
  const x4::Fetch fetch = {code, retry_after.c_str(), etag.c_str(), body.c_str()};
  apply_plan(x4::plan_cycle(fail_streak, updates_since_full, fetch, charging), etag.c_str());
}

void loop() {
  // Unreachable: setup() always deep-sleeps.
}
