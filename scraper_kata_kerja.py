"""
╔══════════════════════════════════════════════════════════════════════╗
║         Scraper Kata Kerja X (Twitter) via Playwright               ║
║         ─────────────────────────────────────────────────           ║
║  Metode  : Playwright (Browser Automation)                          ║
║  Output  : semua_data.csv & semua_data.json                         ║
║                                                                      ║
║  Format Output Data:                                                 ║
║  {                                                                   ║
║    "kata_kerja"      : "...",                                        ║
║    "teks"            : "...",                                        ║
║    "sumber"          : "X",                                          ║
║    "tanggal_upload"  : "YYYY-MM-DD",                                ║
║    "tanggal_scraping": "YYYY-MM-DD",                                ║
║    "mengandung_kerja": true/false,                                   ║
║    "kalimat_kunci"   : "..."                                         ║
║  }                                                                   ║
║                                                                      ║
║  Cara Install Dependensi:                                            ║
║    pip install playwright pandas langdetect                          ║
║    playwright install chromium                                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ══════════════════════════════════════════════════════════════════════
# [1] IMPORT LIBRARY
# ══════════════════════════════════════════════════════════════════════
# sys       → atur encoding terminal agar karakter Indonesia tampil benar
# re        → regex untuk memecah kalimat dan mencocokkan pola teks
# time      → memberi jeda antar-scroll agar tidak terdeteksi sebagai bot
# json      → membaca/menulis file cookies dan data JSON
# random    → membuat jeda waktu acak agar scraping lebih natural
# logging   → menampilkan log aktivitas program di terminal
# datetime  → mengelola dan memformat tanggal
# timedelta → menghitung selisih hari untuk filter tanggal dinamis
# Path      → mengelola path/lokasi file output secara lintas-platform
# pandas    → menyimpan dan mengolah data dalam bentuk tabel (DataFrame)
# playwright→ mengotomasi browser untuk membuka dan mengambil data dari X

import sys
import re
import time
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

# langdetect bersifat opsional — digunakan jika tersedia
# Jika tidak diinstall, program akan memakai fallback deteksi kata Indonesia
try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# Atur encoding stdout/stderr ke UTF-8 di Windows agar karakter Indonesia
# tidak rusak saat dicetak ke terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Konfigurasi format log: tampilkan waktu, level, dan pesan
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# [2] KONFIGURASI UTAMA
# ══════════════════════════════════════════════════════════════════════

# ── Kata Kerja Target ─────────────────────────────────────────────────
# Daftar kata kerja yang akan dicari di X (Twitter).
# Tambah atau ubah sesuai kebutuhan penelitian Anda.
SEED_KEYWORDS: list[str] = [
    "meledak",
    "meleleh",
    "menghangatkan",
    "membeku",
]

# ── Filter Bahasa ─────────────────────────────────────────────────────
# USE_TWITTER_LANG_FILTER → True  : tambahkan "lang:id" ke query pencarian
#                           False : cari tanpa filter bahasa
# FALLBACK_TANPA_LANG_ID  → True  : jika hasil dengan lang:id = 0,
#                                    coba ulang tanpa filter bahasa
USE_TWITTER_LANG_FILTER: bool = True
FALLBACK_TANPA_LANG_ID: bool  = True

# ── Filter Tanggal ────────────────────────────────────────────────────
# SINCE_DATE      → format "YYYY-MM-DD", atau None untuk tanpa batas awal
# SINCE_DATE_DAYS → hitung mundur N hari dari hari ini (alternatif SINCE_DATE)
# UNTIL_DATE      → format "YYYY-MM-DD", atau None untuk tanpa batas akhir
SINCE_DATE: str | None      = "2020-01-01"
SINCE_DATE_DAYS: int | None = None
UNTIL_DATE: str | None      = None

# ── Tab Pencarian ─────────────────────────────────────────────────────
# "top"  → tweet paling relevan (direkomendasikan untuk pencarian tahun lampau)
# "live" → tweet terbaru real-time
SEARCH_TAB_X: str = "top" if SINCE_DATE is not None else "live"

# ── Target Data ───────────────────────────────────────────────────────
# Jumlah tweet yang ingin dikumpulkan per kata kerja
TARGET_PER_KATA: int = 25

# ── Lokasi File Output ────────────────────────────────────────────────
# Semua hasil scraping disimpan di folder "hasil_scraping/"
OUTPUT_DIR = Path("hasil_scraping")
OUTPUT_DIR.mkdir(exist_ok=True)

FILE_SEMUA_DATA_CSV    = OUTPUT_DIR / "semua_data.csv"       # Format tabel
FILE_SEMUA_DATA_JSON   = OUTPUT_DIR / "semua_data.json"      # Format JSON
FAILED_KEYWORDS_FILE   = OUTPUT_DIR / "failed_keywords.json" # Kata yang gagal

# ── Kamus Kata Indonesia Umum ─────────────────────────────────────────
# Digunakan sebagai fallback deteksi bahasa Indonesia
# jika library langdetect tidak tersedia
KATA_INDONESIA_UMUM: set[str] = {
    "yang", "dan", "di", "itu", "ini", "dengan", "untuk", "tidak",
    "ada", "ke", "dari", "juga", "bisa", "sudah", "saya", "aku",
    "kamu", "dia", "kita", "mereka", "atau", "tapi", "kalau", "karena",
    "aja", "gue", "gw", "lo", "lu", "udah", "lagi", "banget", "dong",
    "sih", "deh", "nih", "nah", "kan", "kak", "mas", "sis", "bro",
    "nya", "punya", "mau", "mah", "wkwk", "haha", "emang", "ga", "gak",
    "nggak", "kayak", "gimana", "kenapa", "makanya", "soalnya", "tuh", "kok",
    "doang", "jangan", "pake", "sama", "lebih", "buat", "terus", "biar",
    "kalo", "yg", "dgn", "bener", "pas", "tau", "org", "bgt", "anjir", "woy",
}


# ══════════════════════════════════════════════════════════════════════
# [3] FUNGSI-FUNGSI PEMBANTU (HELPER FUNCTIONS)
# ══════════════════════════════════════════════════════════════════════

def is_indonesian(teks: str, threshold_kata: int = 2) -> bool:
    """
    Mendeteksi apakah teks berbahasa Indonesia.

    Strategi deteksi (berurutan):
      1. Jika langdetect tersedia → gunakan langdetect
      2. Jika tidak → cocokkan dengan KATA_INDONESIA_UMUM
         dan hitung berapa banyak kata yang cocok

    Parameter:
        teks           → teks yang akan diperiksa
        threshold_kata → minimal berapa kata Indonesia harus cocok (default: 2)

    Return:
        True jika terdeteksi berbahasa Indonesia, False jika tidak
    """
    # Abaikan teks yang terlalu pendek atau bukan string
    if not isinstance(teks, str) or len(teks.strip()) < 10:
        return False

    # Prioritas: gunakan langdetect jika tersedia
    if LANGDETECT_AVAILABLE:
        try:
            return detect(teks) == "id"
        except Exception:
            pass  # Jika gagal, lanjut ke metode fallback

    # Fallback: hitung berapa banyak kata Indonesia umum ada di teks
    kata_teks = set(re.findall(r'\b\w+\b', teks.lower()))
    cocok = kata_teks & KATA_INDONESIA_UMUM
    return len(cocok) >= threshold_kata


def cocok_keyword(keyword: str, teks: str) -> bool:
    """
    Mengecek apakah kata kerja (keyword) ada di dalam teks tweet.

    Fitur:
      - Perbandingan case-insensitive (tidak peduli huruf besar/kecil)
      - Menangani kata dengan tanda hubung:
        contoh "me-ledak" tetap cocok dengan "meledak"

    Parameter:
        keyword → kata kerja yang dicari
        teks    → isi tweet yang diperiksa

    Return:
        True jika keyword ditemukan di teks, False jika tidak
    """
    if not isinstance(teks, str):
        return False

    teks_lower = teks.lower()
    kw_lower   = keyword.lower()

    # Cek langsung
    if kw_lower in teks_lower:
        return True

    # Cek dengan menghapus tanda hubung pada keyword maupun teks
    kw_alt   = kw_lower.replace("-", "") if "-" in kw_lower else kw_lower
    teks_alt = teks_lower.replace("-", "")
    return kw_alt in teks_alt


def ekstrak_kalimat_kunci(teks: str, kata: str) -> str:
    """
    Mengambil potongan kalimat dari tweet yang mengandung kata kerja target.

    Cara kerja:
      1. Pecah teks menjadi kalimat berdasarkan tanda baca (. ! ? \\n)
      2. Cari kalimat pertama yang mengandung kata kerja
      3. Jika tidak ditemukan, ambil 150 karakter pertama sebagai fallback

    Parameter:
        teks → isi lengkap tweet
        kata → kata kerja yang dicari

    Return:
        String kalimat yang memuat kata kerja (atau 150 karakter pertama teks)
    """
    if not isinstance(teks, str):
        return ""

    kalimat = re.split(r'[.!?\n]', teks)
    cocok   = [k.strip() for k in kalimat if kata.lower() in k.lower()]
    return cocok[0] if cocok else teks[:150]


# ══════════════════════════════════════════════════════════════════════
# [4] FUNGSI MANAJEMEN DATA TERSIMPAN
# ══════════════════════════════════════════════════════════════════════

def muat_data_tersimpan() -> pd.DataFrame:
    """
    Memuat data hasil scraping sebelumnya dari file lokal.

    Urutan prioritas pembacaan:
      1. semua_data.json  (prioritas utama, lebih lengkap)
      2. semua_data.csv   (fallback jika JSON tidak ada)
      3. DataFrame kosong (jika tidak ada file sama sekali)

    Juga menangani kompatibilitas kolom lama:
      - "kata_gaul" → diubah menjadi "kata_kerja"
      - "tanggal"   → diubah menjadi "tanggal_upload"

    Return:
        pd.DataFrame berisi data yang sudah tersimpan, atau DataFrame kosong
    """
    # Coba baca dari JSON terlebih dahulu
    if FILE_SEMUA_DATA_JSON.exists():
        try:
            df = pd.read_json(FILE_SEMUA_DATA_JSON, encoding="utf-8")
            # Normalisasi nama kolom dari versi lama
            if "kata_gaul" in df.columns and "kata_kerja" not in df.columns:
                df = df.rename(columns={"kata_gaul": "kata_kerja"})
            if "tanggal" in df.columns and "tanggal_upload" not in df.columns:
                df = df.rename(columns={"tanggal": "tanggal_upload"})
            log.info(f"📂 Data master dimuat dari {FILE_SEMUA_DATA_JSON.name} ({len(df)} baris)")
            return df
        except Exception as e:
            log.warning(f"Gagal membaca {FILE_SEMUA_DATA_JSON}: {e}")

    # Fallback ke CSV jika JSON tidak ada atau rusak
    if FILE_SEMUA_DATA_CSV.exists():
        try:
            df = pd.read_csv(FILE_SEMUA_DATA_CSV, encoding="utf-8-sig")
            if "kata_gaul" in df.columns and "kata_kerja" not in df.columns:
                df = df.rename(columns={"kata_gaul": "kata_kerja"})
            if "tanggal" in df.columns and "tanggal_upload" not in df.columns:
                df = df.rename(columns={"tanggal": "tanggal_upload"})
            log.info(f"📂 Data master dimuat dari {FILE_SEMUA_DATA_CSV.name} ({len(df)} baris)")
            return df
        except Exception as e:
            log.warning(f"Gagal membaca {FILE_SEMUA_DATA_CSV}: {e}")

    # Tidak ada file tersimpan — kembalikan DataFrame kosong
    return pd.DataFrame()


def hitung_status_target_kata(
    df: pd.DataFrame,
    target: int = TARGET_PER_KATA,
    keywords: list[str] = None
) -> tuple[dict, list[str], list[str]]:
    """
    Menghitung status pencapaian target per kata kerja.

    Parameter:
        df       → DataFrame data yang sudah terkumpul
        target   → jumlah data yang ingin dicapai per kata
        keywords → daftar kata kerja yang dipantau

    Return:
        counts          → dict {kata: jumlah_data}
        kata_terpenuhi  → list kata yang sudah ≥ target
        kata_kurang     → list kata yang masih < target
    """
    if keywords is None:
        keywords = SEED_KEYWORDS

    counts = {}
    col = "kata_kerja" if (df is not None and "kata_kerja" in df.columns) else "kata_gaul"
    if df is not None and not df.empty and col in df.columns:
        counts = df[col].value_counts().to_dict()

    kata_terpenuhi = [kw for kw in keywords if counts.get(kw, 0) >= target]
    kata_kurang    = [kw for kw in keywords if counts.get(kw, 0) < target]
    return counts, kata_terpenuhi, kata_kurang


# ══════════════════════════════════════════════════════════════════════
# [5] FUNGSI MANAJEMEN KATA GAGAL (FAILED KEYWORDS)
# ══════════════════════════════════════════════════════════════════════

def muat_failed_keywords() -> list[str]:
    """
    Memuat daftar kata yang sebelumnya gagal mendapat data dari file JSON.
    """
    if not FAILED_KEYWORDS_FILE.exists():
        return []
    try:
        with open(FAILED_KEYWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def simpan_failed_keywords(gagal: list[str]) -> None:
    """
    Menambahkan kata-kata yang gagal ke file failed_keywords.json.
    """
    existing = muat_failed_keywords()
    gabungan = list(dict.fromkeys(existing + gagal))
    with open(FAILED_KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(gabungan, f, ensure_ascii=False, indent=2)
    log.info(f"⚠️  {len(gagal)} kata gagal disimpan ke {FAILED_KEYWORDS_FILE.name}")


def hapus_failed_keywords(berhasil: list[str]) -> None:
    """
    Menghapus kata-kata dari daftar gagal jika sudah berhasil mendapat data.
    """
    if not FAILED_KEYWORDS_FILE.exists():
        return
    current = muat_failed_keywords()
    if not current:
        return
    sisa = [kw for kw in current if kw not in berhasil]
    with open(FAILED_KEYWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(sisa, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════
# [6] FUNGSI UTAMA SCRAPING (PLAYWRIGHT)
# ══════════════════════════════════════════════════════════════════════

def scrape_x_playwright(
    keywords: list[str] = None,
    since_date: str | None = SINCE_DATE,
    until_date: str | None = UNTIL_DATE,
    target_per_kata: int = TARGET_PER_KATA,
    use_lang_filter: bool = USE_TWITTER_LANG_FILTER,
    fallback_lang: bool = FALLBACK_TANPA_LANG_ID,
    headless: bool = False,
    cookies_data: list[dict] | None = None,
    user_data_dir: str = "user_data_playwright",
    log_callback = None
) -> pd.DataFrame:
    """
    Fungsi inti: scraping X (Twitter) menggunakan Playwright.
    """
    def emit_log(msg: str, level: str = "info"):
        if level == "warning":
            log.warning(msg)
        elif level == "error":
            log.error(msg)
        else:
            log.info(msg)
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                pass

    keywords = keywords or SEED_KEYWORDS
    results: list[dict] = []
    kata_gagal: list[str] = []

    # Muat data tersimpan untuk mengetahui berapa yang sudah ada
    df_master  = muat_data_tersimpan()
    col        = "kata_kerja" if (not df_master.empty and "kata_kerja" in df_master.columns) else "kata_gaul"
    counts_awal = (
        df_master[col].value_counts().to_dict()
        if not df_master.empty and col in df_master.columns
        else {}
    )

    # ── Bangun parameter filter tanggal untuk URL ─────────────────────
    filter_tanggal = ""
    info_list: list[str] = []

    if since_date is not None:
        filter_tanggal += f"%20since%3A{since_date}"
        info_list.append(f"since:{since_date}")
    elif SINCE_DATE_DAYS is not None:
        calc_since = (datetime.now() - timedelta(days=SINCE_DATE_DAYS)).strftime("%Y-%m-%d")
        filter_tanggal += f"%20since%3A{calc_since}"
        info_list.append(f"since:{calc_since}")

    if until_date is not None:
        filter_tanggal += f"%20until%3A{until_date}"
        info_list.append(f"until:{until_date}")

    info_tanggal = " | ".join(info_list) if info_list else "tanpa batas tanggal"
    search_tab = "top" if since_date is not None else "live"

    def build_url(kw: str, use_lang: bool = True) -> str:
        q_encoded  = kw.replace(" ", "%20")
        lang_param = "%20lang%3Aid" if use_lang else ""
        tab_param  = "&f=live" if search_tab == "live" else ""
        return (
            f"https://x.com/search?q={q_encoded}{lang_param}"
            f"{filter_tanggal}&src=typed_query{tab_param}"
        )

    emit_log(
        f"Konfigurasi: lang:id={use_lang_filter} | "
        f"{info_tanggal} | tab={search_tab} | headless={headless}"
    )

    # ── Buka Browser dengan Playwright ───────────────────────────────
    with sync_playwright() as p:
        ctx = None

        browsers_to_try = [
            ("chrome",  "Google Chrome"),
            ("msedge",  "Microsoft Edge"),
            (None,      "Chromium"),
        ]
        if headless:
            browsers_to_try = [(None, "Chromium (Headless)")]

        for channel_name, label in browsers_to_try:
            try:
                launch_kwargs = {
                    "headless": headless,
                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                }
                if channel_name:
                    launch_kwargs["channel"] = channel_name

                emit_log(f"Membuka browser: {label}...")
                ctx = p.chromium.launch_persistent_context(user_data_dir, **launch_kwargs)
                emit_log(f"✅ Berhasil meluncurkan {label}!")
                break
            except Exception as e_br:
                emit_log(f"Browser {label} gagal dibuka ({e_br}). Mencoba opsi berikutnya...", level="warning")

        if ctx is None:
            raise RuntimeError(
                "Gagal membuka browser Playwright. "
                "Pastikan browser tidak sedang terbuka di proses lain."
            )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ── Muat Cookies Login ────────────────────────────────────────
        loaded_cookies = None
        if cookies_data and isinstance(cookies_data, list):
            emit_log("🍪 Menggunakan cookies dari input data / sesi...")
            loaded_cookies = cookies_data
        else:
            cookie_file = Path("cookies.json")
            if cookie_file.exists():
                emit_log("🍪 Memuat cookies dari cookies.json...")
                try:
                    with open(cookie_file, "r", encoding="utf-8") as f:
                        loaded_cookies = json.load(f)
                except Exception as e_ck:
                    emit_log(f"Gagal membaca cookies.json: {e_ck}", level="warning")

        if loaded_cookies:
            for cookie in loaded_cookies:
                if "expirationDate" in cookie:
                    cookie["expires"] = cookie.pop("expirationDate")
                for k in ["hostOnly", "session", "storeId"]:
                    cookie.pop(k, None)
                if cookie.get("sameSite") == "no_restriction":
                    cookie["sameSite"] = "None"
                elif cookie.get("sameSite") not in ["Strict", "Lax", "None"]:
                    cookie.pop("sameSite", None)

            try:
                ctx.add_cookies(loaded_cookies)
                emit_log("✅ Cookies berhasil dimuat!")
            except Exception as e_ck_add:
                emit_log(f"⚠️ Gagal menerapkan cookies: {e_ck_add}", level="warning")
        else:
            if headless:
                emit_log("⚠️ Mode Headless tanpa cookies.json! X (Twitter) kemungkinan besar membatasi pencarian.", level="warning")
            else:
                page.goto("https://x.com/")
                emit_log("⚠️ Silakan login ke akun X Anda di jendela browser.")
                input("👉 Tekan ENTER di console ini setelah selesai login... ")

        tgl_scraping_hari_ini = datetime.now().strftime("%Y-%m-%d")

        # ── Loop Scraping Per Kata Kerja ─────────────────────────────
        try:
            for kw in keywords:
                sudah_ada      = counts_awal.get(kw, 0)
                butuh_tambahan = max(0, target_per_kata - sudah_ada)

                # Lewati kata yang datanya sudah cukup
                if butuh_tambahan == 0:
                    emit_log(f"⏭️  '{kw}' sudah ada {sudah_ada} data. Melewati...")
                    continue

                emit_log(
                    f"\n🔍 Memproses '{kw}' "
                    f"(Sudah: {sudah_ada} | Butuh: {butuh_tambahan} | "
                    f"Target: {target_per_kata})"
                )

                url = build_url(kw, use_lang=use_lang_filter)
                emit_log(f"URL: {url}")

                try:
                    if not ctx.pages:
                        page = ctx.new_page()
                    else:
                        page = ctx.pages[0]

                    def ambil_tweets(target_url: str, min_butuh: int) -> list[dict]:
                        page.goto(target_url, wait_until="domcontentloaded", timeout=90_000)
                        time.sleep(4)

                        try:
                            retry_btn = page.query_selector(
                                'button:has-text("Retry"), [role="button"]:has-text("Retry")'
                            )
                            if retry_btn:
                                retry_btn.click()
                                time.sleep(3)
                        except Exception:
                            pass

                        item_terkumpul: dict[str, str] = {}
                        scroll_stuck = 0
                        max_scrolls  = 25

                        for s_idx in range(max_scrolls):
                            tweet_articles = page.query_selector_all(
                                'article[data-testid="tweet"]'
                            )
                            prev_count = len(item_terkumpul)

                            for article in tweet_articles:
                                try:
                                    text_el = article.query_selector(
                                        '[data-testid="tweetText"]'
                                    )
                                    if not text_el:
                                        continue

                                    t = text_el.inner_text().strip()

                                    if not (
                                        cocok_keyword(kw, t)
                                        and len(t) > 20
                                        and is_indonesian(t)
                                    ):
                                        continue

                                    time_el   = article.query_selector("time")
                                    tgl_upload = tgl_scraping_hari_ini
                                    if time_el:
                                        dt_attr = time_el.get_attribute("datetime")
                                        if dt_attr:
                                            tgl_upload = dt_attr.split("T")[0]

                                    if t not in item_terkumpul:
                                        item_terkumpul[t] = tgl_upload

                                except Exception:
                                    continue

                            if len(item_terkumpul) >= min_butuh:
                                emit_log(
                                    f"  🎯 Target {min_butuh} tweet untuk '{kw}' "
                                    f"tercapai pada scroll ke-{s_idx + 1}!"
                                )
                                break

                            if len(item_terkumpul) == prev_count:
                                scroll_stuck += 1
                                if scroll_stuck >= 4:
                                    emit_log(
                                        f"  ℹ️  Tidak ada tweet baru setelah "
                                        f"{scroll_stuck} scroll berturut-turut."
                                    )
                                    break
                            else:
                                scroll_stuck = 0

                            page.keyboard.press("End")
                            time.sleep(random.uniform(1.8, 2.8))

                        return [
                            {
                                "kata_kerja"       : kw,
                                "teks"             : t,
                                "sumber"           : "X",
                                "tanggal_upload"   : tgl_up,
                                "tanggal_scraping" : tgl_scraping_hari_ini,
                                "mengandung_kerja" : cocok_keyword(kw, t),
                                "kalimat_kunci"    : ekstrak_kalimat_kunci(t, kw),
                            }
                            for t, tgl_up in item_terkumpul.items()
                        ]

                    tweets_lolos = ambil_tweets(url, butuh_tambahan)

                    if (
                        len(tweets_lolos) == 0
                        and use_lang_filter
                        and fallback_lang
                    ):
                        emit_log(
                            f"  ⚠️  0 hasil untuk '{kw}' dengan lang:id. "
                            f"Mencoba ulang tanpa filter lang:id...",
                            level="warning"
                        )
                        url_fallback = build_url(kw, use_lang=False)
                        tweets_lolos = ambil_tweets(url_fallback, butuh_tambahan)
                        emit_log(
                            f"  → Fallback '{kw}' mendapat {len(tweets_lolos)} tweet."
                        )

                    results.extend(tweets_lolos)
                    found_count   = len(tweets_lolos)
                    total_sekarang = sudah_ada + found_count

                    if found_count == 0 and sudah_ada == 0:
                        kata_gagal.append(kw)

                    emit_log(
                        f"  → {found_count} tweet baru. "
                        f"Total: {total_sekarang}/{target_per_kata}"
                    )

                except Exception as e:
                    emit_log(f"Gagal memproses kata '{kw}': {e}", level="warning")
                    if sudah_ada == 0:
                        kata_gagal.append(kw)

                time.sleep(random.uniform(2.5, 4.0))

        except KeyboardInterrupt:
            emit_log("\n⚠️  Scraping dihentikan manual (KeyboardInterrupt).", level="warning")
            kw_sudah  = set(r["kata_kerja"] for r in results) | set(kata_gagal)
            kw_belum  = [k for k in keywords if k not in kw_sudah]
            kata_gagal.extend(kw_belum)

        finally:
            try:
                ctx.close()
            except Exception:
                pass

    # ── Simpan Status Kata Gagal ──────────────────────────────────────
    berhasil = [kw for kw in keywords if kw not in kata_gagal]
    if kata_gagal:
        simpan_failed_keywords(kata_gagal)
    if berhasil:
        hapus_failed_keywords(berhasil)

    return pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════
# [7] FUNGSI PENYIMPANAN & PENGGABUNGAN DATA
# ══════════════════════════════════════════════════════════════════════

def format_dan_bersihkan_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merapikan dan menstandarkan struktur DataFrame sebelum disimpan.

    Fungsi ini memastikan:
      - Kolom lama dinormalisasi ke nama baru
      - Kolom yang hilang diisi dengan nilai default
      - Hanya kolom yang diperlukan yang disertakan
      - Urutan kolom konsisten di setiap penyimpanan

    Kolom final yang dihasilkan:
      kata_kerja | teks | sumber | tanggal_upload |
      tanggal_scraping | mengandung_kerja | kalimat_kunci

    Parameter:
        df → DataFrame yang akan dirapikan

    Return:
        DataFrame yang sudah dirapikan, atau DataFrame kosong jika input kosong
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Normalisasi nama kolom dari versi lama program
    if "kata_gaul" in df.columns and "kata_kerja" not in df.columns:
        df = df.rename(columns={"kata_gaul": "kata_kerja"})
    if "tanggal" in df.columns and "tanggal_upload" not in df.columns:
        df = df.rename(columns={"tanggal": "tanggal_upload"})

    # Isi kolom yang mungkin tidak ada
    tgl_hari_ini = datetime.now().strftime("%Y-%m-%d")
    if "tanggal_scraping" not in df.columns:
        df["tanggal_scraping"] = tgl_hari_ini

    if "mengandung_kerja" not in df.columns:
        df["mengandung_kerja"] = df.apply(
            lambda r: cocok_keyword(str(r["kata_kerja"]), str(r["teks"])), axis=1
        )

    if "kalimat_kunci" not in df.columns:
        df["kalimat_kunci"] = df.apply(
            lambda r: ekstrak_kalimat_kunci(str(r["teks"]), str(r["kata_kerja"])), axis=1
        )

    # Pastikan semua kolom final ada; isi string kosong jika tidak ada
    kolom_final = [
        "kata_kerja",
        "teks",
        "sumber",
        "tanggal_upload",
        "tanggal_scraping",
        "mengandung_kerja",
        "kalimat_kunci",
    ]
    for col in kolom_final:
        if col not in df.columns:
            df[col] = ""

    return df[kolom_final]


def simpan_hasil_gabungan(
    df_baru: pd.DataFrame,
    df_lama: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Menggabungkan data baru dengan data lama, lalu menyimpannya.

    Proses:
      1. Format dan bersihkan kedua DataFrame
      2. Gabungkan menjadi satu (concat)
      3. Hapus duplikat berdasarkan kata_kerja + teks
      4. Simpan ke semua_data.csv dan semua_data.json
      5. Tampilkan laporan ringkas

    Parameter:
        df_baru → DataFrame berisi tweet dari sesi scraping ini
        df_lama → DataFrame data yang sudah tersimpan sebelumnya
                  (jika None, akan dimuat otomatis)

    Return:
        DataFrame gabungan yang sudah disimpan
    """
    if df_lama is None:
        df_lama = muat_data_tersimpan()

    list_df: list[pd.DataFrame] = []
    if df_lama is not None and not df_lama.empty:
        list_df.append(format_dan_bersihkan_df(df_lama))
    if df_baru is not None and not df_baru.empty:
        list_df.append(format_dan_bersihkan_df(df_baru))

    if not list_df:
        log.warning("Tidak ada data untuk disimpan.")
        return pd.DataFrame()

    df_gabungan   = pd.concat(list_df, ignore_index=True)
    total_sebelum = len(df_gabungan)

    # Hapus duplikat: tweet yang sama untuk kata yang sama
    df_gabungan   = df_gabungan.drop_duplicates(
        subset=["kata_kerja", "teks"], keep="first"
    )
    total_setelah = len(df_gabungan)
    duplikat      = total_sebelum - total_setelah

    # Tampilkan laporan ringkas
    print("\n" + "=" * 60)
    print("📊 LAPORAN PENGGABUNGAN DATA")
    print("=" * 60)
    print(f"  • Data baru diperoleh        : {len(df_baru) if df_baru is not None else 0} baris")
    if duplikat > 0:
        print(f"  • Duplikat dibersihkan       : {duplikat} baris")
    print(f"  • Total akhir data tersimpan : {total_setelah} baris")
    kata_terkumpul = df_gabungan["kata_kerja"].unique().tolist()
    print(f"  • Kata kerja tercakup        : {len(kata_terkumpul)} kata")
    print(f"    {kata_terkumpul}")
    print("=" * 60)

    # Simpan ke file master (keduanya selalu diperbarui bersamaan)
    df_gabungan.to_csv(FILE_SEMUA_DATA_CSV, index=False, encoding="utf-8-sig")
    df_gabungan.to_json(
        FILE_SEMUA_DATA_JSON, orient="records", force_ascii=False, indent=2
    )
    log.info(f"✅ Disimpan ke {FILE_SEMUA_DATA_JSON.name} & {FILE_SEMUA_DATA_CSV.name}")

    # Bersihkan daftar kata gagal untuk kata yang kini sudah berhasil
    hapus_failed_keywords(kata_terkumpul)

    return df_gabungan


# ══════════════════════════════════════════════════════════════════════
# [8] FUNGSI UTAMA (MAIN)
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Titik masuk utama program.

    Alur:
      1. Tampilkan header dan status data tersimpan
      2. Tampilkan menu pilihan kepada pengguna
      3. Jalankan scraping sesuai pilihan
      4. Simpan dan gabungkan hasil

    Menu:
      [1] Scrape semua SEED_KEYWORDS dari awal
      [2] Scrape hanya kata yang belum memenuhi target (+ kata gagal sebelumnya)
      [3] Input kata kerja manual dari keyboard
    """
    print("=" * 60)
    print("  Scraper Kata Kerja X (Twitter) - Playwright")
    print("=" * 60)

    # Muat data dan hitung status
    df_lama   = muat_data_tersimpan()
    failed_kws = muat_failed_keywords()
    counts_lama, kata_terpenuhi, kata_kurang = hitung_status_target_kata(
        df_lama, TARGET_PER_KATA, SEED_KEYWORDS
    )

    # Gabungkan kata gagal sebelumnya dengan kata yang masih kurang
    # dict.fromkeys menjaga urutan dan menghapus duplikat
    kata_perlu_scrape   = list(dict.fromkeys(failed_kws + kata_kurang))
    ada_belum_terpenuhi = bool(kata_perlu_scrape)

    # Tampilkan status data saat ini
    print("\n📁 Status Data:")
    if not df_lama.empty:
        print(f"   • Data tersimpan     : {len(df_lama)} baris")
        print(f"   • Target per kata    : minimal {TARGET_PER_KATA} data")
        print(f"   • Target terpenuhi   : {len(kata_terpenuhi)} dari {len(SEED_KEYWORDS)} kata")
        print(f"   • Belum terpenuhi    : {len(kata_perlu_scrape)} kata")
        if kata_perlu_scrape:
            rincian = [
                f"'{k}' ({counts_lama.get(k, 0)}/{TARGET_PER_KATA})"
                for k in kata_perlu_scrape
            ]
            print(f"   • Rincian            : {', '.join(rincian)}")
    else:
        print(f"   • Belum ada data tersimpan.")
        print(f"   • Target: {TARGET_PER_KATA} data per kata ({len(SEED_KEYWORDS)} kata).")

    # Tampilkan menu pilihan
    print("\nPilihan:")
    print("  [1] Jalankan Scraping Seed Keywords (Playwright/X)")
    if ada_belum_terpenuhi:
        print(
            f"  [2] 🔁 Scrape HANYA kata yang BELUM capai {TARGET_PER_KATA} data "
            f"({len(kata_perlu_scrape)} kata)"
        )
    print("  [3] ✍️  Input kata kerja manual")

    pilihan = input("\nMasukkan pilihan (1/2/3) [Default: 1]: ").strip()

    # Tentukan kata mana yang akan di-scrape
    target_keywords = SEED_KEYWORDS
    custom_since = SINCE_DATE

    if pilihan == "2" and ada_belum_terpenuhi:
        # Hanya scrape kata yang belum memenuhi target
        target_keywords = kata_perlu_scrape

    elif pilihan == "3":
        # Input manual kata kerja dari pengguna
        manual = input(f"Masukkan kata kerja (pisahkan koma) [Default: {', '.join(SEED_KEYWORDS)}]: ").strip()
        if manual:
            target_keywords = [k.strip() for k in manual.split(",") if k.strip()]

        input_since = input(f"Masukkan tanggal awal SINCE_DATE (YYYY-MM-DD, kosongkan jika tanpa filter) [Default: {SINCE_DATE or 'None'}]: ").strip()
        if input_since.lower() in ["none", "kosong", "tidak"]:
            custom_since = None
        elif input_since:
            custom_since = input_since

    elif pilihan in ["", "1"]:
        # Default: scrape semua, tapi tawarkan opsi hanya yang kurang
        if not df_lama.empty and ada_belum_terpenuhi:
            opsi = input(
                f"Lanjutkan hanya kata yang kurang "
                f"({len(kata_perlu_scrape)} kata)? [Y/n]: "
            ).strip().lower()
            if opsi in ["", "y", "yes"]:
                target_keywords = kata_perlu_scrape

        tanya_since = input(f"Ubah tanggal awal SINCE_DATE? (tekan ENTER untuk tetap '{SINCE_DATE}', ketik tanggal 'YYYY-MM-DD', atau 'none'): ").strip()
        if tanya_since.lower() == "none":
            custom_since = None
        elif tanya_since:
            custom_since = tanya_since

    log.info(f"Mulai scraping untuk {len(target_keywords)} kata: {target_keywords} | SINCE_DATE: {custom_since}")

    # Jalankan scraping
    df_baru = scrape_x_playwright(keywords=target_keywords, since_date=custom_since)

    # Tangani kondisi tidak ada data sama sekali
    if df_baru.empty and df_lama.empty:
        print("❌ Tidak ada data yang berhasil dikumpulkan.")
        return

    # Gabungkan dan simpan hasil
    simpan_hasil_gabungan(df_baru=df_baru, df_lama=df_lama)
    print("\n✅ Selesai!")


# ══════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()