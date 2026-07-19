"""Pipeline 4 — Aggregator: skor prioritas gabungan (SPEC.md Bagian 3 Pipeline 4).

Metode SAMA dengan Pipeline 3 — AHP (Bagian 3.2) untuk bobot + WLC (Bagian
3.3) untuk penggabungan — di-REUSE langsung dari modul
``pipeline_3_weather_risk`` (``ahp_weights``, ``wlc_combine``, ``normalize``),
bukan implementasi ulang. Yang beda hanya KRITERIA (Bagian 3, "PIPELINE 4"):

  [0] severity           : tingkat keparahan error dari P1/P2 (skor numerik)
  [1] population_density : kepadatan populasi terdampak (proxy WorldPop)
  [2] ease_of_fix        : kemudahan perbaikan, skor manual 1-5

Semua kriteria berarah BENEFIT (nilai besar -> prioritas naik): error berat
dan berdampak ke banyak orang jelas didahulukan; kemudahan perbaikan tinggi
juga menaikkan prioritas (quick win dikerjakan duluan, konsisten tujuan P4:
"urutan mana yang harus ditangani duluan").

Matriks pairwise P4 (keputusan proyek — SPEC menetapkan metode + daftar
kriteria, bukan angka matriks): severity 2x lebih penting dari populasi dan
4x dari kemudahan; populasi 2x dari kemudahan. Matriks konsisten sempurna
(2 x 2 = 4) -> bobot eksak [4/7, 2/7, 1/7], CR = 0 (lolos syarat CR <= 0.1).
Justifikasi: severity adalah sinyal risiko operasional langsung, populasi
memodulasi besarnya dampak, kemudahan perbaikan berperan sebagai tie-breaker.

Skala severity (keputusan proyek): low=1, medium=2, high=3
(``SEVERITY_SCORE``) — pemetaan dari kolom ``severity`` tabel road_errors;
untuk sumber lain (P2 confidence, P3 risk) pemetaan diputuskan saat runner
agregasi dibuat. Normalisasi Min-Max per batch (Bagian 3.1) -> skor prioritas
RELATIF terhadap batch temuan yang diagregasi bersama, di [0, 1]. Kriteria
tanpa variasi dalam batch ternormalisasi jadi 0 (netral di WLC — keputusan
degenerate yang sama dengan Pipeline 3, lihat ``normalize.py``).

NaN pada kriteria DITOLAK (raise), bukan diam-diam dianggap 0: temuan tanpa
data populasi/severity harus dilengkapi dulu sebelum diagregasi, karena
``priority_score`` di tabel ``aggregated_findings`` non-nullable.

Setiap run dicatat ke ``pipeline_logs`` (SPEC 5.3 poin 3) via ``run()``.
"""

import numpy as np
import pandas as pd

from src.db.writer import log_pipeline_run, save_aggregated_findings
from src.pipeline_3_weather_risk.ahp_weights import compute_ahp_weights
from src.pipeline_3_weather_risk.normalize import min_max_normalize
from src.pipeline_3_weather_risk.wlc_combine import wlc_combine

PIPELINE_NAME = "pipeline_4_aggregator"

# Kriteria + matriks pairwise Pipeline 4 (lihat docstring modul).
CRITERIA_P4 = ["severity", "population_density", "ease_of_fix"]
PAIRWISE_MATRIX_P4 = [
    [1.0, 2.0, 4.0],
    [0.5, 1.0, 2.0],
    [0.25, 0.5, 1.0],
]

# Pemetaan severity string (road_errors.severity) -> skor numerik kriteria [0].
SEVERITY_SCORE = {"low": 1.0, "medium": 2.0, "high": 3.0}

# Rentang sah skor manual kemudahan perbaikan (SPEC Bagian 3 Pipeline 4: 1-5).
EASE_OF_FIX_MIN, EASE_OF_FIX_MAX = 1.0, 5.0

_REQUIRED_COLUMNS = ["source_pipeline", "source_id", *CRITERIA_P4]


def prioritize(findings: pd.DataFrame) -> pd.DataFrame:
    """Hitung ``priority_score`` AHP+WLC per temuan, urut prioritas menurun.

    ``findings`` wajib punya kolom ``source_pipeline``, ``source_id`` (rujukan
    baris asal di road_errors/poi_anomalies/weather_risk_grid) + 3 kriteria
    numerik ``CRITERIA_P4``. Return copy DataFrame + kolom ``priority_score``
    (di [0, 1], relatif per batch), diurutkan menurun (output SPEC P4:
    "urutan mana yang harus ditangani duluan").
    """
    missing = [c for c in _REQUIRED_COLUMNS if c not in findings.columns]
    if missing:
        raise ValueError(f"kolom wajib hilang: {missing}")
    if findings.empty:
        raise ValueError("tidak ada temuan untuk diprioritaskan")

    df = findings.copy().reset_index(drop=True)
    criteria_values = {c: df[c].to_numpy(dtype=float) for c in CRITERIA_P4}
    for name, values in criteria_values.items():
        if np.isnan(values).any():
            raise ValueError(
                f"kriteria '{name}' mengandung NaN — lengkapi data dulu, "
                "temuan tanpa data tidak boleh diam-diam dianggap 0"
            )
    ease = criteria_values["ease_of_fix"]
    if ease.min() < EASE_OF_FIX_MIN or ease.max() > EASE_OF_FIX_MAX:
        raise ValueError(
            f"ease_of_fix harus skor manual {EASE_OF_FIX_MIN:.0f}-"
            f"{EASE_OF_FIX_MAX:.0f} (SPEC Bagian 3 Pipeline 4)"
        )

    ahp = compute_ahp_weights(PAIRWISE_MATRIX_P4)  # raise kalau CR > 0.1
    df["priority_score"] = wlc_combine(
        criteria=[min_max_normalize(criteria_values[c]) for c in CRITERIA_P4],
        weights=ahp.weights,
    )
    return df.sort_values("priority_score", ascending=False, kind="stable").reset_index(
        drop=True
    )


def run(findings: pd.DataFrame, engine=None) -> dict:
    """Prioritaskan -> simpan ``aggregated_findings`` -> log run. Return ringkasan."""
    try:
        df = prioritize(findings)
        rows = [
            {
                "source_pipeline": r.source_pipeline,
                "source_id": int(r.source_id),
                "priority_score": float(r.priority_score),
            }
            for r in df.itertuples()
        ]
        n_saved = save_aggregated_findings(rows, engine=engine)
        ahp = compute_ahp_weights(PAIRWISE_MATRIX_P4)
        summary = {
            "findings": len(df),
            "weights": [round(float(w), 4) for w in ahp.weights],
            "cr": round(ahp.consistency_ratio, 4),
            "priority_min": round(float(df["priority_score"].min()), 4),
            "priority_max": round(float(df["priority_score"].max()), 4),
            "top_source": f"{df.loc[0, 'source_pipeline']}:{df.loc[0, 'source_id']}",
            "saved": n_saved,
        }
    except Exception as exc:
        log_pipeline_run(
            PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}", engine=engine
        )
        raise
    log_pipeline_run(
        PIPELINE_NAME,
        len(df),
        "success",
        detail=(
            f"findings={summary['findings']} weights={summary['weights']} "
            f"cr={summary['cr']} priority_max={summary['priority_max']} "
            f"top={summary['top_source']}"
        ),
        engine=engine,
    )
    return summary
