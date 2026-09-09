#include <Arduino.h>
#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>
#include <Fonts/FreeSansBold18pt7b.h>
#include <Fonts/FreeSansBold24pt7b.h>
#include <GxEPD2_BW.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <cstdio>
#include <cstring>
#include <driver/gpio.h>
#include <esp_sleep.h>
#include <esp_wifi.h>

#include "GxEPD2_368_X3.h"
#include "bq27220.hpp"
#include "duty_cycle.hpp"
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

GxEPD2_BW<GxEPD2_368_X3, 16> display(GxEPD2_368_X3(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

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

static bool is_charging() { return bq27220::is_charging(read_charge_current_ma()); }

static void radio_off() {
  WiFi.disconnect(true, true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

static bool page_key_pressed() {
  return analogRead(KEY_ADC_GPIO) < KEY_ADC_IDLE || analogRead(KEY_ADC_GPIO_B) < KEY_ADC_IDLE;
}

static bool power_button_down() { return digitalRead(POWER_BUTTON_GPIO) == LOW; }

static x4::ButtonSample read_buttons() {
  return {power_button_down(), page_key_pressed()};
}

static void wait_power_button_release() {
  const unsigned long start = millis();
  while (power_button_down() && millis() - start < 4000) {
    delay(20);
  }
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

static bool attention_status(const char* status) {
  return std::strcmp(status, "FAIL") == 0 || std::strcmp(status, "UNKNOWN") == 0 ||
         std::strcmp(status, "APPROVAL") == 0 || std::strcmp(status, "CONNECTION_ERROR") == 0 ||
         std::strncmp(status, "HTTP", 4) == 0;
}

static const char* hero_label(const char* status) {
  if (std::strcmp(status, "NONE") == 0) {
    return "Idle";
  }
  if (std::strcmp(status, "PASS") == 0) {
    return "Pass";
  }
  if (std::strcmp(status, "FAIL") == 0) {
    return "Fail";
  }
  if (std::strcmp(status, "UNKNOWN") == 0) {
    return "Unknown";
  }
  if (std::strcmp(status, "APPROVAL") == 0) {
    return "Hold";
  }
  if (std::strcmp(status, "CONNECTION_ERROR") == 0) {
    return "Offline";
  }
  return status;
}

static const char* chip_label(const char* status) {
  if (std::strcmp(status, "FAIL") == 0) {
    return "FAIL";
  }
  if (std::strcmp(status, "RUNNING") == 0) {
    return "RUN";
  }
  if (std::strcmp(status, "WAITING") == 0) {
    return "WAIT";
  }
  if (std::strcmp(status, "APPROVAL") == 0) {
    return "HOLD";
  }
  if (std::strcmp(status, "CONNECTION_ERROR") == 0) {
    return "ERR";
  }
  if (std::strcmp(status, "UNKNOWN") == 0) {
    return "?";
  }
  if (std::strcmp(status, "PASS") == 0) {
    return "OK";
  }
  return status;
}

static bool has_name(const char* value) { return value != nullptr && value[0] != '\0' && std::strcmp(value, "?") != 0; }

static const char* repo_leaf(const char* repo) {
  const char* slash = std::strrchr(repo, '/');
  if (slash != nullptr && slash[1] != '\0') {
    return slash + 1;
  }
  return repo;
}

static void draw_centered(const GFXfont* font, int16_t baseline, const char* text) {
  display.setFont(font);
  int16_t x1 = 0;
  int16_t y1 = 0;
  uint16_t w = 0;
  uint16_t h = 0;
  display.getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  if (w + 40 > display.width()) {
    display.setFont(&FreeSansBold18pt7b);
    display.getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  }
  display.setCursor((display.width() - static_cast<int16_t>(w)) / 2 - x1, baseline);
  display.print(text);
}

static void draw_fast_notice(const char* title) {
  display.setRotation(1);
  display.setTextSize(1);
  display.setPartialWindow(0, 0, display.width(), 48);
  display.firstPage();
  do {
    display.fillScreen(GxEPD_BLACK);
    display.setTextColor(GxEPD_WHITE);
    display.setFont(&FreeSansBold12pt7b);
    int16_t x1 = 0;
    int16_t y1 = 0;
    uint16_t tw = 0;
    uint16_t th = 0;
    display.getTextBounds(title, 0, 0, &x1, &y1, &tw, &th);
    display.setCursor((display.width() - static_cast<int16_t>(tw)) / 2 - x1, 32);
    display.print(title);
  } while (display.nextPage());
}

static void hold_power_latch() {
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis(static_cast<gpio_num_t>(POWER_LATCH_GPIO));
  pinMode(POWER_LATCH_GPIO, OUTPUT);
  digitalWrite(POWER_LATCH_GPIO, HIGH);
}

static void power_down() {
  Serial.println("power down");
  Serial.flush();
  radio_off();
  draw_fast_notice("Off");
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
    draw_fast_notice("Refreshing");
    return true;
  }
  return false;
}

static void wait_for_next(uint32_t seconds) {
  if (HWCDC::isPlugged() && seconds > x4::kUsbDeskSleepSeconds) {
    seconds = x4::kUsbDeskSleepSeconds;
  }
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

static void print_clipped(int16_t x, int16_t y, int16_t max_w, const char* text) {
  int16_t x1 = 0;
  int16_t y1 = 0;
  uint16_t w = 0;
  uint16_t h = 0;
  display.getTextBounds(text, 0, 0, &x1, &y1, &w, &h);
  display.setCursor(x, y);
  if (static_cast<int16_t>(w) <= max_w) {
    display.print(text);
    return;
  }
  char buf[x4::kRepoCap];
  std::size_t n = std::strlen(text);
  if (n >= sizeof(buf) - 2) {
    n = sizeof(buf) - 3;
  }
  std::memcpy(buf, text, n);
  buf[n] = '\0';
  while (n > 1) {
    buf[n] = '.';
    buf[n + 1] = '.';
    buf[n + 2] = '\0';
    display.getTextBounds(buf, 0, 0, &x1, &y1, &w, &h);
    if (static_cast<int16_t>(w) <= max_w) {
      display.setCursor(x, y);
      display.print(buf);
      return;
    }
    --n;
    buf[n] = '\0';
  }
  display.setCursor(x, y);
  display.print(buf);
}

static int16_t draw_chip(int16_t x, int16_t baseline, const char* label, bool filled) {
  display.setFont(&FreeSansBold9pt7b);
  int16_t x1 = 0;
  int16_t y1 = 0;
  uint16_t tw = 0;
  uint16_t th = 0;
  display.getTextBounds(label, 0, 0, &x1, &y1, &tw, &th);
  const int16_t pad_x = 8;
  const int16_t pad_y = 5;
  const int16_t box_x = x;
  const int16_t box_y = baseline + y1 - pad_y;
  const int16_t box_w = static_cast<int16_t>(tw) + 2 * pad_x;
  const int16_t box_h = static_cast<int16_t>(th) + 2 * pad_y;
  if (filled) {
    display.fillRoundRect(box_x, box_y, box_w, box_h, 4, GxEPD_BLACK);
    display.setTextColor(GxEPD_WHITE);
  } else {
    display.drawRoundRect(box_x, box_y, box_w, box_h, 4, GxEPD_BLACK);
    display.setTextColor(GxEPD_BLACK);
  }
  display.setCursor(box_x + pad_x - x1, baseline);
  display.print(label);
  display.setTextColor(GxEPD_BLACK);
  return box_w;
}

static void draw_section(int16_t x, int16_t y, const char* label, unsigned count) {
  display.setFont(&FreeSans9pt7b);
  display.setCursor(x, y);
  display.printf("%s  %u", label, count);
}

static void format_sleep(char* dest, std::size_t cap, uint32_t seconds) {
  if (seconds >= 120) {
    std::snprintf(dest, cap, "%u min", static_cast<unsigned>((seconds + 30) / 60));
  } else {
    std::snprintf(dest, cap, "%u s", static_cast<unsigned>(seconds));
  }
}

static void draw_status(const x4::CyclePlan& plan) {
  display.setRotation(1);
  display.setTextSize(1);
  if (plan.panel == x4::PanelAction::Full) {
    display.setFullWindow();
  } else {
    display.setPartialWindow(0, 0, display.width(), display.height());
  }
  const int16_t w = display.width();
  const int16_t h = display.height();
  const int16_t margin = 24;
  const bool alarm = attention_status(plan.snapshot.status);
  const int16_t header_h = plan.snapshot.is_running ? 118 : 100;
  const int16_t chip_col = 78;
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    if (alarm) {
      display.fillRect(0, 0, w, header_h, GxEPD_BLACK);
      display.setTextColor(GxEPD_WHITE);
    } else {
      display.setTextColor(GxEPD_BLACK);
      display.fillRect(0, header_h - 4, w, 4, GxEPD_BLACK);
    }
    draw_centered(&FreeSansBold24pt7b, plan.snapshot.is_running ? 62 : 68, hero_label(plan.snapshot.status));
    if (plan.snapshot.is_running) {
      display.setFont(&FreeSans9pt7b);
      int16_t x1 = 0;
      int16_t y1 = 0;
      uint16_t tw = 0;
      uint16_t th = 0;
      display.getTextBounds("Running", 0, 0, &x1, &y1, &tw, &th);
      display.setCursor((w - static_cast<int16_t>(tw)) / 2 - x1, 96);
      display.print("Running");
    }
    display.setTextColor(GxEPD_BLACK);
    int16_t y = header_h + 36;
    const int16_t y_limit = h - 36;
    const int16_t name_x = margin + chip_col;
    const int16_t name_w = w - name_x - margin;
    if (plan.snapshot.build_count > 0) {
      draw_section(margin, y, "Jobs", plan.snapshot.build_count);
      y += 34;
      for (uint8_t i = 0; i < plan.snapshot.build_count; ++i) {
        if (y + 28 > y_limit) {
          break;
        }
        const x4::BuildRow& row = plan.snapshot.builds[i];
        const bool filled = attention_status(row.status) || std::strcmp(row.status, "FAIL") == 0;
        draw_chip(margin, y, chip_label(row.status), filled);
        display.setFont(&FreeSansBold12pt7b);
        const char* title = has_name(row.repo) ? repo_leaf(row.repo) : row.workflow;
        print_clipped(name_x, y, name_w, title);
        if (has_name(row.repo) && has_name(row.workflow)) {
          y += 22;
          display.setFont(&FreeSans9pt7b);
          print_clipped(name_x, y, name_w, row.workflow);
        }
        y += 38;
      }
    }
    if (plan.snapshot.open_pr_count > 0 && y + 40 < y_limit) {
      if (plan.snapshot.build_count > 0) {
        display.drawFastHLine(margin, y - 18, w - 2 * margin, GxEPD_BLACK);
        y += 6;
      }
      draw_section(margin, y, "PRs", plan.snapshot.open_pr_count);
      y += 34;
      for (uint8_t i = 0; i < plan.snapshot.open_pr_count; ++i) {
        if (y > y_limit) {
          break;
        }
        char count[8];
        std::snprintf(count, sizeof(count), "%u", static_cast<unsigned>(plan.snapshot.open_prs[i].pr_count));
        draw_chip(margin, y, count, false);
        display.setFont(&FreeSansBold12pt7b);
        print_clipped(name_x, y, name_w, repo_leaf(plan.snapshot.open_prs[i].repo));
        y += 40;
      }
    }
    if (plan.snapshot.build_count == 0 && plan.snapshot.open_pr_count == 0) {
      display.setFont(&FreeSans12pt7b);
      display.setCursor(margin, y);
      display.print(alarm ? "No detail in snapshot" : "All clear");
    }
    char sleep_label[16];
    format_sleep(sleep_label, sizeof(sleep_label), plan.sleep_seconds);
    display.setFont(&FreeSans9pt7b);
    int16_t x1 = 0;
    int16_t y1 = 0;
    uint16_t tw = 0;
    uint16_t th = 0;
    display.getTextBounds(sleep_label, 0, 0, &x1, &y1, &tw, &th);
    display.setCursor(w - margin - static_cast<int16_t>(tw) - x1, h - 16);
    display.print(sleep_label);
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
  if (last_etag[0] != '\0' && !HWCDC::isPlugged() && button_refresh == 0) {
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
  if (button_refresh != 0) {
    button_refresh = 0;
    to_draw.panel = x4::PanelAction::Full;
  }
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
  SPISettings spi_settings(SPI_HZ, MSBFIRST, SPI_MODE0);
  display.init(0, true, 15, false, SPI, spi_settings);
  wait_power_button_release();
  last_buttons = read_buttons();
}

void loop() {
  const bool charging = is_charging();
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
