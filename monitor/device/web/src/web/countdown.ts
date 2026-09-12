export type TickerTiming = {
  poll_in_seconds?: number;
  next_check_at?: number | string | null;
  last_checked_at?: number | string | null;
  fetching?: boolean;
  status?: string;
};

export type TickerElement = {
  dataset: Record<string, string | undefined>;
  textContent: string | null;
  title?: string;
  style?: { strokeDashoffset: string };
  setAttribute: (name: string, value: string) => void;
  removeAttribute: (name: string) => void;
};

export type TickerHost = {
  getElementById: (id: string) => TickerElement | null;
  body?: { dataset: Record<string, string | undefined> };
  requestAnimationFrame: (cb: () => void) => number;
  cancelAnimationFrame: (id: number) => void;
  addEventListener: (type: string, listener: () => void) => void;
};

export type BuildMonitorTicker = {
  applyTiming: (timing: TickerTiming) => void;
  setFetching: (isFetching: boolean) => void;
  setStatus: (status: string) => void;
  tick: () => void;
};

function tickerHostFromGlobal(): TickerHost {
  const doc = (globalThis as { document?: Partial<TickerHost> }).document;
  const clock = globalThis as unknown as Pick<
    TickerHost,
    'requestAnimationFrame' | 'cancelAnimationFrame' | 'addEventListener'
  >;
  return {
    getElementById: (id) => doc?.getElementById?.(id) ?? null,
    body: doc?.body,
    requestAnimationFrame: (cb) => clock.requestAnimationFrame(cb),
    cancelAnimationFrame: (id) => clock.cancelAnimationFrame(id),
    addEventListener: (type, listener) => clock.addEventListener(type, listener),
  };
}

export function startCountdown(
  host: TickerHost = tickerHostFromGlobal(),
): BuildMonitorTicker | undefined {
  const dial = host.getElementById('status-dial');
  const progress = host.getElementById('ticker-progress');
  const lastChecked = host.getElementById('last-checked');
  if (!dial || !progress) {
    return undefined;
  }

  const statusDial = dial;
  const tickerProgress = progress;
  let pollSeconds = Number(statusDial.dataset.pollSeconds || 30);
  let nextCheckAt = statusDial.dataset.nextCheckAt ? Number(statusDial.dataset.nextCheckAt) : null;
  let lastCheckedAt = lastChecked?.dataset.lastCheckedAt
    ? Number(lastChecked.dataset.lastCheckedAt)
    : null;
  let fetching = statusDial.dataset.fetching === 'true';
  let frameId = 0;
  let lastLabelSecond = -1;

  function setFetching(isFetching: boolean): void {
    const next = Boolean(isFetching);
    if (fetching === next) return;
    fetching = next;
    statusDial.dataset.fetching = fetching ? 'true' : 'false';
    if (!fetching) {
      tick();
    }
  }

  function setStatus(status: string): void {
    if (!status) return;
    statusDial.dataset.status = status;
    if (host.body) {
      host.body.dataset.status = status;
    }
  }

  function formatClock(timestamp: number): string {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }

  function formatLastCheckedLabel(timestamp: number | null): string {
    if (timestamp == null || !Number.isFinite(timestamp)) {
      return 'Not checked yet';
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

  function updateLastCheckedLabel(force = false): void {
    if (!lastChecked) return;
    const second = Math.floor(Date.now() / 1000);
    if (!force && second === lastLabelSecond) return;
    lastLabelSecond = second;
    lastChecked.textContent = formatLastCheckedLabel(lastCheckedAt);
    if (lastCheckedAt != null && Number.isFinite(lastCheckedAt)) {
      lastChecked.title = new Date(lastCheckedAt * 1000).toLocaleString();
    } else {
      lastChecked.removeAttribute('title');
    }
  }

  function asOptionalNumber(value: number | string | null | undefined): number | null {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (value == null) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function applyTiming(timing: TickerTiming): void {
    if (typeof timing.poll_in_seconds === 'number' && timing.poll_in_seconds > 0) {
      pollSeconds = timing.poll_in_seconds;
      statusDial.dataset.pollSeconds = String(pollSeconds);
    }
    if (timing.next_check_at !== undefined) {
      nextCheckAt = asOptionalNumber(timing.next_check_at);
      statusDial.dataset.nextCheckAt = nextCheckAt == null ? '' : String(nextCheckAt);
    }
    if (timing.last_checked_at !== undefined) {
      lastCheckedAt = asOptionalNumber(timing.last_checked_at);
      if (lastChecked) {
        lastChecked.dataset.lastCheckedAt = lastCheckedAt == null ? '' : String(lastCheckedAt);
      }
      updateLastCheckedLabel(true);
    }
    setFetching(Boolean(timing.fetching));
    if (timing.status) setStatus(timing.status);
    tick();
  }

  function tick(): void {
    updateLastCheckedLabel();
    if (fetching || nextCheckAt == null) {
      if (tickerProgress.style) {
        tickerProgress.style.strokeDashoffset = fetching ? '' : '0.12';
      }
      statusDial.setAttribute(
        'aria-label',
        fetching ? 'Checking build status' : 'Waiting for next schedule',
      );
      return;
    }

    const remainingMs = Math.max(0, nextCheckAt * 1000 - Date.now());
    const remainingSec = remainingMs / 1000;
    const ratio = Math.min(1, Math.max(0, remainingSec / pollSeconds));
    if (tickerProgress.style) {
      tickerProgress.style.strokeDashoffset = String(1 - ratio);
    }

    const whole = Math.ceil(remainingSec);
    statusDial.setAttribute(
      'aria-label',
      whole <= 0 ? 'Checking build status soon' : `Next check in ${whole} seconds`,
    );
  }

  function loop(): void {
    tick();
    frameId = host.requestAnimationFrame(loop);
  }

  const ticker: BuildMonitorTicker = { applyTiming, setFetching, setStatus, tick };
  (globalThis as { BuildMonitorTicker?: BuildMonitorTicker }).BuildMonitorTicker = ticker;
  updateLastCheckedLabel(true);
  frameId = host.requestAnimationFrame(loop);
  host.addEventListener('beforeunload', () => host.cancelAnimationFrame(frameId));
  return ticker;
}
