#include "client.hpp"

#include <cstdio>
#include <cstring>

namespace x4 {

bool should_send_if_none_match(const char* etag, bool usb_plugged, bool button_refresh) {
  return etag != nullptr && etag[0] != '\0' && !usb_plugged && !button_refresh;
}

CyclePlan present_for_panel(CyclePlan plan, bool usb_plugged, uint8_t* button_refresh, int http_code) {
  if (button_refresh != nullptr && *button_refresh != 0) {
    *button_refresh = 0;
    plan.panel = PanelAction::Full;
  }
  if (usb_plugged) {
    plan.panel = PanelAction::Full;
    if (http_code != 200 || std::strcmp(plan.snapshot.status, "UNKNOWN") == 0) {
      std::snprintf(plan.snapshot.status, kStatusCap, "HTTP %d", http_code);
    }
  }
  return plan;
}

uint32_t desk_idle_seconds(uint32_t planned, bool usb_plugged) {
  return apply_usb_sleep_cap(planned, usb_plugged);
}

}  // namespace x4
