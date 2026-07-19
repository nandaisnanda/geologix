// Dashboard GeoLogix — SPEC.md PRD "Dashboard" + Fase 5 step 18:
// peta deck.gl 3 layer (weather-risk H3, road error, POI anomali),
// panel log riwayat pipeline, filter waktu (kemarin vs sekarang),
// auto-refresh 5 menit.
import { useCallback, useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import "maplibre-gl/dist/maplibre-gl.css";

import { getJSON, fmtUtc } from "./api";
import { CATEGORY_COLORS, CATEGORY_LABELS, riskColor } from "./colors";
import LogPanel from "./LogPanel";
import Legend from "./Legend";

const INITIAL_VIEW = { longitude: 106.85, latitude: -6.35, zoom: 8.6 };
const BASEMAP = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";
const REFRESH_MS = 5 * 60 * 1000;

export default function App() {
  const [at, setAt] = useState(""); // "" = snapshot terbaru
  const [show, setShow] = useState({ weather: true, poi: true, road: false });
  const [weather, setWeather] = useState({ meta: null, items: [] });
  const [road, setRoad] = useState({ meta: null, items: [] });
  const [poi, setPoi] = useState({ meta: null, items: [] });
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  const refresh = useCallback(async () => {
    // `at` dari <input datetime-local> = waktu lokal (WIB) -> kirim UTC ISO;
    // backend menormalkan aware -> naive UTC (kolom DB UTC).
    const atUtc = at ? new Date(at).toISOString() : undefined;
    try {
      const [w, r, p, l] = await Promise.all([
        getJSON("/weather-risk", { at: atUtc, limit: 2000 }),
        getJSON("/road-errors", { at: atUtc, limit: 5000 }),
        getJSON("/poi-anomalies", { at: atUtc, limit: 5000 }),
        getJSON("/pipeline-logs", { limit: 20 }),
      ]);
      setWeather(w);
      setRoad(r);
      setPoi(p);
      setLogs(l.items);
      setError(null);
      setLastFetch(new Date());
    } catch (exc) {
      setError(String(exc));
    }
  }, [at]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const layers = useMemo(
    () => [
      show.weather &&
        new H3HexagonLayer({
          id: "weather-risk",
          data: weather.items,
          getHexagon: (d) => d.h3_index,
          getFillColor: (d) => riskColor(d.risk_index),
          extruded: false,
          stroked: false,
          pickable: true,
        }),
      show.road &&
        new ScatterplotLayer({
          id: "road-errors",
          data: road.items,
          getPosition: (d) => [d.lon, d.lat],
          getFillColor: (d) => CATEGORY_COLORS[d.error_type] || [90, 90, 90],
          radiusMinPixels: 3,
          radiusMaxPixels: 8,
          stroked: true,
          getLineColor: [255, 255, 255],
          lineWidthMinPixels: 1,
          pickable: true,
        }),
      show.poi &&
        new ScatterplotLayer({
          id: "poi-anomalies",
          data: poi.items,
          getPosition: (d) => [d.lon, d.lat],
          getFillColor: CATEGORY_COLORS.poi_anomaly,
          radiusMinPixels: 4,
          radiusMaxPixels: 10,
          stroked: true,
          getLineColor: [255, 255, 255],
          lineWidthMinPixels: 1,
          pickable: true,
        }),
    ].filter(Boolean),
    [show, weather.items, road.items, poi.items]
  );

  const getTooltip = useCallback(({ object, layer }) => {
    if (!object) return null;
    if (layer.id === "weather-risk") {
      return {
        text:
          `Risk index: ${object.risk_index.toFixed(3)}\n` +
          `Hujan 1 jam: ${object.rainfall_realtime_mm ?? "—"} mm\n` +
          `Gi* z: ${object.hotspot_gi_star_z?.toFixed(2) ?? "—"}\n` +
          `H3: ${object.h3_index}`,
      };
    }
    if (layer.id === "road-errors") {
      return {
        text:
          `${CATEGORY_LABELS[object.error_type] || object.error_type}\n` +
          `Severity: ${object.severity}\n` +
          `OSM node/way: ${object.osm_node_id ?? "—"} / ${object.osm_way_id ?? "—"}`,
      };
    }
    return {
      text:
        `POI anomali (${object.poi_category || "?"})\n` +
        `Jarak ke jalan: ${object.distance_to_road_m.toFixed(1)} m\n` +
        `Confidence: ${object.confidence_score.toFixed(2)}`,
    };
  }, []);

  const toggle = (key) => setShow((s) => ({ ...s, [key]: !s[key] }));

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>GeoLogix AI</h1>
        <p className="subtitle">
          QA data geospasial Jabodetabek — hasil 4 pipeline otomatis
        </p>

        <section>
          <h2>Filter waktu</h2>
          <input
            type="datetime-local"
            value={at}
            onChange={(e) => setAt(e.target.value)}
            aria-label="Lihat kondisi pada waktu"
          />
          <button onClick={() => setAt("")} disabled={!at}>
            Sekarang
          </button>
          <p className="hint">
            Kosong = snapshot terbaru. Isi waktu untuk melihat kondisi saat itu
            (mis. kemarin).
          </p>
        </section>

        <section>
          <h2>Layer</h2>
          <label>
            <input
              type="checkbox"
              checked={show.weather}
              onChange={() => toggle("weather")}
            />
            Weather-risk ({weather.meta?.total ?? 0} sel
            {weather.items[0] ? `, ${fmtUtc(weather.items[0].computed_at)}` : ""})
          </label>
          <label>
            <input
              type="checkbox"
              checked={show.poi}
              onChange={() => toggle("poi")}
            />
            POI anomali ({poi.meta?.total ?? 0})
          </label>
          <label>
            <input
              type="checkbox"
              checked={show.road}
              onChange={() => toggle("road")}
            />
            Road error ({road.meta?.total ?? 0}
            {road.meta && road.meta.total > road.items.length
              ? `, tampil ${road.items.length}`
              : ""}
            )
          </label>
          {show.road && (
            <p className="warning">
              Run full-area saat ini memuat dangling artefak clip boundary
              (keputusan filter masih tertunda) — jangan jadikan dasar
              kesimpulan.
            </p>
          )}
        </section>

        <Legend />

        <section className="status">
          {error ? (
            <p className="error">⚠ {error}</p>
          ) : (
            <p className="hint">
              Terakhir dimuat:{" "}
              {lastFetch ? lastFetch.toLocaleTimeString("id-ID") : "…"} ·
              auto-refresh 5 mnt
            </p>
          )}
        </section>

        <LogPanel logs={logs} />
      </aside>

      <main className="map">
        <DeckGL
          initialViewState={INITIAL_VIEW}
          controller
          layers={layers}
          getTooltip={getTooltip}
        >
          <Map mapStyle={BASEMAP} />
        </DeckGL>
      </main>
    </div>
  );
}
