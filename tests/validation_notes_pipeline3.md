# Catatan Validasi Manual — Pipeline 3 Weather-Risk (SPEC 5.4)

Tanggal: 2026-07-19. Data: Open-Meteo snapshot 07:00 UTC (1.079 sel res 7),
baseline CHIRPS annual 2020-2024.

## 1. Rumus dicek terhadap nilai independen
- **Min-Max (3.1), AHP (3.2), WLC (3.3), Gi* (3.4)**: masing-masing diuji unit
  test terhadap nilai yang dihitung tangan/analitik (lihat `test_normalize.py`,
  `test_ahp_weights.py` — termasuk kasus wajib CR>0.1 raise, `test_wlc_combine.py`,
  `test_hotspot_gi_star.py` — z pusat klaster dihitung manual dari rumus SPEC).
- AHP P3 (2 kriteria, preferensi 2): bobot persis [2/3, 1/3], CR=0 — sesuai
  solusi analitik matriks 2x2.

## 2. Determinisme (checklist 5.4)
3x run `python -m src.pipeline_3_weather_risk` berturut-turut → identik:
1.079 sel, 348 hotspot, risk_min 0,0202, risk_max 0,9723 — log id 16-18 di
`pipeline_logs`, 3.237 baris (1.079x3) di `weather_risk_grid`.

## 3. Kewajaran geografis hasil nyata (sanity check)
- **Baseline CHIRPS**: 1.620-5.028 mm/tahun; pesisir Jakarta kering,
  selatan (Bogor) basah — gradien orografis tertangkap benar, 0 sel NaN,
  5/5 tahun valid semua sel.
- **Hotspot Gi\*** (348 sel, p<0.05 satu sisi): SEMUA di selatan grid
  (lat -6,44 sampai -6,77 — Depok selatan/Bogor/kaki Salak-Pangrango),
  mean historis 4.328 mm/th vs 2.662 mm/th non-hotspot. Konsisten dengan
  reputasi Bogor "kota hujan" → hotspot bukan artefak.
- **Sel risk tertinggi** (0,972): h3 `878c10220ffffff`, lat -6,67 (Bogor
  selatan) — gabungan hujan real-time maksimum jam itu (0,4 mm) + z Gi*
  4,23. Masuk akal.
- Hujan real-time run ini kecil (musim kemarau, max 0,4 mm) → spread
  RiskIndex didominasi variasi kriteria realtime yang sempit; perilaku saat
  hujan deras perlu diamati lagi saat musim hujan (bukan blocker).

## 4. Catatan/keputusan yang menunggu (bukan blocker)
- 348/1079 sel (32%) hotspot — wilayah signifikan luas & bersambung karena
  gradien orografis kuat. Kalau nanti mau lebih selektif: koreksi multiple
  testing (FDR/Bonferroni) ATAU naikkan ambang |z|; putuskan sebelum
  dashboard Fase 5.
- Budget API Open-Meteo untuk cron per jam melebihi free tier — keputusan
  frekuensi cron ditunda ke CI Fase 4 (lihat PROGRESS.md).
