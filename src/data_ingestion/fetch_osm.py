"""Download + clip OSM ``.pbf`` untuk Pipeline 1 (Road QA) — SPEC.md Bagian 5.2b.

Sumber: Geofabrik ``java-latest.osm.pbf`` (region Java, lisensi ODbL), di-clip ke
boundary Jabodetabek (``data/boundaries/jabodetabek.poly``) memakai osmium-tool.
Khusus ``.pbf`` — POI dari ``.shp.zip`` ditangani terpisah oleh ``fetch_osm_poi.py``
(SPEC.md Bagian 5.2c, dua sumber OSM jangan dicampur).

Logika idempotent sesuai pseudocode SPEC.md Bagian 5.2b:
- Clipped ``.pbf`` belum ada (cache miss)  -> full download + ``osmium extract --polygon``.
- Sudah ada (cache hit)                    -> download diff ``.osc.gz`` Geofabrik,
  ``osmium apply-changes``, lalu re-extract polygon (diff mencakup seluruh Java,
  jadi hasil apply-changes wajib di-clip ulang).
- Fallback wajib: incremental gagal apa pun sebabnya -> jatuh ke full download.

Setiap run dicatat ke tabel ``pipeline_logs`` (SPEC.md Bagian 5.3) dengan
``detail`` berisi mode: ``full_download`` | ``incremental_update`` |
``full_download_fallback``.

Butuh ``osmium`` CLI di PATH — tersedia di GitHub Actions Ubuntu runner
(``apt-get install osmium-tool``); tidak tersedia di Windows dev lokal, sehingga
uji lokal memakai sample kecamatan via OSMnx (lihat ``graph_builder.py``).
"""

import shutil
import subprocess

import geopandas as gpd
import requests
from shapely.geometry import MultiPolygon, Polygon

from src import config
from src.db.writer import log_pipeline_run

PIPELINE_NAME = "osm_refresh"

GEOFABRIK_PBF_URL = "https://download.geofabrik.de/asia/indonesia/java-latest.osm.pbf"
GEOFABRIK_UPDATES_BASE = "https://download.geofabrik.de/asia/indonesia/java-updates"

BOUNDARY_SHP_PATH = config.BOUNDARIES_DIR / "jabodetabek.shp"
JAVA_PBF_PATH = config.RAW_DATA_DIR / "java-latest.osm.pbf"
REPLICATION_STATE_PATH = config.RAW_DATA_DIR / "osm_replication_state.txt"

# Toleransi geometri (derajat, ~100-200 m di ekuator): buffer menutup sliver
# antar-poligon desa hasil dissolve, simplify menekan jumlah vertex .poly.
_DISSOLVE_BUFFER_DEG = 0.002
_SIMPLIFY_TOLERANCE_DEG = 0.001
_MIN_PART_AREA_DEG2 = 1e-4  # buang serpihan poligon < ~1 km^2


def write_poly(geometry: Polygon | MultiPolygon, path, name: str = "jabodetabek") -> None:
    """Tulis geometri ke format .poly osmium (exterior ring saja, tanpa hole)."""
    parts = [geometry] if isinstance(geometry, Polygon) else list(geometry.geoms)
    lines = [name]
    for i, part in enumerate(parts, start=1):
        lines.append(str(i))
        for lon, lat in part.exterior.coords:
            lines.append(f"   {lon:.7f}   {lat:.7f}")
        lines.append("END")
    lines.append("END")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def ensure_boundary_poly(force: bool = False):
    """Dissolve shapefile desa Jabodetabek -> data/boundaries/jabodetabek.poly."""
    poly_path = config.JABODETABEK_BOUNDARY_PATH
    if poly_path.exists() and not force:
        return poly_path

    gdf = gpd.read_file(BOUNDARY_SHP_PATH)
    union = gdf.geometry.union_all()
    union = (
        union.buffer(_DISSOLVE_BUFFER_DEG)
        .simplify(_SIMPLIFY_TOLERANCE_DEG)
        .buffer(0)
    )
    parts = [union] if isinstance(union, Polygon) else list(union.geoms)
    parts = [Polygon(p.exterior) for p in parts if p.area >= _MIN_PART_AREA_DEG2]
    if not parts:
        raise RuntimeError("Dissolve boundary menghasilkan geometri kosong")
    geometry = parts[0] if len(parts) == 1 else MultiPolygon(parts)
    write_poly(geometry, poly_path)
    return poly_path


def _run_osmium(*args: str) -> None:
    subprocess.run(["osmium", *args], check=True)


def _download(url: str, dest) -> None:
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(dest)


def _remote_sequence() -> int:
    resp = requests.get(f"{GEOFABRIK_UPDATES_BASE}/state.txt", timeout=60)
    resp.raise_for_status()
    for line in resp.text.splitlines():
        if line.startswith("sequenceNumber="):
            return int(line.split("=", 1)[1])
    raise RuntimeError("sequenceNumber tidak ditemukan di state.txt Geofabrik")


def _diff_url(sequence: int) -> str:
    return (
        f"{GEOFABRIK_UPDATES_BASE}/{sequence // 1_000_000:03d}"
        f"/{sequence // 1_000 % 1_000:03d}/{sequence % 1_000:03d}.osc.gz"
    )


def _extract_jabodetabek(source_pbf) -> None:
    _run_osmium(
        "extract",
        "--polygon", str(config.JABODETABEK_BOUNDARY_PATH),
        str(source_pbf),
        "-o", str(config.OSM_PBF_PATH),
        "--overwrite",
    )


def full_download() -> None:
    """Cache miss: download java-latest.osm.pbf penuh lalu clip ke Jabodetabek."""
    if not JAVA_PBF_PATH.exists():
        _download(GEOFABRIK_PBF_URL, JAVA_PBF_PATH)
    _extract_jabodetabek(JAVA_PBF_PATH)
    REPLICATION_STATE_PATH.write_text(str(_remote_sequence()), encoding="ascii")


def incremental_update() -> None:
    """Cache hit: apply semua diff .osc.gz sejak run terakhir, lalu re-clip."""
    local_seq = int(REPLICATION_STATE_PATH.read_text().strip())
    remote_seq = _remote_sequence()
    if remote_seq <= local_seq:
        return
    updated = config.OSM_PBF_PATH
    for seq in range(local_seq + 1, remote_seq + 1):
        diff_path = config.RAW_DATA_DIR / f"update-{seq}.osc.gz"
        _download(_diff_url(seq), diff_path)
        tmp_out = updated.with_suffix(".updated.pbf")
        _run_osmium("apply-changes", str(updated), str(diff_path), "-o", str(tmp_out), "--overwrite")
        shutil.move(str(tmp_out), str(updated))
        diff_path.unlink()
    _extract_jabodetabek(updated)
    REPLICATION_STATE_PATH.write_text(str(remote_seq), encoding="ascii")


def main() -> str:
    """Jalankan refresh OSM idempotent + log ke pipeline_logs. Return mode run."""
    ensure_boundary_poly()
    try:
        if config.OSM_PBF_PATH.exists() and REPLICATION_STATE_PATH.exists():
            try:
                incremental_update()
                mode = "incremental_update"
            except Exception:
                full_download()
                mode = "full_download_fallback"
        else:
            full_download()
            mode = "full_download"
    except Exception as exc:
        log_pipeline_run(PIPELINE_NAME, 0, "failed", detail=f"{type(exc).__name__}: {exc}")
        raise
    log_pipeline_run(PIPELINE_NAME, 0, "success", detail=mode)
    return mode


if __name__ == "__main__":
    main()
