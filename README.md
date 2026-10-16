# Scraper Kata X (Twitter) - Playwright

Aplikasi otomasi pencarian dan scraping tweet di platform **X (Twitter)** berbasis **Playwright**. Program ini dirancang untuk mengumpulkan tweet berbahasa Indonesia berdasarkan kata kunci pilihan (*keywords*), menyaring tweet relevan, mengekstrak tanggal unggah secara akurat, serta menggabungkan data ke dalam berkas master (JSON & CSV) tanpa duplikasi.

---

## 🚀 Fitur Utama

- **Otomasi Browser (Playwright)**: Mensimulasikan perilaku pengguna nyata dengan dukungan Google Chrome, Microsoft Edge, atau Chromium bawaan.
- **Bypass Login dengan Cookies**: Menggunakan berkas `cookies.json` untuk sesi login otomatis tanpa perlu mengetik kredensial berulang kali.
- **Penyaringan Bahasa Indonesia**: Menggabungkan `langdetect` dan kamus kata umum bahasa Indonesia untuk memfilter tweet secara akurat.
- **Ekstraksi Tanggal Nyata**: Mengambil atribut `datetime` asli dari elemen `<time>` tweet (`tanggal_upload`), dipadukan dengan tanggal saat pengambilan data (`tanggal_scraping`).
- **Deduplikasi Cerdas**: Secara otomatis mencegah penyimpanan tweet duplikat berdasarkan kombinasi `kata_kerja` dan `teks`.
- **Target Tracking & Resume**: Melacak kuota tweet per kata (default: 25 tweet/kata). Jika dijalankan kembali, scraper hanya akan melanjutkan kata yang belum memenuhi target.
- **Pencarian Arsip / Top Tweets**: Mendukung parameter tanggal lampau (`SINCE_DATE`, misalnya tahun 2020 ke atas) menggunakan tab pencarian *Top* agar aman dari batas/error Twitter.

---

## 📁 Struktur Direktori

```text
├── cookies.json               # Berkas sesi cookies login Twitter/X
├── scraper_kata_kerja.py      # Skrip utama scraper
├── README.md                  # Dokumentasi proyek
├── user_data_playwright/      # Direktori sesi browser Playwright (dibuat otomatis)
└── hasil_scraping/            # Output data hasil scraping
    ├── semua_data.json        # Data master dalam format JSON
    ├── semua_data.csv         # Data master dalam format CSV
    └── failed_keywords.json   # Log kata kunci yang gagal mendapatkan tweet
```

---

## 🛠️ Instalasi & Prasyarat

1. **Python**: Pastikan menggunakan Python versi 3.10 atau yang lebih baru.
2. **Install Dependensi Python**:
   ```bash
   pip install playwright pandas langdetect
   ```
3. **Install Binary Browser Playwright**:
   ```bash
   playwright install chromium
   ```

---

## 🔐 Konfigurasi Akun (`cookies.json`)

Agar scraper dapat menelusuri pencarian Twitter/X tanpa terblokir halaman login:
1. Pasang ekstensi browser ekspor cookie (seperti *EditThisCookie* atau *Cookie-Editor*) di browser Anda.
2. Buka dan login ke akun [X (Twitter)](https://x.com/).
3. Ekspor cookies dalam format **JSON**.
4. Simpan hasilnya di direktori proyek dengan nama `cookies.json`.

---

## ⚙️ Konfigurasi Program

Pengaturan utama terdapat di bagian atas skrip [scraper_kata_kerja.py](scraper_kata_kerja.py):

| Variabel | Tipe | Default | Keterangan |
|---|---|---|---|
| `SEED_KEYWORDS` | `list` | `["meledak", "meleleh", "mengahangatkan", "membeku"]` | Daftar kata kerja target yang akan dicari. |
| `TARGET_PER_KATA` | `int` | `25` | Kuota minimal jumlah tweet yang ingin dikumpulkan per kata. |
| `SINCE_DATE` | `str` / `None` | `"2020-01-01"` | Batas awal tanggal tweet yang dicari (format `YYYY-MM-DD`). |
| `UNTIL_DATE` | `str` / `None` | `None` | Batas akhir tanggal tweet (opsional). |
| `USE_TWITTER_LANG_FILTER` | `bool` | `True` | Mengaktifkan filter bawaan pencarian `lang:id`. |
| `FALLBACK_TANPA_LANG_ID` | `bool` | `True` | Otomatis mencoba ulang tanpa `lang:id` jika hasil 0. |

---

## 🏃 Cara Menjalankan

### Opsi A: Menggunakan Antarmuka Web Streamlit (Direkomendasikan)
Jalankan aplikasi web interaktif:
```bash
streamlit run app.py
```
Di antarmuka browser:
- Anda dapat mengetik kata kerja target secara fleksibel (`SEED_KEYWORDS`).
- Memilih batas tanggal pencarian (`SINCE_DATE` dan `UNTIL_DATE`) via antarmuka tanggal.
- Memantau log proses scraping secara real-time.
- Mengunduh langsung hasil data dalam format CSV dan JSON.

---

### Opsi B: Menggunakan Terminal / CLI
Jalankan skrip secara langsung:
```bash
python scraper_kata_kerja.py
```
Menu interaktif akan muncul di terminal:
```text
Pilihan:
  [1] Jalankan Scraping Seed Keywords (Playwright/X)
  [2] 🔁 Scrape HANYA kata yang BELUM capai 25 data
  [3] ✍️  Input kata kerja manual
```
- Anda dapat memilih opsi **3** atau opsi **1** untuk menyesuaikan `SEED_KEYWORDS` dan `SINCE_DATE`.

---

## ☁️ Deploy ke Streamlit Cloud via GitHub

1. **Inisialisasi Git & Push ke GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for Streamlit X Scraper"
   git branch -M main
   git remote add origin https://github.com/<username-anda>/<nama-repo>.git
   git push -u origin main
   ```
2. **Koneksikan ke Streamlit Cloud**:
   - Kunjungi [share.streamlit.io](https://share.streamlit.io/).
   - Buat aplikasi baru dan pilih repository GitHub Anda.
   - Set Main file path ke `app.py`.
   - File `requirements.txt` dan `packages.txt` akan secara otomatis memasang Chromium dan Playwright di server Linux cloud.
3. **Autentikasi di Cloud**:
   - Saat aplikasi berjalan di Streamlit Cloud, centang opsi **"Jalankan Headless (Background)"** di sidebar, lalu unggah file `cookies.json` akun X Anda pada form upload yang tersedia.

---

## 📊 Format Output Data

Setiap data tersimpan di `hasil_scraping/semua_data.json` dengan format berikut:

```json
[
  {
    "kata_kerja": "meledak",
    "teks": "Jangan deh, nanti meledak -",
    "sumber": "X",
    "tanggal_upload": "2026-10-14",
    "tanggal_scraping": "2026-10-16",
    "mengandung_kerja": true,
    "kalimat_kunci": "Jangan deh, nanti meledak -",
    "link": "https://x.com/username/status/1234567890123456789"
  }
]
```

### Keterangan Kolom:
- **`kata_kerja`**: Kata kunci yang dicari.
- **`teks`**: Teks lengkap tweet.
- **`sumber`**: Sumber platform (`X`).
- **`tanggal_upload`**: Tanggal tweet dipublikasikan oleh pengguna.
- **`tanggal_scraping`**: Tanggal saat tweet diambil oleh scraper.
- **`mengandung_kerja`**: Nilai boolean (`true`/`false`) penanda keberadaan kata kerja dalam teks.
- **`kalimat_kunci`**: Potongan kalimat spesifik yang memuat kata kerja target.
- **`link`**: URL langsung ke tweet asli di X.
