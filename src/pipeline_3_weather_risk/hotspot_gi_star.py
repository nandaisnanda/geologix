"""Getis-Ord Gi* untuk baseline historis — implementasi SPEC.md Bagian 3.4.

Rumus persis SPEC:

    Gi* = [ sum_j(wij * xj) - Xbar * sum_j(wij) ]
          / [ S * sqrt( (n * sum_j(wij^2) - (sum_j wij)^2) / (n - 1) ) ]

- xj   = nilai sel j (di sini: rainfall_hist_mm dari CHIRPS 5 tahun)
- wij  = bobot spasial sel i-j. Keputusan proyek (SPEC: "biasanya berdasarkan
  kedekatan/contiguity"): biner 1 untuk tetangga contiguity k-ring 1 H3
  (h3.grid_disk(i, 1) — hexagon punya relasi tetangga alami), TERMASUK sel i
  sendiri — itulah bedanya Gi* ("star") dari Gi. Tetangga di luar grid
  (tepi boundary) tidak dihitung.
- Xbar, S = mean dan standar deviasi GLOBAL semua sel (S versi populasi,
  S = sqrt(mean(x^2) - Xbar^2), konsisten formulasi Getis-Ord 1992).
- Hasil = z-score. Hotspot signifikan: p < 0.05 (config
  GI_STAR_SIGNIFICANCE_LEVEL), uji SATU SISI ke atas (hotspot = nilai tinggi;
  p = P(Z > z) = 0.5 * erfc(z / sqrt(2)) — tanpa dependensi scipy).

Kasus degenerate: S = 0 (semua nilai sama) atau penyebut 0 -> z = 0,
p = 0.5, bukan hotspot (tidak ada variasi = tidak ada hotspot).
NaN pada nilai input tidak diperbolehkan — sel tanpa data harus difilter
pemanggil sebelum uji statistik, supaya Xbar/S tidak bias diam-diam.
"""

import math

import h3
import numpy as np
import pandas as pd

from src import config


def gi_star(cells, values) -> pd.DataFrame:
    """Z-score Gi* per sel H3.

    ``cells``: daftar H3 index (unik); ``values``: nilai per sel (tanpa NaN).
    Return DataFrame: h3_index, gi_star_z, p_value, is_hotspot.
    """
    cells = list(cells)
    x = np.asarray(values, dtype=float)
    if len(cells) != x.size or x.size == 0:
        raise ValueError("cells dan values harus sama panjang dan tidak kosong")
    if len(set(cells)) != len(cells):
        raise ValueError("h3_index duplikat — tiap sel harus unik")
    if np.isnan(x).any():
        raise ValueError("values mengandung NaN — filter sel tanpa data dulu")

    n = x.size
    x_bar = float(x.mean())
    s = math.sqrt(float((x**2).mean()) - x_bar**2)

    index_of = {c: i for i, c in enumerate(cells)}
    z_scores = np.zeros(n)
    for i, cell in enumerate(cells):
        # wij biner: k-ring 1 (termasuk diri sendiri), hanya yang ada di grid.
        neighbor_idx = [
            index_of[nb] for nb in h3.grid_disk(cell, 1) if nb in index_of
        ]
        w_sum = float(len(neighbor_idx))  # sum wij = sum wij^2 (bobot biner)
        numerator = float(x[neighbor_idx].sum()) - x_bar * w_sum
        variance_term = (n * w_sum - w_sum**2) / (n - 1) if n > 1 else 0.0
        denominator = s * math.sqrt(variance_term)
        z_scores[i] = numerator / denominator if denominator > 0 else 0.0

    # Uji satu sisi ke atas: p = P(Z > z).
    p_values = np.array([0.5 * math.erfc(z / math.sqrt(2)) for z in z_scores])
    return pd.DataFrame(
        {
            "h3_index": cells,
            "gi_star_z": z_scores,
            "p_value": p_values,
            "is_hotspot": (z_scores > 0)
            & (p_values < config.GI_STAR_SIGNIFICANCE_LEVEL),
        }
    )
