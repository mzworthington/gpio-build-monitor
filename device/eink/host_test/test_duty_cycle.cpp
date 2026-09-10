#include "duty_cycle.hpp"
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

void test_parse_snapshot_repos_include_zero_pr_counts() {
  const char* json =
      "{"
      "\"status\":\"FAIL\","
      "\"repos\":["
      "{\"repo\":\"acme/api\",\"status\":\"PASS\",\"workflow_count\":1,\"pr_count\":2,\"is_running\":false},"
      "{\"repo\":\"acme/web\",\"status\":\"FAIL\",\"workflow_count\":2,\"pr_count\":0,\"is_running\":false}"
      "]"
      "}";
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot(json, &snap));
  CHECK_EQ(snap.repo_count, 2);
  CHECK_STREQ(snap.repos[0].repo, "acme/api");
  CHECK_EQ(snap.repos[0].workflow_count, 1);
  CHECK_EQ(snap.repos[0].pr_count, 2);
  CHECK_STREQ(snap.repos[1].status, "FAIL");
  CHECK_EQ(snap.repos[1].pr_count, 0);
}

void test_monitor_lines_list_every_repo_with_action_and_pr_counts() {
  eink::Snapshot snap = {};
  std::strcpy(snap.status, "FAIL");
  snap.has_sleep_seconds = true;
  snap.sleep_seconds = 180;
  snap.repo_count = 2;
  std::strcpy(snap.repos[0].repo, "acme/api");
  std::strcpy(snap.repos[0].status, "PASS");
  snap.repos[0].workflow_count = 1;
  snap.repos[0].pr_count = 2;
  std::strcpy(snap.repos[1].repo, "acme/web");
  std::strcpy(snap.repos[1].status, "FAIL");
  snap.repos[1].workflow_count = 2;
  snap.repos[1].pr_count = 0;

  eink::MonitorLine lines[eink::kMaxMonitorLines] = {};
  CHECK_EQ(eink::fill_monitor_lines(snap, lines, eink::kMaxMonitorLines), 3);
  CHECK_STREQ(lines[0].title, "Fail");
  CHECK_STREQ(lines[1].title, "acme/api");
  CHECK_STREQ(lines[1].subtitle, "OK · 1 action · 2 PRs");
  CHECK_STREQ(lines[2].title, "acme/web");
  CHECK_STREQ(lines[2].subtitle, "FAIL · 2 actions · 0 PRs");
}

void test_parse_snapshot_repos_include_workflows() {
  const char* json =
      "{"
      "\"status\":\"FAIL\","
      "\"repos\":["
      "{\"repo\":\"acme/web\",\"status\":\"FAIL\",\"workflow_count\":2,\"pr_count\":0,\"is_running\":false,"
      "\"workflows\":[{\"workflow\":\"CI\",\"status\":\"FAIL\"},{\"workflow\":\"Deploy\",\"status\":\"PASS\"}]}"
      "]"
      "}";
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot(json, &snap));
  CHECK_EQ(snap.repo_count, 1);
  CHECK_EQ(snap.repos[0].workflow_n, 2);
  CHECK_STREQ(snap.repos[0].workflows[0].workflow, "CI");
  CHECK_STREQ(snap.repos[0].workflows[0].status, "FAIL");
  CHECK_STREQ(snap.repos[0].workflows[1].workflow, "Deploy");
  CHECK_STREQ(snap.repos[0].workflows[1].status, "PASS");
}

void test_parse_snapshot_list_omits_workflows() {
  const char* json =
      "{"
      "\"status\":\"FAIL\","
      "\"repos\":["
      "{\"repo\":\"acme/web\",\"status\":\"FAIL\",\"workflow_count\":24,\"pr_count\":0,\"is_running\":false}"
      "]"
      "}";
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot(json, &snap));
  CHECK_EQ(snap.repos[0].workflow_count, 24);
  CHECK_EQ(snap.repos[0].workflow_n, 0);
}

void test_merge_repo_workflows_from_detail_snapshot() {
  eink::Snapshot list = {};
  list.repo_count = 1;
  std::strcpy(list.repos[0].repo, "acme/web");
  list.repos[0].workflow_count = 24;
  eink::Snapshot detail = {};
  detail.repo_count = 1;
  std::strcpy(detail.repos[0].repo, "acme/web");
  detail.repos[0].workflow_count = 24;
  detail.repos[0].workflow_n = 2;
  std::strcpy(detail.repos[0].workflows[0].workflow, "CI");
  std::strcpy(detail.repos[0].workflows[0].status, "FAIL");
  CHECK(eink::merge_repo_workflows(detail, &list.repos[0]));
  CHECK_EQ(list.repos[0].workflow_n, 2);
  CHECK_STREQ(list.repos[0].workflows[0].workflow, "CI");
}

void test_monitor_lines_open_repo_lists_every_action() {
  eink::Snapshot snap = {};
  snap.repo_count = 1;
  std::strcpy(snap.repos[0].repo, "acme/web");
  std::strcpy(snap.repos[0].status, "FAIL");
  snap.repos[0].workflow_count = 2;
  snap.repos[0].pr_count = 0;
  snap.repos[0].workflow_n = 2;
  std::strcpy(snap.repos[0].workflows[0].workflow, "CI");
  std::strcpy(snap.repos[0].workflows[0].status, "FAIL");
  std::strcpy(snap.repos[0].workflows[1].workflow, "Deploy");
  std::strcpy(snap.repos[0].workflows[1].status, "PASS");

  CHECK_EQ(eink::repo_from_monitor_index(0, 1), -1);
  CHECK_EQ(eink::repo_from_monitor_index(1, 1), 0);
  CHECK_EQ(eink::repo_from_monitor_index(2, 1), -1);

  eink::MonitorLine lines[eink::kMaxMonitorLines] = {};
  CHECK_EQ(eink::fill_repo_action_lines(snap, 0, lines, eink::kMaxMonitorLines), 3);
  CHECK_STREQ(lines[0].title, "acme/web");
  CHECK_STREQ(lines[0].subtitle, "FAIL · 2 actions · 0 PRs");
  CHECK_STREQ(lines[1].title, "CI");
  CHECK_STREQ(lines[1].subtitle, "FAIL");
  CHECK_STREQ(lines[2].title, "Deploy");
  CHECK_STREQ(lines[2].subtitle, "OK");
  CHECK_EQ(eink::fill_repo_action_lines(snap, 1, lines, eink::kMaxMonitorLines), 0);
}

void test_snapshot_is_too_large_for_esp32_task_stack() {
  CHECK(sizeof(eink::Snapshot) > 4096);
  CHECK(sizeof(eink::Snapshot) < 48 * 1024);
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
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot(json, &snap));
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
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot(json, &snap));
  CHECK_STREQ(snap.status, "PASS");
  CHECK_EQ(snap.build_count, 0);
  CHECK_EQ(snap.open_pr_count, 1);
  CHECK_STREQ(snap.open_prs[0].repo, "acme/web");
  CHECK_EQ(snap.open_prs[0].pr_count, 4);
}

void test_parse_snapshot_defaults_and_rejects_garbage() {
  eink::Snapshot snap = {};
  CHECK(eink::parse_snapshot("{}", &snap));
  CHECK_STREQ(snap.status, "UNKNOWN");
  CHECK(!snap.is_running);
  CHECK(!snap.has_sleep_seconds);
  CHECK_EQ(snap.build_count, 0);

  CHECK(!eink::parse_snapshot("", &snap));
  CHECK(!eink::parse_snapshot("{", &snap));
  CHECK(!eink::parse_snapshot("[]", &snap));
  CHECK(!eink::parse_snapshot(nullptr, &snap));
}

void test_status_view_labels_and_job_title() {
  CHECK_STREQ(eink::hero_label("NONE"), "Idle");
  CHECK_STREQ(eink::hero_label("FAIL"), "Fail");
  CHECK_STREQ(eink::chip_label("RUNNING"), "RUN");
  CHECK(eink::attention_status("FAIL"));
  CHECK(!eink::attention_status("PASS"));
  eink::BuildRow row = {};
  std::strcpy(row.repo, "acme/web");
  std::strcpy(row.workflow, "CI");
  CHECK_STREQ(eink::job_title(row), "web");
  CHECK(eink::job_shows_workflow(row));
  CHECK_STREQ(eink::empty_body(false), "All clear");
  char sleep[16];
  eink::format_sleep(sleep, sizeof(sleep), 900);
  CHECK_STREQ(sleep, "15 min");
}

void test_monitor_lines_from_failing_jobs_and_open_prs() {
  eink::Snapshot snap = {};
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

  eink::MonitorLine lines[eink::kMaxMonitorLines] = {};
  CHECK_EQ(eink::fill_monitor_lines(snap, lines, eink::kMaxMonitorLines), 3);
  CHECK_STREQ(lines[0].title, "Fail");
  CHECK_STREQ(lines[0].subtitle, "2 min");
  CHECK_STREQ(lines[1].title, "web");
  CHECK_STREQ(lines[1].subtitle, "FAIL CI");
  CHECK_STREQ(lines[2].title, "web");
  CHECK_STREQ(lines[2].subtitle, "4 open");
}

void test_monitor_lines_idle_when_snapshot_is_empty() {
  eink::Snapshot snap = {};
  std::strcpy(snap.status, "NONE");
  eink::MonitorLine lines[2] = {};
  CHECK_EQ(eink::fill_monitor_lines(snap, lines, 2), 1);
  CHECK_STREQ(lines[0].title, "Idle");
  CHECK_STREQ(lines[0].subtitle, "All clear");
  CHECK_EQ(eink::fill_monitor_lines(snap, nullptr, 2), 0);
}

}  // namespace

int main() {
  test_parse_snapshot_repos_include_zero_pr_counts();
  test_parse_snapshot_repos_include_workflows();
  test_parse_snapshot_list_omits_workflows();
  test_merge_repo_workflows_from_detail_snapshot();
  test_monitor_lines_list_every_repo_with_action_and_pr_counts();
  test_monitor_lines_open_repo_lists_every_action();
  test_snapshot_is_too_large_for_esp32_task_stack();
  test_parse_snapshot_compact_payload();
  test_parse_snapshot_open_prs_when_workflows_are_green();
  test_parse_snapshot_defaults_and_rejects_garbage();
  test_status_view_labels_and_job_title();
  test_monitor_lines_from_failing_jobs_and_open_prs();
  test_monitor_lines_idle_when_snapshot_is_empty();

  if (g_fails != 0) {
    std::fprintf(stderr, "%d/%d checks failed\n", g_fails, g_checks);
    return 1;
  }
  std::printf("%d checks passed\n", g_checks);
  return 0;
}
