"""
ATLAS OS
Système de journalisation.
"""

from datetime import datetime


class AtlasLogger:
    @staticmethod
    def info(message):
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"[INFO] {message}"
        )

    @staticmethod
    def warning(message):
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"[WARNING] {message}"
        )

    @staticmethod
    def error(message):
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"[ERROR] {message}"
        )