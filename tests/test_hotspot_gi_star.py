"""Unit test hotspot_gi_star.py — rumus Getis-Ord Gi* SPEC.md Bagian 3.4."""

import math

import h3
import numpy as np
import pytest

from src.pipeline_3_weather_risk.hotspot_gi_star import gi_star

# Sel res 7 di sekitar Monas sebagai pusat grid sintetis.
CENTER = h3.latlng_to_cell(-6.175, 106.827, 7)


def test_gi_star_nilai_persis_rumus_manual():
    """Cek angka z persis rumus SPEC pada kasus kecil yang dihitung tangan."""
    cells = sorted(h3.grid_disk(CENTER, 2))  # 19 sel
    values = [10.0 if c == CENTER else 0.0 for c in cells]

    hasil = gi_star(cells, values).set_index("h3_index")

    n = 19
    x_bar = 10.0 / n
    s = math.sqrt(100.0 / n - x_bar**2)
    w = 7.0  # tetangga pusat = disk-1 (6 hex + diri sendiri), semua di grid
    num = 10.0 - x_bar * w
    den = s * math.sqrt((n * w - w**2) / (n - 1))
    assert np.isclose(hasil.loc[CENTER, "gi_star_z"], num / den)
    # p satu sisi ke atas dari z.
    z = num / den
    assert np.isclose(hasil.loc[CENTER, "p_value"], 0.5 * math.erfc(z / math.sqrt(2)))


def test_gi_star_klaster_tinggi_jadi_hotspot():
    cells = sorted(h3.grid_disk(CENTER, 3))  # 37 sel
    inti = set(h3.grid_disk(CENTER, 1))
    values = [100.0 if c in inti else 0.0 for c in cells]

    hasil = gi_star(cells, values).set_index("h3_index")

    # Pusat klaster = z tertinggi dan hotspot signifikan (p < 0.05).
    assert hasil["gi_star_z"].idxmax() == CENTER
    assert bool(hasil.loc[CENTER, "is_hotspot"])
    assert hasil.loc[CENTER, "p_value"] < 0.05
    # Sel tepi (jauh dari klaster) bukan hotspot.
    tepi = [c for c in cells if c not in set(h3.grid_disk(CENTER, 2))]
    assert not hasil.loc[tepi, "is_hotspot"].any()


def test_gi_star_degenerate_semua_sama():
    cells = sorted(h3.grid_disk(CENTER, 1))
    hasil = gi_star(cells, [5.0] * len(cells))

    # S = 0 -> z = 0, p = 0.5, tidak ada hotspot (tidak boleh bagi nol).
    assert (hasil["gi_star_z"] == 0.0).all()
    assert (hasil["p_value"] == 0.5).all()
    assert not hasil["is_hotspot"].any()


def test_gi_star_validasi_input():
    cells = sorted(h3.grid_disk(CENTER, 1))
    with pytest.raises(ValueError, match="NaN"):
        gi_star(cells, [1.0] * (len(cells) - 1) + [np.nan])
    with pytest.raises(ValueError, match="duplikat"):
        gi_star([CENTER, CENTER], [1.0, 2.0])
    with pytest.raises(ValueError, match="sama panjang"):
        gi_star(cells, [1.0])
