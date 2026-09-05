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
    assert "Vos connexions et vos données" in script
    assert "Source actuelle" in script
    assert 'connection.provider === "health-connect" ? "atlas-connect"' in script
    assert "Garmin Wellness" in script
    assert "absente de Santé Connect" in script
    assert "margin-left:280px" not in (ROOT / "app" / "css" / "atlas-connections.css").read_text(encoding="utf-8")
    assert 'class="profile-calibration-next"' in coach
