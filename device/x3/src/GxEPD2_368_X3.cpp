#include "GxEPD2_368_X3.h"

namespace {

// Stock X3 UC81xx LUTs (OEM 5.x dump). 7 phases × 6 bytes.
const uint8_t kLutVcomFull[] = {
    0x00, 0x08, 0x0B, 0x02, 0x03, 0x01, 0x00, 0x0C, 0x02, 0x07, 0x02, 0x01, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutWwFull[] = {
    0xA8, 0x08, 0x0B, 0x02, 0x03, 0x01, 0x44, 0x0C, 0x02, 0x07, 0x02, 0x01, 0x04, 0x01, 0x00, 0x02, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutBwFull[] = {
    0x80, 0x08, 0x0B, 0x02, 0x03, 0x01, 0x62, 0x0C, 0x02, 0x07, 0x02, 0x01, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutWbFull[] = {
    0x88, 0x08, 0x0B, 0x02, 0x03, 0x01, 0x60, 0x0C, 0x02, 0x07, 0x02, 0x01, 0x00, 0x01, 0x00, 0x02, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutBbFull[] = {
    0x00, 0x08, 0x0B, 0x02, 0x03, 0x01, 0x4A, 0x0C, 0x02, 0x07, 0x02, 0x01, 0x88, 0x01, 0x00, 0x02, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

const uint8_t kLutVcomTurbo[] = {
    0x00, 0x18, 0x04, 0x0E, 0x0A, 0x01, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutWwTurbo[] = {
    0x4A, 0x18, 0x04, 0x0E, 0x0A, 0x01, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutBwTurbo[] = {
    0x0A, 0x18, 0x04, 0x0E, 0x0A, 0x01, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutWbTurbo[] = {
    0x04, 0x18, 0x04, 0x0E, 0x0A, 0x01, 0x40, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};
const uint8_t kLutBbTurbo[] = {
    0x84, 0x18, 0x04, 0x0E, 0x0A, 0x01, 0x40, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
};

static_assert(sizeof(kLutVcomFull) == 42 && sizeof(kLutBbTurbo) == 42, "UC8253 LUT is 42 bytes");

}  // namespace

GxEPD2_368_X3::GxEPD2_368_X3(int16_t cs, int16_t dc, int16_t rst, int16_t busy)
    : GxEPD2_EPD(cs, dc, rst, busy, LOW, 10000000, WIDTH, HEIGHT, panel, hasColor, hasPartialUpdate,
                 hasFastPartialUpdate) {}

void GxEPD2_368_X3::clearScreen(uint8_t value) {
  writeScreenBuffer(value);
  refresh(true);
  writeScreenBufferAgain(value);
}

void GxEPD2_368_X3::writeScreenBuffer(uint8_t value) {
  _initial_write = false;
  _InitDisplay();
  _writeScreenBuffer(0x13, value);
  _writeScreenBuffer(0x10, 0xFF);
}

void GxEPD2_368_X3::writeScreenBufferAgain(uint8_t value) { _writeScreenBuffer(0x10, value); }

void GxEPD2_368_X3::_writeScreenBuffer(uint8_t command, uint8_t value) {
  _writeCommand(command);
  for (uint32_t i = 0; i < uint32_t(WIDTH) * HEIGHT / 8; ++i) {
    _writeData(value);
  }
}

void GxEPD2_368_X3::_writeLut(uint8_t command, const uint8_t* lut) {
  _writeCommand(command);
  for (uint8_t i = 0; i < 42; ++i) {
    _writeData(lut[i]);
  }
}

void GxEPD2_368_X3::_loadFullLuts() {
  _writeLut(0x20, kLutVcomFull);
  _writeLut(0x21, kLutWwFull);
  _writeLut(0x22, kLutBwFull);
  _writeLut(0x23, kLutWbFull);
  _writeLut(0x24, kLutBbFull);
}

void GxEPD2_368_X3::_loadTurboLuts() {
  _writeLut(0x20, kLutVcomTurbo);
  _writeLut(0x21, kLutWwTurbo);
  _writeLut(0x22, kLutBwTurbo);
  _writeLut(0x23, kLutWbTurbo);
  _writeLut(0x24, kLutBbTurbo);
}

void GxEPD2_368_X3::_writeImage(uint8_t command, const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h,
                                bool invert, bool mirror_y, bool pgm) {
  if (bitmap == nullptr) {
    return;
  }
  if (_initial_write) {
    writeScreenBuffer();
  }
  delay(1);
  int16_t wb = (w + 7) / 8;
  x -= x % 8;
  w = wb * 8;
  int16_t x1 = x < 0 ? 0 : x;
  int16_t y1 = y < 0 ? 0 : y;
  int16_t w1 = x + w < int16_t(WIDTH) ? w : int16_t(WIDTH) - x;
  int16_t h1 = y + h < int16_t(HEIGHT) ? h : int16_t(HEIGHT) - y;
  int16_t dx = x1 - x;
  int16_t dy = y1 - y;
  w1 -= dx;
  h1 -= dy;
  if ((w1 <= 0) || (h1 <= 0)) {
    return;
  }
  _writeCommand(0x91);
  _setPartialRamArea(static_cast<uint16_t>(x1), static_cast<uint16_t>(y1), static_cast<uint16_t>(w1),
                     static_cast<uint16_t>(h1));
  _writeCommand(command);
  for (int16_t i = 0; i < h1; i++) {
    for (int16_t j = 0; j < w1 / 8; j++) {
      uint8_t data;
      int16_t idx = j + dx / 8 + int16_t(mirror_y ? (h - (i + dy) - 1) : (i + dy)) * wb;
      if (pgm) {
#ifdef ESP8266
        data = pgm_read_byte(&bitmap[idx]);
#else
        data = bitmap[idx];
#endif
      } else {
        data = bitmap[idx];
      }
      if (invert) {
        data = ~data;
      }
      _writeData(data);
    }
  }
  _writeCommand(0x92);
  delay(1);
}

void GxEPD2_368_X3::_setPartialRamArea(uint16_t x, uint16_t y, uint16_t w, uint16_t h) {
  const uint16_t xe = (x + w - 1) | 0x0007;
  const uint16_t ye = y + h - 1;
  x &= 0xFFF8;
  _writeCommand(0x90);
  _writeData(x / 256);
  _writeData(x % 256);
  _writeData(xe / 256);
  _writeData(xe % 256);
  _writeData(y / 256);
  _writeData(y % 256);
  _writeData(ye / 256);
  _writeData(ye % 256);
  _writeData(0x01);
}

void GxEPD2_368_X3::writeImage(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                               bool mirror_y, bool pgm) {
  _writeImage(0x13, bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImageForFullRefresh(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h,
                                             bool invert, bool mirror_y, bool pgm) {
  _writeImage(0x13, bitmap, x, y, w, h, invert, mirror_y, pgm);
  _writeImage(0x10, bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImageToPrevious(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h,
                                         bool invert, bool mirror_y, bool pgm) {
  _writeImage(0x10, bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImageAgain(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                                    bool mirror_y, bool pgm) {
  _writeImage(0x10, bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImagePart(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap,
                                   int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                                   bool mirror_y, bool pgm) {
  (void)x_part;
  (void)y_part;
  (void)w_bitmap;
  (void)h_bitmap;
  writeImage(bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImagePartToPrevious(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap,
                                             int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                                             bool mirror_y, bool pgm) {
  (void)x_part;
  (void)y_part;
  (void)w_bitmap;
  (void)h_bitmap;
  writeImageToPrevious(bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImagePartAgain(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap,
                                        int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                                        bool mirror_y, bool pgm) {
  (void)x_part;
  (void)y_part;
  (void)w_bitmap;
  (void)h_bitmap;
  writeImageAgain(bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImage(const uint8_t* black, const uint8_t* color, int16_t x, int16_t y, int16_t w, int16_t h,
                               bool invert, bool mirror_y, bool pgm) {
  (void)color;
  writeImage(black, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeImagePart(const uint8_t* black, const uint8_t* color, int16_t x_part, int16_t y_part,
                                   int16_t w_bitmap, int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h,
                                   bool invert, bool mirror_y, bool pgm) {
  (void)color;
  writeImagePart(black, x_part, y_part, w_bitmap, h_bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::writeNative(const uint8_t* data1, const uint8_t* data2, int16_t x, int16_t y, int16_t w, int16_t h,
                                bool invert, bool mirror_y, bool pgm) {
  (void)data2;
  writeImage(data1, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::drawImage(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                              bool mirror_y, bool pgm) {
  writeImage(bitmap, x, y, w, h, invert, mirror_y, pgm);
  refresh(x, y, w, h);
  writeImageAgain(bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::drawImagePart(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap,
                                  int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                                  bool mirror_y, bool pgm) {
  writeImagePart(bitmap, x_part, y_part, w_bitmap, h_bitmap, x, y, w, h, invert, mirror_y, pgm);
  refresh(x, y, w, h);
  writeImagePartAgain(bitmap, x_part, y_part, w_bitmap, h_bitmap, x, y, w, h, invert, mirror_y, pgm);
}

void GxEPD2_368_X3::drawImage(const uint8_t* black, const uint8_t* color, int16_t x, int16_t y, int16_t w, int16_t h,
                              bool invert, bool mirror_y, bool pgm) {
  writeImage(black, color, x, y, w, h, invert, mirror_y, pgm);
  refresh(x, y, w, h);
}

void GxEPD2_368_X3::drawImagePart(const uint8_t* black, const uint8_t* color, int16_t x_part, int16_t y_part,
                                  int16_t w_bitmap, int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h,
                                  bool invert, bool mirror_y, bool pgm) {
  writeImagePart(black, color, x_part, y_part, w_bitmap, h_bitmap, x, y, w, h, invert, mirror_y, pgm);
  refresh(x, y, w, h);
}

void GxEPD2_368_X3::drawNative(const uint8_t* data1, const uint8_t* data2, int16_t x, int16_t y, int16_t w, int16_t h,
                               bool invert, bool mirror_y, bool pgm) {
  writeNative(data1, data2, x, y, w, h, invert, mirror_y, pgm);
  refresh(x, y, w, h);
}

void GxEPD2_368_X3::refresh(bool partial_update_mode) {
  if (partial_update_mode) {
    _Update_Part();
  } else {
    _Update_Full();
  }
}

void GxEPD2_368_X3::refresh(int16_t x, int16_t y, int16_t w, int16_t h) {
  (void)x;
  (void)y;
  (void)w;
  (void)h;
  _Update_Part();
}

void GxEPD2_368_X3::powerOff() { _PowerOff(); }

void GxEPD2_368_X3::hibernate() {
  _PowerOff();
  if (_rst >= 0) {
    _writeCommand(0x07);
    _writeData(0xA5);
    _hibernating = true;
  }
}

void GxEPD2_368_X3::_PowerOn() {
  if (!_power_is_on) {
    _writeCommand(0x04);
    _waitWhileBusy("_PowerOn", power_on_time);
  }
  _power_is_on = true;
}

void GxEPD2_368_X3::_PowerOff() {
  if (_power_is_on) {
    _writeCommand(0x02);
    _waitWhileBusy("_PowerOff", power_off_time);
  }
  _power_is_on = false;
  _using_partial_mode = false;
}

void GxEPD2_368_X3::_InitDisplay() {
  if (_hibernating) {
    _reset();
  }
  delay(10);
  _waitWhileBusy("_InitDisplay", 100);
  _writeCommand(0x00);
  _writeData(0x3F);
  _writeData(0x0A);
  _writeCommand(0x61);
  _writeData(WIDTH / 256);
  _writeData(WIDTH % 256);
  _writeData(0x02);
  _writeData(0x58);
  _waitWhileBusy("_Resolution", 100);
  _writeCommand(0x65);
  _writeData(0x00);
  _writeData(0x00);
  _writeData(0x00);
  _writeData(0x00);
  _writeCommand(0x03);
  _writeData(0x20);
  _writeCommand(0x01);
  _writeData(0x07);
  _writeData(0x17);
  _writeData(0x3F);
  _writeData(0x3F);
  _writeData(0x17);
  _writeCommand(0x82);
  _writeData(0x24);
  _writeCommand(0x06);
  _writeData(0x25);
  _writeData(0x25);
  _writeData(0x3C);
  _writeData(0x37);
  _writeCommand(0x30);
  _writeData(0x09);
  _writeCommand(0xE1);
  _writeData(0x02);
}

void GxEPD2_368_X3::_Update_Full() {
  _writeCommand(0x50);
  _writeData(0xA9);
  _writeData(0x07);
  _loadFullLuts();
  _PowerOn();
  _writeCommand(0x12);
  _waitWhileBusy("_Update_Full", full_refresh_time);
  _using_partial_mode = false;
}

void GxEPD2_368_X3::_Update_Part() {
  _loadTurboLuts();
  _writeCommand(0x50);
  _writeData(0x29);
  _writeData(0x07);
  _PowerOn();
  _writeCommand(0x12);
  _waitWhileBusy("_Update_Part", partial_refresh_time);
  _using_partial_mode = true;
}
