"""Normalisasi kriteria Min-Max Scaling — implementasi SPEC.md Bagian 3.1.

Rumus persis SPEC (Pipeline 3, GIS-MCDA):

    xi_norm = (xi - xi_min) / (xi_max - xi_min)

Setiap kriteria (curah hujan real-time, baseline historis) punya satuan beda —
WAJIB dinormalisasi ke skala 0-1 sebelum digabung WLC (Bagian 3.3).

Kasus degenerate (keputusan proyek, SPEC tidak menetapkan): semua nilai sama
(xi_max == xi_min, pembagi nol) -> seluruh sel bernilai 0.0, karena kriteria
tanpa variasi tidak membedakan risiko antar sel (kontribusi netral di WLC).
NaN pada input dipertahankan sebagai NaN (min/max memakai nanmin/nanmax).
"""

import numpy as np


def min_max_normalize(values) -> np.ndarray:
    """Normalisasi array 1D ke [0, 1] persis rumus Bagian 3.1."""
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size == 0:
        raise ValueError("input harus array 1D tidak kosong")
    if np.isnan(x).all():
        raise ValueError("seluruh nilai NaN — tidak ada yang bisa dinormalisasi")
    x_min = np.nanmin(x)
    x_max = np.nanmax(x)
    if x_max == x_min:
        return np.zeros_like(x)
    return (x - x_min) / (x_max - x_min)
