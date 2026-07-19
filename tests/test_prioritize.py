"""Unit test Pipeline 4 — prioritas gabungan AHP+WLC (SPEC Bagian 3 Pipeline 4)."""

import numpy as np
import pandas as pd
import pytest

from src.pipeline_3_weather_risk.ahp_weights import (
    AhpConsistencyError,
    compute_ahp_weights,
)
from src.pipeline_4_aggregator import prioritize as p4


@pytest.fixture()
def tangkapan(monkeypatch):
    saved, logged = [], []
    monkeypatch.setattr(
        p4, "save_aggregated_findings",
        lambda rows, engine=None: (saved.extend(rows), len(rows))[1],
    )
    monkeypatch.setattr(
        p4, "log_pipeline_run",
        lambda name, n, status, detail=None, engine=None: logged.append(
            (name, n, status, detail)
        ),
    )
    return saved, logged


def _findings():
    return pd.DataFrame(
        {
            "source_pipeline": ["road_errors", "road_errors", "poi_anomalies"],
            "source_id": [10, 20, 30],
            "severity": [1.0, 2.0, 3.0],
            "population_density": [100.0, 50.0, 200.0],
            "ease_of_fix": [5.0, 1.0, 3.0],
        }
    )


def test_bobot_p4_eksak_dan_cr_nol():
    # Matriks konsisten sempurna (2x2=4) -> bobot [4/7, 2/7, 1/7], CR = 0.
    ahp = compute_ahp_weights(p4.PAIRWISE_MATRIX_P4)
    assert np.allclose(ahp.weights, [4 / 7, 2 / 7, 1 / 7])
    assert ahp.consistency_ratio == pytest.approx(0.0, abs=1e-9)


def test_prioritize_skor_sesuai_hitungan_tangan_dan_terurut():
    df = p4.prioritize(_findings())

    # Hitungan tangan: norm severity=[0,.5,1], pop=[1/3,0,1], ease=[1,0,.5];
    # w=[4/7,2/7,1/7] -> id10=5/21, id20=2/7, id30=6.5/7. Urut menurun.
    skor = dict(zip(df["source_id"], df["priority_score"]))
    assert skor[10] == pytest.approx(5 / 21)
    assert skor[20] == pytest.approx(2 / 7)
    assert skor[30] == pytest.approx(6.5 / 7)
    assert list(df["source_id"]) == [30, 20, 10]
    assert df["priority_score"].between(0, 1).all()


def test_prioritize_nan_kriteria_ditolak():
    findings = _findings()
    findings.loc[1, "population_density"] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        p4.prioritize(findings)


def test_prioritize_ease_di_luar_1_5_ditolak():
    findings = _findings()
    findings.loc[0, "ease_of_fix"] = 7.0
    with pytest.raises(ValueError, match="ease_of_fix"):
        p4.prioritize(findings)


def test_prioritize_kolom_hilang_dan_kosong_ditolak():
    with pytest.raises(ValueError, match="kolom wajib"):
        p4.prioritize(pd.DataFrame({"source_pipeline": [], "source_id": []}))
    with pytest.raises(ValueError, match="tidak ada temuan"):
        p4.prioritize(_findings().iloc[0:0])


def test_matriks_tak_konsisten_raise_bukan_lolos_diam(monkeypatch):
    # Edge case wajib SPEC 5.3 poin 2: CR > 0.1 harus raise.
    monkeypatch.setattr(
        p4, "PAIRWISE_MATRIX_P4",
        [[1.0, 9.0, 1 / 9], [1 / 9, 1.0, 9.0], [9.0, 1 / 9, 1.0]],
    )
    with pytest.raises(AhpConsistencyError):
        p4.prioritize(_findings())


def test_run_simpan_dan_log(tangkapan):
    saved, logged = tangkapan

    summary = p4.run(_findings())

    assert summary["findings"] == 3 and summary["saved"] == 3
    assert summary["weights"] == [0.5714, 0.2857, 0.1429]
    assert summary["cr"] == 0.0
    assert summary["top_source"] == "poi_anomalies:30"
    assert len(saved) == 3
    assert set(saved[0]) == {"source_pipeline", "source_id", "priority_score"}
    name, n, status, detail = logged[0]
    assert name == "pipeline_4_aggregator" and status == "success" and n == 3
    assert "top=poi_anomalies:30" in detail


def test_run_gagal_tercatat_failed(tangkapan):
    _, logged = tangkapan
    findings = _findings()
    findings.loc[0, "severity"] = np.nan

    with pytest.raises(ValueError):
        p4.run(findings)

    name, n, status, detail = logged[0]
    assert status == "failed" and n == 0 and "NaN" in detail
