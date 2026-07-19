import { CATEGORY_COLORS, CATEGORY_LABELS, RISK_RAMP, rgb } from "./colors";

export default function Legend() {
  return (
    <section>
      <h2>Legenda</h2>
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
      <ul className="legend-cats">
        {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
          <li key={key}>
            <span
              className="dot"
              style={{ background: rgb(CATEGORY_COLORS[key]) }}
            />
            {label}
          </li>
        ))}
      </ul>
    </section>
  );
}
