import * as cloudflare from '@pulumi/cloudflare';
import * as pulumi from '@pulumi/pulumi';

const config = new pulumi.Config();
const accountId = config.require('accountId');
const zoneId = config.require('zoneId');
const pagesProjectName = config.get('pagesProjectName') ?? config.get('workerName');
if (!pagesProjectName) {
  throw new Error('Set pagesProjectName (or workerName) to the Pages project name');
}

/** Public hostnames for the status UI (Pages custom domains). */
function resolveHostnames(): string[] {
  const listed =
    config.getObject<string[]>('pagesHostnames') ??
    config.getObject<string[]>('workerHostnames');
  if (listed && listed.length > 0) return listed;
  throw new Error(
    'Set pagesHostnames (or workerHostnames) to a JSON array, e.g. ["monitor.mzworthington.co.uk"]',
  );
}

const pagesHostnames = resolveHostnames();

const pagesProject = new cloudflare.PagesProject('site', {
  accountId,
  name: pagesProjectName,
  productionBranch: 'main',
});

for (const hostname of pagesHostnames) {
  const safe = hostname.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '');
  const dns = new cloudflare.DnsRecord(
    `pages-dns-${safe}`,
    {
      zoneId,
      name: hostname,
      type: 'CNAME',
      content: pagesProject.subdomain,
      proxied: true,
      ttl: 1,
      comment: 'Cloudflare Pages',
    },
    { deleteBeforeReplace: true },
  );

  new cloudflare.PagesDomain(
    `pages-domain-${safe}`,
    {
      accountId,
      projectName: pagesProject.name,
      name: hostname,
    },
    { dependsOn: [dns] },
  );

  new cloudflare.ObservatoryScheduledTest(`observatory-${safe}`, {
    zoneId,
    url: hostname,
  });
}

const zone = cloudflare.getZoneOutput({ zoneId });

export const pagesProjectNameOut = pagesProject.name;
export const pagesSubdomain = pagesProject.subdomain;
export const pagesHostnamesOut = pagesHostnames;
export const zoneName = zone.name;
