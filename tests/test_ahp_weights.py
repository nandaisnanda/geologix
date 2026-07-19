"""Unit test ahp_weights.py — AHP Saaty SPEC.md Bagian 3.2.

Termasuk kasus wajib SPEC 5.3 poin 2: CR > 0.1 harus raise, bukan lolos diam-diam.
"""

import numpy as np
import pytest

from src.pipeline_3_weather_risk.ahp_weights import (
    PAIRWISE_MATRIX_P3,
    AhpConsistencyError,
    compute_ahp_weights,
)


def test_matriks_p3_bobot_dua_pertiga_dan_konsisten():
    hasil = compute_ahp_weights(PAIRWISE_MATRIX_P3)
    # 2x2 dengan preferensi 2: w = [2/3, 1/3], selalu konsisten sempurna.
    assert np.allclose(hasil.weights, [2 / 3, 1 / 3])
    assert np.isclose(hasil.weights.sum(), 1.0)
    assert hasil.consistency_ratio == 0.0


def test_matriks_3x3_konsisten_sempurna():
    # Rasio transitif sempurna (2 dan 4): eigenvector ~ [4, 2, 1].
    a = [[1, 2, 4], [1 / 2, 1, 2], [1 / 4, 1 / 2, 1]]
    hasil = compute_ahp_weights(a)
    assert np.allclose(hasil.weights, [4 / 7, 2 / 7, 1 / 7])
    assert np.isclose(hasil.lambda_max, 3.0)
    assert hasil.consistency_ratio <= 1e-9


def test_cr_lebih_dari_0_1_wajib_raise():
    # Matriks siklik A>B>C>A — sangat tidak konsisten (SPEC 5.3 poin 2).
    a = [[1, 9, 1 / 9], [1 / 9, 1, 9], [9, 1 / 9, 1]]
    with pytest.raises(AhpConsistencyError, match="CR="):
        compute_ahp_weights(a)


def test_validasi_bentuk_matriks():
    with pytest.raises(ValueError, match="reciprocal"):
        compute_ahp_weights([[1, 3], [3, 1]])  # A[1][0] harus 1/3
    with pytest.raises(ValueError, match="diagonal"):
        compute_ahp_weights([[2, 1], [1, 2]])
    with pytest.raises(ValueError, match="positif"):
        compute_ahp_weights([[1, -2], [-0.5, 1]])
