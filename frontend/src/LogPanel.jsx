// Panel log riwayat run pipeline (SPEC.md PRD Dashboard: bukti sistem
// otomatis). Status memakai ikon + label, bukan warna saja; log gagal
// sengaja ikut tampil — jejak insiden adalah bagian dari bukti.
import { fmtUtc } from "./api";

const PIPELINE_SHORT = {
  pipeline_1_road_qa: "P1 · road QA",
  pipeline_2_poi_qa: "P2 · POI QA",
  pipeline_3_weather_risk: "P3 · weather",
  pipeline_4_aggregator: "P4 · agregator",
  osm_refresh: "OSM refresh",
  poi_ingestion: "POI ingest",
  openmeteo_ingestion: "Open-Meteo",
  chirps_ingestion: "CHIRPS",
  worldpop_ingestion: "WorldPop",
  h3_grid: "Grid H3",
};

export default function LogPanel({ logs }) {
  return (
    <section className="logs">
      <h2>Riwayat run pipeline</h2>
      <table>
        <thead>
          <tr>
            <th>Waktu</th>
            <th>Pipeline</th>
            <th className="num">Temuan</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} title={log.detail || ""}>
              <td>{fmtUtc(log.timestamp)}</td>
              <td className="pname">
                {PIPELINE_SHORT[log.pipeline_name] || log.pipeline_name}
              </td>
              <td className="num">{log.jumlah_temuan.toLocaleString("id-ID")}</td>
              <td className={log.status === "success" ? "ok" : "fail"}>
                {log.status === "success" ? "✓ sukses" : "✕ gagal"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="hint">
        Arahkan kursor ke baris untuk detail run. Log gagal dibiarkan tampil —
        jejak insiden nyata, bukan dibersihkan.
      </p>
    </section>
  );
}
