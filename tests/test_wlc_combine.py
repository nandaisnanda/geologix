"""Unit test wlc_combine.py — WLC SPEC.md Bagian 3.3."""

import numpy as np
import pytest

from src.pipeline_3_weather_risk.wlc_combine import wlc_combine


def test_wlc_persis_rumus():
    risk = wlc_combine(
        criteria=[np.array([0.0, 0.5, 1.0]), np.array([1.0, 0.5, 0.0])],
        weights=[2 / 3, 1 / 3],
    )
    # RiskIndex = 2/3*x1 + 1/3*x2, selalu di [0, 1].
    assert np.allclose(risk, [1 / 3, 0.5, 2 / 3])
    assert (risk >= 0).all() and (risk <= 1).all()


def test_wlc_nan_menghasilkan_nan_bukan_nol():
    risk = wlc_combine([np.array([0.5, np.nan])], weights=[1.0])
    assert risk[0] == 0.5 and np.isnan(risk[1])


def test_wlc_bobot_tidak_jumlah_satu_raise():
    with pytest.raises(ValueError, match="sum bobot"):
        wlc_combine([np.array([0.5])], weights=[0.6, 0.6][:1])
    with pytest.raises(ValueError, match="sum bobot"):
        wlc_combine([np.array([0.5]), np.array([0.5])], weights=[0.7, 0.6])


def test_wlc_kriteria_belum_dinormalisasi_raise():
    with pytest.raises(ValueError, match="luar"):
        wlc_combine([np.array([0.0, 5.0])], weights=[1.0])


def test_wlc_jumlah_kriteria_bobot_tidak_cocok_raise():
    with pytest.raises(ValueError, match="jumlah kriteria"):
        wlc_combine([np.array([0.5])], weights=[0.5, 0.5])
