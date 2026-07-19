"""Unit test fondasi untuk src/config.py (SPEC.md Bagian 5.2 urutan 1)."""

from src import config


def test_iqr_multiplier_matches_spec():
    # SPEC.md Bagian 2.2: batas atas = Q3 + 1.5 x IQR
    assert config.IQR_OUTLIER_MULTIPLIER == 1.5


def test_ahp_consistency_ratio_matches_spec():
    # SPEC.md Bagian 3.2: syarat valid CR <= 0.1
    assert config.AHP_CONSISTENCY_RATIO_MAX == 0.1


def test_project_paths_resolve_under_base_dir():
    assert config.RAW_DATA_DIR.parent == config.DATA_DIR
    assert config.BOUNDARIES_DIR.parent == config.DATA_DIR
