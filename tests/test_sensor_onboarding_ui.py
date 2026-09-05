from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sensor_onboarding_prioritizes_three_real_paths():
    html = (ROOT / "app" / "performance-running.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "js" / "performance-running.js").read_text(encoding="utf-8")

    assert "Synchronisation Android automatique" in html
    assert "Importer mes fichiers FIT et Wellness" in html
    assert "Continuer sans montre" in html
    assert '<details class="secondary-providers">' in html
    assert "async function verifyAtlasConnect" in script
    assert "Atlas indique uniquement les données réellement publiées" in script
    assert "data-atlas-connect-check" in script
