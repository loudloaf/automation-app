# BBI Automation: frontend React (migrasi bertahap)

Folder ini berdampingan dengan `frontend/index.html` lama (tidak diubah). `main.py` menyajikan `frontend-react/dist` bila ada; bila tidak, memakai UI lama.

## Menjalankan
```
cd frontend-react
npm install
npm run build        # hasil di dist/, lalu jalankan uvicorn seperti biasa (localhost:8000)
npm run build:watch  # selama migrasi: build otomatis tiap file disimpan
npm run dev          # opsional: localhost:5173 (login sekali lewat :8000, cookie dipakai bersama)
```
UI lama tetap bisa dibuka di http://localhost:8000/legacy selama migrasi. Kembali penuh ke UI lama: ganti nama/hapus folder `dist`.

## Aturan file
- 1 halaman = 1 file; tiap file diawali blok PAGE/FILE/ROUTE/ORIGIN/API/STORE dan bagian bertanda `[KODE-n]`.
- Skrip/dashboard baru: 1 file halaman + 1 entri di `src/registry/`.

## Status
Langkah 1-2 selesai (scaffold, shell, login). Halaman lain masih sementara.
