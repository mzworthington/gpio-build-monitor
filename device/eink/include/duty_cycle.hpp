#pragma once

#include <cstddef>
#include <cstdint>

namespace eink {

constexpr std::size_t kStatusCap = 24;
constexpr std::size_t kWorkflowCap = 64;
constexpr std::size_t kMaxBuilds = 16;
constexpr std::size_t kMaxRepos = 16;
constexpr std::size_t kRepoCap = 48;
constexpr uint8_t kMaxOpenPrs = 8;

struct BuildRow {
  char status[kStatusCap];
  char workflow[kWorkflowCap];
  char repo[kRepoCap];
};

struct OpenPrRow {
  char repo[kRepoCap];
  uint32_t pr_count;
};

struct RepoRow {
  char repo[kRepoCap];
  char status[kStatusCap];
  uint32_t workflow_count;
  uint32_t pr_count;
  bool is_running;
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
  RepoRow repos[kMaxRepos];
  uint8_t repo_count;
};

bool parse_snapshot(const char* json, Snapshot* out);

}  // namespace eink
