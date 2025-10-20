import re
import os
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
from flask import current_app
from src.file_loader import baca_file  # pastikan ada seperti saran sebelumnya

# user-agent agar server tidak memblokir
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}

# cari semua link pdf/docx pada sebuah halaman (lebih spesifik daripada semua <a>)
def ambil_daftar_skripsi(base_url: str = "https://repositori.uin-alauddin.ac.id/", limit: int | None = 200):
    sess = requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    resp = sess.get(base_url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # coba cari href yang berakhiran .pdf atau .docx
    pattern = re.compile(r"\.pdf$|\.docx$", re.IGNORECASE)
    hasil = []
    for a in soup.find_all("a", href=pattern):
        href = a.get("href", "").strip()
        if not href:
            continue
        nama = a.get_text(strip=True) or os.path.basename(href)
        full = requests.compat.urljoin(base_url, href)
        hasil.append({"nama": nama, "url": full})
        if limit and len(hasil) >= limit:
            break

    # fallback: jika tidak ditemukan, periksa atribut data- atau area lain (opsional)
    return hasil

def unduh_skripsi_dan_simpan(skripsi_url: str, judul: str | None = None, penulis: str | None = None):
    sess = requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    resp = sess.get(skripsi_url, stream=True, timeout=30)
    resp.raise_for_status()

    upload_folder = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads"))
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(os.path.basename(skripsi_url.split("?")[0]) or "dokumen")
    tmp_path = os.path.join(upload_folder, filename)

    # tulis berkas secara streaming agar tidak memakan memori besar
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    # ekstrak teks (gunakan file_loader)
    teks = baca_file(tmp_path)

    # ambil instance layanan dari app config (pastikan sudah diset di app.py)
    layanan = current_app.config.get("layanan")
    if layanan is None:
        raise RuntimeError("Layanan tidak terkonfigurasi. Pastikan app.config['layanan'] di-set pada saat app dibuat.")

    # simpan dokumen ke repositori via layanan
    dok = layanan.tambah_dokumen(judul=judul or filename, penulis=penulis, isi=teks)
    return dok
