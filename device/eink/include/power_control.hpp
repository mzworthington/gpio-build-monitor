#pragma once

namespace x4 {

struct ButtonSample {
  bool power_down;
  bool page_down;
};

enum class ButtonIntent { None, Refresh, PowerOff };

inline ButtonIntent button_intent(const ButtonSample& now, const ButtonSample& prev) {
  if (now.power_down && !prev.power_down) {
    return ButtonIntent::PowerOff;
  }
  if (now.page_down && !prev.page_down) {
    return ButtonIntent::Refresh;
  }
  return ButtonIntent::None;
}

inline bool may_drop_latch(bool power_still_down) { return !power_still_down; }

enum class IdlePath { UsbPoll, BatteryLightSleep };

inline IdlePath idle_path(bool usb_plugged) {
  return usb_plugged ? IdlePath::UsbPoll : IdlePath::BatteryLightSleep;
}

}  // namespace x4
