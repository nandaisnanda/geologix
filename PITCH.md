# PITCH.md — Narasi Interview & Demo Flow (SPEC Fase 6, step 21)

Dokumen internal persiapan interview — bukan bagian dari dokumentasi teknis.

## Narasi 15 detik

> "Saya membangun sistem QA data peta untuk Jabodetabek yang berjalan otomatis
> tiap hari: mengaudit topologi jalan OSM dengan graph theory, memvalidasi posisi
> POI dengan statistik, dan menghitung peta risiko hujan per-hexagon dengan AHP
> dan Getis-Ord Gi*. Semua temuan diprioritaskan berdasarkan severity, populasi
> terdampak, dan kemudahan perbaikan — dan buktinya bukan klaim: setiap run
> tercatat di database dan bisa dilihat live di dashboard."

Versi satu kalimat (kalau dipotong):
> "Pipeline geospasial otomatis yang menemukan error peta OSM dan titik rawan
> hujan di Jabodetabek, lalu memprioritaskan mana yang paling layak diperbaiki
> dulu — berjalan terjadwal, log-nya bisa diaudit."

## Demo flow (±3 menit)

1. **Buka dashboard** https://geologix.vercel.app
   (ingat: API Render free tier — buka duluan sebelum interview supaya tidak
   kena cold start ±1 menit di depan orang).
2. **Layer hexagon risiko** (default on): "Tiap hexagon H3 = skor risiko hujan,
   gabungan hujan real-time Open-Meteo dan hotspot historis CHIRPS 5 tahun yang
   signifikan secara statistik. Perhatikan gradien ke arah Bogor — konsisten
   dengan orografi, bukan artefak." Hover satu sel → tunjukkan skor.
3. **Layer POI anomali**: "2.072 POI yang jaraknya ke jalan terdekat outlier
   IQR. Saya bedah 32 sample satu-satu terhadap OSM live — saya tahu persis mana
   yang artefak metode dan mana yang riil." (Ini poin jujur yang membedakan.)
4. **Panel log pipeline**: "Ini bukti sistem hidup — tiap baris satu run cron
   GitHub Actions, termasuk yang gagal. Log gagal sengaja tidak saya hapus:
   429 rate limit, OOM runner, timeout — semuanya ada penanganannya."
5. **Filter waktu**: mundurkan ke tanggal sebelumnya → "data snapshot per batch,
   bisa lihat kondisi 'kemarin vs sekarang'."
6. **Tutup dengan roadmap**: "ML sengaja belum — sistem ini justru sedang
   memproduksi data training-nya sendiri. Setelah beberapa bulan log konsisten,
   baru layak melatih model, dan hanya dipakai kalau menang dari baseline ini."

## Pertanyaan yang mungkin ditanya + jawaban singkat

- **"Kenapa tidak pakai ML dari awal?"** → Tidak ada data berlabel dan tidak ada
  baseline pembanding. Rule-based dulu = menghasilkan keduanya. (SPEC Bagian 4.)
- **"26% node dangling — masa error semua?"** → Betul, bukan. Itu justru temuan
  penting run full-area pertama: campuran artefak clip boundary + cul-de-sac
  asli. Respons saya: filter boundary + hanya simpan dead-end kelas arteri.
  Deteksi tetap utuh, persistence yang diseleksi.
- **"Kenapa H3 resolusi 7?"** → Model cuaca sumber ~11-25 km; grid lebih halus
  dari sumber = presisi palsu + 7× beban API/DB.
- **"AHP-nya konsisten?"** → CR = 0 (matriks 3 kriteria konsisten sempurna,
  bobot eksak 4/7, 2/7, 1/7); pipeline raise error kalau CR > 0.1.
- **"Apa yang akan kamu perbaiki berikutnya?"** → Jarak POI area dari tepi
  poligon (bukan representative_point), gang motorcycle-only masuk filter,
  koreksi FDR untuk hotspot. Semua sudah tercatat sebagai known limitation.

## Fakta angka yang harus hafal

| Angka | Arti |
|---|---|
| 703.926 / 1.708.734 | node / edge graph jalan Jabodetabek |
| 46.979 → 2.072 (4,4%) | POI full-area → outlier IQR |
| 1.079 / 348 | sel H3 res 7 / hotspot Gi* signifikan |
| 179.582 → 16 | kandidat dangling full-area → yang disimpan (dead-end kelas arteri saja) |
| 2.945 | temuan terprioritaskan P4 full-area (CR = 0; validasi checklist: 173 di sample Menteng) |
| 114 | unit test pass |
| 4 workflow, ±1.500 mnt/bln | jadwal cron hemat kuota (2.000 mnt) |
