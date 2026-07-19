# CLAUDE.md — Aturan Proyek GeoLogix AI

## Referensi Utama
Spesifikasi lengkap ada di `SPEC.md`. JANGAN baca seluruh SPEC.md tiap sesi —
rujuk hanya bagian yang relevan dengan tugas saat ini (misal: "baca Bagian 3.1
soal graph theory").

## Aturan Wajib
1. Ikuti urutan fase di SPEC.md Bagian 2 (STEP PENGERJAAN). Jangan loncat fase.
2. JANGAN buat/edit file apapun di folder `ml/` sebelum Fase 1-6 selesai dan
   punya log historis nyata. Kalau diminta fitur AI sebelum itu, tolak dan
   arahkan kembali ke fase yang belum selesai.
3. Semua rumus matematika (graph theory, AHP, WLC, Getis-Ord Gi*, IQR) WAJIB
   diimplementasikan persis sesuai SPEC.md Bagian 3 — bukan pendekatan bebas.
4. Setiap file pipeline wajib: docstring yang merujuk bagian SPEC.md terkait,
   minimal 1 unit test, dan logging hasil run ke tabel `pipeline_logs`.
5. Data OSM pakai 2 sumber terpisah — jangan dicampur:
   - `.pbf` → Pipeline 1 (Road QA, butuh topologi graph)
   - `.shp.zip` layer POI → Pipeline 2 (POI Validation)

## Struktur Folder
Ikuti struktur di SPEC.md Bagian 5.1. Jangan buat struktur folder sendiri.

## Sebelum Sesi Berakhir / Ganti Fase
Selalu update `PROGRESS.md` dengan: apa yang selesai, keputusan penting yang
diambil, dan langkah selanjutnya — sebelum user menjalankan /clear.

## Gaya Kerja
- Satu sesi fokus ke satu fase/pipeline.
- Kalau ada error, ringkas pesan errornya, jangan tempel full log/traceback
  panjang kecuali diminta.
- Jangan review/refactor banyak pipeline sekaligus dalam satu permintaan.
