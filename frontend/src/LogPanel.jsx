// Panel log riwayat run pipeline (SPEC.md PRD Dashboard: bukti sistem
// otomatis). Status memakai ikon + label, bukan warna saja.
import { fmtUtc } from "./api";

export default function LogPanel({ logs }) {
  return (
    <section className="logs">
      <h2>Riwayat run pipeline</h2>
      <table>
        <thead>
          <tr>
            <th>Waktu</th>
            <th>Pipeline</th>
            <th>Temuan</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} title={log.detail || ""}>
              <td>{fmtUtc(log.timestamp)}</td>
              <td>{log.pipeline_name}</td>
              <td className="num">{log.jumlah_temuan.toLocaleString("id-ID")}</td>
              <td className={log.status === "success" ? "ok" : "fail"}>
                {log.status === "success" ? "✓ sukses" : "✕ gagal"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
