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
    assert '"atlas_retrospective_v1"' in server
    assert '"sv2_speed_kmh": (6, 28)' in server


def test_historical_fit_backfill_is_explicit_and_anchored():
    orchestrator = (ROOT / "src" / "training" / "post_sync_orchestrator.py").read_text(encoding="utf-8")
    assert "def _retrospective_physiology" in orchestrator
    assert '"source": "historical_fit"' in orchestrator
    assert "tendance terrain hebdomadaire sur 42 jours" in orchestrator
    assert "offset = float(target) - float(values[-1])" in orchestrator


def test_historical_curve_uses_weekly_points_and_active_reference():
    orchestrator = (ROOT / "src" / "training" / "post_sync_orchestrator.py").read_text(encoding="utf-8")
    assert "cursor += timedelta(days=7)" in orchestrator
    assert "start = endpoint - timedelta(days=41)" in orchestrator
    assert "return {**saved, **snapshot}" in orchestrator


def test_estimate_never_silently_replaces_active_reference():
    orchestrator = (ROOT / "src" / "training" / "post_sync_orchestrator.py").read_text(encoding="utf-8")
    assert "profile = previous" in orchestrator
    assert "_program_proposal(proposed_profile" in orchestrator
    assert '"maximum_heart_rate_bpm": maximum_hr' in orchestrator
