#include <Arduino.h>
#include <GxEPD2_BW.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <cstdio>
#include <cstring>
#include <esp_sleep.h>
#include <esp_wifi.h>

#include "GxEPD2_368_X3.h"
#include "bq27220.hpp"
#include "duty_cycle.hpp"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.h.example"
#endif

#define EPD_SCLK 8
#define EPD_MOSI 10
#define EPD_MISO 7
#define EPD_CS 21
#define EPD_DC 4
#define EPD_RST 5
#define EPD_BUSY 6
#define SD_CS_GPIO 12
#define POWER_BUTTON_GPIO 3
#define POWER_LATCH_GPIO 13
#define I2C_SCL 0
#define I2C_SDA 20
#define BQ27220_ADDR 0x55
#define BQ27220_CURRENT 0x0C
#define SPI_HZ 10000000
#define USER_AGENT "gpio-build-monitor-x3/0.1 (+https://github.com/mzworthington/gpio-build-monitor)"
#define WIFI_TIMEOUT_MS 15000
#define HTTP_TIMEOUT_MS 10000

GxEPD2_BW<GxEPD2_368_X3, 16> display(GxEPD2_368_X3(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

RTC_DATA_ATTR char last_etag[x4::kEtagCap] = "";
RTC_DATA_ATTR uint8_t fail_streak = 0;
RTC_DATA_ATTR uint8_t updates_since_full = 0;

static int16_t read_charge_current_ma() {
  Wire.beginTransmission(BQ27220_ADDR);
  Wire.write(BQ27220_CURRENT);
  if (Wire.endTransmission(false) != 0) {
    return 0;
  }
  if (Wire.requestFrom(BQ27220_ADDR, static_cast<uint8_t>(2)) != 2) {
    return 0;
  }
  const uint8_t lo = static_cast<uint8_t>(Wire.read());
  const uint8_t hi = static_cast<uint8_t>(Wire.read());
  return static_cast<int16_t>(uint16_t(lo) | (uint16_t(hi) << 8));
}

static bool is_charging() { return bq27220::is_charging(read_charge_current_ma()); }

static void radio_off() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

static void enter_deep_sleep(uint32_t seconds) {
  if (HWCDC::isPlugged() && seconds > x4::kUsbDeskSleepSeconds) {
    seconds = x4::kUsbDeskSleepSeconds;
  }
  radio_off();
  Serial.printf("deep sleep %u s\n", seconds);
  Serial.flush();
  // Native USB CDC drops in deep sleep; stay in a timed restart while a host is
  // enumerated so `pio run -t upload` can find /dev/cu.usbmodem*.
  if (HWCDC::isPlugged()) {
    Serial.printf("usb hold %u s\n", seconds);
    Serial.flush();
    delay(static_cast<unsigned long>(seconds) * 1000UL);
    ESP.restart();
  }
  esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(seconds) * 1000000ULL);
  esp_deep_sleep_enable_gpio_wakeup(1ULL << POWER_BUTTON_GPIO, ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
}

static bool wifi_connect() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  delay(100);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(200);
  }
  const bool ok = WiFi.status() == WL_CONNECTED;
  Serial.printf("wifi %s\n", ok ? "up" : "down");
  return ok;
}

static void draw_status(const x4::CyclePlan& plan) {
  display.setRotation(0);
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
    const int y_limit = display.height() - 16;
    int y = 90;
    for (uint8_t i = 0; i < plan.snapshot.build_count; ++i) {
      display.setCursor(16, y);
      display.printf("%s %s", plan.snapshot.builds[i].status, plan.snapshot.builds[i].workflow);
      y += 18;
      if (y > y_limit) {
        break;
      }
    }
    for (uint8_t i = 0; i < plan.snapshot.open_pr_count; ++i) {
      if (y > y_limit) {
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
  if (last_etag[0] != '\0' && !HWCDC::isPlugged()) {
    http.addHeader("If-None-Match", last_etag);
  }
  const int code = http.GET();
  Serial.printf("http %d\n", code);
  *retry_after = http.header("Retry-After");
  *etag = http.header("ETag");
  if (code == 200) {
    *body = http.getString();
  }
  http.end();
  return code;
}

static void apply_plan(const x4::CyclePlan& plan, const char* etag, int http_code) {
  fail_streak = plan.fail_streak;
  updates_since_full = plan.updates_since_full;
  if (plan.store_etag) {
    x4::copy_etag(last_etag, sizeof(last_etag), etag);
  }
  x4::CyclePlan to_draw = plan;
  if (HWCDC::isPlugged()) {
    to_draw.panel = x4::PanelAction::Full;
    if (http_code != 200 || std::strcmp(to_draw.snapshot.status, "UNKNOWN") == 0) {
      std::snprintf(to_draw.snapshot.status, x4::kStatusCap, "HTTP %d", http_code);
    }
  }
  if (to_draw.panel != x4::PanelAction::Leave) {
    Serial.println("panel draw");
    draw_status(to_draw);
    Serial.println("panel done");
  } else {
    Serial.println("panel skip");
  }
  enter_deep_sleep(plan.sleep_seconds);
}

void setup() {
  pinMode(POWER_BUTTON_GPIO, INPUT);
  pinMode(POWER_LATCH_GPIO, OUTPUT);
  digitalWrite(POWER_LATCH_GPIO, HIGH);
  pinMode(SD_CS_GPIO, OUTPUT);
  digitalWrite(SD_CS_GPIO, HIGH);
  pinMode(EPD_CS, OUTPUT);
  pinMode(EPD_DC, OUTPUT);
  pinMode(EPD_RST, OUTPUT);
  pinMode(EPD_BUSY, INPUT);
  digitalWrite(EPD_CS, HIGH);
  digitalWrite(EPD_DC, HIGH);
  digitalWrite(EPD_RST, HIGH);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(400000);
  Serial.begin(115200);

  SPI.begin(EPD_SCLK, EPD_MISO, EPD_MOSI, /*ss=*/-1);
  SPISettings spi_settings(SPI_HZ, MSBFIRST, SPI_MODE0);
  display.init(0, true, 15, false, SPI, spi_settings);

  const bool charging = is_charging();
  if (!wifi_connect()) {
    apply_plan(x4::plan_cycle(fail_streak, updates_since_full, {0, nullptr, nullptr, nullptr}, charging),
               nullptr, 0);
  }

  String body;
  String etag;
  String retry_after;
  const int code = fetch_snapshot(&body, &etag, &retry_after);
  const x4::Fetch fetch = {code, retry_after.c_str(), etag.c_str(), body.c_str()};
  apply_plan(x4::plan_cycle(fail_streak, updates_since_full, fetch, charging), etag.c_str(), code);
}

void loop() {}
