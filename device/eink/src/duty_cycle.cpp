#include "duty_cycle.hpp"

#include <cctype>
#include <cstdint>
#include <cstring>

namespace x4 {
namespace {

void set_default_snapshot(Snapshot* out) {
  std::strcpy(out->status, "UNKNOWN");
  out->is_running = false;
  out->sleep_seconds = 0;
  out->has_sleep_seconds = false;
  out->build_count = 0;
  out->open_pr_count = 0;
}

const char* skip_ws(const char* p) {
  while (p && *p && std::isspace(static_cast<unsigned char>(*p))) {
    ++p;
  }
  return p;
}

bool parse_string(const char** pp, char* dest, std::size_t cap) {
  const char* p = skip_ws(*pp);
  if (*p != '"') {
    return false;
  }
  ++p;
  std::size_t n = 0;
  while (*p && *p != '"') {
    char ch = *p++;
    if (ch == '\\') {
      if (*p == '\0') {
        return false;
      }
      ch = *p++;
    }
    if (dest != nullptr && cap > 0 && n + 1 < cap) {
      dest[n++] = ch;
    } else if (dest == nullptr) {
      ++n;
    }
  }
  if (*p != '"') {
    return false;
  }
  if (dest != nullptr && cap > 0) {
    dest[n] = '\0';
  }
  *pp = p + 1;
  return true;
}

bool parse_bool(const char** pp, bool* out) {
  const char* p = skip_ws(*pp);
  if (std::strncmp(p, "true", 4) == 0 && !std::isalnum(static_cast<unsigned char>(p[4]))) {
    *out = true;
    *pp = p + 4;
    return true;
  }
  if (std::strncmp(p, "false", 5) == 0 && !std::isalnum(static_cast<unsigned char>(p[5]))) {
    *out = false;
    *pp = p + 5;
    return true;
  }
  return false;
}

bool parse_uint(const char** pp, uint32_t* out) {
  const char* p = skip_ws(*pp);
  if (*p < '0' || *p > '9') {
    return false;
  }
  uint32_t value = 0;
  while (*p >= '0' && *p <= '9') {
    uint32_t digit = static_cast<uint32_t>(*p - '0');
    if (value > (UINT32_MAX - digit) / 10) {
      return false;
    }
    value = value * 10 + digit;
    ++p;
  }
  *out = value;
  *pp = p;
  return true;
}

bool skip_string(const char** pp) { return parse_string(pp, nullptr, 0); }

bool skip_value(const char** pp);

bool skip_number(const char** pp) {
  const char* p = skip_ws(*pp);
  if (*p == '-') {
    ++p;
  }
  if (*p < '0' || *p > '9') {
    return false;
  }
  while (*p >= '0' && *p <= '9') {
    ++p;
  }
  if (*p == '.') {
    ++p;
    if (*p < '0' || *p > '9') {
      return false;
    }
    while (*p >= '0' && *p <= '9') {
      ++p;
    }
  }
  if (*p == 'e' || *p == 'E') {
    ++p;
    if (*p == '+' || *p == '-') {
      ++p;
    }
    if (*p < '0' || *p > '9') {
      return false;
    }
    while (*p >= '0' && *p <= '9') {
      ++p;
    }
  }
  *pp = p;
  return true;
}

bool skip_object_or_array(const char** pp, char open_ch, char close_ch) {
  const char* p = skip_ws(*pp);
  if (*p != open_ch) {
    return false;
  }
  ++p;
  *pp = p;
  p = skip_ws(*pp);
  if (*p == close_ch) {
    *pp = p + 1;
    return true;
  }
  while (*p) {
    if (open_ch == '{') {
      if (!skip_string(pp)) {
        return false;
      }
      p = skip_ws(*pp);
      if (*p != ':') {
        return false;
      }
      *pp = p + 1;
    }
    if (!skip_value(pp)) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p == ',') {
      *pp = p + 1;
      p = skip_ws(*pp);
      continue;
    }
    if (*p == close_ch) {
      *pp = p + 1;
      return true;
    }
    return false;
  }
  return false;
}

bool skip_value(const char** pp) {
  const char* p = skip_ws(*pp);
  if (*p == '"') {
    return skip_string(pp);
  }
  if (*p == '{') {
    return skip_object_or_array(pp, '{', '}');
  }
  if (*p == '[') {
    return skip_object_or_array(pp, '[', ']');
  }
  if (std::strncmp(p, "true", 4) == 0) {
    *pp = p + 4;
    return true;
  }
  if (std::strncmp(p, "false", 5) == 0) {
    *pp = p + 5;
    return true;
  }
  if (std::strncmp(p, "null", 4) == 0) {
    *pp = p + 4;
    return true;
  }
  if (*p == '-' || (*p >= '0' && *p <= '9')) {
    return skip_number(pp);
  }
  return false;
}

bool parse_build_object(const char** pp, BuildRow* row) {
  const char* p = skip_ws(*pp);
  if (*p != '{') {
    return false;
  }
  ++p;
  *pp = p;
  std::strcpy(row->status, "?");
  std::strcpy(row->workflow, "?");
  p = skip_ws(*pp);
  if (*p == '}') {
    *pp = p + 1;
    return true;
  }
  while (*p) {
    char key[24];
    if (!parse_string(pp, key, sizeof(key))) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p != ':') {
      return false;
    }
    *pp = p + 1;
    if (std::strcmp(key, "status") == 0) {
      if (!parse_string(pp, row->status, sizeof(row->status))) {
        return false;
      }
    } else if (std::strcmp(key, "workflow") == 0) {
      if (!parse_string(pp, row->workflow, sizeof(row->workflow))) {
        return false;
      }
    } else if (!skip_value(pp)) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p == ',') {
      *pp = p + 1;
      p = skip_ws(*pp);
      continue;
    }
    if (*p == '}') {
      *pp = p + 1;
      return true;
    }
    return false;
  }
  return false;
}

bool parse_builds(const char** pp, Snapshot* out) {
  const char* p = skip_ws(*pp);
  if (*p != '[') {
    return false;
  }
  ++p;
  *pp = p;
  p = skip_ws(*pp);
  if (*p == ']') {
    *pp = p + 1;
    return true;
  }
  while (*p) {
    if (out->build_count < kMaxBuilds) {
      if (!parse_build_object(pp, &out->builds[out->build_count])) {
        return false;
      }
      ++out->build_count;
    } else if (!skip_value(pp)) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p == ',') {
      *pp = p + 1;
      p = skip_ws(*pp);
      continue;
    }
    if (*p == ']') {
      *pp = p + 1;
      return true;
    }
    return false;
  }
  return false;
}

bool parse_open_pr_object(const char** pp, OpenPrRow* row) {
  const char* p = skip_ws(*pp);
  if (*p != '{') {
    return false;
  }
  ++p;
  *pp = p;
  std::strcpy(row->repo, "?");
  row->pr_count = 0;
  p = skip_ws(*pp);
  if (*p == '}') {
    *pp = p + 1;
    return true;
  }
  while (*p) {
    char key[24];
    if (!parse_string(pp, key, sizeof(key))) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p != ':') {
      return false;
    }
    *pp = p + 1;
    if (std::strcmp(key, "repo") == 0) {
      if (!parse_string(pp, row->repo, sizeof(row->repo))) {
        return false;
      }
    } else if (std::strcmp(key, "pr_count") == 0) {
      if (!parse_uint(pp, &row->pr_count)) {
        return false;
      }
    } else if (!skip_value(pp)) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p == ',') {
      *pp = p + 1;
      p = skip_ws(*pp);
      continue;
    }
    if (*p == '}') {
      *pp = p + 1;
      return true;
    }
    return false;
  }
  return false;
}

bool parse_open_prs(const char** pp, Snapshot* out) {
  const char* p = skip_ws(*pp);
  if (*p != '[') {
    return false;
  }
  ++p;
  *pp = p;
  p = skip_ws(*pp);
  if (*p == ']') {
    *pp = p + 1;
    return true;
  }
  while (*p) {
    if (out->open_pr_count < kMaxOpenPrs) {
      if (!parse_open_pr_object(pp, &out->open_prs[out->open_pr_count])) {
        return false;
      }
      ++out->open_pr_count;
    } else if (!skip_value(pp)) {
      return false;
    }
    p = skip_ws(*pp);
    if (*p == ',') {
      *pp = p + 1;
      p = skip_ws(*pp);
      continue;
    }
    if (*p == ']') {
      *pp = p + 1;
      return true;
    }
    return false;
  }
  return false;
}

}  // namespace

uint8_t bump_fail_streak(uint8_t fail_streak) {
  if (fail_streak >= kMaxFailStreak) {
    return kMaxFailStreak;
  }
  return static_cast<uint8_t>(fail_streak + 1);
}

uint32_t backoff_sleep(uint32_t base, uint8_t fail_streak) {
  uint32_t seconds = base;
  if (fail_streak >= 32) {
    return kMaxSleepSeconds;
  }
  seconds = base << fail_streak;
  if (seconds < base || seconds > kMaxSleepSeconds) {
    return kMaxSleepSeconds;
  }
  return seconds;
}

uint32_t apply_usb_sleep_cap(uint32_t seconds, bool charging) {
  if (charging && seconds > kUsbDeskSleepSeconds) {
    return kUsbDeskSleepSeconds;
  }
  return seconds;
}

bool copy_etag(char* dest, std::size_t dest_cap, const char* etag) {
  if (dest == nullptr || dest_cap == 0 || etag == nullptr || etag[0] == '\0') {
    return false;
  }
  const std::size_t len = std::strlen(etag);
  if (len >= dest_cap) {
    return false;
  }
  std::memcpy(dest, etag, len + 1);
  return true;
}

uint32_t parse_retry_after(const char* header) {
  if (header == nullptr || header[0] == '\0') {
    return 0;
  }
  const char* p = header;
  uint32_t value = 0;
  if (!parse_uint(&p, &value)) {
    return 0;
  }
  return value;
}

bool parse_snapshot(const char* json, Snapshot* out) {
  if (out == nullptr || json == nullptr) {
    return false;
  }
  set_default_snapshot(out);
  const char* p = skip_ws(json);
  if (*p != '{') {
    return false;
  }
  ++p;
  p = skip_ws(p);
  if (*p == '}') {
    return true;
  }
  while (*p) {
    char key[32];
    if (!parse_string(&p, key, sizeof(key))) {
      return false;
    }
    p = skip_ws(p);
    if (*p != ':') {
      return false;
    }
    ++p;
    if (std::strcmp(key, "status") == 0) {
      if (!parse_string(&p, out->status, sizeof(out->status))) {
        return false;
      }
    } else if (std::strcmp(key, "is_running") == 0) {
      if (!parse_bool(&p, &out->is_running)) {
        return false;
      }
    } else if (std::strcmp(key, "sleep_seconds") == 0) {
      uint32_t seconds = 0;
      if (!parse_uint(&p, &seconds)) {
        return false;
      }
      out->sleep_seconds = seconds;
      out->has_sleep_seconds = true;
    } else if (std::strcmp(key, "builds") == 0) {
      if (!parse_builds(&p, out)) {
        return false;
      }
    } else if (std::strcmp(key, "open_prs") == 0) {
      if (!parse_open_prs(&p, out)) {
        return false;
      }
    } else if (!skip_value(&p)) {
      return false;
    }
    p = skip_ws(p);
    if (*p == ',') {
      ++p;
      p = skip_ws(p);
      continue;
    }
    if (*p == '}') {
      return true;
    }
    return false;
  }
  return false;
}

CyclePlan plan_cycle(
    uint8_t fail_streak,
    uint8_t updates_since_full,
    const Fetch& fetch,
    bool charging) {
  CyclePlan plan = {};
  plan.panel = PanelAction::Leave;
  plan.fail_streak = fail_streak;
  plan.updates_since_full = updates_since_full;
  plan.store_etag = false;
  set_default_snapshot(&plan.snapshot);

  auto finish = [&](uint32_t seconds) {
    if (seconds == 0) {
      seconds = kDefaultSleepSeconds;
    }
    plan.sleep_seconds = apply_usb_sleep_cap(seconds, charging);
    return plan;
  };

  if (fetch.http_code == 0) {
    plan.fail_streak = bump_fail_streak(fail_streak);
    if (fail_streak == 0) {
      plan.panel = PanelAction::Full;
      std::strcpy(plan.snapshot.status, "NO WIFI");
    }
    return finish(backoff_sleep(kFetchErrorSleepSeconds, plan.fail_streak));
  }

  const uint32_t retry = parse_retry_after(fetch.retry_after);
  uint32_t sleep = retry;

  if (fetch.http_code == 304) {
    plan.fail_streak = 0;
    plan.store_etag = true;
    return finish(sleep);
  }

  if (fetch.http_code != 200) {
    plan.fail_streak = bump_fail_streak(fail_streak);
    const uint32_t base = retry != 0 ? retry : kDefaultSleepSeconds;
    return finish(backoff_sleep(base, plan.fail_streak));
  }

  if (!parse_snapshot(fetch.body, &plan.snapshot)) {
    plan.fail_streak = bump_fail_streak(fail_streak);
    return finish(backoff_sleep(kDefaultSleepSeconds, plan.fail_streak));
  }

  plan.fail_streak = 0;
  plan.store_etag = true;
  if (plan.snapshot.has_sleep_seconds && plan.snapshot.sleep_seconds > 0) {
    sleep = plan.snapshot.sleep_seconds;
  }
  const bool full =
      updates_since_full >= kFullRefreshEvery || std::strcmp(plan.snapshot.status, "FAIL") == 0;
  plan.panel = full ? PanelAction::Full : PanelAction::Partial;
  plan.updates_since_full = full ? 0 : static_cast<uint8_t>(updates_since_full + 1);
  return finish(sleep);
}

}  // namespace x4
