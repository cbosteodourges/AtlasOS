from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_connections_page_separates_setup_from_training():
    page = (ROOT / "app" / "atlas-connections.html").read_text(encoding="utf-8")
    coach = (ROOT / "app" / "performance-running.html").read_text(encoding="utf-8")
    nav = (ROOT / "app" / "js" / "atlas-global-nav.js").read_text(encoding="utf-8")
    script = (ROOT / "app" / "js" / "atlas-connections.js").read_text(encoding="utf-8")

    assert "Comment souhaitez-vous commencer ?" in page
    assert "Atlas Connect" in page and "Importer Garmin" in page
    assert "Continuer sans montre" in page
    assert 'data-coach-nav="sensors"' not in nav
    assert 'href="./atlas-connections.html" aria-label="Gérer les connexions et les données"' in nav
    assert 'id="syncPanel" hidden' in coach
    assert "Gérer mes connexions et mes données" in coach
    assert "Non transmise par Santé Connect" in script
