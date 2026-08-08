(() => {
  const lights = {
    blue: document.querySelector('[data-light="blue"]'),
    green: document.querySelector('[data-light="green"]'),
    yellow: document.querySelector('[data-light="yellow"]'),
    red: document.querySelector('[data-light="red"]'),
    purple: document.querySelector('[data-light="purple"]'),
  };
  const connection = document.getElementById("connection");
  const summary = document.getElementById("summary");
  const statusWord = document.getElementById("status-word");
  const issuesSection = document.getElementById("issues");
  const issueList = document.getElementById("issue-list");
  const issueCount = document.getElementById("issue-count");

  const summaries = {
    PASS: "All builds passed",
    FAIL: "At least one build failed",
    UNKNOWN: "Mixed or unknown status",
    CONNECTION_ERROR: "Could not reach a CI provider",
    NONE: "No build results yet",
  };

  const statusWords = {
    PASS: "Passing",
    FAIL: "Failing",
    UNKNOWN: "Mixed",
    CONNECTION_ERROR: "Offline",
    NONE: "Idle",
  };

  const attentionStatuses = new Set(["FAIL", "CONNECTION_ERROR", "UNKNOWN"]);

  function setLight(name, mode) {
    const el = lights[name];
    if (!el) return;
    el.classList.toggle("on", mode === "on");
    el.classList.toggle("pulse", mode === "pulse");
  }

  function fitStatusWord() {
    if (!statusWord) return;
    const core = statusWord.closest(".status-dial-core") || statusWord.parentElement;
    if (!core) return;

    statusWord.style.fontSize = "";
    const maxPx = parseFloat(getComputedStyle(statusWord).fontSize) || 32;

    const diameter = core.getBoundingClientRect().width;
    const styles = getComputedStyle(core);
    const padX =
      (parseFloat(styles.paddingLeft) || 0) + (parseFloat(styles.paddingRight) || 0);
    // Stay inside the circular chord (stricter than the square content box).
    const available = Math.max(24, (diameter - padX) * 0.72);

    let lo = 11;
    let hi = maxPx;
    let best = 11;
    for (let i = 0; i < 16; i += 1) {
      const mid = (lo + hi) / 2;
      statusWord.style.fontSize = `${mid}px`;
      if (statusWord.scrollWidth <= available) {
        best = mid;
        lo = mid;
      } else {
        hi = mid;
      }
    }
    statusWord.style.fontSize = `${best}px`;
  }

  function scheduleFitStatusWord() {
    window.requestAnimationFrame(() => {
      fitStatusWord();
      window.requestAnimationFrame(fitStatusWord);
    });
  }

  function splitRepo(repo) {
    const value = repo || "unknown repo";
    const index = value.indexOf("/");
    if (index <= 0 || index === value.length - 1) {
      return { org: "", name: value };
    }
    return {
      org: value.slice(0, index + 1),
      name: value.slice(index + 1),
    };
  }

  function renderIssues(builds) {
    const issues = (builds || []).filter((build) => attentionStatuses.has(build.status));
    issueList.replaceChildren();
    if (!issues.length) {
      issuesSection.hidden = true;
      return;
    }

    issuesSection.hidden = false;
    if (issueCount) {
      issueCount.textContent = `${issues.length} open`;
    }

    issues.forEach((issue, index) => {
      const item = document.createElement("li");
      item.className = `issue issue-${String(issue.status || "").toLowerCase()}`;
      item.style.setProperty("--delay", `${index * 40}ms`);

      const { org, name } = splitRepo(issue.repo);
      const repo = document.createElement("span");
      repo.className = "issue-repo";
      if (org) {
        const orgEl = document.createElement("span");
        orgEl.className = "issue-org";
        orgEl.textContent = org;
        const nameEl = document.createElement("span");
        nameEl.className = "issue-name";
        nameEl.textContent = name;
        repo.append(orgEl, nameEl);
      } else {
        repo.textContent = name;
      }

      const workflow = document.createElement("span");
      workflow.className = "issue-workflow";
      workflow.textContent = issue.workflow || "";

      const status = document.createElement("span");
      status.className = "issue-status";
      status.textContent = issue.status || "";

      if (issue.url) {
        const link = document.createElement("a");
        link.href = issue.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.append(repo, workflow, status);
        item.append(link);
      } else {
        item.append(repo, workflow, status);
      }
      issueList.append(item);
    });
  }

  function render(payload) {
    const status = payload.status || "NONE";
    const fetching = Boolean(payload.fetching);
    const isRunning = Boolean(payload.is_running);

    setLight("blue", fetching ? "on" : "off");
    setLight("purple", status === "CONNECTION_ERROR" ? "on" : "off");
    setLight("green", status === "PASS" || status === "UNKNOWN" ? "on" : "off");
    setLight("red", status === "FAIL" || status === "UNKNOWN" ? "on" : "off");
    setLight("yellow", isRunning ? "pulse" : "off");

    if (statusWord) {
      statusWord.textContent = fetching
        ? "Checking"
        : statusWords[status] || statusWords.NONE;
      scheduleFitStatusWord();
    }

    summary.textContent = summaries[status] || summaries.NONE;
    if (isRunning) {
      summary.textContent += " · build running";
    }
    if (fetching) {
      summary.textContent += " · fetching";
    }
    renderIssues(payload.builds);

    if (window.BuildMonitorTicker) {
      window.BuildMonitorTicker.applyTiming(payload);
    }
  }

  function setConnection(state, text) {
    connection.dataset.state = state;
    connection.textContent = text;
  }

  let socket;
  let retryMs = 1000;

  function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.addEventListener("open", () => {
      retryMs = 1000;
      setConnection("live", "Live");
    });

    socket.addEventListener("message", (event) => {
      try {
        render(JSON.parse(event.data));
      } catch (_err) {
        summary.textContent = "Received invalid status payload";
      }
    });

    socket.addEventListener("close", () => {
      setConnection("offline", "Reconnecting…");
      window.setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 15000);
    });

    socket.addEventListener("error", () => {
      socket.close();
    });
  }

  connect();
  scheduleFitStatusWord();
  window.addEventListener("resize", scheduleFitStatusWord);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(scheduleFitStatusWord);
  }
})();
