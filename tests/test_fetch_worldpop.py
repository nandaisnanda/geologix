"""Unit test fetch_worldpop — sampling densitas populasi (SPEC Bagian 3 P4)."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.data_ingestion import fetch_worldpop

NODATA = -99999.0


@pytest.fixture()
def raster_sintetis(tmp_path):
    """GeoTIFF 2x2 EPSG:4326 di sekitar Jakarta: [[100, 200], [nodata, 400]]."""
    path = tmp_path / "pop.tif"
    data = np.array([[100.0, 200.0], [NODATA, 400.0]], dtype="float32")
    with rasterio.open(
        path, "w", driver="GTiff", height=2, width=2, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(106.0, -6.0, 0.5, 0.5),
        nodata=NODATA,
    ) as dst:
        dst.write(data, 1)
    return path


def test_sample_density_nilai_dan_nodata_jadi_nan(raster_sintetis):
    # Pusat piksel: (106.25,-6.25)=100, (106.75,-6.25)=200, (106.25,-6.75)=nodata.
    values = fetch_worldpop.sample_density(
        [106.25, 106.75, 106.25], [-6.25, -6.25, -6.75], tif_path=raster_sintetis
    )
    assert values[0] == pytest.approx(100.0)
    assert values[1] == pytest.approx(200.0)
    assert np.isnan(values[2])  # nodata -> NaN, bukan diam-diam 0


def test_sample_density_panjang_beda_ditolak(raster_sintetis):
    with pytest.raises(ValueError, match="panjang sama"):
        fetch_worldpop.sample_density([106.0], [-6.0, -6.5], tif_path=raster_sintetis)


def test_ensure_worldpop_idempotent_tanpa_download_ulang(tmp_path, monkeypatch):
    tif = tmp_path / "idn.tif"
    tif.write_bytes(b"sudah ada")
    monkeypatch.setattr(fetch_worldpop, "WORLDPOP_TIF_PATH", tif)
    monkeypatch.setattr(
        fetch_worldpop.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("tidak boleh download")),
    )
    assert fetch_worldpop.ensure_worldpop_tif() == tif
