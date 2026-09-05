from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recovery_gauge_markup_and_script_are_present():
    html = (ROOT / "app" / "atlas-cockpit.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "js" / "atlas-cockpit.js").read_text(encoding="utf-8")

    assert "data-recovery-gauge" in html
    assert "data-recovery-gauge-marker" in html
    assert "data-recovery-zone" in html
    assert 'class="positive" data-recovery-label' not in html
    assert "updateRecoveryTone" in script
    assert "FC repos" in script
    assert "updateRecoveryGauge" in script
    assert 'gauge.setAttribute("aria-valuenow"' in script


def test_recovery_gauge_uses_four_decision_zones():
    css = (ROOT / "app" / "css" / "atlas-cockpit.css").read_text(encoding="utf-8")

    assert ".recovery-gauge-track" in css
    assert "#ef5264 40%" in css
    assert "#ff922f 55%" in css
    assert "#f6d54a 70%" in css
    assert "#45dfa6 100%" in css
