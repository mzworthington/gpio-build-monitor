(() => {
  const dial = document.getElementById("status-dial");
  const progress = document.getElementById("ticker-progress");
  const lastChecked = document.getElementById("last-checked");
  if (!dial || !progress) {
    return;
  }

  let pollSeconds = Number(dial.dataset.pollSeconds || 30);
  let nextCheckAt = dial.dataset.nextCheckAt
    ? Number(dial.dataset.nextCheckAt)
    : null;
  let lastCheckedAt = lastChecked?.dataset.lastCheckedAt
    ? Number(lastChecked.dataset.lastCheckedAt)
    : null;
  let fetching = dial.dataset.fetching === "true";
  let frameId = 0;
  let lastLabelSecond = -1;

  function setFetching(isFetching) {
    fetching = Boolean(isFetching);
    dial.dataset.fetching = fetching ? "true" : "false";
  }

  function setStatus(status) {
    if (!status) return;
    dial.dataset.status = status;
    document.body.dataset.status = status;
  }

  function formatClock(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }

  function formatLastCheckedLabel(timestamp) {
    if (timestamp == null || !Number.isFinite(timestamp)) {
      return "Not checked yet";
    }
    const ageSec = Math.max(0, Math.floor(Date.now() / 1000 - timestamp));
    const clock = formatClock(timestamp);
    if (ageSec < 5) {
      return `Checked ${clock} · just now`;
    }
    if (ageSec < 60) {
      return `Checked ${clock} · ${ageSec}s ago`;
    }
    const ageMin = Math.floor(ageSec / 60);
    if (ageMin < 60) {
      return `Checked ${clock} · ${ageMin}m ago`;
    }
    const ageHr = Math.floor(ageMin / 60);
    return `Checked ${clock} · ${ageHr}h ago`;
  }

  function updateLastCheckedLabel(force = false) {
    if (!lastChecked) return;
    const second = Math.floor(Date.now() / 1000);
    if (!force && second === lastLabelSecond) return;
    lastLabelSecond = second;
    lastChecked.textContent = formatLastCheckedLabel(lastCheckedAt);
    if (lastCheckedAt != null && Number.isFinite(lastCheckedAt)) {
      lastChecked.title = new Date(lastCheckedAt * 1000).toLocaleString();
    } else {
      lastChecked.removeAttribute("title");
    }
  }

  function applyTiming({
    poll_in_seconds,
    next_check_at,
    last_checked_at,
    fetching: isFetching,
    status,
  }) {
    if (typeof poll_in_seconds === "number" && poll_in_seconds > 0) {
      pollSeconds = poll_in_seconds;
      dial.dataset.pollSeconds = String(pollSeconds);
    }
    nextCheckAt =
      typeof next_check_at === "number"
        ? next_check_at
        : next_check_at == null
          ? null
          : Number(next_check_at);
    if (nextCheckAt != null && !Number.isFinite(nextCheckAt)) {
      nextCheckAt = null;
    }
    dial.dataset.nextCheckAt = nextCheckAt == null ? "" : String(nextCheckAt);

    if (last_checked_at !== undefined) {
      lastCheckedAt =
        typeof last_checked_at === "number"
          ? last_checked_at
          : last_checked_at == null
            ? null
            : Number(last_checked_at);
      if (lastCheckedAt != null && !Number.isFinite(lastCheckedAt)) {
        lastCheckedAt = null;
      }
      if (lastChecked) {
        lastChecked.dataset.lastCheckedAt =
          lastCheckedAt == null ? "" : String(lastCheckedAt);
      }
      updateLastCheckedLabel(true);
    }

    setFetching(Boolean(isFetching));
    if (status) setStatus(status);
    tick();
  }

  function tick() {
    updateLastCheckedLabel();
    if (fetching || nextCheckAt == null) {
      // CSS owns the quiet fetch spinner; keep inline offset clear of the arc.
      progress.style.strokeDashoffset = fetching ? "" : "0.12";
      dial.setAttribute(
        "aria-label",
        fetching ? "Checking build status" : "Waiting for next schedule",
      );
      return;
    }

    const remainingMs = Math.max(0, nextCheckAt * 1000 - Date.now());
    const remainingSec = remainingMs / 1000;
    const ratio = Math.min(1, Math.max(0, remainingSec / pollSeconds));
    progress.style.strokeDashoffset = String(1 - ratio);

    const whole = Math.ceil(remainingSec);
    dial.setAttribute(
      "aria-label",
      whole <= 0
        ? "Checking build status soon"
        : `Next check in ${whole} seconds`,
    );
  }

  function loop() {
    tick();
    frameId = window.requestAnimationFrame(loop);
  }

  window.BuildMonitorTicker = { applyTiming, setFetching, setStatus, tick };
  updateLastCheckedLabel(true);
  frameId = window.requestAnimationFrame(loop);
  window.addEventListener("beforeunload", () => window.cancelAnimationFrame(frameId));
})();
