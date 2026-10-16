import streamlit as st
import pandas as pd
import json
import sys
import subprocess
from datetime import datetime, date
from pathlib import Path

# Otomatis install Chromium Playwright saat deploy di Cloud / Linux
@st.cache_resource
def ensure_playwright_browsers():
    if sys.platform != "win32":
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        except Exception as e:
            st.warning(f"Gagal menginstall browser Playwright: {e}")

ensure_playwright_browsers()

# Import fungsi-fungsi inti dari scraper_kata_kerja.py
from scraper_kata_kerja import (
    scrape_x_playwright,
    simpan_hasil_gabungan,
    muat_data_tersimpan,
    muat_failed_keywords,
    hitung_status_target_kata,
    FILE_SEMUA_DATA_CSV,
    FILE_SEMUA_DATA_JSON,
    SEED_KEYWORDS,
    TARGET_PER_KATA,
    SINCE_DATE
)

# ── Konfigurasi Halaman ────────────────────────────────────────────────
st.set_page_config(
    page_title="X (Twitter) Scraper Kata",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling CSS Modern ─────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1DA1F2, #00BA7C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #8899A6;
        margin-bottom: 1.5rem;
    }
    .stat-card {
        background-color: rgba(29, 161, 242, 0.08);
        border: 1px solid rgba(29, 161, 242, 0.2);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .stat-val {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1DA1F2;
    }
    .stat-lbl {
        font-size: 0.85rem;
        color: #71767B;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🐦 Scraper Kata X (Twitter)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Aplikasi otomasi pencarian data tweet berbahasa Indonesia berbasis Playwright & Streamlit.</div>', unsafe_allow_html=True)

# ── Inisialisasi Session State ─────────────────────────────────────────
if "scraping_logs" not in st.session_state:
    st.session_state.scraping_logs = []
if "is_scraping" not in st.session_state:
    st.session_state.is_scraping = False

# ── Sidebar: Pengaturan & Konfigurasi ──────────────────────────────────
with st.sidebar:
    st.header("⚙️ Konfigurasi Scraping")

    # 1. Input Keywords
    st.subheader("1. Kata Kunci (Keywords)")
    default_keywords_str = ", ".join(SEED_KEYWORDS)
    keywords_input = st.text_area(
        "Daftar Kata (pisahkan dengan koma):",
        value=default_keywords_str,
        help="Masukkan kata yang ingin dicari di Twitter. Pisahkan dengan tanda koma.",
        height=100
    )
    user_keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

    # 2. Filter Tanggal SINCE_DATE
    st.subheader("2. Filter Tanggal")
    use_since = st.checkbox("Aktifkan batas awal tanggal (SINCE_DATE)", value=True)
    if use_since:
        default_since = datetime.strptime(SINCE_DATE, "%Y-%m-%d").date() if SINCE_DATE else date(2020, 1, 1)
        since_date_val = st.date_input(
            "Mulai Tanggal (SINCE_DATE):",
            value=default_since,
            help="Hanya mencari tweet yang dipublikasikan setelah tanggal ini."
        )
        since_str = since_date_val.strftime("%Y-%m-%d")
    else:
        since_str = None

    use_until = st.checkbox("Aktifkan batas akhir tanggal (UNTIL_DATE)", value=False)
    if use_until:
        until_date_val = st.date_input("Sampai Tanggal (UNTIL_DATE):", value=date.today())
        until_str = until_date_val.strftime("%Y-%m-%d")
    else:
        until_str = None

    # 3. Target Data Per Kata
    st.subheader("3. Kuota Target")
    target_count = st.number_input(
        "Target tweet per kata kerja:",
        min_value=1,
        max_value=500,
        value=TARGET_PER_KATA,
        step=5
    )

    # 4. Mode Browser & Language Filter
    st.subheader("4. Pengaturan Browser")
    headless_mode = st.checkbox(
        "Jalankan Headless (Background)",
        value=(sys.platform != "win32"),
        help="Wajib dicentang jika dijalankan di Streamlit Cloud / Server tanpa display."
    )
    use_lang_filter = st.checkbox("Gunakan filter Twitter `lang:id`", value=True)
    fallback_lang = st.checkbox("Fallback tanpa filter bahasa jika 0 hasil", value=True)

    # 5. Autentikasi Cookies
    st.subheader("5. Autentikasi Akun (Cookies)")
    st.markdown("X mewajibkan login. Masukkan/tempel teks JSON cookies Anda di bawah ini:")
    
    cookies_input = st.text_area(
        "Paste JSON Cookies",
        height=180,
        placeholder='[\n  {\n    "domain": ".x.com",\n    "name": "auth_token",\n    "value": "..."\n  }\n]',
        help="Salin isi JSON dari ekstensi cookies editor browser lalu tempel di sini."
    )
    
    cookies_data = None
    if cookies_input.strip():
        try:
            parsed_cookies = json.loads(cookies_input.strip())
            if isinstance(parsed_cookies, list):
                cookies_data = parsed_cookies
                st.success(f"✅ Cookies valid! Terdeteksi {len(cookies_data)} cookie.")
            else:
                st.error("Format harus berupa array/list JSON `[...]`.")
        except Exception as e:
            st.error(f"Format JSON tidak valid: {e}")
    elif Path("cookies.json").exists():
        st.info("ℹ️ Menggunakan `cookies.json` lokal bawaan (karena input teks kosong).")


# ── Main Content Area ─────────────────────────────────────────────────
df_lama = muat_data_tersimpan()
failed_kws = muat_failed_keywords()
counts_lama, kata_terpenuhi, kata_kurang = hitung_status_target_kata(
    df_lama, target_count, user_keywords
)

# Tampilkan Statistik Kartu
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-val">{len(df_lama)}</div>
        <div class="stat-lbl">Total Tweet Tersimpan</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-val">{len(user_keywords)}</div>
        <div class="stat-lbl">Kata Kunci Input</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-val" style="color:#00BA7C;">{len(kata_terpenuhi)}</div>
        <div class="stat-lbl">Target Terpenuhi (&ge;{target_count})</div>
    </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-val" style="color:#F91880;">{len(kata_kurang)}</div>
        <div class="stat-lbl">Belum Terpenuhi (&lt;{target_count})</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs Navigasi ─────────────────────────────────────────────────────
tab_scrape, tab_data = st.tabs(["🚀 Mulai Scraping", "📊 Data Tersimpan",])

with tab_scrape:
    st.markdown("### Eksekusi Scraping")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        tombol_semua = st.button("▶️ Scrape Semua Kata Input", type="primary", use_container_width=True)
    with col_btn2:
        kata_perlu = list(dict.fromkeys(failed_kws + kata_kurang))
        label_lanjut = f"🔁 Lanjutkan Hanya Kata yang Kurang ({len(kata_perlu)} kata)"
        tombol_kurang = st.button(label_lanjut, use_container_width=True, disabled=len(kata_perlu) == 0)

    target_scrape = None
    if tombol_semua:
        if not user_keywords:
            st.error("Daftar kata kunci tidak boleh kosong!")
        else:
            target_scrape = user_keywords
    elif tombol_kurang:
        target_scrape = [k for k in kata_perlu if k in user_keywords] or kata_perlu

    if target_scrape:
        st.info(f"Target kata ({len(target_scrape)} kata): **{', '.join(target_scrape)}**")
        
        # Tempat log langsung di antarmuka
        log_expander = st.expander("📝 Live Log Scraping", expanded=True)
        log_placeholder = log_expander.empty()
        logs_buffer = []

        def log_cb(message: str):
            logs_buffer.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            log_placeholder.code("\n".join(logs_buffer[-20:]), language="text")

        with st.spinner("Sedang menjalankan scraping dengan Playwright... Mohon tunggu"):
            try:
                df_baru = scrape_x_playwright(
                    keywords=target_scrape,
                    since_date=since_str,
                    until_date=until_str,
                    target_per_kata=int(target_count),
                    use_lang_filter=use_lang_filter,
                    fallback_lang=fallback_lang,
                    headless=headless_mode,
                    cookies_data=cookies_data,
                    log_callback=log_cb
                )

                if df_baru.empty and df_lama.empty:
                    st.warning("⚠️ Tidak ada data tweet baru yang berhasil dikumpulkan.")
                else:
                    df_final = simpan_hasil_gabungan(df_baru=df_baru, df_lama=df_lama)
                    st.success(f"🎉 Scraping selesai! Berhasil memperoleh {len(df_baru)} data baru. Total data saat ini: {len(df_final)} baris.")
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat scraping: {e}")

with tab_data:
    st.markdown("### Data Hasil Scraping")
    df_current = muat_data_tersimpan()
    
    if df_current.empty:
        st.info("Belum ada data tersimpan. Jalankan scraping terlebih dahulu.")
    else:
        # Filter kata di tabel
        daftar_kata_unik = ["Semua"] + sorted(list(df_current["kata_kerja"].dropna().unique()))
        pilihan_filter = st.selectbox("Filter berdasarkan kata:", daftar_kata_unik)

        if pilihan_filter != "Semua":
            df_tampil = df_current[df_current["kata_kerja"] == pilihan_filter]
        else:
            df_tampil = df_current

        st.dataframe(df_tampil, use_container_width=True, height=400)

        # Download Buttons
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            csv_data = df_current.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Unduh Data (CSV)",
                data=csv_data,
                file_name="hasil_scraping_x.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c_dl2:
            json_data = df_current.to_json(orient="records", force_ascii=False, indent=2)
            st.download_button(
                label="📥 Unduh Data (JSON)",
                data=json_data,
                file_name="hasil_scraping_x.json",
                mime="application/json",
                use_container_width=True
            )
