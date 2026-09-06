#include <Arduino.h>
#include <ArduinoJson.h>
#include <GxEPD2_BW.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <cstring>
#include <esp_sleep.h>
#include <esp_wifi.h>

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
#define MAX_SLEEP_SECONDS 1800
#define DEFAULT_SLEEP_SECONDS 900
#define FETCH_ERROR_SLEEP_SECONDS 300
#define FULL_REFRESH_EVERY 8

GxEPD2_BW<GxEPD2_426_GDEQ0426T82, GxEPD2_426_GDEQ0426T82::HEIGHT> display(
    GxEPD2_426_GDEQ0426T82(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

RTC_DATA_ATTR char last_etag[40] = "";
RTC_DATA_ATTR uint8_t fail_streak = 0;
RTC_DATA_ATTR uint8_t updates_since_full = 0;

static void store_etag(const String &etag) {
  if (etag.length() == 0 || etag.length() >= sizeof(last_etag)) {
    return;
  }
  strncpy(last_etag, etag.c_str(), sizeof(last_etag) - 1);
  last_etag[sizeof(last_etag) - 1] = '\0';
}

static uint32_t backoff_sleep(uint32_t base) {
  uint32_t seconds = base << fail_streak;
  if (seconds > MAX_SLEEP_SECONDS) {
    seconds = MAX_SLEEP_SECONDS;
  }
  return seconds;
}

static void radio_off() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

static void enter_deep_sleep(uint32_t seconds) {
  radio_off();
  if (digitalRead(USB_DETECT_GPIO) == HIGH && seconds > 60) {
    seconds = 60;
  }
  Serial.printf("deep sleep %u s\n", seconds);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
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

static void draw_status(const char *status, bool is_running, JsonArray builds, int http_code) {
  display.setRotation(3);
  display.setTextColor(GxEPD_BLACK);
  const bool full = http_code == 200 && (updates_since_full >= FULL_REFRESH_EVERY || strcmp(status, "FAIL") == 0);
  if (full) {
    display.setFullWindow();
    updates_since_full = 0;
  } else {
    display.setPartialWindow(0, 0, display.width(), display.height());
    updates_since_full++;
  }
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    display.setCursor(16, 48);
    display.setTextSize(3);
    if (is_running) {
      display.print("RUN ");
    }
    display.print(status);
    display.setTextSize(1);
    int y = 90;
    for (JsonObject build : builds) {
      display.setCursor(16, y);
      display.printf("%s %s", build["status"] | "?", build["workflow"] | "?");
      y += 18;
      if (y > 450) {
        break;
      }
    }
  } while (display.nextPage());
}

static int fetch_snapshot(String *body, String *etag, uint32_t *sleep_seconds) {
  HTTPClient http;
  WiFiClient client;
  WiFiClientSecure secure;
#if STATUS_HTTPS
  // Bring-up only: replace with the Worker certificate for a real install.
  secure.setInsecure();
  WiFiClient &stream = secure;
#else
  WiFiClient &stream = client;
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
  const char *header_keys[] = {"ETag", "Retry-After"};
  http.collectHeaders(header_keys, 2);
  if (last_etag[0] != '\0') {
    http.addHeader("If-None-Match", last_etag);
  }
  const int code = http.GET();
  const String retry = http.header("Retry-After");
  if (retry.length() > 0) {
    *sleep_seconds = retry.toInt();
  }
  const String new_etag = http.header("ETag");
  if (new_etag.length() > 0 && new_etag.length() < sizeof(last_etag)) {
    *etag = new_etag;
  }
  if (code == 200) {
    *body = http.getString();
  }
  http.end();
  return code;
}

void setup() {
  pinMode(POWER_BUTTON_GPIO, INPUT);
  pinMode(USB_DETECT_GPIO, INPUT);
  pinMode(BAT_GPIO, INPUT);
  Serial.begin(115200);

  SPI.begin(EPD_SCLK, /*miso=*/-1, EPD_MOSI, EPD_CS);
  SPISettings spi_settings(40000000, MSBFIRST, SPI_MODE0);
  display.init(115200, true, 2, false, SPI, spi_settings);

  uint32_t sleep_seconds = DEFAULT_SLEEP_SECONDS;
  if (!wifi_connect()) {
    fail_streak = fail_streak + 1 > 4 ? 4 : fail_streak + 1;
    enter_deep_sleep(backoff_sleep(FETCH_ERROR_SLEEP_SECONDS));
  }

  String body;
  String etag;
  const int code = fetch_snapshot(&body, &etag, &sleep_seconds);
  if (code == 304) {
    fail_streak = 0;
    store_etag(etag);
    enter_deep_sleep(sleep_seconds > 0 ? sleep_seconds : DEFAULT_SLEEP_SECONDS);
  }
  if (code != 200) {
    fail_streak = fail_streak + 1 > 4 ? 4 : fail_streak + 1;
    enter_deep_sleep(backoff_sleep(sleep_seconds > 0 ? sleep_seconds : DEFAULT_SLEEP_SECONDS));
  }

  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, body);
  if (err) {
    fail_streak = fail_streak + 1 > 4 ? 4 : fail_streak + 1;
    enter_deep_sleep(backoff_sleep(DEFAULT_SLEEP_SECONDS));
  }

  fail_streak = 0;
  const char *status = doc["status"] | "UNKNOWN";
  const bool is_running = doc["is_running"] | false;
  if (doc["sleep_seconds"].is<uint32_t>()) {
    sleep_seconds = doc["sleep_seconds"].as<uint32_t>();
  }
  draw_status(status, is_running, doc["builds"].as<JsonArray>(), code);
  store_etag(etag);
  enter_deep_sleep(sleep_seconds > 0 ? sleep_seconds : DEFAULT_SLEEP_SECONDS);
}

void loop() {
  // Unreachable: setup() always deep-sleeps.
}
