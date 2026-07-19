// Panel layer: toggle switch per layer + legend kontekstual (legend muncul
// di bawah layer yang aktif — identitas warna tidak pernah color-alone,
// selalu berlabel; skill dataviz).
import { categoryColors, CATEGORY_LABELS, RISK_RAMP, rgb } from "./colors";
import { fmtUtc } from "./api";

function LayerRow({ title, sub, checked, onToggle, children }) {
  return (
    <div className="layer-row">
      <label className="layer-head">
        <div>
          <div className="layer-title">{title}</div>
          <div className="layer-sub">{sub}</div>
        </div>
        <span className="switch">
          <input type="checkbox" checked={checked} onChange={onToggle} />
          <span className="track" />
        </span>
      </label>
      {checked && children ? <div className="layer-legend">{children}</div> : null}
    </div>
  );
}

export default function Layers({ show, toggle, weather, poi, road, theme }) {
  const cat = categoryColors(theme);
  const roadKeys = [
    "dangling_node",
    "disconnected_component",
    "oneway_inconsistency",
  ];

  return (
    <section>
      <h2>Layer peta</h2>

      <LayerRow
        title="Risiko cuaca"
        sub={`${(weather.meta?.total ?? 0).toLocaleString("id-ID")} sel H3${
          weather.items[0] ? ` · ${fmtUtc(weather.items[0].computed_at)}` : ""
        }`}
        checked={show.weather}
        onToggle={() => toggle("weather")}
      >
        <div className="legend-ramp" aria-label="Skala risk index 0 sampai 1">
          {RISK_RAMP.map((c, i) => (
            <span key={i} style={{ background: rgb(c) }} />
          ))}
        </div>
        <div className="legend-ramp-labels">
          <span>0</span>
          <span>risk index</span>
          <span>1</span>
        </div>
      </LayerRow>

      <LayerRow
        title="POI anomali"
        sub={`${(poi.meta?.total ?? 0).toLocaleString("id-ID")} titik`}
        checked={show.poi}
        onToggle={() => toggle("poi")}
      >
        <ul className="legend-cats">
          <li>
            <span className="dot" style={{ background: rgb(cat.poi_anomaly) }} />
            {CATEGORY_LABELS.poi_anomaly} — jarak ke jalan &gt; batas IQR
          </li>
        </ul>
      </LayerRow>

      <LayerRow
        title="Road error"
        sub={`${(road.meta?.total ?? 0).toLocaleString("id-ID")} temuan${
          road.meta && road.meta.total > road.items.length
            ? ` · tampil ${road.items.length.toLocaleString("id-ID")}`
            : ""
        }`}
        checked={show.road}
        onToggle={() => toggle("road")}
      >
        <ul className="legend-cats">
          {roadKeys.map((k) => (
            <li key={k}>
              <span className="dot" style={{ background: rgb(cat[k]) }} />
              {CATEGORY_LABELS[k]}
            </li>
          ))}
        </ul>
        <p className="note">
          Temuan tersimpan pasca-filter boundary + kebijakan{" "}
          <strong>major</strong>: dead-end hanya di kelas jalan arteri
          (motorway–tertiary). Ujung gang/cul-de-sac perumahan tidak disimpan.
        </p>
      </LayerRow>
    </section>
  );
}
