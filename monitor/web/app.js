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
  const reposSection = document.getElementById("repos");
  const repoList = document.getElementById("repo-list");
  const repoCount = document.getElementById("repo-count");
  const issuesSection = document.getElementById("issues");
  const issueList = document.getElementById("issue-list");
  const issueCount = document.getElementById("issue-count");

  const summaries = {
    PASS: "All builds passed",
    FAIL: "At least one build failed",
    UNKNOWN: "Unresolved build status",
    APPROVAL: "Waiting for human approval",
    CONNECTION_ERROR: "Could not reach a CI provider",
    NONE: "No build results yet",
    RUNNING: "Build in progress",
    WAITING: "Waiting for another pipeline",
  };

  const statusWords = {
    PASS: "Passing",
    FAIL: "Failing",
    UNKNOWN: "Unknown",
    APPROVAL: "Approval",
    CONNECTION_ERROR: "Offline",
    NONE: "Idle",
    RUNNING: "Running",
    WAITING: "Waiting",
  };

  const attentionStatuses = new Set(["FAIL", "CONNECTION_ERROR", "APPROVAL", "UNKNOWN"]);
  const inProgressStatuses = new Set(["RUNNING", "WAITING"]);
  const inProgressOverrides = new Set(["PASS", "NONE", "UNKNOWN"]);
  const expandedRepos = new Set();
  let lastBuildsKey = "";
  let lastStatusKey = "";
  let quietFetch = false;

  function displayStatus(status, isRunning, fetching, builds) {
    if (fetching) return status;
    if (status === "APPROVAL" || status === "FAIL" || status === "CONNECTION_ERROR") {
      return status;
    }
    const buildStatuses = new Set((builds || []).map((b) => b.status));
    if (buildStatuses.has("APPROVAL")) return "APPROVAL";
    if (buildStatuses.has("RUNNING")) return "RUNNING";
    if (buildStatuses.has("WAITING")) return "WAITING";
    if (isRunning && inProgressOverrides.has(status)) return "RUNNING";
    return status;
  }

  function buildsKey(builds) {
    try {
      return JSON.stringify(builds || []);
    } catch (_err) {
      return "";
    }
  }

  function statusKey(status, isRunning, shown) {
    return `${status}|${isRunning ? 1 : 0}|${shown}`;
  }

  /** Mid-poll: show fetch light + dial spinner; leave status copy and lists alone. */
  function applyQuietFetch(isFetching) {
    quietFetch = Boolean(isFetching);
    setLight("blue", quietFetch ? "on" : "off");
    if (window.BuildMonitorTicker) {
      window.BuildMonitorTicker.setFetching(quietFetch);
    }
  }

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

  function appendRepoLabel(parent, repo) {
    const { org, name } = splitRepo(repo);
    if (org) {
      const orgEl = document.createElement("span");
      orgEl.className = "issue-org";
      orgEl.textContent = org;
      const nameEl = document.createElement("span");
      nameEl.className = "issue-name";
      nameEl.textContent = name;
      parent.append(orgEl, nameEl);
      return;
    }
    parent.textContent = name;
  }

  function summarizeRepos(builds) {
    const byRepo = new Map();
    (builds || []).forEach((build) => {
      const key = build.repo || "unknown repo";
      if (!byRepo.has(key)) {
        byRepo.set(key, []);
      }
      byRepo.get(key).push(build);
    });

    return [...byRepo.entries()]
      .map(([repo, repoBuilds]) => {
        const settled = repoBuilds.filter((b) => !inProgressStatuses.has(b.status));
        let status = "NONE";
        if (settled.some((b) => b.status === "FAIL")) {
          status = "FAIL";
        } else if (settled.some((b) => b.status === "CONNECTION_ERROR")) {
          status = "CONNECTION_ERROR";
        } else if (settled.some((b) => b.status === "APPROVAL")) {
          status = "APPROVAL";
        } else if (settled.length && settled.every((b) => b.status === "PASS")) {
          status = "PASS";
        } else if (settled.length) {
          status = "UNKNOWN";
        }
        const isRunning = repoBuilds.some((b) => inProgressStatuses.has(b.status));
        if (status === "NONE" && isRunning) {
          const hasRunning = repoBuilds.some((b) => b.status === "RUNNING");
          const hasWaiting = repoBuilds.some((b) => b.status === "WAITING");
          status = !hasRunning && hasWaiting ? "WAITING" : "RUNNING";
        }
        const workflows = [...repoBuilds].sort((a, b) =>
          String(a.workflow || "").localeCompare(String(b.workflow || "")),
        );
        return {
          repo,
          status,
          workflow_count: repoBuilds.length,
          is_running: isRunning,
          url: repo.includes("/") ? `https://github.com/${repo}` : "",
          workflows,
        };
      })
      .sort((a, b) => a.repo.localeCompare(b.repo));
  }

  function createWorkflowRow(workflow) {
    const item = document.createElement("li");
    item.className = `workflow-row workflow-${String(workflow.status || "").toLowerCase()}`;

    const name = document.createElement("span");
    name.className = "workflow-name";
    name.textContent = workflow.workflow || "(unnamed)";

    const status = document.createElement("span");
    status.className = "workflow-status";
    status.textContent = workflow.status || "";

    if (workflow.url) {
      const link = document.createElement("a");
      link.href = workflow.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.append(name, status);
      item.append(link);
    } else {
      item.append(name, status);
    }
    return item;
  }

  function renderRepos(builds) {
    if (!reposSection || !repoList) return;
    repoList.querySelectorAll("details.repo-row[open]").forEach((el) => {
      if (el.dataset.repo) {
        expandedRepos.add(el.dataset.repo);
      }
    });
    const repos = summarizeRepos(builds);
    repoList.replaceChildren();
    if (!repos.length) {
      reposSection.hidden = true;
      return;
    }

    reposSection.hidden = false;
    if (repoCount) {
      repoCount.textContent = `${repos.length} watched`;
    }

    repos.forEach((entry, index) => {
      const item = document.createElement("li");
      item.className = `repo-item`;
      item.style.setProperty("--delay", `${index * 40}ms`);

      const details = document.createElement("details");
      details.className = `repo-row repo-${String(entry.status || "").toLowerCase()}`;
      if (entry.is_running) {
        details.classList.add("is-running");
      }
      details.dataset.repo = entry.repo;
      if (expandedRepos.has(entry.repo)) {
        details.open = true;
      }
      details.addEventListener("toggle", () => {
        if (details.open) {
          expandedRepos.add(entry.repo);
        } else {
          expandedRepos.delete(entry.repo);
        }
      });

      const summary = document.createElement("summary");
      summary.className = "repo-summary";

      const chevron = document.createElement("span");
      chevron.className = "repo-chevron";
      chevron.setAttribute("aria-hidden", "true");

      const name = document.createElement("span");
      name.className = "repo-name";
      appendRepoLabel(name, entry.repo);

      const meta = document.createElement("span");
      meta.className = "repo-meta";
      const count = entry.workflow_count;
      meta.textContent = `${count} workflow${count === 1 ? "" : "s"}`;
      if (entry.is_running) {
        meta.textContent += " · running";
      }

      const status = document.createElement("span");
      status.className = "repo-status";
      status.textContent = entry.status || "";

      summary.append(chevron, name, meta, status);

      if (entry.url) {
        const link = document.createElement("a");
        link.className = "repo-external";
        link.href = entry.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.title = `Open ${entry.repo} on GitHub`;
        link.setAttribute("aria-label", `Open ${entry.repo} on GitHub`);
        link.textContent = "↗";
        link.addEventListener("click", (event) => {
          event.stopPropagation();
        });
        summary.append(link);
      }

      const workflowList = document.createElement("ul");
      workflowList.className = "repo-workflows";
      entry.workflows.forEach((workflow) => {
        workflowList.append(createWorkflowRow(workflow));
      });

      details.append(summary, workflowList);
      item.append(details);
      repoList.append(item);
    });
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

      const repo = document.createElement("span");
      repo.className = "issue-repo";
      appendRepoLabel(repo, issue.repo);

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

    // Quiet reconcile polls: keep the current status composition stable.
    if (fetching) {
      applyQuietFetch(true);
      return;
    }
    if (quietFetch) {
      applyQuietFetch(false);
    }

    const shown = displayStatus(status, isRunning, false, payload.builds);
    const nextStatusKey = statusKey(status, isRunning, shown);
    const nextBuildsKey = buildsKey(payload.builds);
    const statusChanged = nextStatusKey !== lastStatusKey;
    const buildsChanged = nextBuildsKey !== lastBuildsKey;

    if (statusChanged) {
      lastStatusKey = nextStatusKey;
      const awaiting = shown === "RUNNING" || shown === "WAITING" || shown === "APPROVAL";
      setLight("purple", status === "CONNECTION_ERROR" ? "on" : "off");
      setLight("green", status === "PASS" && !awaiting ? "on" : "off");
      setLight("red", status === "FAIL" || status === "UNKNOWN" ? "on" : "off");
      setLight("yellow", isRunning || shown === "WAITING" || shown === "APPROVAL" ? "pulse" : "off");
      setLight("blue", "off");

      if (statusWord) {
        const nextWord = statusWords[shown] || statusWords.NONE;
        if (statusWord.textContent !== nextWord) {
          statusWord.textContent = nextWord;
          scheduleFitStatusWord();
        }
      }

      if (shown === "RUNNING" || shown === "WAITING" || shown === "APPROVAL") {
        summary.textContent = summaries[shown];
      } else {
        summary.textContent = summaries[status] || summaries.NONE;
        if (isRunning) {
          summary.textContent += " · build running";
        }
      }
    }

    if (buildsChanged) {
      lastBuildsKey = nextBuildsKey;
      renderRepos(payload.builds);
      renderIssues(payload.builds);
    }

    if (window.BuildMonitorTicker) {
      window.BuildMonitorTicker.applyTiming({
        ...payload,
        fetching: false,
        status: shown,
      });
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
