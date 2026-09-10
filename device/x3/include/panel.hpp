#pragma once

#include "duty_cycle.hpp"

#include <SPI.h>

void panel_init(SPIClass& spi, const SPISettings& settings);
void panel_draw_status(const x4::CyclePlan& plan);
void panel_draw_notice(const char* title);
