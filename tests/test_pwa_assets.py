"""Contrôles statiques de la fondation PWA Atlas."""

import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit


APP_ROOT = Path(__file__).resolve().parents[1] / "app"


class PwaAssetsTests(unittest.TestCase):
    def test_manifest_targets_and_icons_exist(self):
        manifest = json.loads(
            (APP_ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["display"], "standalone")
        self.assertTrue((APP_ROOT / manifest["start_url"]).exists())
        for icon in manifest["icons"]:
            self.assertTrue((APP_ROOT / icon["src"]).exists(), icon["src"])

    def test_service_worker_shell_files_exist_and_api_is_excluded(self):
        source = (APP_ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn('url.pathname.startsWith("/api/")', source)
        self.assertIn('caches.match("./offline.html")', source)
        for relative in (
            "atlas-cockpit.html",
            "performance-running.html",
            "atlas-hub.html",
            "atlas-metric-history.html",
            "offline.html",
            "manifest.webmanifest",
            "assets/atlas-logo-full.jpg",
            "assets/atlas-os-icon-avatar-master.png",
            "css/atlas-responsive.css",
            "js/atlas-pwa.js",
        ):
            self.assertTrue((APP_ROOT / relative).exists(), relative)

    def test_key_pages_do_not_reference_missing_local_files(self):
        import re

        for page_name in (
            "atlas-cockpit.html",
            "performance-running.html",
            "atlas-hub.html",
            "atlas-metric-history.html",
        ):
            source = (APP_ROOT / page_name).read_text(encoding="utf-8")
            references = re.findall(r'(?:src|href)="([^"#?]+)', source)
            for reference in references:
                parsed = urlsplit(reference)
                if parsed.scheme or reference.startswith("/"):
                    continue
                self.assertTrue(
                    (APP_ROOT / parsed.path).exists(),
                    f"{page_name}: {reference}",
                )

    def test_hub_global_navigation_replaces_legacy_sidebar(self):
        navigation = (APP_ROOT / "js" / "atlas-global-nav.js").read_text(
            encoding="utf-8"
        )
        hub = (APP_ROOT / "atlas-hub.html").read_text(encoding="utf-8")

        self.assertIn('app.querySelector(":scope > .sidebar")?.remove()', navigation)
        self.assertIn("atlas-global-nav.js?v=12", hub)


if __name__ == "__main__":
    unittest.main()

