#include "MonitorActivity.h"

#include <HalDisplay.h>
#include <I18n.h>
#include <Logging.h>
#include <WiFi.h>

#include <cstdio>
#include <string>

#include "MappedInputManager.h"
#include "components/UITheme.h"
#include "duty_cycle.hpp"
#include "network/HttpDownloader.h"

#ifndef MONITOR_STATUS_URL
#define MONITOR_STATUS_URL "https://monitor.mzworthington.co.uk/status?view=eink"
#endif

namespace fui = freeink::ui;

MonitorActivity::MonitorActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("BuildMonitor", renderer, mappedInput) {}

void MonitorActivity::onEnter() {
  UiListActivity::onEnter();
  refreshSnapshot();
}

const char* MonitorActivity::headerTitle() const { return tr(STR_BUILD_MONITOR); }

void MonitorActivity::drawFooter() {
  const auto labels = mappedInput.mapLabels(tr(STR_BACK), tr(STR_RETRY), tr(STR_DIR_UP), tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}

void MonitorActivity::showMessage(const char* title, const char* subtitle) {
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

void MonitorActivity::refreshSnapshot() {
  if (WiFi.status() != WL_CONNECTED) {
    showMessage(tr(STR_CONNECTION_FAILED), tr(STR_CHECKING_WIFI));
    requestUpdate();
    return;
  }

  std::string body;
  if (!HttpDownloader::fetchUrl(MONITOR_STATUS_URL, body) || body.empty()) {
    LOG_ERR("MONITOR", "GET failed: %s", MONITOR_STATUS_URL);
    showMessage(tr(STR_CONNECTION_FAILED), tr(STR_PRESS_OK_SCAN));
    requestUpdate();
    return;
  }

  eink::Snapshot snap = {};
  if (!eink::parse_snapshot(body.c_str(), &snap)) {
    LOG_ERR("MONITOR", "bad snapshot JSON (%u bytes)", static_cast<unsigned>(body.size()));
    showMessage(tr(STR_PAGE_LOAD_ERROR), tr(STR_RETRY));
    requestUpdate();
    return;
  }

  rowCount = eink::fill_monitor_lines(snap, lines, eink::kMaxMonitorLines);
  rebuildRows();
  requestUpdate();
}

void MonitorActivity::activateIndex(int) {
  app.clearTapFlash();
  refreshSnapshot();
}

bool MonitorActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    onBackButton();
    return true;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    app.clearTapFlash();
    refreshSnapshot();
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
