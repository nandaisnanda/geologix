"""Analytic Hierarchy Process (AHP) Saaty — implementasi SPEC.md Bagian 3.2.

Langkah persis SPEC:
1. Matriks perbandingan berpasangan A (n x n, skala Saaty 1-9),
   A[j][i] = 1 / A[i][j], diagonal 1.
2. Bobot wi = eigenvector utama A (eigenvalue terbesar), dinormalisasi
   sehingga sum(wi) = 1.
3. Uji konsistensi WAJIB:
       CI = (lambda_max - n) / (n - 1)
       CR = CI / RI          (RI = Random Index tabel standar Saaty)
   Syarat valid CR <= 0.1 (config.AHP_CONSISTENCY_RATIO_MAX). CR > 0.1 ->
   raise AhpConsistencyError (SPEC 5.3 poin 2: tidak boleh lolos diam-diam).

Kasus n <= 2: RI = 0 (matriks reciprocal 1x1/2x2 selalu konsisten sempurna,
lambda_max = n) -> CR didefinisikan 0.0, tidak dibagi nol.

Matriks kriteria Pipeline 3 (keputusan proyek, SPEC menetapkan metode tapi
tidak angka matriksnya): 2 kriteria (Bagian 3.1) —
  [0] rainfall_realtime : curah hujan real-time Open-Meteo (mm/jam terakhir)
  [1] hist_hotspot      : baseline historis = z-score Getis-Ord Gi* dari
                          CHIRPS 5 tahun (Bagian 3.4)
Penilaian: rainfall_realtime SEDIKIT lebih penting (2 pada skala Saaty) —
peta risiko di-update per jam untuk keputusan operasional, hujan saat ini
adalah pemicu langsung; kerawanan historis memodulasi. Hasil: w = [2/3, 1/3],
CR = 0 (n=2).
"""

from dataclasses import dataclass

import numpy as np

from src import config

# Random Index (RI) standar Saaty per ukuran matriks n (Saaty 1980).
SAATY_RANDOM_INDEX = {
    1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}

# Kriteria + matriks pairwise Pipeline 3 (lihat docstring modul).
CRITERIA_P3 = ["rainfall_realtime", "hist_hotspot"]
PAIRWISE_MATRIX_P3 = [
    [1.0, 2.0],
    [0.5, 1.0],
]


class AhpConsistencyError(ValueError):
    """CR > 0.1 — matriks pairwise tidak konsisten, bobot tidak valid (SPEC 3.2)."""


@dataclass(frozen=True)
class AhpResult:
    weights: np.ndarray  # bobot wi, sum = 1
    lambda_max: float
    consistency_index: float  # CI
    consistency_ratio: float  # CR


def compute_ahp_weights(matrix) -> AhpResult:
    """Bobot AHP + uji konsistensi persis Bagian 3.2. Raise jika CR > 0.1."""
    a = np.asarray(matrix, dtype=float)
    n = a.shape[0]
    if a.ndim != 2 or a.shape != (n, n):
        raise ValueError("matriks pairwise harus persegi (n x n)")
    if (a <= 0).any():
        raise ValueError("semua elemen matriks Saaty harus positif")
    if not np.allclose(np.diag(a), 1.0):
        raise ValueError("diagonal matriks pairwise harus 1")
    if not np.allclose(a * a.T, 1.0, rtol=1e-6):
        raise ValueError("matriks harus reciprocal: A[j][i] = 1 / A[i][j]")

    eigenvalues, eigenvectors = np.linalg.eig(a)
    idx = int(np.argmax(eigenvalues.real))
    lambda_max = float(eigenvalues[idx].real)
    principal = np.abs(eigenvectors[:, idx].real)
    weights = principal / principal.sum()

    if n <= 2:
        ci, cr = 0.0, 0.0
    else:
        ci = (lambda_max - n) / (n - 1)
        ri = SAATY_RANDOM_INDEX.get(n)
        if ri is None:
            raise ValueError(f"tidak ada Random Index Saaty untuk n={n}")
        cr = ci / ri

    if cr > config.AHP_CONSISTENCY_RATIO_MAX:
        raise AhpConsistencyError(
            f"CR={cr:.4f} > {config.AHP_CONSISTENCY_RATIO_MAX} — matriks "
            "pairwise harus direvisi (SPEC Bagian 3.2, bobot tidak valid)"
        )
    return AhpResult(weights, lambda_max, ci, cr)
