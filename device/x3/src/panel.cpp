#include "panel.hpp"

#include <Fonts/FreeSans12pt7b.h>
#include <Fonts/FreeSans9pt7b.h>
#include <Fonts/FreeSansBold9pt7b.h>
#include <Fonts/FreeSansBold12pt7b.h>
#include <Fonts/FreeSansBold18pt7b.h>
#include <Fonts/FreeSansBold24pt7b.h>
#include <GxEPD2_BW.h>
#include <cstdio>
#include <cstring>

#include "GxEPD2_368_X3.h"
#include "status_view.hpp"

#define EPD_CS 21
#define EPD_DC 4
#define EPD_RST 5
#define EPD_BUSY 6

namespace {

GxEPD2_BW<GxEPD2_368_X3, 16> display(GxEPD2_368_X3(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

void draw_centered(const GFXfont* font, int16_t baseline, const char* text) {
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

void print_clipped(int16_t x, int16_t y, int16_t max_w, const char* text) {
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

int16_t draw_chip(int16_t x, int16_t baseline, const char* label, bool filled) {
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

void draw_section(int16_t x, int16_t y, const char* label, unsigned count) {
  display.setFont(&FreeSans9pt7b);
  display.setCursor(x, y);
  display.printf("%s  %u", label, count);
}

}  // namespace

void panel_init(SPIClass& spi, const SPISettings& settings) {
  display.init(0, true, 15, false, spi, settings);
}

void panel_draw_notice(const char* title) {
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

void panel_draw_status(const x4::CyclePlan& plan) {
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
  const bool alarm = x4::attention_status(plan.snapshot.status);
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
    draw_centered(&FreeSansBold24pt7b, plan.snapshot.is_running ? 62 : 68, x4::hero_label(plan.snapshot.status));
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
        draw_chip(margin, y, x4::chip_label(row.status), x4::chip_filled(row.status));
        display.setFont(&FreeSansBold12pt7b);
        print_clipped(name_x, y, name_w, x4::job_title(row));
        if (x4::job_shows_workflow(row)) {
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
        print_clipped(name_x, y, name_w, x4::repo_leaf(plan.snapshot.open_prs[i].repo));
        y += 40;
      }
    }
    if (plan.snapshot.build_count == 0 && plan.snapshot.open_pr_count == 0) {
      display.setFont(&FreeSans12pt7b);
      display.setCursor(margin, y);
      display.print(x4::empty_body(alarm));
    }
    char sleep_label[16];
    x4::format_sleep(sleep_label, sizeof(sleep_label), plan.sleep_seconds);
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
