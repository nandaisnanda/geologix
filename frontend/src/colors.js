// Warna mengikuti palet referensi skill dataviz, tervalidasi
// (validate_palette.js --pairs all --mode light: PASS; WARN kontras
// magenta/kuning dimitigasi legend berlabel + tooltip + ring putih titik).

// Kategorikal slot 1-4 (urutan tetap, jangan diubah/di-cycle).
export const CATEGORY_COLORS = {
  dangling_node: [42, 120, 214], // #2a78d6
  disconnected_component: [0, 131, 0], // #008300
  oneway_inconsistency: [232, 123, 164], // #e87ba4
  poi_anomaly: [237, 161, 0], // #eda100
};

export const CATEGORY_LABELS = {
  dangling_node: "Dangling node",
  disconnected_component: "Komponen terputus",
  oneway_inconsistency: "Oneway tidak konsisten",
  poi_anomaly: "POI anomali",
};

// Sequential biru 100→700 (magnitudo risk index 0..1, satu hue terang→gelap).
export const RISK_RAMP = [
  [205, 226, 251], // 100
  [158, 197, 244], // 200
  [109, 167, 236], // 300
  [57, 135, 229], // 400
  [37, 106, 191], // 500
  [24, 79, 149], // 600
  [13, 54, 107], // 700
];

export function riskColor(risk) {
  const idx = Math.min(
    RISK_RAMP.length - 1,
    Math.max(0, Math.floor(risk * RISK_RAMP.length))
  );
  return [...RISK_RAMP[idx], 170];
}

export const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
