"""Konfigurasi global GeoLogix AI: path, koneksi database, dan threshold rumus.

Fase 0 (SPEC.md Bagian 5.2 urutan 1). Merujuk SPEC.md Bagian 3 (Dasar Matematika)
untuk tiap threshold pipeline — lihat komentar di masing-masing konstanta.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Path proyek (SPEC.md Bagian 5.1) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
BOUNDARIES_DIR = DATA_DIR / "boundaries"

JABODETABEK_BOUNDARY_PATH = BOUNDARIES_DIR / "jabodetabek.poly"
OSM_PBF_PATH = RAW_DATA_DIR / "jabodetabek.osm.pbf"

# --- Database: PostgreSQL + PostGIS, hosting Supabase/Neon (Bagian 7) ---
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# --- Endpoint data eksternal (Bagian 6), override via env jika perlu ---
OPEN_METEO_BASE_URL = os.environ.get(
    "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
)
# CHIRPS v2.0 annual GeoTIFF (CHC UCSB). File .tif polos + server dukung HTTP
# range -> bisa dibaca jendela kecil via GDAL /vsicurl/ tanpa download penuh.
# Pakai `or` (bukan default os.environ.get): .env lama berisi CHIRPS_BASE_URL=
# kosong, string kosong harus jatuh ke default juga.
CHIRPS_BASE_URL = (
    os.environ.get("CHIRPS_BASE_URL")
    or "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_annual/tifs"
)

# --- Threshold Pipeline 1: Road Network QA (Bagian 3.1-3.3) ---
DANGLING_NODE_DEGREE = 1  # Bagian 3.1: degree(v) = 1 -> dangling node

# Bagian 3.2 hanya menetapkan syarat "|Ci| kecil relatif terhadap |Ci| terbesar"
# tanpa angka pasti. Nilai di bawah adalah titik awal, WAJIB divalidasi manual
# di Fase 1 (lihat SPEC.md Bagian 5.4) sebelum dipakai sebagai keputusan final.
DISCONNECTED_COMPONENT_MIN_RATIO = 0.05

# --- Threshold Pipeline 2: POI Validation (Bagian 3.2.1-3.2.2 dalam PRD) ---
EARTH_RADIUS_KM = 6371  # Haversine, Bagian 2.1
IQR_OUTLIER_MULTIPLIER = 1.5  # Bagian 2.2: batas atas = Q3 + 1.5 x IQR

# --- Threshold Pipeline 3: Weather-Risk (Bagian 3.2-3.4) ---
AHP_CONSISTENCY_RATIO_MAX = 0.1  # Bagian 3.2: syarat valid CR <= 0.1
GI_STAR_SIGNIFICANCE_LEVEL = 0.05  # Bagian 3.4: p < 0.05 = hotspot signifikan

# H3_RESOLUTION tidak ditetapkan SPEC.md — keputusan Fase 3 (lihat h3_grid.py):
# resolusi 7 (avg hex 5,16 km2, edge ~1,2 km) ~ 1.400 sel utk Jabodetabek
# (~7.000 km2). Data Open-Meteo utk Indonesia beresolusi model ~11-25 km,
# grid lebih halus dari sumber tidak menambah informasi; res 8 = 7x beban
# API/DB per jam, res 6 (36 km2/hex) terlalu kasar utk peta risiko kota.
H3_RESOLUTION = 7

# --- Logging pipeline (Bagian 5.3) ---
PIPELINE_LOG_TABLE = "pipeline_logs"
