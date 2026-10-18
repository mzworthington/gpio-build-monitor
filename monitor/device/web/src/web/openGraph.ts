import type { BuildDetail } from '../ci';
import { collectOpenFindings, collectOpenPulls, summarizeRepos } from './presentPage';

const TAGLINE = 'CI you notice without looking for it - on the web or glowing on your desk.';

export function openWorkLine(pulls: number, findings: number): string {
  const prLabel = `${pulls} PR${pulls === 1 ? '' : 's'}`;
  const findingLabel = `${findings} finding${findings === 1 ? '' : 's'}`;
  return `${prLabel} and ${findingLabel}`;
}

function replaceMetaContent(html: string, attr: 'property' | 'name', key: string, content: string): string {
  const pattern = new RegExp(`(<meta\\s[\\s\\S]*?${attr}="${key}"[\\s\\S]*?content=")[\\s\\S]*?(")`);
  return html.replace(pattern, `$1${content}$2`);
}

/** Puts the live open-work counts into the tags crawlers read. Counts once per repo. */
export function stampOpenGraph(html: string, builds: BuildDetail[]): string {
  const repos = summarizeRepos(builds);
  const pulls = collectOpenPulls(repos).length;
  const findings = collectOpenFindings(repos).length;
  if (pulls === 0 && findings === 0) {
    return html;
  }
  const content = `${openWorkLine(pulls, findings)}. ${TAGLINE}`;
  return replaceMetaContent(
    replaceMetaContent(
      replaceMetaContent(html, 'property', 'og:description', content),
      'name',
      'twitter:description',
      content,
    ),
    'name',
    'description',
    content,
  );
}
