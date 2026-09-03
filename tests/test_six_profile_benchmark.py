import unittest

from scripts.generate_six_profile_benchmark import CASES, START
from src.training.program_generator import TrainingProgramGenerator
from src.training.program_models import ProgramGenerationSettings


class SixProfileBenchmarkTests(unittest.TestCase):
    def test_all_six_profiles_generate_valid_complete_programs(self):
        self.assertEqual([item[0] for item in CASES], list("ABCDEF"))
        for code, _, athlete, goal, sessions in CASES:
            program = TrainingProgramGenerator().generate(
                profile=athlete, goal=goal, start_date=START,
                settings=ProgramGenerationSettings(
                    running_sessions_per_week=sessions,
                    optional_running_sessions_per_week=0 if code in {"A", "B"} else 1,
                    strength_sessions_per_week=1 if code in {"A", "B"} else 2,
                    preferred_quality_days=["tuesday", "friday"],
                    maximum_weekly_progression_percent=6 if code in {"A", "B"} else 8,
                ), available_dynamic_metrics={"recovery_status"},
            )
            self.assertGreaterEqual(program.duration_weeks, 10)
            self.assertGreater(program.total_running_workouts, 0)
            self.assertEqual(program.end_date, goal.event_date)


if __name__ == "__main__":
    unittest.main()
