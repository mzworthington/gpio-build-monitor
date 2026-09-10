#pragma once

#include "duty_cycle.hpp"

#include <cstdio>
#include <cstring>

namespace eink {

inline bool attention_status(const char* status) {
  return std::strcmp(status, "FAIL") == 0 || std::strcmp(status, "UNKNOWN") == 0 ||
         std::strcmp(status, "APPROVAL") == 0 || std::strcmp(status, "CONNECTION_ERROR") == 0 ||
         std::strncmp(status, "HTTP", 4) == 0;
}

inline const char* hero_label(const char* status) {
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

inline const char* chip_label(const char* status) {
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

inline bool has_name(const char* value) {
  return value != nullptr && value[0] != '\0' && std::strcmp(value, "?") != 0;
}

inline const char* repo_leaf(const char* repo) {
  const char* slash = std::strrchr(repo, '/');
  if (slash != nullptr && slash[1] != '\0') {
    return slash + 1;
  }
  return repo;
}

inline const char* job_title(const BuildRow& row) {
  return has_name(row.repo) ? repo_leaf(row.repo) : row.workflow;
}

inline bool job_shows_workflow(const BuildRow& row) {
  return has_name(row.repo) && has_name(row.workflow);
}

inline bool chip_filled(const char* status) {
  return attention_status(status) || std::strcmp(status, "FAIL") == 0;
}

inline const char* empty_body(bool alarm) { return alarm ? "No detail in snapshot" : "All clear"; }

inline void format_sleep(char* dest, std::size_t cap, uint32_t seconds) {
  if (seconds >= 120) {
    std::snprintf(dest, cap, "%u min", static_cast<unsigned>((seconds + 30) / 60));
  } else {
    std::snprintf(dest, cap, "%u s", static_cast<unsigned>(seconds));
  }
}

inline constexpr std::size_t kLineCap = kStatusCap + kWorkflowCap + 2;

struct MonitorLine {
  char title[kWorkflowCap];
  char subtitle[kLineCap];
};

inline constexpr uint8_t kMaxMonitorLines = 1 + (kMaxRepos > kMaxWorkflowsPerRepo ? kMaxRepos : kMaxWorkflowsPerRepo);

inline const char* count_label(uint32_t n, const char* one, const char* many) { return n == 1 ? one : many; }

inline void format_repo_counts(char* dest, std::size_t cap, const RepoRow& row) {
  std::snprintf(dest, cap, "%s · %u %s · %u %s", chip_label(row.status),
                static_cast<unsigned>(row.workflow_count), count_label(row.workflow_count, "action", "actions"),
                static_cast<unsigned>(row.pr_count), count_label(row.pr_count, "PR", "PRs"));
}

inline void format_chip_workflow(char* dest, std::size_t cap, const char* status, const char* workflow) {
  std::snprintf(dest, cap, "%s %s", chip_label(status), workflow);
}

inline int8_t repo_from_monitor_index(int list_index, uint8_t repo_count) {
  if (list_index <= 0) {
    return -1;
  }
  const int idx = list_index - 1;
  if (idx >= static_cast<int>(repo_count)) {
    return -1;
  }
  return static_cast<int8_t>(idx);
}

inline uint8_t fill_repo_action_lines(const Snapshot& snap, uint8_t repo_index, MonitorLine* out, uint8_t cap) {
  if (out == nullptr || cap == 0 || repo_index >= snap.repo_count) {
    return 0;
  }
  const RepoRow& row = snap.repos[repo_index];
  uint8_t n = 0;
  std::snprintf(out[n].title, sizeof(out[n].title), "%s", row.repo);
  format_repo_counts(out[n].subtitle, sizeof(out[n].subtitle), row);
  ++n;
  for (uint8_t i = 0; i < row.workflow_n && n < cap; ++i) {
    std::snprintf(out[n].title, sizeof(out[n].title), "%s", row.workflows[i].workflow);
    std::snprintf(out[n].subtitle, sizeof(out[n].subtitle), "%s", chip_label(row.workflows[i].status));
    ++n;
  }
  return n;
}

inline uint8_t fill_monitor_lines(const Snapshot& snap, MonitorLine* out, uint8_t cap) {
  if (out == nullptr || cap == 0) {
    return 0;
  }
  uint8_t n = 0;
  std::snprintf(out[n].title, sizeof(out[n].title), "%s", hero_label(snap.status));
  if (snap.repo_count == 0 && snap.build_count == 0 && snap.open_pr_count == 0) {
    std::snprintf(out[n].subtitle, sizeof(out[n].subtitle), "%s", empty_body(attention_status(snap.status)));
  } else if (snap.has_sleep_seconds) {
    format_sleep(out[n].subtitle, sizeof(out[n].subtitle), snap.sleep_seconds);
  } else {
    out[n].subtitle[0] = '\0';
  }
  ++n;
  if (snap.repo_count > 0) {
    for (uint8_t i = 0; i < snap.repo_count && n < cap; ++i) {
      std::snprintf(out[n].title, sizeof(out[n].title), "%s", snap.repos[i].repo);
      format_repo_counts(out[n].subtitle, sizeof(out[n].subtitle), snap.repos[i]);
      ++n;
    }
    return n;
  }
  for (uint8_t i = 0; i < snap.build_count && n < cap; ++i) {
    std::snprintf(out[n].title, sizeof(out[n].title), "%s", job_title(snap.builds[i]));
    if (job_shows_workflow(snap.builds[i])) {
      format_chip_workflow(out[n].subtitle, sizeof(out[n].subtitle), snap.builds[i].status,
                           snap.builds[i].workflow);
    } else {
      std::snprintf(out[n].subtitle, sizeof(out[n].subtitle), "%s", chip_label(snap.builds[i].status));
    }
    ++n;
  }
  for (uint8_t i = 0; i < snap.open_pr_count && n < cap; ++i) {
    std::snprintf(out[n].title, sizeof(out[n].title), "%s", repo_leaf(snap.open_prs[i].repo));
    std::snprintf(out[n].subtitle, sizeof(out[n].subtitle), "%u open",
                  static_cast<unsigned>(snap.open_prs[i].pr_count));
    ++n;
  }
  return n;
}

}  // namespace eink
