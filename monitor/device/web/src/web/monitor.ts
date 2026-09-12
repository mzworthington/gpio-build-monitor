import type { BuildDetail, PullRequestItem, SecurityFinding } from '../ci';
import {
  collectOpenFindings,
  collectOpenPulls,
  findingCardClass,
  findingRowClass,
  prChipClass,
  presentChrome,
  pullCardClass,
  pullRowClass,
  securityChipClass,
  splitRepo,
  summarizeRepos,
  taggedSecurityItems,
  type LightMode,
  type OpenFindingGlance,
  type OpenPullGlance,
  type RepoSummary,
  type TaggedFinding,
} from './presentPage';
import { type ShownBuild } from './shownStatus';

export type AlpineHost = {
  data: (name: string, factory: () => MonitorPage) => void;
  $data?: (el: object) => MonitorPage;
};

export type MonitorSnapshot = {
  status: string;
  is_running: boolean;
  fetching: boolean;
  builds: ShownBuild[];
  poll_in_seconds?: number;
  last_checked_at?: number | null;
  next_check_at?: number | null;
};

export type MonitorPage = {
  shown: string;
  fetching: boolean;
  statusWord: string;
  summary: string;
  connection: string;
  connectionLabel: string;
  lights: Record<'blue' | 'green' | 'yellow' | 'red' | 'purple', LightMode>;
  repos: RepoSummary[];
  issues: BuildDetail[];
  openTab: 'prs' | 'findings';
  expanded: Record<string, boolean>;
  applySnapshot: (snapshot: MonitorSnapshot) => MonitorPage;
  setConnection: (state: string, label: string) => MonitorPage;
  rememberRepo: (repo: string, open: boolean) => void;
  repoIsOpen: (repo: string) => boolean;
  repoOrg: (repo: string) => string;
  repoName: (repo: string) => string;
  workflowMeta: (entry: RepoSummary) => string;
  prLabel: (entry: RepoSummary) => string;
  securityLabel: (entry: RepoSummary) => string;
  prChipClass: (entry: RepoSummary) => string;
  securityChipClass: (entry: RepoSummary) => string;
  prItems: (entry: RepoSummary) => PullRequestItem[];
  securityItems: (entry: RepoSummary) => TaggedFinding[];
  openPulls: () => OpenPullGlance[];
  openFindings: () => OpenFindingGlance[];
  openCount: () => number;
  openLabel: () => string;
  pullRowClass: (draft: boolean) => string;
  findingRowClass: (severity: string | null) => string;
  pullCardClass: (draft: boolean) => string;
  findingCardClass: (severity: string | null) => string;
  itemStatus: (kind: 'pr' | 'security', item: PullRequestItem | SecurityFinding) => string;
  repoRowClass: (entry: RepoSummary) => string;
  workflowRowClass: (workflow: BuildDetail) => string;
  issueClass: (issue: BuildDetail) => string;
  lightClass: (name: keyof MonitorPage['lights']) => Record<string, boolean>;
};

const IDLE_LIGHTS: MonitorPage['lights'] = {
  blue: 'off',
  green: 'off',
  yellow: 'off',
  red: 'off',
  purple: 'off',
};

export function registerMonitor(alpine: AlpineHost): void {
  alpine.data('monitor', () => ({
    shown: 'NONE',
    fetching: false,
    statusWord: 'Idle',
    summary: 'Waiting for status…',
    connection: 'connecting',
    connectionLabel: 'Connecting…',
    lights: { ...IDLE_LIGHTS },
    repos: [],
    issues: [],
    openTab: 'prs',
    expanded: {},
    applySnapshot(this: MonitorPage, snapshot: MonitorSnapshot) {
      const ticker = (globalThis as { BuildMonitorTicker?: {
        setFetching?: (fetching: boolean) => void;
        applyTiming?: (payload: unknown) => void;
      } }).BuildMonitorTicker;
      if (snapshot.fetching) {
        this.fetching = true;
        this.lights = { ...this.lights, blue: 'on' };
        ticker?.setFetching?.(true);
        return this;
      }
      this.fetching = false;
      ticker?.setFetching?.(false);
      const chrome = presentChrome({
        status: snapshot.status,
        is_running: snapshot.is_running,
        fetching: false,
        builds: snapshot.builds as BuildDetail[],
      });
      this.shown = chrome.shown;
      this.statusWord = chrome.statusWord;
      this.summary = chrome.summary;
      this.lights = chrome.lights;
      this.issues = chrome.issues;
      this.repos = summarizeRepos(snapshot.builds as BuildDetail[]);
      const pulls = collectOpenPulls(this.repos);
      const findings = collectOpenFindings(this.repos);
      if (this.openTab === 'prs' && pulls.length === 0 && findings.length > 0) {
        this.openTab = 'findings';
      } else if (this.openTab === 'findings' && findings.length === 0 && pulls.length > 0) {
        this.openTab = 'prs';
      }
      ticker?.applyTiming?.({
        ...snapshot,
        fetching: false,
        status: chrome.shown,
      });
      return this;
    },
    setConnection(this: MonitorPage, state: string, label: string) {
      this.connection = state;
      this.connectionLabel = label;
      return this;
    },
    rememberRepo(this: MonitorPage, repo: string, open: boolean) {
      this.expanded = { ...this.expanded, [repo]: open };
    },
    repoIsOpen(this: MonitorPage, repo: string) {
      return this.expanded[repo] === true;
    },
    repoOrg(repo: string) {
      return splitRepo(repo).org;
    },
    repoName(repo: string) {
      return splitRepo(repo).name;
    },
    workflowMeta(entry: RepoSummary) {
      const count = entry.workflow_count;
      let text = `${count} workflow${count === 1 ? '' : 's'}`;
      if (entry.is_running) {
        text += ' · running';
      }
      return text;
    },
    prLabel(entry: RepoSummary) {
      const count = entry.pull_requests?.count ?? 0;
      return `${count} PR${count === 1 ? '' : 's'}`;
    },
    securityLabel(entry: RepoSummary) {
      const count = entry.security?.count ?? 0;
      return `${count} finding${count === 1 ? '' : 's'}`;
    },
    prChipClass(entry: RepoSummary) {
      return prChipClass(entry.pull_requests?.count ?? 0);
    },
    securityChipClass(entry: RepoSummary) {
      return securityChipClass(entry.security);
    },
    prItems(entry: RepoSummary) {
      return entry.pull_requests?.items ?? [];
    },
    securityItems(entry: RepoSummary) {
      return taggedSecurityItems(entry.security);
    },
    openPulls(this: MonitorPage) {
      return collectOpenPulls(this.repos);
    },
    openFindings(this: MonitorPage) {
      return collectOpenFindings(this.repos);
    },
    openCount(this: MonitorPage) {
      return this.openPulls().length + this.openFindings().length;
    },
    openLabel(this: MonitorPage) {
      const count = this.openCount();
      return `${count} to review`;
    },
    pullRowClass,
    findingRowClass,
    pullCardClass,
    findingCardClass,
    itemStatus(kind: 'pr' | 'security', item: PullRequestItem | SecurityFinding) {
      if (kind === 'pr') {
        return (item as PullRequestItem).draft ? 'draft' : 'open';
      }
      return String((item as SecurityFinding).severity || (item as SecurityFinding).state || 'open');
    },
    repoRowClass(entry: RepoSummary) {
      return `repo-row repo-${String(entry.status || '').toLowerCase()}${entry.is_running ? ' is-running' : ''}`;
    },
    workflowRowClass(workflow: BuildDetail) {
      return `workflow-row workflow-${String(workflow.status || '').toLowerCase()}`;
    },
    issueClass(issue: BuildDetail) {
      return `issue issue-${String(issue.status || '').toLowerCase()}`;
    },
    lightClass(this: MonitorPage, name: keyof MonitorPage['lights']) {
      const mode = this.lights[name];
      return { on: mode === 'on', pulse: mode === 'pulse' };
    },
  }));
}
