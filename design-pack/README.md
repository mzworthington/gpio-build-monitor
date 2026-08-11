# Design pack

Brand assets for the GPIO build monitor UI — favicon, logo, apple-touch, and Open Graph card.

## Identity

| Token | Value | Role |
| --- | --- | --- |
| Background | `#000000` | Icon plate (UI surfaces stay `#0b0e13`) |
| Ink | `#f3f0e8` | Headings |
| Muted | `#8a92a1` | Taglines |
| Fetch | `#6aa8ff` | Blue LED |
| Pass | `#3dd68c` | Green LED + dial arc |
| Run | `#efc15a` | Yellow LED |
| Fail | `#ff6b6b` | Red LED |
| Error | `#c084fc` | Purple LED |
| Display | Syne | Wordmark |
| Body | Manrope | Tagline |

**Mark:** five status LEDs on a dial ring — the same signal lights as the desk hardware and the web UI.

## Sources

| File | Purpose |
| --- | --- |
| `mark.svg` | Rounded logo (in-app brand mark, `logo.png`) |
| `mark-square.svg` | Full-bleed square (apple-touch / PWA; OS masks corners). Dial
  stays inside the circular safe zone so orbs aren’t clipped. |
| `favicon.svg` | Tab icon — **opaque full-bleed plate** (no rounded alpha; Android
  shortcuts composite transparent corners onto white) |
| `social-share.svg` | Open Graph / Twitter card (1200×630) |

## Shipped to the app

```text
monitor/web/
  favicon.svg
  favicon.png
  favicon-32.png
  logo.svg
  logo.png
  apple-touch-icon.png
  icon-192.png
  icon-512.png
  social-share.png
  manifest.webmanifest
```

`index.html` and `templates/status.html.j2` wire favicon, apple-touch, theme-color,
web manifest (maskable PWA icon, ArchLens-style), and `og:` / `twitter:` image meta
to `/social-share.png`.

## Regenerate PNGs

```bash
bin/sync-design-pack.sh   # requires librsvg: brew install librsvg
```
