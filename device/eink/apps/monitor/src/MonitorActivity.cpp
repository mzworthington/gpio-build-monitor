#include "MonitorActivity.h"

#include <HalDisplay.h>
#include <I18n.h>
#include <Logging.h>
#include <WiFi.h>

#include <cstdio>
#include <string>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "network/HttpDownloader.h"

#ifndef MONITOR_STATUS_URL
#define MONITOR_STATUS_URL "https://monitor.mzworthington.co.uk/status?view=eink"
#endif

namespace fui = freeink::ui;

namespace {
eink::Snapshot g_snap{};
eink::Snapshot g_detail{};

void appendEncodedRepo(std::string& url, const char* repo) {
  url += "&repo=";
  for (const char* p = repo; p != nullptr && *p != '\0'; ++p) {
    const unsigned char c = static_cast<unsigned char>(*p);
    if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '.' ||
        c == '_' || c == '-') {
      url += static_cast<char>(c);
    } else {
      char buf[4];
      std::snprintf(buf, sizeof(buf), "%%%02X", c);
      url += buf;
    }
  }
}

enum class FetchResult { Ok, Http, Parse };

FetchResult fetchSnapshot(const std::string& url, eink::Snapshot* dest) {
  std::string body;
  if (!HttpDownloader::fetchUrl(url, body) || body.empty()) {
    LOG_ERR("MONITOR", "GET failed: %s", url.c_str());
    return FetchResult::Http;
  }
  if (!eink::parse_snapshot(body.c_str(), dest)) {
    LOG_ERR("MONITOR", "bad snapshot JSON (%u bytes)", static_cast<unsigned>(body.size()));
    return FetchResult::Parse;
  }
  return FetchResult::Ok;
}
}  // namespace

MonitorActivity::MonitorActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("BuildMonitor", renderer, mappedInput) {}

void MonitorActivity::onEnter() {
  UiListActivity::onEnter();
  refreshSnapshot();
}

const char* MonitorActivity::headerTitle() const {
  if (selectedRepo_ >= 0 && selectedRepo_ < static_cast<int>(g_snap.repo_count)) {
    return eink::repo_leaf(g_snap.repos[static_cast<uint8_t>(selectedRepo_)].repo);
  }
  return tr(STR_BUILD_MONITOR);
}

void MonitorActivity::drawFooter() {
  const char* confirm = selectedRepo_ >= 0 ? tr(STR_RETRY) : tr(STR_SELECT);
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), confirm, tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}

void MonitorActivity::showMessage(const char* title, const char* subtitle) {
  selectedRepo_ = -1;
  std::snprintf(lines[0].title, sizeof(lines[0].title), "%s", title);
  std::snprintf(lines[0].subtitle, sizeof(lines[0].subtitle), "%s", subtitle != nullptr ? subtitle : "");
  rowCount = 1;
  rebuildRows();
}

void MonitorActivity::rebuildRows() {
  for (int i = 0; i < rowCount; ++i) {
    fui::ListItem item;
    item.label = lines[i].title;
    item.subtitle = lines[i].subtitle[0] != '\0' ? lines[i].subtitle : nullptr;
    item.actionValue = static_cast<int16_t>(i);
    rowItems[i] = item;
  }
}

void MonitorActivity::applyView() {
  if (selectedRepo_ >= 0 && selectedRepo_ < static_cast<int>(g_snap.repo_count)) {
    rowCount = eink::fill_repo_action_lines(g_snap, static_cast<uint8_t>(selectedRepo_), lines, eink::kMaxMonitorLines);
  } else {
    selectedRepo_ = -1;
    rowCount = eink::fill_monitor_lines(g_snap, lines, eink::kMaxMonitorLines);
  }
  rebuildRows();
}

void MonitorActivity::refreshSnapshot() {
  if (WiFi.status() != WL_CONNECTED) {
    showMessage(tr(STR_CONNECTION_FAILED), tr(STR_CHECKING_WIFI));
    requestUpdate();
    return;
  }

  const FetchResult fetched = fetchSnapshot(MONITOR_STATUS_URL, &g_snap);
  if (fetched != FetchResult::Ok) {
    showMessage(
        tr(fetched == FetchResult::Parse ? STR_PAGE_LOAD_ERROR : STR_CONNECTION_FAILED),
        tr(fetched == FetchResult::Parse ? STR_RETRY : STR_PRESS_OK_SCAN));
    requestUpdate();
    return;
  }

  if (selectedRepo_ >= static_cast<int>(g_snap.repo_count)) {
    selectedRepo_ = -1;
  }
  if (selectedRepo_ >= 0) {
    refreshRepoWorkflows();
  }
  applyView();
  requestUpdate();
}

void MonitorActivity::refreshRepoWorkflows() {
  if (selectedRepo_ < 0 || selectedRepo_ >= static_cast<int>(g_snap.repo_count)) {
    return;
  }
  std::string url = MONITOR_STATUS_URL;
  appendEncodedRepo(url, g_snap.repos[static_cast<uint8_t>(selectedRepo_)].repo);
  if (fetchSnapshot(url, &g_detail) != FetchResult::Ok) {
    return;
  }
  eink::merge_repo_workflows(g_detail, &g_snap.repos[static_cast<uint8_t>(selectedRepo_)]);
}

void MonitorActivity::activateIndex(int index) {
  app.clearTapFlash();
  if (selectedRepo_ < 0) {
    const int8_t repo = eink::repo_from_monitor_index(index, g_snap.repo_count);
    if (repo >= 0) {
      selectedRepo_ = repo;
      refreshRepoWorkflows();
      applyView();
      requestUpdate();
      return;
    }
  }
  refreshSnapshot();
}

bool MonitorActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (selectedRepo_ >= 0) {
      selectedRepo_ = -1;
      applyView();
      requestUpdate();
      return true;
    }
    onBackButton();
    return true;
  }
  return false;
}

void MonitorActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMarginFromScreen(fui::Insets{
      static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)), static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  fui::ListProps props;
  props.items = rowItems;
  props.count = static_cast<uint16_t>(rowCount);
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  props.labelText = screen.theme().smallText;
  props.labelText.maxLines = 2;
  syncListViewport(screen, props, true);
  screen.list(props);
}
