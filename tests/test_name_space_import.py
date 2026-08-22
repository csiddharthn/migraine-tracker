from backend.config.name_space import cfg
from backend.analytics.calculations import WEEKDAYS, LATERALITY_LABELS


def test_name_space_import():
    assert cfg.WEEKDAYS == WEEKDAYS
    assert cfg.LATERALITY_LABELS == LATERALITY_LABELS
