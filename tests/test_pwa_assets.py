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
            "assets/anatomy/servier/foot-ankle-anterior.png",
            "assets/anatomy/servier/foot-ankle-lateral-deep.png",
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
        self.assertIn("atlas-global-nav.js?v=23", hub)
        self.assertIn("atlas-pwa.js?v=3", hub)
        self.assertIn(
            'document.body.classList.toggle("has-atlas-context-nav", !isHub)',
            navigation,
        )

    def test_styles_and_scripts_are_network_first(self):
        worker = (APP_ROOT / "service-worker.js").read_text(encoding="utf-8")
        pwa = (APP_ROOT / "js" / "atlas-pwa.js").read_text(encoding="utf-8")
        self.assertIn('CACHE_NAME = "atlas-shell-v52"', worker)
        self.assertIn('["style", "script"]', worker)
        self.assertIn('fetch(event.request, { cache: "no-store" })', worker)
        self.assertIn('service-worker.js?v=4', pwa)

    def test_training_page_has_one_calendar_renderer(self):
        page = (APP_ROOT / "performance-running.html").read_text(
            encoding="utf-8"
        )
        legacy = (APP_ROOT / "js" / "performance-running.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-calendar-renderer="premium"', page)
        self.assertIn(
            'planPanel.dataset.calendarRenderer !== "premium"',
            legacy,
        )
        self.assertIn('performance-running.js?v=22', page)
        self.assertIn('atlas-training-calendar.js?v=101', page)

    def test_legacy_execution_timeline_is_rebased_on_planned_warmup(self):
        calendar = (APP_ROOT / "js" / "atlas-training-calendar.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("prescribedWarmupSeconds", calendar)
        self.assertIn("timestampsAreCompressed", calendar)
        self.assertIn("firstStart + structuredWorkSeconds", calendar)
        self.assertIn(
            'zone: 1, duration: firstStart / 60, label: "Échauffement"',
            calendar,
        )
        self.assertIn(
            'zone: 1, duration: coolDownSeconds / 60, label: "Retour au calme"',
            calendar,
        )
        self.assertIn("const heightPercent = segment =>", calendar)
        self.assertIn("(speed - reference) * 16", calendar)
        self.assertIn("const detectedRecovery =", calendar)
        self.assertIn('"Retour au calme" : "Données non mesurées"', calendar)
        self.assertIn('recoveryRole: isDetectedCoolDown ? "cool_down"', calendar)
        self.assertIn('Fractions, récupérations et retour au calme', calendar)
        self.assertIn('<span>Après la fraction</span>', calendar)

    def test_planned_timeline_uses_stable_semantic_colors(self):
        calendar = (APP_ROOT / "js" / "atlas-training-calendar.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("const ATLAS_TIMELINE_ROLE_COLORS = Object.freeze", calendar)
        self.assertIn("easy: DISPLAY_ZONE_COLORS[2]", calendar)
        self.assertIn("recovery: DISPLAY_ZONE_COLORS[1]", calendar)
        self.assertIn("cool_down: DISPLAY_ZONE_COLORS[1]", calendar)
        self.assertIn('1: "#49d17d"', calendar)
        self.assertIn('2: "#38a9ff"', calendar)
        self.assertIn('if (blockType === "cool_down")', calendar)
        self.assertIn("color: plannedTimelineColor(workout, block)", calendar)
        self.assertIn(
            "segment.color || DISPLAY_ZONE_COLORS[segment.zone]",
            calendar,
        )

    def test_desktop_content_tracks_the_rendered_header_height(self):
        calendar = (APP_ROOT / "js" / "atlas-training-calendar.js").read_text(
            encoding="utf-8"
        )
        styles = (APP_ROOT / "css" / "performance-running.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("const HEADER_CONTENT_GAP_PX = 20", calendar)
        self.assertIn("new ResizeObserver(syncTrainingHeaderOffset)", calendar)
        self.assertIn('"--atlas-training-header-offset"', calendar)
        self.assertIn(
            "padding-top: var(--atlas-training-header-offset, 318px)",
            styles,
        )

    def test_mobile_global_navigation_keeps_four_labeled_destinations(self):
        navigation_css = (APP_ROOT / "css" / "atlas-global-nav.css").read_text(
            encoding="utf-8"
        )
        navigation = (APP_ROOT / "js" / "atlas-global-nav.js").read_text(
            encoding="utf-8"
        )
        health_css = (APP_ROOT / "css" / "atlas-health.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "grid-template-columns: repeat(4, minmax(0, 1fr))",
            navigation_css,
        )
        self.assertIn(".atlas-global-nav .atlas-primary-nav", navigation_css)
        self.assertNotIn('data-history-root="true"', navigation)
        self.assertIn('data-coach-nav="history"', navigation)
        self.assertIn(".atlas-global-nav .atlas-nav-label", navigation_css)
        self.assertIn("opacity: 1", navigation_css)
        self.assertIn(".app.has-atlas-global-nav", navigation_css)
        self.assertIn("body > main.app", health_css)
        self.assertIn("grid-template-columns:minmax(0,1fr)!important", health_css)


if __name__ == "__main__":
    unittest.main()
