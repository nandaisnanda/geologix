"""Unit test fetch_osm.py — SPEC.md Bagian 5.2b (download+clip idempotent + fallback)."""

from shapely.geometry import Polygon

from src.data_ingestion import fetch_osm


def test_write_poly_format_osmium(tmp_path):
    square = Polygon([(106.0, -6.0), (107.0, -6.0), (107.0, -7.0), (106.0, -7.0)])
    out = tmp_path / "test.poly"
    fetch_osm.write_poly(square, out, name="testarea")

    lines = out.read_text().splitlines()
    assert lines[0] == "testarea"
    assert lines[1] == "1"
    assert lines[-2] == "END"  # penutup section poligon
    assert lines[-1] == "END"  # penutup file
    coord_lines = lines[2:-2]
    assert len(coord_lines) == 5  # ring tertutup: 4 titik + pengulangan titik awal
    lon, lat = coord_lines[0].split()
    assert float(lon) == 106.0 and float(lat) == -6.0


def test_main_fallback_ke_full_download_saat_incremental_gagal(monkeypatch, tmp_path):
    """SPEC 5.2b: incremental gagal TIDAK boleh stuck — wajib jatuh ke full download."""
    fake_pbf = tmp_path / "jabodetabek.osm.pbf"
    fake_pbf.write_bytes(b"x")
    fake_state = tmp_path / "state.txt"
    fake_state.write_text("100")
    monkeypatch.setattr(fetch_osm.config, "OSM_PBF_PATH", fake_pbf)
    monkeypatch.setattr(fetch_osm, "REPLICATION_STATE_PATH", fake_state)
    monkeypatch.setattr(fetch_osm, "ensure_boundary_poly", lambda: None)

    calls = []
    monkeypatch.setattr(
        fetch_osm, "incremental_update",
        lambda: (_ for _ in ()).throw(RuntimeError("osc corrupt")),
    )
    monkeypatch.setattr(fetch_osm, "full_download", lambda: calls.append("full"))

    logged = []
    monkeypatch.setattr(
        fetch_osm, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, status, detail)),
    )

    mode = fetch_osm.main()

    assert mode == "full_download_fallback"
    assert calls == ["full"]
    assert logged == [("osm_refresh", "success", "full_download_fallback")]


def test_diff_url_zero_padded():
    assert fetch_osm._diff_url(4007) == (
        "https://download.geofabrik.de/asia/indonesia/java-updates/000/004/007.osc.gz"
    )
