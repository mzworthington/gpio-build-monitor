#pragma once

#include "duty_cycle.hpp"

#include <cstdint>

namespace x4 {

bool should_send_if_none_match(const char* etag, bool usb_plugged, bool button_refresh);
CyclePlan present_for_panel(CyclePlan plan, bool usb_plugged, uint8_t* button_refresh, int http_code);
uint32_t desk_idle_seconds(uint32_t planned, bool usb_plugged);

}  // namespace x4
