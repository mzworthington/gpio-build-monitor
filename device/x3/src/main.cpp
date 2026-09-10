#include <Arduino.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <esp_sleep.h>
#include <esp_wifi.h>

#include "bq27220.hpp"
#include "client.hpp"
#include "duty_cycle.hpp"
#include "panel.hpp"
#include "power_control.hpp"

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
#define KEY_ADC_GPIO 1
#define KEY_ADC_GPIO_B 2
#define KEY_ADC_IDLE 3999
#define POWER_LATCH_GPIO 13
#define I2C_SCL 0
#define I2C_SDA 20
#define BQ27220_ADDR 0x55
#define BQ27220_CURRENT 0x0C
#define SPI_HZ 10000000
#define USER_AGENT "gpio-build-monitor-x3/0.1 (+https://github.com/mzworthington/gpio-build-monitor)"
#define WIFI_TIMEOUT_MS 15000
#define HTTP_TIMEOUT_MS 10000

RTC_DATA_ATTR char last_etag[x4::kEtagCap] = "";
RTC_DATA_ATTR uint8_t fail_streak = 0;
RTC_DATA_ATTR uint8_t updates_since_full = 0;
RTC_DATA_ATTR uint8_t button_refresh = 0;

static x4::ButtonSample last_buttons = {};

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

static bool page_key_pressed() {
  return analogRead(KEY_ADC_GPIO) < KEY_ADC_IDLE || analogRead(KEY_ADC_GPIO_B) < KEY_ADC_IDLE;
}

static bool power_button_down() { return digitalRead(POWER_BUTTON_GPIO) == LOW; }

static x4::ButtonSample read_buttons() { return {power_button_down(), page_key_pressed()}; }

static void wait_power_button_release() {
  const unsigned long start = millis();
  while (power_button_down() && millis() - start < 4000) {
    delay(20);
  }
}

static void radio_off() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

static void hold_power_latch() {
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis(static_cast<gpio_num_t>(POWER_LATCH_GPIO));
  pinMode(POWER_LATCH_GPIO, OUTPUT);
  digitalWrite(POWER_LATCH_GPIO, HIGH);
}

static void power_down();
static x4::ButtonIntent poll_buttons();

static bool wifi_connect() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  delay(100);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    if (poll_buttons() == x4::ButtonIntent::PowerOff) {
      power_down();
    }
    delay(200);
  }
  const bool ok = WiFi.status() == WL_CONNECTED;
  Serial.printf("wifi %s\n", ok ? "up" : "down");
  return ok;
}

static void power_down() {
  Serial.println("power down");
  Serial.flush();
  radio_off();
  panel_draw_notice("Off");
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  while (!x4::may_drop_latch(power_button_down())) {
    delay(20);
  }
  Serial.end();

  const gpio_num_t latch = static_cast<gpio_num_t>(POWER_LATCH_GPIO);
  gpio_set_direction(latch, GPIO_MODE_OUTPUT);
  gpio_set_level(latch, 0);
  esp_sleep_config_gpio_isolate();
  gpio_deep_sleep_hold_en();
  gpio_hold_en(latch);
  pinMode(POWER_BUTTON_GPIO, INPUT_PULLUP);
  esp_deep_sleep_enable_gpio_wakeup(1ULL << POWER_BUTTON_GPIO, ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
}

static x4::ButtonIntent poll_buttons() {
  const x4::ButtonSample now = read_buttons();
  const x4::ButtonIntent intent = x4::button_intent(now, last_buttons);
  last_buttons = now;
  return intent;
}

static bool handle_idle_buttons() {
  const x4::ButtonIntent intent = poll_buttons();
  if (intent == x4::ButtonIntent::PowerOff) {
    power_down();
  }
  if (intent == x4::ButtonIntent::Refresh) {
    Serial.println("page key");
    Serial.flush();
    last_etag[0] = '\0';
    button_refresh = 1;
    panel_draw_notice("Refreshing");
    return true;
  }
  return false;
}

static void wait_for_next(uint32_t seconds) {
  seconds = x4::desk_idle_seconds(seconds, HWCDC::isPlugged());
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  radio_off();
  Serial.printf("wait %u s\n", seconds);
  Serial.flush();
  last_buttons = read_buttons();
  if (x4::idle_path(HWCDC::isPlugged()) == x4::IdlePath::UsbPoll) {
    const unsigned long until = millis() + static_cast<unsigned long>(seconds) * 1000UL;
    while (static_cast<long>(until - millis()) > 0) {
      if (handle_idle_buttons()) {
        return;
      }
      delay(20);
    }
    return;
  }
  uint32_t left_ms = seconds * 1000UL;
  while (left_ms > 0) {
    if (handle_idle_buttons()) {
      return;
    }
    const uint32_t slice = left_ms > 100 ? 100 : left_ms;
    gpio_wakeup_enable(static_cast<gpio_num_t>(POWER_BUTTON_GPIO), GPIO_INTR_LOW_LEVEL);
    esp_sleep_enable_gpio_wakeup();
    esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(slice) * 1000ULL);
    esp_light_sleep_start();
    left_ms -= slice;
  }
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
  if (x4::should_send_if_none_match(last_etag, HWCDC::isPlugged(), button_refresh != 0)) {
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
  const x4::CyclePlan to_draw = x4::present_for_panel(plan, HWCDC::isPlugged(), &button_refresh, http_code);
  if (to_draw.panel != x4::PanelAction::Leave) {
    Serial.println("panel draw");
    panel_draw_status(to_draw);
    Serial.println("panel done");
  } else {
    Serial.println("panel skip");
  }
  wait_for_next(plan.sleep_seconds);
}

void setup() {
  pinMode(POWER_BUTTON_GPIO, INPUT_PULLUP);
  analogSetAttenuation(ADC_11db);
  analogReadResolution(12);
  hold_power_latch();
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
  panel_init(SPI, SPISettings(SPI_HZ, MSBFIRST, SPI_MODE0));
  wait_power_button_release();
  last_buttons = read_buttons();
}

void loop() {
  const bool charging = bq27220::is_charging(read_charge_current_ma());
  if (!wifi_connect()) {
    apply_plan(x4::plan_cycle(fail_streak, updates_since_full, {0, nullptr, nullptr, nullptr}, charging),
               nullptr, 0);
    return;
  }

  String body;
  String etag;
  String retry_after;
  const int code = fetch_snapshot(&body, &etag, &retry_after);
  const x4::Fetch fetch = {code, retry_after.c_str(), etag.c_str(), body.c_str()};
  apply_plan(x4::plan_cycle(fail_streak, updates_since_full, fetch, charging), etag.c_str(), code);
}
