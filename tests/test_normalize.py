"""Unit test normalize.py — rumus Min-Max SPEC.md Bagian 3.1."""

import numpy as np
import pytest

from src.pipeline_3_weather_risk.normalize import min_max_normalize


def test_min_max_persis_rumus():
    hasil = min_max_normalize([2.0, 4.0, 10.0])
    # (xi - 2) / (10 - 2)
    assert np.allclose(hasil, [0.0, 0.25, 1.0])
    assert hasil.min() == 0.0 and hasil.max() == 1.0


def test_min_max_degenerate_semua_sama_jadi_nol():
    # Keputusan proyek: pembagi nol -> 0.0 semua (kriteria tanpa variasi).
    assert (min_max_normalize([7.0, 7.0, 7.0]) == 0.0).all()


def test_min_max_nan_dipertahankan():
    hasil = min_max_normalize([0.0, np.nan, 5.0])
    assert np.isnan(hasil[1])
    assert np.allclose([hasil[0], hasil[2]], [0.0, 1.0])


def test_min_max_input_tidak_valid_raise():
    with pytest.raises(ValueError):
        min_max_normalize([])
    with pytest.raises(ValueError):
        min_max_normalize([np.nan, np.nan])
