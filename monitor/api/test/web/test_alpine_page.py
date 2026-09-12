from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WEB = ROOT / "monitor" / "device" / "web"
WEB_PUBLIC = WEB / "public"


def test_status_page_binds_alpine_monitor():
    html = (WEB_PUBLIC / "index.html").read_text(encoding="utf-8")
    assert 'x-data="monitor"' in html


def test_status_page_loads_typed_alpine_bundle():
    html = (WEB_PUBLIC / "index.html").read_text(encoding="utf-8")
    assert 'src="/monitor.js"' in html


def test_privacy_page_loads_typed_bundle():
    html = (WEB_PUBLIC / "privacy.html").read_text(encoding="utf-8")
    assert 'src="/monitor.js"' in html
    assert 'src="/posthog.js"' not in html


def test_status_page_lets_alpine_render_status_without_vanilla_app_js():
    html = (WEB_PUBLIC / "index.html").read_text(encoding="utf-8")
    assert 'x-for="(entry, index) in repos"' in html
    assert 'src="/app.js"' not in html
    assert not (WEB_PUBLIC / "app.js").is_file()


def test_status_page_does_not_load_handwritten_countdown_script():
    html = (WEB_PUBLIC / "index.html").read_text(encoding="utf-8")
    assert 'src="/countdown.js"' not in html


def test_typed_bundle_starts_failure_push_controls():
    script = (WEB / "src" / "web" / "start.ts").read_text(encoding="utf-8")
    assert "startPushControls" in script


def test_typed_bundle_boots_posthog():
    script = (WEB / "src" / "web" / "start.ts").read_text(encoding="utf-8")
    assert "bootPosthog" in script


def test_status_page_declares_python_api_origin():
    html = (WEB_PUBLIC / "index.html").read_text(encoding="utf-8")
    assert 'name="monitor-api-origin"' in html


def test_status_client_opens_websocket_on_python_api():
    script = (WEB / "src" / "web" / "liveStatus.ts").read_text(encoding="utf-8")
    assert "statusWsUrl" in script
    assert "monitor-api-origin" in script


def test_web_assets_directory_is_public():
    config = (WEB / "wrangler.jsonc").read_text(encoding="utf-8")
    assert '"directory": "./public"' in config


def test_web_bundle_writes_into_public():
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert "--outfile=./public/monitor.js" in package


def test_dev_watches_alpine_bundle_without_cloudflare():
    import json

    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    dev = package["scripts"]["dev"]
    assert "esbuild" in dev
    assert "--watch" in dev
    assert "wrangler" not in dev


def test_dev_serves_alpine_public_over_http():
    import json

    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert "--servedir=./public" in package["scripts"]["dev"]


def test_cloudflare_dev_uses_wrangler_worker():
    import json

    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"]["dev:worker"] == "wrangler dev"


def test_frontend_deploys_to_cloudflare_pages():
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert "pages deploy" in package


def test_pages_deploy_does_not_stamp_python_api_origin():
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert "stamp-api-origin.mjs" not in package
    assert not (WEB / "scripts" / "stamp-api-origin.mjs").is_file()


def test_typed_posthog_boot_fetches_config_json():
    script = (WEB / "src" / "web" / "posthog.ts").read_text(encoding="utf-8")
    assert "posthog-config.json" in script


def test_pages_ships_default_posthog_config():
    path = WEB_PUBLIC / "posthog-config.json"
    assert path.is_file()


def test_pulumi_example_declares_pages_project():
    example = (ROOT / "infra" / "cloudflare" / "Pulumi.prod.yaml.example").read_text(encoding="utf-8")
    assert "pagesProjectName" in example
    assert "pagesHostnames" in example


def test_pages_deploy_waits_for_frontend_tests():
    import yaml

    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    needs = ci["jobs"]["deploy-pages"]["needs"]
    if isinstance(needs, str):
        needs = [needs]
    assert "test" in needs
    assert "web" in needs


def test_api_worker_deploy_builds_the_alpine_bundle():
    import json

    import yaml

    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    runs = "\n".join(str(step.get("run", "")) for step in ci["jobs"]["deploy-api"]["steps"])
    assert "build:web" in runs
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    assert "build:web" in package["scripts"]["deploy:api"]


def test_web_public_ships_static_site():
    for name in (
        "styles.css",
        "favicon.svg",
        "privacy.html",
        "manifest.webmanifest",
        "sw.js",
        "social-share.png",
        "posthog-config.json",
    ):
        assert (WEB_PUBLIC / name).is_file(), name


def test_design_pack_syncs_into_web_public():
    script = (ROOT / "bin" / "sync-design-pack.sh").read_text(encoding="utf-8")
    assert 'WEB="$ROOT/monitor/device/web/public"' in script


def test_status_site_is_not_under_legacy_monitor_web():
    legacy = ROOT / "monitor" / "web" / "index.html"
    assert not legacy.is_file()
