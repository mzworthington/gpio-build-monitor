#pragma once

#include <cstddef>
#include <cstdint>

namespace x4 {

constexpr uint32_t kMaxSleepSeconds = 1800;
constexpr uint32_t kDefaultSleepSeconds = 900;
constexpr uint32_t kFetchErrorSleepSeconds = 300;
constexpr uint32_t kUsbDeskSleepSeconds = 60;
constexpr uint8_t kMaxFailStreak = 4;
constexpr uint8_t kFullRefreshEvery = 8;
constexpr std::size_t kEtagCap = 40;
constexpr std::size_t kStatusCap = 24;
constexpr std::size_t kWorkflowCap = 64;
constexpr std::size_t kMaxBuilds = 16;
constexpr std::size_t kRepoCap = 48;
constexpr uint8_t kMaxOpenPrs = 8;

uint8_t bump_fail_streak(uint8_t fail_streak);
uint32_t backoff_sleep(uint32_t base, uint8_t fail_streak);
uint32_t apply_usb_sleep_cap(uint32_t seconds, bool charging);
bool copy_etag(char* dest, std::size_t dest_cap, const char* etag);
uint32_t parse_retry_after(const char* header);

struct BuildRow {
  char status[kStatusCap];
  char workflow[kWorkflowCap];
};

struct OpenPrRow {
  char repo[kRepoCap];
  uint32_t pr_count;
};

struct Snapshot {
  char status[kStatusCap];
  bool is_running;
  uint32_t sleep_seconds;
  bool has_sleep_seconds;
  BuildRow builds[kMaxBuilds];
  uint8_t build_count;
  OpenPrRow open_prs[kMaxOpenPrs];
  uint8_t open_pr_count;
};

bool parse_snapshot(const char* json, Snapshot* out);

struct Fetch {
  int http_code;  // 0 = radio / connect failed
  const char* retry_after;
  const char* etag;
  const char* body;
};

enum class PanelAction {
  Leave,
  Partial,
  Full,
};

struct CyclePlan {
  PanelAction panel;
  uint32_t sleep_seconds;
  uint8_t fail_streak;
  uint8_t updates_since_full;
  bool store_etag;
  Snapshot snapshot;
};

CyclePlan plan_cycle(
    uint8_t fail_streak,
    uint8_t updates_since_full,
    const Fetch& fetch,
    bool charging);

}  // namespace x4
