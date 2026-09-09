#pragma once

#include <GxEPD2_EPD.h>

// Xteink X3 3.68" 792×528 UC8253. Same EPD GPIOs as the X4; 10 MHz SPI.
class GxEPD2_368_X3 : public GxEPD2_EPD {
 public:
  static const uint16_t WIDTH = 792;
  static const uint16_t WIDTH_VISIBLE = WIDTH;
  static const uint16_t HEIGHT = 528;
  static const GxEPD2::Panel panel = GxEPD2::GDEQ0426T82;
  static const bool hasColor = false;
  static const bool hasPartialUpdate = true;
  static const bool hasFastPartialUpdate = true;
  static const uint16_t power_on_time = 150;
  static const uint16_t power_off_time = 200;
  static const uint16_t full_refresh_time = 900;
  static const uint16_t partial_refresh_time = 450;

  GxEPD2_368_X3(int16_t cs, int16_t dc, int16_t rst, int16_t busy);
  void clearScreen(uint8_t value = 0xFF);
  void writeScreenBuffer(uint8_t value = 0xFF);
  void writeScreenBufferAgain(uint8_t value = 0xFF);
  void writeImage(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                  bool mirror_y = false, bool pgm = false);
  void writeImageForFullRefresh(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h,
                                bool invert = false, bool mirror_y = false, bool pgm = false);
  void writeImageToPrevious(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h,
                            bool invert = false, bool mirror_y = false, bool pgm = false);
  void writeImagePart(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap, int16_t h_bitmap,
                      int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false, bool mirror_y = false,
                      bool pgm = false);
  void writeImagePartToPrevious(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap,
                                int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                                bool mirror_y = false, bool pgm = false);
  void writeImage(const uint8_t* black, const uint8_t* color, int16_t x, int16_t y, int16_t w, int16_t h,
                  bool invert = false, bool mirror_y = false, bool pgm = false);
  void writeImagePart(const uint8_t* black, const uint8_t* color, int16_t x_part, int16_t y_part, int16_t w_bitmap,
                      int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                      bool mirror_y = false, bool pgm = false);
  void writeImageAgain(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                       bool mirror_y = false, bool pgm = false);
  void writeImagePartAgain(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap, int16_t h_bitmap,
                           int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false, bool mirror_y = false,
                           bool pgm = false);
  void writeNative(const uint8_t* data1, const uint8_t* data2, int16_t x, int16_t y, int16_t w, int16_t h,
                   bool invert = false, bool mirror_y = false, bool pgm = false);
  void drawImage(const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                 bool mirror_y = false, bool pgm = false);
  void drawImagePart(const uint8_t bitmap[], int16_t x_part, int16_t y_part, int16_t w_bitmap, int16_t h_bitmap,
                     int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false, bool mirror_y = false,
                     bool pgm = false);
  void drawImage(const uint8_t* black, const uint8_t* color, int16_t x, int16_t y, int16_t w, int16_t h,
                 bool invert = false, bool mirror_y = false, bool pgm = false);
  void drawImagePart(const uint8_t* black, const uint8_t* color, int16_t x_part, int16_t y_part, int16_t w_bitmap,
                     int16_t h_bitmap, int16_t x, int16_t y, int16_t w, int16_t h, bool invert = false,
                     bool mirror_y = false, bool pgm = false);
  void drawNative(const uint8_t* data1, const uint8_t* data2, int16_t x, int16_t y, int16_t w, int16_t h,
                  bool invert = false, bool mirror_y = false, bool pgm = false);
  void refresh(bool partial_update_mode = false);
  void refresh(int16_t x, int16_t y, int16_t w, int16_t h);
  void powerOff();
  void hibernate();

 private:
  void _writeScreenBuffer(uint8_t command, uint8_t value);
  void _writeImage(uint8_t command, const uint8_t bitmap[], int16_t x, int16_t y, int16_t w, int16_t h, bool invert,
                   bool mirror_y, bool pgm);
  void _writeLut(uint8_t command, const uint8_t* lut);
  void _loadFullLuts();
  void _loadTurboLuts();
  void _setPartialRamArea(uint16_t x, uint16_t y, uint16_t w, uint16_t h);
  void _PowerOn();
  void _PowerOff();
  void _InitDisplay();
  void _Update_Full();
  void _Update_Part();
};
