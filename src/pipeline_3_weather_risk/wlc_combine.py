"""Weighted Linear Combination (WLC) — implementasi SPEC.md Bagian 3.3.

Rumus persis SPEC (praktik GIS-MCDA, Malczewski 2000; 2006):

    RiskIndex(grid) = sum( wi * xi_norm )    dengan sum(wi) = 1

Prasyarat yang DIVALIDASI di sini (bukan diasumsikan):
- Bobot wi berasal dari AHP (Bagian 3.2, sudah lolos CR <= 0.1) dan
  sum(wi) = 1 — dicek ulang.
- Setiap kriteria xi_norm sudah hasil Min-Max (Bagian 3.1), berada di [0, 1]
  — dicek ulang (NaN dibiarkan menghasilkan RiskIndex NaN, sel tanpa data
  tidak boleh diam-diam dianggap 0).
Konsekuensi: RiskIndex selalu di [0, 1].
"""

import numpy as np


def wlc_combine(criteria, weights) -> np.ndarray:
    """RiskIndex per sel: ``criteria`` list of array 1D xi_norm (urutan = bobot).

    ``criteria[k][i]`` = nilai kriteria k (ternormalisasi) di sel i.
    """
    w = np.asarray(weights, dtype=float)
    if w.ndim != 1 or len(criteria) != w.size or w.size == 0:
        raise ValueError("jumlah kriteria dan bobot harus sama dan > 0")
    if not np.isclose(w.sum(), 1.0):
        raise ValueError(f"sum bobot harus 1 (dapat {w.sum():.6f}) — SPEC 3.3")

    xs = [np.asarray(c, dtype=float) for c in criteria]
    n = xs[0].size
    for k, x in enumerate(xs):
        if x.ndim != 1 or x.size != n:
            raise ValueError("semua kriteria harus array 1D dengan panjang sama")
        valid = x[~np.isnan(x)]
        if valid.size and (valid.min() < 0 or valid.max() > 1):
            raise ValueError(
                f"kriteria ke-{k} di luar [0,1] — normalisasi dulu (Bagian 3.1)"
            )
    return sum(wk * xk for wk, xk in zip(w, xs))
