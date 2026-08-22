from backend.config import name_space
from backend.analytics.calculations import WEEKDAYS, LATERALITY_LABELS


def test_name_space_import():
    assert name_space.WEEKDAYS == WEEKDAYS
    assert name_space.LATERALITY_LABELS == LATERALITY_LABELS
