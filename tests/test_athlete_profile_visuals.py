from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_profile_uses_atlas_coach_visual_language():
    html = (ROOT / "app" / "atlas-cockpit.html").read_text(encoding="utf-8")
    assert html.count('class="physiology-ring') == 5
    assert html.count("data-physiology-period") == 10
    assert "data-physiology-chart" in html
    assert "insight-lanes" in html


def test_profile_history_is_real_and_longitudinal():
    server = (ROOT / "tools" / "atlas_web_server.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "src" / "training" / "post_sync_orchestrator.py").read_text(encoding="utf-8")
    assert '"physiology_history": load_physiology_history()' in server
    assert "history = [item for item in history" in orchestrator
    assert "history[-5000:]" in orchestrator
    assert "history[-365:]" not in orchestrator


def test_profile_chart_requires_two_real_measurements():
    script = (ROOT / "app" / "js" / "atlas-cockpit.js").read_text(encoding="utf-8")
    assert "points.length < 2" in script
    assert "Une deuxième mesure distincte" in script


def test_only_validated_physiology_is_charted():
    server = (ROOT / "tools" / "atlas_web_server.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "src" / "training" / "post_sync_orchestrator.py").read_text(encoding="utf-8")
    assert '"schema": "validated_profile_v1"' in orchestrator
    assert 'raw.get("schema") != "validated_profile_v1"' in server
    assert '"sv2_speed_kmh": (6, 28)' in server
