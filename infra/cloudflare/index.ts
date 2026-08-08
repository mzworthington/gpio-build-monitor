import * as cloudflare from '@pulumi/cloudflare';
import * as pulumi from '@pulumi/pulumi';

const config = new pulumi.Config();
const accountId = config.require('accountId');
const zoneId = config.require('zoneId');

/**
 * Worker script name. Prefers `workerName`; falls back to `pagesProjectName` so
 * edge-dns `setup-cloudflare-hosting.sh` / CI vars keep working unchanged.
 */
function resolveWorkerName(): string {
  const name = config.get('workerName') ?? config.get('pagesProjectName');
  if (!name) {
    throw new Error('Set workerName (or pagesProjectName) to the Worker script name');
  }
  return name;
}

/** Hostnames attached via Workers custom domains (DNS + certs managed by Cloudflare). */
function resolveWorkerHostnames(): string[] {
  const listed =
    config.getObject<string[]>('workerHostnames') ??
    config.getObject<string[]>('pagesHostnames');
  if (listed && listed.length > 0) return listed;
  throw new Error(
    'Set workerHostnames (or pagesHostnames) to a JSON array, e.g. ["monitor.mzworthington.co.uk"]',
  );
}

const workerName = resolveWorkerName();
const workerHostnames = resolveWorkerHostnames();

const zone = cloudflare.getZoneOutput({ zoneId });

/** Account Worker identity; script content is deployed with wrangler (see /worker). */
const worker = new cloudflare.Worker('monitor', {
  accountId,
  name: workerName,
  subdomain: {
    enabled: true,
    previewsEnabled: true,
  },
  observability: {
    enabled: true,
    logs: {
      enabled: true,
      invocationLogs: true,
    },
  },
});

for (const hostname of workerHostnames) {
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
export const workerHostnamesOut = workerHostnames;
export const zoneName = zone.name;
