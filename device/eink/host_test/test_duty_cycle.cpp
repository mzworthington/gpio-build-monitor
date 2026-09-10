#include "bq27220.hpp"
#include "client.hpp"
#include "duty_cycle.hpp"
#include "power_control.hpp"
#include "status_view.hpp"

#include <cstdio>
#include <cstring>

namespace {

int g_checks = 0;
int g_fails = 0;

void check(bool cond, const char* expr, const char* file, int line) {
  ++g_checks;
  if (!cond) {
    ++g_fails;
    std::fprintf(stderr, "FAIL %s:%d: %s\n", file, line, expr);
  }
}

#define CHECK(cond) check(static_cast<bool>(cond), #cond, __FILE__, __LINE__)

#define CHECK_EQ(a, b) \
  do { \
    const auto _va = (a); \
    const auto _vb = (b); \
    ++g_checks; \
    if (_va != _vb) { \
      ++g_fails; \
      std::fprintf(stderr, "FAIL %s:%d: %s == %s (%u != %u)\n", __FILE__, __LINE__, #a, #b, \
                   static_cast<unsigned>(_va), static_cast<unsigned>(_vb)); \
    } \
  } while (0)

#define CHECK_STREQ(a, b) \
  do { \
    const char* _sa = (a); \
    const char* _sb = (b); \
    ++g_checks; \
    if (_sa == nullptr || _sb == nullptr || std::strcmp(_sa, _sb) != 0) { \
      ++g_fails; \
      std::fprintf(stderr, "FAIL %s:%d: %s == %s (%s != %s)\n", __FILE__, __LINE__, #a, #b, \
                   _sa ? _sa : "(null)", _sb ? _sb : "(null)"); \
    } \
  } while (0)

void test_backoff_doubles_then_caps() {
  CHECK_EQ(x4::bump_fail_streak(0), 1);
  CHECK_EQ(x4::bump_fail_streak(3), 4);
  CHECK_EQ(x4::bump_fail_streak(4), 4);
  CHECK_EQ(x4::backoff_sleep(300, 1), 600);
  CHECK_EQ(x4::backoff_sleep(300, 4), 1800);
  CHECK_EQ(x4::backoff_sleep(900, 4), 1800);
}

void test_usb_cap_only_when_charging() {
  CHECK_EQ(x4::apply_usb_sleep_cap(900, false), 900);
  CHECK_EQ(x4::apply_usb_sleep_cap(900, true), 60);
  CHECK_EQ(x4::apply_usb_sleep_cap(45, true), 45);
}

void test_copy_etag_rejects_empty_and_overflow() {
  char dest[x4::kEtagCap];
  std::memset(dest, 0x5a, sizeof(dest));
  CHECK(!x4::copy_etag(dest, sizeof(dest), nullptr));
  CHECK(!x4::copy_etag(dest, sizeof(dest), ""));
  CHECK(x4::copy_etag(dest, sizeof(dest), "W/\"abc\""));
  CHECK_STREQ(dest, "W/\"abc\"");

  char too_long[x4::kEtagCap + 8];
  std::memset(too_long, 'x', x4::kEtagCap);
  too_long[x4::kEtagCap] = '\0';
  CHECK(!x4::copy_etag(dest, sizeof(dest), too_long));
  CHECK_STREQ(dest, "W/\"abc\"");

  char exact[x4::kEtagCap];
  std::memset(exact, 'y', x4::kEtagCap - 1);
  exact[x4::kEtagCap - 1] = '\0';
  CHECK(x4::copy_etag(dest, sizeof(dest), exact));
}

void test_parse_retry_after() {
  CHECK_EQ(x4::parse_retry_after(nullptr), 0);
  CHECK_EQ(x4::parse_retry_after(""), 0);
  CHECK_EQ(x4::parse_retry_after("120"), 120);
  CHECK_EQ(x4::parse_retry_after("nope"), 0);
}

void test_parse_snapshot_compact_payload() {
  const char* json =
      "{"
      "\"type\":\"status\","
      "\"fetching\":false,"
      "\"status\":\"FAIL\","
      "\"is_running\":true,"
      "\"builds\":["
      "{\"repo\":\"acme/web\",\"workflow\":\"CI\",\"status\":\"FAIL\",\"url\":\"https://example.com/1\"},"
      "{\"repo\":\"acme/api\",\"workflow\":\"Lint\",\"status\":\"RUNNING\",\"url\":\"https://example.com/3\"}"
      "],"
      "\"poll_in_seconds\":30,"
      "\"last_checked_at\":1710000000.5,"
      "\"next_check_at\":1710000030.5,"
      "\"sleep_seconds\":120"
      "}";
  x4::Snapshot snap = {};
  CHECK(x4::parse_snapshot(json, &snap));
  CHECK_STREQ(snap.status, "FAIL");
  CHECK(snap.is_running);
  CHECK(snap.has_sleep_seconds);
  CHECK_EQ(snap.sleep_seconds, 120);
  CHECK_EQ(snap.build_count, 2);
  CHECK_STREQ(snap.builds[0].status, "FAIL");
  CHECK_STREQ(snap.builds[0].workflow, "CI");
  CHECK_STREQ(snap.builds[0].repo, "acme/web");
  CHECK_STREQ(snap.builds[1].status, "RUNNING");
  CHECK_STREQ(snap.builds[1].workflow, "Lint");
  CHECK_STREQ(snap.builds[1].repo, "acme/api");
}

void test_parse_snapshot_open_prs_when_workflows_are_green() {
  const char* json =
      "{"
      "\"status\":\"PASS\","
      "\"is_running\":false,"
      "\"builds\":[],"
      "\"open_prs\":["
      "{\"repo\":\"acme/web\",\"pr_count\":4,\"pr_url\":\"https://github.com/acme/web/pulls\"}"
      "],"
      "\"sleep_seconds\":900"
      "}";
  x4::Snapshot snap = {};
  CHECK(x4::parse_snapshot(json, &snap));
  CHECK_STREQ(snap.status, "PASS");
  CHECK_EQ(snap.build_count, 0);
  CHECK_EQ(snap.open_pr_count, 1);
  CHECK_STREQ(snap.open_prs[0].repo, "acme/web");
  CHECK_EQ(snap.open_prs[0].pr_count, 4);
}

void test_parse_snapshot_defaults_and_rejects_garbage() {
  x4::Snapshot snap = {};
  CHECK(x4::parse_snapshot("{}", &snap));
  CHECK_STREQ(snap.status, "UNKNOWN");
  CHECK(!snap.is_running);
  CHECK(!snap.has_sleep_seconds);
  CHECK_EQ(snap.build_count, 0);

  CHECK(!x4::parse_snapshot("", &snap));
  CHECK(!x4::parse_snapshot("{", &snap));
  CHECK(!x4::parse_snapshot("[]", &snap));
  CHECK(!x4::parse_snapshot(nullptr, &snap));
}

void test_wifi_failure_redraws_once() {
  x4::Fetch fetch = {0, nullptr, nullptr, nullptr};
  x4::CyclePlan plan = x4::plan_cycle(0, 3, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Full);
  CHECK_STREQ(plan.snapshot.status, "NO WIFI");
  CHECK_EQ(plan.fail_streak, 1);
  CHECK_EQ(plan.updates_since_full, 3);
  CHECK(!plan.store_etag);
  CHECK_EQ(plan.sleep_seconds, 600);
}

void test_wifi_failure_later_does_not_redraw() {
  x4::Fetch fetch = {0, nullptr, nullptr, nullptr};
  x4::CyclePlan plan = x4::plan_cycle(1, 3, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Leave);
  CHECK_EQ(plan.fail_streak, 2);
  CHECK_EQ(plan.sleep_seconds, 1200);
}

void test_http_error_backs_off_from_retry_after() {
  x4::Fetch fetch = {503, "180", nullptr, nullptr};
  x4::CyclePlan plan = x4::plan_cycle(1, 0, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Leave);
  CHECK_EQ(plan.fail_streak, 2);
  CHECK_EQ(plan.sleep_seconds, 720);
  CHECK(!plan.store_etag);
}

void test_not_modified_skips_panel_and_clears_streak() {
  x4::Fetch fetch = {304, "900", "W/\"abc\"", nullptr};
  x4::CyclePlan plan = x4::plan_cycle(3, 5, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Leave);
  CHECK_EQ(plan.fail_streak, 0);
  CHECK_EQ(plan.updates_since_full, 5);
  CHECK(plan.store_etag);
  CHECK_EQ(plan.sleep_seconds, 900);
}

void test_bad_json_does_not_redraw() {
  x4::Fetch fetch = {200, "120", "W/\"x\"", "{not json"};
  x4::CyclePlan plan = x4::plan_cycle(0, 0, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Leave);
  CHECK_EQ(plan.fail_streak, 1);
  CHECK(!plan.store_etag);
}

void test_fail_uses_full_refresh_and_json_sleep() {
  x4::Fetch fetch = {
      200,
      "900",
      "W/\"fail\"",
      "{\"status\":\"FAIL\",\"is_running\":false,\"sleep_seconds\":180,"
      "\"builds\":[{\"workflow\":\"CI\",\"status\":\"FAIL\"}]}",
  };
  x4::CyclePlan plan = x4::plan_cycle(2, 1, fetch, false);
  CHECK(plan.panel == x4::PanelAction::Full);
  CHECK_EQ(plan.fail_streak, 0);
  CHECK_EQ(plan.updates_since_full, 0);
  CHECK(plan.store_etag);
  CHECK_EQ(plan.sleep_seconds, 180);
  CHECK_STREQ(plan.snapshot.status, "FAIL");
  CHECK_EQ(plan.snapshot.build_count, 1);
}

void test_pass_uses_partial_until_full_refresh_every() {
  x4::Fetch fetch = {
      200,
      nullptr,
      "W/\"pass\"",
      "{\"status\":\"PASS\",\"is_running\":false,\"sleep_seconds\":900}",
  };
  x4::CyclePlan partial = x4::plan_cycle(0, 0, fetch, false);
  CHECK(partial.panel == x4::PanelAction::Partial);
  CHECK_EQ(partial.updates_since_full, 1);

  x4::CyclePlan full = x4::plan_cycle(0, x4::kFullRefreshEvery, fetch, false);
  CHECK(full.panel == x4::PanelAction::Full);
  CHECK_EQ(full.updates_since_full, 0);
}

void test_running_json_sleep_beats_retry_after() {
  x4::Fetch fetch = {
      200,
      "900",
      "W/\"run\"",
      "{\"status\":\"PASS\",\"is_running\":true,\"sleep_seconds\":120}",
  };
  x4::CyclePlan plan = x4::plan_cycle(0, 0, fetch, false);
  CHECK_EQ(plan.sleep_seconds, 120);
  CHECK(plan.snapshot.is_running);
  CHECK(plan.panel == x4::PanelAction::Partial);
}

void test_charging_caps_green_sleep() {
  x4::Fetch fetch = {
      200,
      nullptr,
      "W/\"pass\"",
      "{\"status\":\"PASS\",\"is_running\":false,\"sleep_seconds\":900}",
  };
  x4::CyclePlan plan = x4::plan_cycle(0, 0, fetch, true);
  CHECK_EQ(plan.sleep_seconds, 60);
  CHECK(plan.panel == x4::PanelAction::Partial);
}

void test_missing_sleep_falls_back_to_default() {
  x4::Fetch fetch = {304, nullptr, "W/\"z\"", nullptr};
  x4::CyclePlan plan = x4::plan_cycle(0, 0, fetch, false);
  CHECK_EQ(plan.sleep_seconds, 900);
}

}  // namespace

void test_page_key_refreshes_and_power_key_shuts_down() {
  const x4::ButtonSample idle = {false, false};
  CHECK(x4::button_intent(idle, idle) == x4::ButtonIntent::None);
  CHECK(x4::button_intent({true, false}, idle) == x4::ButtonIntent::PowerOff);
  CHECK(x4::button_intent({false, true}, idle) == x4::ButtonIntent::Refresh);
  CHECK(x4::button_intent({true, true}, idle) == x4::ButtonIntent::PowerOff);
  CHECK(x4::button_intent({true, false}, {true, false}) == x4::ButtonIntent::None);
  CHECK(x4::button_intent({false, true}, {true, false}) == x4::ButtonIntent::Refresh);
  CHECK(x4::button_intent({false, true}, {false, true}) == x4::ButtonIntent::None);
}

void test_latch_drops_only_after_power_release() {
  CHECK(!x4::may_drop_latch(true));
  CHECK(x4::may_drop_latch(false));
}

void test_idle_path_polls_on_usb_and_sleeps_on_battery() {
  CHECK(x4::idle_path(true) == x4::IdlePath::UsbPoll);
  CHECK(x4::idle_path(false) == x4::IdlePath::BatteryLightSleep);
}

void test_status_view_labels_and_job_title() {
  CHECK_STREQ(x4::hero_label("NONE"), "Idle");
  CHECK_STREQ(x4::hero_label("FAIL"), "Fail");
  CHECK_STREQ(x4::chip_label("RUNNING"), "RUN");
  CHECK(x4::attention_status("FAIL"));
  CHECK(!x4::attention_status("PASS"));
  x4::BuildRow row = {};
  std::strcpy(row.repo, "acme/web");
  std::strcpy(row.workflow, "CI");
  CHECK_STREQ(x4::job_title(row), "web");
  CHECK(x4::job_shows_workflow(row));
  CHECK_STREQ(x4::empty_body(false), "All clear");
  char sleep[16];
  x4::format_sleep(sleep, sizeof(sleep), 900);
  CHECK_STREQ(sleep, "15 min");
}

void test_monitor_lines_from_failing_jobs_and_open_prs() {
  x4::Snapshot snap = {};
  std::strcpy(snap.status, "FAIL");
  snap.has_sleep_seconds = true;
  snap.sleep_seconds = 120;
  snap.build_count = 1;
  std::strcpy(snap.builds[0].repo, "acme/web");
  std::strcpy(snap.builds[0].workflow, "CI");
  std::strcpy(snap.builds[0].status, "FAIL");
  snap.open_pr_count = 1;
  std::strcpy(snap.open_prs[0].repo, "acme/web");
  snap.open_prs[0].pr_count = 4;

  x4::MonitorLine lines[x4::kMaxMonitorLines] = {};
  CHECK_EQ(x4::fill_monitor_lines(snap, lines, x4::kMaxMonitorLines), 3);
  CHECK_STREQ(lines[0].title, "Fail");
  CHECK_STREQ(lines[0].subtitle, "2 min");
  CHECK_STREQ(lines[1].title, "web");
  CHECK_STREQ(lines[1].subtitle, "FAIL CI");
  CHECK_STREQ(lines[2].title, "web");
  CHECK_STREQ(lines[2].subtitle, "4 open");
}

void test_monitor_lines_idle_when_snapshot_is_empty() {
  x4::Snapshot snap = {};
  std::strcpy(snap.status, "NONE");
  x4::MonitorLine lines[2] = {};
  CHECK_EQ(x4::fill_monitor_lines(snap, lines, 2), 1);
  CHECK_STREQ(lines[0].title, "Idle");
  CHECK_STREQ(lines[0].subtitle, "All clear");
  CHECK_EQ(x4::fill_monitor_lines(snap, nullptr, 2), 0);
}

void test_present_forces_full_on_usb_and_button() {
  x4::CyclePlan plan = {};
  plan.panel = x4::PanelAction::Leave;
  std::strcpy(plan.snapshot.status, "PASS");
  uint8_t button = 1;
  x4::CyclePlan out = x4::present_for_panel(plan, false, &button, 200);
  CHECK(out.panel == x4::PanelAction::Full);
  CHECK_EQ(button, 0);
  button = 0;
  plan.panel = x4::PanelAction::Leave;
  out = x4::present_for_panel(plan, true, &button, 0);
  CHECK(out.panel == x4::PanelAction::Full);
  CHECK_STREQ(out.snapshot.status, "HTTP 0");
}

void test_if_none_match_skipped_on_usb_or_button() {
  CHECK(x4::should_send_if_none_match("W/\"a\"", false, false));
  CHECK(!x4::should_send_if_none_match("W/\"a\"", true, false));
  CHECK(!x4::should_send_if_none_match("W/\"a\"", false, true));
  CHECK(!x4::should_send_if_none_match("", false, false));
}

void test_desk_idle_caps_when_usb_plugged() {
  CHECK_EQ(x4::desk_idle_seconds(900, false), 900);
  CHECK_EQ(x4::desk_idle_seconds(900, true), 60);
}

void test_x3_fuel_gauge_treats_positive_current_as_charging() {
  CHECK(bq27220::is_charging(1));
  CHECK(bq27220::is_charging(120));
  CHECK(!bq27220::is_charging(0));
  CHECK(!bq27220::is_charging(-15));
}

int main() {
  test_if_none_match_skipped_on_usb_or_button();
  test_present_forces_full_on_usb_and_button();
  test_status_view_labels_and_job_title();
  test_monitor_lines_from_failing_jobs_and_open_prs();
  test_monitor_lines_idle_when_snapshot_is_empty();
  test_page_key_refreshes_and_power_key_shuts_down();
  test_latch_drops_only_after_power_release();
  test_idle_path_polls_on_usb_and_sleeps_on_battery();
  test_desk_idle_caps_when_usb_plugged();
  test_x3_fuel_gauge_treats_positive_current_as_charging();
  test_backoff_doubles_then_caps();
  test_usb_cap_only_when_charging();
  test_copy_etag_rejects_empty_and_overflow();
  test_parse_retry_after();
  test_parse_snapshot_compact_payload();
  test_parse_snapshot_open_prs_when_workflows_are_green();
  test_parse_snapshot_defaults_and_rejects_garbage();
  test_wifi_failure_redraws_once();
  test_wifi_failure_later_does_not_redraw();
  test_http_error_backs_off_from_retry_after();
  test_not_modified_skips_panel_and_clears_streak();
  test_bad_json_does_not_redraw();
  test_fail_uses_full_refresh_and_json_sleep();
  test_pass_uses_partial_until_full_refresh_every();
  test_running_json_sleep_beats_retry_after();
  test_charging_caps_green_sleep();
  test_missing_sleep_falls_back_to_default();

  if (g_fails != 0) {
    std::fprintf(stderr, "%d/%d checks failed\n", g_fails, g_checks);
    return 1;
  }
  std::printf("%d checks passed\n", g_checks);
  return 0;
}
