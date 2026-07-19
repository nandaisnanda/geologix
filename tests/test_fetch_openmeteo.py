"""Unit test fetch_openmeteo.py — SPEC.md Bagian 6 (curah hujan real-time P3)."""

import pandas as pd
import pytest
import requests

from src.data_ingestion import fetch_openmeteo


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Matikan jeda antar-batch/backoff supaya test tidak menunggu sungguhan."""
    monkeypatch.setattr(fetch_openmeteo.time, "sleep", lambda s: None)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error")

    def json(self):
        return self._payload


def _fake_get_factory(calls, rain_value=1.5):
    """requests.get palsu: catat params, balas 1 lokasi per koordinat diminta."""

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        n = len(params["latitude"].split(","))
        payload = [
            {"current": {"precipitation": rain_value, "time": "2026-07-19T07:00"}}
            for _ in range(n)
        ]
        # API Open-Meteo: 1 lokasi -> dict tunggal, bukan list.
        return FakeResponse(payload[0] if n == 1 else payload)

    return fake_get


def test_fetch_rainfall_batching_dan_urutan(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch_openmeteo.requests, "get", _fake_get_factory(calls))
    monkeypatch.setattr(fetch_openmeteo, "BATCH_SIZE", 100)

    n = 250
    df = fetch_openmeteo.fetch_rainfall([-6.2] * n, [106.8] * n)

    # 250 koordinat, batch 100 -> 3 call (100+100+50).
    assert [len(c["latitude"].split(",")) for c in calls] == [100, 100, 50]
    assert all(c["current"] == "precipitation" for c in calls)
    assert len(df) == n
    assert (df["rainfall_mm"] == 1.5).all()
    assert (df["weather_time"] == "2026-07-19T07:00").all()


def test_fetch_rainfall_satu_lokasi_response_dict(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch_openmeteo.requests, "get", _fake_get_factory(calls))

    df = fetch_openmeteo.fetch_rainfall([-6.2], [106.8])

    assert len(calls) == 1 and len(df) == 1
    assert df.loc[0, "rainfall_mm"] == 1.5


def test_fetch_rainfall_retry_429_lalu_sukses(monkeypatch):
    """Limit per menit Open-Meteo (HTTP 429) -> backoff lalu ulang, bukan gagal."""
    attempts = []

    def fake_get(url, params=None, timeout=None):
        attempts.append(params)
        if len(attempts) == 1:
            return FakeResponse({}, status_code=429)
        return FakeResponse(
            {"current": {"precipitation": 0.3, "time": "2026-07-19T07:00"}}
        )

    monkeypatch.setattr(fetch_openmeteo.requests, "get", fake_get)

    df = fetch_openmeteo.fetch_rainfall([-6.2], [106.8])

    assert len(attempts) == 2
    assert df.loc[0, "rainfall_mm"] == 0.3


def test_fetch_rainfall_retry_timeout_lalu_sukses(monkeypatch):
    """ReadTimeout transient (insiden CI log id 25) -> backoff lalu ulang."""
    attempts = []

    def fake_get(url, params=None, timeout=None):
        attempts.append(params)
        if len(attempts) <= 2:
            raise requests.ReadTimeout("Read timed out.")
        return FakeResponse(
            {"current": {"precipitation": 0.7, "time": "2026-07-19T07:00"}}
        )

    monkeypatch.setattr(fetch_openmeteo.requests, "get", fake_get)

    df = fetch_openmeteo.fetch_rainfall([-6.2], [106.8])

    assert len(attempts) == 3
    assert df.loc[0, "rainfall_mm"] == 0.7


def test_fetch_rainfall_timeout_terus_menerus_raise(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.ConnectTimeout("connect timeout")

    monkeypatch.setattr(fetch_openmeteo.requests, "get", fake_get)
    with pytest.raises(requests.Timeout):
        fetch_openmeteo.fetch_rainfall([-6.2], [106.8])


def test_fetch_rainfall_429_terus_menerus_raise(monkeypatch):
    monkeypatch.setattr(
        fetch_openmeteo.requests, "get",
        lambda *a, **k: FakeResponse({}, status_code=429),
    )
    with pytest.raises(requests.HTTPError, match="429"):
        fetch_openmeteo.fetch_rainfall([-6.2], [106.8])


def test_fetch_rainfall_jumlah_lokasi_tidak_cocok_raise(monkeypatch):
    monkeypatch.setattr(
        fetch_openmeteo.requests, "get",
        lambda *a, **k: FakeResponse(
            [{"current": {"precipitation": 0.0, "time": "t"}}]
        ),
    )
    with pytest.raises(ValueError, match="lokasi"):
        fetch_openmeteo.fetch_rainfall([-6.2, -6.3], [106.8, 106.9])


def test_fetch_rainfall_for_grid_gabung_h3_index(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch_openmeteo.requests, "get", _fake_get_factory(calls))
    grid = pd.DataFrame(
        {"h3_index": ["a", "b"], "lat": [-6.2, -6.3], "lng": [106.8, 106.9]}
    )

    df = fetch_openmeteo.fetch_rainfall_for_grid(grid)

    assert list(df.columns) == ["h3_index", "lat", "lng", "rainfall_mm", "weather_time"]
    assert list(df["h3_index"]) == ["a", "b"]


def test_main_simpan_csv_dan_log_pipeline(tmp_path, monkeypatch):
    logged = []
    monkeypatch.setattr(
        fetch_openmeteo, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )
    monkeypatch.setattr(fetch_openmeteo.requests, "get", _fake_get_factory([]))
    grid = pd.DataFrame(
        {"h3_index": ["a", "b", "c"], "lat": [-6.2] * 3, "lng": [106.8] * 3}
    )
    monkeypatch.setattr(fetch_openmeteo, "load_grid", lambda: grid)
    out = tmp_path / "rain_test.csv"

    n = fetch_openmeteo.main(output_path=out)

    assert n == 3 and out.exists()
    saved = pd.read_csv(out)
    assert len(saved) == 3 and "fetched_at" in saved.columns
    assert logged == [
        ("openmeteo_ingestion", 3, "success",
         "cells=3 weather_time=2026-07-19T07:00 rain_max_mm=1.50 -> rain_test.csv"),
    ]


def test_main_gagal_log_failed_dan_raise(monkeypatch):
    logged = []
    monkeypatch.setattr(
        fetch_openmeteo, "log_pipeline_run",
        lambda name, n, status, detail=None: logged.append((name, n, status, detail)),
    )

    def boom():
        raise RuntimeError("grid rusak")

    monkeypatch.setattr(fetch_openmeteo, "load_grid", boom)

    with pytest.raises(RuntimeError, match="grid rusak"):
        fetch_openmeteo.main(output_path=None)
    assert logged == [
        ("openmeteo_ingestion", 0, "failed", "RuntimeError: grid rusak"),
    ]
