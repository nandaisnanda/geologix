// Stat tiles (skill dataviz: angka tunggal = stat tile, bukan chart).
// Nilai mengikuti slice filter waktu yang sama dengan peta.
import { relTime } from "./api";

export default function StatTiles({ weather, poi, road, logs }) {
  const riskMax = weather.items.length
    ? Math.max(...weather.items.map((d) => d.risk_index))
    : null;
  const last = logs[0];

  return (
    <div className="tiles" role="group" aria-label="Ringkasan snapshot">
      <div className="tile">
        <div className="v">{(weather.meta?.total ?? 0).toLocaleString("id-ID")}</div>
        <div className="l">sel risiko cuaca</div>
        <div className="s">
          {riskMax === null ? "…" : `risk maks ${riskMax.toFixed(2)}`}
        </div>
      </div>
      <div className="tile">
        <div className="v">{(poi.meta?.total ?? 0).toLocaleString("id-ID")}</div>
        <div className="l">POI anomali</div>
        <div className="s">outlier IQR jarak-ke-jalan</div>
      </div>
      <div className="tile">
        <div className="v">{(road.meta?.total ?? 0).toLocaleString("id-ID")}</div>
        <div className="l">road error</div>
        <div className="s">pasca-filter kelas arteri</div>
      </div>
      <div className="tile">
        <div className="v" style={{ fontSize: 15, marginTop: 3 }}>
          {last ? (
            <span className={last.status === "success" ? "okc" : "failc"}>
              {last.status === "success" ? "✓ sukses" : "✕ gagal"}
            </span>
          ) : (
            "…"
          )}
        </div>
        <div className="l">run pipeline terakhir</div>
        <div className="s">{last ? relTime(last.timestamp) : ""}</div>
      </div>
    </div>
  );
}
