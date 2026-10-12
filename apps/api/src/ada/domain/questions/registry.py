from pathlib import Path

import yaml

from ada.spi.decision import QuestionSet

_DIR = Path(__file__).parent


def load(version: str = "v1") -> QuestionSet:
    return QuestionSet(**yaml.safe_load((_DIR / f"{version}.yaml").read_text()))
