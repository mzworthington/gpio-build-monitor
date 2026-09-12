import type { BuildDetail } from '../ci';

export type ShownBuild = Pick<BuildDetail, 'status'> & Partial<BuildDetail>;

const ATTENTION = new Set(['APPROVAL', 'FAIL', 'CONNECTION_ERROR']);
const IN_PROGRESS_OVERRIDES = new Set(['PASS', 'NONE', 'UNKNOWN']);

export function shownStatus(input: {
  status: string;
  is_running: boolean;
  fetching: boolean;
  builds: ShownBuild[];
}): string {
  if (input.fetching) return input.status;
  if (ATTENTION.has(input.status)) return input.status;
  const buildStatuses = new Set(input.builds.map((build) => build.status));
  if (buildStatuses.has('APPROVAL')) return 'APPROVAL';
  if (buildStatuses.has('RUNNING')) return 'RUNNING';
  if (buildStatuses.has('WAITING')) return 'WAITING';
  if (input.is_running && IN_PROGRESS_OVERRIDES.has(input.status)) return 'RUNNING';
  return input.status;
}
