// Dashboard GeoLogix — SPEC.md PRD "Dashboard" + Fase 5 step 18:
// peta deck.gl 3 layer (weather-risk H3, road error, POI anomali),
// panel log riwayat pipeline, filter waktu (kemarin vs sekarang),
// auto-refresh 5 menit. Tema terang/gelap (basemap + warna layer ikut).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import "maplibre-gl/dist/maplibre-gl.css";

import { getJSON, fmtUtc, relTime } from "./api";
import { categoryColors, CATEGORY_LABELS, riskColor, rgb } from "./colors";
import LogPanel from "./LogPanel";
import Layers from "./Layers";
import StatTiles from "./StatTiles";

const INITIAL_VIEW = { longitude: 106.85, latitude: -6.35, zoom: 8.6 };
const BASEMAPS = {
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
};
const REFRESH_MS = 5 * 60 * 1000;

const initialTheme = () => {
  const fromUrl = new URLSearchParams(window.location.search).get("theme");
  if (fromUrl === "light" || fromUrl === "dark") return fromUrl;
  const saved = localStorage.getItem("glx-theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

// Nilai tooltip di-escape — poi_category/detail berasal dari data OSM.
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

const ttRow = (k, v) =>
  `<div class="tt-row"><span class="k">${esc(k)}</span><span class="v">${esc(
    v
  )}</span></div>`;

// datetime-local butuh "YYYY-MM-DDTHH:mm" dalam waktu lokal.
const toLocalInput = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(
    d.getHours()
  )}:${p(d.getMinutes())}`;
};

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 34 34" fill="none" aria-hidden>
      <path
        d="M17 2.5 29.5 9.75v14.5L17 31.5 4.5 24.25V9.75L17 2.5Z"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <circle cx="17" cy="17" r="3.1" fill="currentColor" />
      <path
        d="M17 13.9V8m2.7 10.6 5.6 3.2M14.3 18.6l-5.6 3.2"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  const [at, setAt] = useState(""); // "" = snapshot terbaru
  const [show, setShow] = useState({ weather: true, poi: true, road: true });
  const [weather, setWeather] = useState({ meta: null, items: [] });
  const [road, setRoad] = useState({ meta: null, items: [] });
  const [poi, setPoi] = useState({ meta: null, items: [] });
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [booted, setBooted] = useState(false);
  const [slowBoot, setSlowBoot] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const bootedRef = useRef(false);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("glx-theme", theme);
  }, [theme]);

  const refresh = useCallback(async () => {
    // `at` dari <input datetime-local> = waktu lokal (WIB) -> kirim UTC ISO;
    // backend menormalkan aware -> naive UTC (kolom DB UTC).
    const atUtc = at ? new Date(at).toISOString() : undefined;
    setFetching(true);
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
      setBooted(true);
      bootedRef.current = true;
    } catch (exc) {
      setError(String(exc));
    } finally {
      setFetching(false);
    }
  }, [at]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  // Free tier Render tidur saat idle — kalau load pertama >4 dtk,
  // jelaskan cold start supaya user tidak mengira dashboard rusak.
  useEffect(() => {
    const t = setTimeout(() => {
      if (!bootedRef.current) setSlowBoot(true);
    }, 4000);
    return () => clearTimeout(t);
  }, []);

  const cat = useMemo(() => categoryColors(theme), [theme]);
  const pointRing = theme === "dark" ? [26, 26, 25] : [255, 255, 255];

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
          getFillColor: (d) => cat[d.error_type] || [90, 90, 90],
          radiusMinPixels: 3.5,
          radiusMaxPixels: 8,
          stroked: true,
          getLineColor: pointRing,
          lineWidthMinPixels: 1,
          pickable: true,
        }),
      show.poi &&
        new ScatterplotLayer({
          id: "poi-anomalies",
          data: poi.items,
          getPosition: (d) => [d.lon, d.lat],
          getFillColor: cat.poi_anomaly,
          radiusMinPixels: 4,
          radiusMaxPixels: 10,
          stroked: true,
          getLineColor: pointRing,
          lineWidthMinPixels: 1,
          pickable: true,
        }),
    ].filter(Boolean),
    [show, weather.items, road.items, poi.items, cat, pointRing]
  );

  // Tooltip: nilai menonjol, label sekunder (hierarki skill dataviz);
  // styling via .deck-tooltip + .tt di styles.css.
  const getTooltip = useCallback(
    ({ object, layer }) => {
      if (!object) return null;
      if (layer.id === "weather-risk") {
        const c = riskColor(object.risk_index);
        return {
          html:
            `<div class="tt"><div class="tt-title">` +
            `<span class="dot" style="background:${rgb(c)}"></span>Sel risiko cuaca</div>` +
            ttRow("Risk index", object.risk_index.toFixed(3)) +
            ttRow(
              "Hujan 1 jam",
              object.rainfall_realtime_mm != null
                ? `${object.rainfall_realtime_mm} mm`
                : "—"
            ) +
            ttRow("Gi* z-score", object.hotspot_gi_star_z?.toFixed(2) ?? "—") +
            ttRow("H3", object.h3_index) +
            `</div>`,
        };
      }
      if (layer.id === "road-errors") {
        const c = cat[object.error_type] || [90, 90, 90];
        return {
          html:
            `<div class="tt"><div class="tt-title">` +
            `<span class="dot" style="background:${rgb(c)}"></span>` +
            `${esc(CATEGORY_LABELS[object.error_type] || object.error_type)}</div>` +
            ttRow("Severity", object.severity) +
            ttRow("OSM node", object.osm_node_id ?? "—") +
            ttRow("OSM way", object.osm_way_id ?? "—") +
            `</div>`,
        };
      }
      return {
        html:
          `<div class="tt"><div class="tt-title">` +
          `<span class="dot" style="background:${rgb(cat.poi_anomaly)}"></span>` +
          `POI anomali</div>` +
          ttRow("Kategori", object.poi_category || "?") +
          ttRow("Jarak ke jalan", `${object.distance_to_road_m.toFixed(1)} m`) +
          ttRow("Confidence", object.confidence_score.toFixed(2)) +
          `</div>`,
      };
    },
    [cat]
  );

  const toggle = (key) => setShow((s) => ({ ...s, [key]: !s[key] }));
  const setYesterday = () =>
    setAt(toLocalInput(new Date(Date.now() - 24 * 3600 * 1000)));

  return (
    <div className="app">
      <aside className={`sidebar${panelOpen ? " open" : ""}`}>
        <div className="sidebar-inner">
          <header className="brand">
            <BrandMark />
            <div className="brand-text">
              <h1>GeoLogix AI</h1>
              <p>QA data geospasial Jabodetabek</p>
            </div>
            <div className="brand-actions">
              <button
                className="icon-btn"
                onClick={refresh}
                title="Muat ulang data"
                aria-label="Muat ulang data"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  className={fetching ? "spin" : ""}
                >
                  <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                  <path d="M20 3v5h-5" />
                </svg>
              </button>
              <button
                className="icon-btn"
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                title={theme === "dark" ? "Mode terang" : "Mode gelap"}
                aria-label="Ganti tema"
              >
                {theme === "dark" ? (
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                  >
                    <circle cx="12" cy="12" r="4.2" />
                    <path d="M12 2.5v2.4m0 14.2v2.4M2.5 12h2.4m14.2 0h2.4M5 5l1.7 1.7M17.3 17.3 19 19M19 5l-1.7 1.7M6.7 17.3 5 19" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.4 14.2A8.5 8.5 0 0 1 9.8 3.6a8.5 8.5 0 1 0 10.6 10.6Z" />
                  </svg>
                )}
              </button>
            </div>
          </header>

          <div className="live-row">
            <span className={`live-badge${error ? " err" : ""}`}>
              <span className="live-dot" />
              {error ? "GANGGUAN" : "LIVE"}
            </span>
            <span>
              {lastFetch
                ? `dimuat ${lastFetch.toLocaleTimeString("id-ID", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })} · auto-refresh 5 mnt`
                : "memuat…"}
            </span>
          </div>

          {error && (
            <div className="error-box">
              Gagal memuat data: {error}
              <br />
              <button onClick={refresh}>Coba lagi</button>
            </div>
          )}

          <StatTiles weather={weather} poi={poi} road={road} logs={logs} />

          <section>
            <h2>Waktu snapshot</h2>
            <div className="card">
              <div className="time-presets">
                <button
                  className={`chip${!at ? " active" : ""}`}
                  onClick={() => setAt("")}
                >
                  Sekarang
                </button>
                <button className="chip" onClick={setYesterday}>
                  Kemarin
                </button>
              </div>
              <div className="time-custom">
                <input
                  type="datetime-local"
                  value={at}
                  onChange={(e) => setAt(e.target.value)}
                  aria-label="Lihat kondisi pada waktu"
                />
              </div>
              <p className="hint">
                Peta menampilkan batch data terakhir sebelum waktu terpilih
                (PRD: bandingkan "kemarin vs sekarang").
              </p>
            </div>
          </section>

          <Layers
            show={show}
            toggle={toggle}
            weather={weather}
            poi={poi}
            road={road}
            theme={theme}
          />

          <LogPanel logs={logs} />

          <p className="foot">
            Backend <a href="https://geologix-api.onrender.com/docs">FastAPI</a>{" "}
            di Render free tier — permintaan pertama bisa ±1 mnt (cold start).
            <br />
            Data peta ©{" "}
            <a href="https://www.openstreetmap.org/copyright">
              kontributor OpenStreetMap
            </a>{" "}
            · basemap © CARTO · cuaca Open-Meteo & CHIRPS.
          </p>
        </div>
      </aside>

      <main className="map">
        <button
          className="panel-fab"
          onClick={() => setPanelOpen((v) => !v)}
          aria-expanded={panelOpen}
        >
          {panelOpen ? "✕ Tutup" : "☰ Panel"}
        </button>

        {at && (
          <div className="snapshot-chip">
            Snapshot {fmtUtc(new Date(at).toISOString())}
            <button onClick={() => setAt("")}>Kembali ke sekarang</button>
          </div>
        )}

        {!booted && !error && (
          <div className="map-overlay">
            <div className="box">
              <div className="spinner" />
              <div className="t">Memuat data pipeline…</div>
              {slowBoot && (
                <div className="s">
                  Server API (free tier) sedang dibangunkan — cold start bisa
                  ±1 menit. Terima kasih sudah menunggu.
                </div>
              )}
            </div>
          </div>
        )}

        <DeckGL
          initialViewState={INITIAL_VIEW}
          controller
          layers={layers}
          getTooltip={getTooltip}
          onClick={() => setPanelOpen(false)}
        >
          <Map mapStyle={BASEMAPS[theme]} />
        </DeckGL>
      </main>
    </div>
  );
}
