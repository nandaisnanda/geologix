// Klien REST backend FastAPI (src/api/main.py) — SPEC.md Fase 5 step 18.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function getJSON(path, params = {}) {
  const url = new URL(path, API_BASE);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  }
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`${path}: HTTP ${resp.status}`);
  return resp.json();
}

// Timestamp DB = UTC naive (tanpa zona); tampilkan sebagai waktu lokal (WIB).
export function fmtUtc(isoNaive) {
  if (!isoNaive) return "—";
  return new Date(isoNaive.slice(0, 19) + "Z").toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Waktu relatif ringkas ("5 mnt lalu") untuk stat tile / status bar.
export function relTime(isoNaive) {
  if (!isoNaive) return "—";
  const ms = Date.now() - new Date(isoNaive.slice(0, 19) + "Z").getTime();
  const m = Math.round(ms / 60000);
  if (m < 1) return "baru saja";
  if (m < 60) return `${m} mnt lalu`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h} jam lalu`;
  return `${Math.round(h / 24)} hari lalu`;
}
