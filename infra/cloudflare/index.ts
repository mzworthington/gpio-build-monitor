import * as cloudflare from '@pulumi/cloudflare';
import * as pulumi from '@pulumi/pulumi';

const config = new pulumi.Config();
const accountId = config.require('accountId');
const zoneId = config.require('zoneId');

function resolveWorkerName(): string {
  const name = config.get('workerName') ?? config.get('pagesProjectName');
  if (!name) {
    throw new Error('Set workerName (or pagesProjectName) to the Worker script name');
  }
  return name;
}

function resolveHostnames(): string[] {
  const listed =
    config.getObject<string[]>('workerHostnames') ??
    config.getObject<string[]>('pagesHostnames');
  if (listed && listed.length > 0) return listed;
  throw new Error(
    'Set workerHostnames (or pagesHostnames) to a JSON array, e.g. ["monitor.mzworthington.co.uk"]',
  );
}

const workerName = resolveWorkerName();
const hostnames = resolveHostnames();
const zone = cloudflare.getZoneOutput({ zoneId });

const pagesProject = new cloudflare.PagesProject('site', {
  accountId,
  name: workerName,
  productionBranch: 'main',
});

const worker = new cloudflare.Worker(
  'monitor',
  {
    accountId,
    name: workerName,
  },
  { ignoreChanges: ['subdomain', 'observability'] },
);

for (const hostname of hostnames) {
  const safe = hostname.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '');

  new cloudflare.WorkersCustomDomain(`worker-domain-${safe}`, {
    accountId,
    zoneId,
    zoneName: zone.name,
    hostname,
    service: worker.name,
  });

  new cloudflare.ObservatoryScheduledTest(`observatory-${safe}`, {
    zoneId,
    url: hostname,
  });
}

export const workerNameOut = worker.name;
export const workerId = worker.id;
export const hostnamesOut = hostnames;
export const pagesProjectNameOut = pagesProject.name;
export const zoneName = zone.name;
