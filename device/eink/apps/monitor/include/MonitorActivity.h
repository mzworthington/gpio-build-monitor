#pragma once

#include <GfxRenderer.h>

#include "activities/UiListActivity.h"
#include "status_view.hpp"

class MappedInputManager;

class MonitorActivity final : public UiListActivity {
 public:
  MonitorActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);

  void onEnter() override;

 private:
  int listCount() const override { return rowCount; }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  const char* headerTitle() const override;
  void drawFooter() override;

  void refreshSnapshot();
  void rebuildRows();
  void showMessage(const char* title, const char* subtitle);

  x4::MonitorLine lines[x4::kMaxMonitorLines]{};
  freeink::ui::ListItem rowItems[x4::kMaxMonitorLines]{};
  int rowCount = 0;
};
