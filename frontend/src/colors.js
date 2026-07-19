// Warna mengikuti palet referensi skill dataviz, tervalidasi
// (validate_palette.js --pairs all: PASS utk 4 slot pertama di kedua mode;
// WARN kontras slot magenta/kuning di mode terang dimitigasi legend
// berlabel + tooltip + ring pada titik). Varian dark = step dark resmi
// palet (bukan hasil flip otomatis).

// Kategorikal slot 1-4 (urutan tetap, jangan diubah/di-cycle).
const CATEGORY_COLORS_LIGHT = {
  dangling_node: [42, 120, 214], // #2a78d6
  disconnected_component: [0, 131, 0], // #008300
  oneway_inconsistency: [232, 123, 164], // #e87ba4
  poi_anomaly: [237, 161, 0], // #eda100
};

const CATEGORY_COLORS_DARK = {
  dangling_node: [57, 135, 229], // #3987e5
  disconnected_component: [0, 131, 0], // #008300
  oneway_inconsistency: [213, 81, 129], // #d55181
  poi_anomaly: [201, 133, 0], // #c98500
};

export function categoryColors(theme) {
  return theme === "dark" ? CATEGORY_COLORS_DARK : CATEGORY_COLORS_LIGHT;
}

export const CATEGORY_LABELS = {
  dangling_node: "Dangling node (arteri)",
  disconnected_component: "Komponen terputus",
  oneway_inconsistency: "Oneway tidak konsisten",
  poi_anomaly: "POI anomali",
};

// Sequential biru 100→700 (magnitudo risk index 0..1, satu hue terang→gelap).
// Ramp sama utk kedua tema: overlay di atas basemap, bukan di surface panel.
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
  return [...RISK_RAMP[idx], 175];
}

export const rgb = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
