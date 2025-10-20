import gradio as gr
import os
import re
import io
import fitz  # PyMuPDF
import docx
from PIL import Image
import pytesseract
import difflib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ========== KONFIGURASI DASAR ==========
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

users = {"60200121055": "12345"}  # Contoh data login


# ========== PEMBACAAN DOKUMEN ==========
def baca_pdf(path):
    teks = ""
    try:
        doc = fitz.open(path)
        for page in doc:
            page_text = page.get_text("text")
            if not page_text.strip():
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(img)
            teks += page_text + " "
        doc.close()
    except Exception as e:
        print("Error baca PDF:", e)
    return teks


def baca_docx(path):
    try:
        doc = docx.Document(path)
        return " ".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print("Error baca DOCX:", e)
        return ""


def baca_dokumen(path):
    if path.endswith(".pdf"):
        return baca_pdf(path)
    elif path.endswith(".docx"):
        return baca_docx(path)
    return ""


def bersihkan_teks(teks):
    teks = teks.lower()
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)
    return teks.strip()


# ========== SIMILARITY ==========
def levenshtein_similarity(teks1, teks2):
    seq = difflib.SequenceMatcher(None, teks1, teks2)
    return seq.ratio() * 100


def cbf_similarity(teks1, teks2):
    vectorizer = TfidfVectorizer()
    try:
        vectors = vectorizer.fit_transform([teks1, teks2])
        cosine_sim = cosine_similarity(vectors[0], vectors[1])[0][0]
        return cosine_sim * 100
    except ValueError:
        return 0.0


# ========== BUAT PDF HASIL ==========
def buat_pdf_hasil(teks_asli, teks_uji, hasil_data, filename="hasil_plagiarisme.pdf"):
    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    merah = ParagraphStyle("merah", parent=styles["Normal"], textColor=colors.red)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    story = []

    story.append(Paragraph("Hasil Deteksi Plagiarisme", styles["Heading1"]))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"Skor Final: {hasil_data['final']}%", styles["Heading2"]))
    story.append(Paragraph(f"Levenshtein: {hasil_data['levenshtein']}%", normal))
    story.append(Paragraph(f"CBF: {hasil_data['cbf']}%", normal))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Kalimat yang mirip ditandai warna merah:", styles["Heading2"]))
    story.append(Spacer(1, 10))

    kalimat_asli = teks_asli.split(".")
    kalimat_uji = teks_uji.split(".")

    for kalimat in kalimat_uji:
        if any(difflib.SequenceMatcher(None, kalimat, ref).ratio() >= 0.9 for ref in kalimat_asli):
            story.append(Paragraph(kalimat.strip(), merah))
        else:
            story.append(Paragraph(kalimat.strip(), normal))
        story.append(Spacer(1, 6))

    doc.build(story)
    return pdf_path


# ========== FUNGSI DETEKSI ==========
def deteksi_plagiarisme(file1, file2):
    if not file1 or not file2:
        return "❗ Harap unggah dua dokumen.", None, None, None

    # Simpan file ke folder uploads
    path1 = os.path.join(UPLOAD_FOLDER, file1.name)
    path2 = os.path.join(UPLOAD_FOLDER, file2.name)
    file1.save(path1)
    file2.save(path2)

    teks1 = baca_dokumen(path1)
    teks2 = baca_dokumen(path2)

    if not teks1 or not teks2:
        return "❗ Gagal membaca isi dokumen.", None, None, None

    teks1_b = bersihkan_teks(teks1)
    teks2_b = bersihkan_teks(teks2)

    skor_lev = levenshtein_similarity(teks1_b, teks2_b)
    skor_cbf = cbf_similarity(teks1_b, teks2_b)
    skor_final = (skor_lev + skor_cbf) / 2

    hasil = {
        "levenshtein": round(skor_lev, 2),
        "cbf": round(skor_cbf, 2),
        "final": round(skor_final, 2),
    }

    pdf_path = buat_pdf_hasil(teks1, teks2, hasil)
    return f"✅ Analisis selesai! Skor Kemiripan: {hasil['final']}%", hasil["levenshtein"], hasil["cbf"], pdf_path


# ========== SISTEM LOGIN ==========
def do_login(nim, password):
    if not nim or not password:
        return (
            "❗ Harap isi NIM dan password.",
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    if nim in users and users[nim] == password:
        return (
            f"✅ Login berhasil. Selamat datang, {nim}!",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        )
    else:
        return (
            "❌ NIM atau password salah.",
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )


def do_logout():
    return (
        "🔒 Anda telah logout.",
        gr.update(visible=True),
        gr.update(value=""),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def forgot_password(nim):
    if not nim:
        return "❗ Masukkan NIM untuk mendapatkan password."
    if nim in users:
        return f"🔑 Password untuk NIM {nim} adalah: **{users[nim]}**"
    else:
        return "❌ NIM tidak ditemukan."


# ========== ANTARMUKA GRADIO ==========
with gr.Blocks(title="Sistem Deteksi Plagiarisme") as demo:
    gr.Markdown("## 🔒 Login - Sistem Deteksi Plagiarisme")

    nim_input = gr.Textbox(label="NIM")
    pass_input = gr.Textbox(label="Password", type="password")
    login_btn = gr.Button("Login")
    forgot_btn = gr.Button("Lupa Password?")
    login_status = gr.Markdown("")

    main_panel = gr.Column(visible=False)
    logout_btn = gr.Button("Logout", visible=False)

    with main_panel:
        gr.Markdown("## 📘 Upload Dua Dokumen untuk Analisis")
        file1 = gr.File(label="Upload Skripsi Asli (PDF/DOCX)")
        file2 = gr.File(label="Upload Skripsi Uji (PDF/DOCX)")
        hasil_btn = gr.Button("🔍 Deteksi Plagiarisme")
        output_text = gr.Textbox(label="Status")
        lev_score = gr.Number(label="Levenshtein (%)")
        cbf_score = gr.Number(label="CBF (%)")
        pdf_out = gr.File(label="📄 Download Hasil PDF")

        hasil_btn.click(
            fn=deteksi_plagiarisme,
            inputs=[file1, file2],
            outputs=[output_text, lev_score, cbf_score, pdf_out],
        )

    login_btn.click(
        fn=do_login,
        inputs=[nim_input, pass_input],
        outputs=[login_status, nim_input, pass_input, login_btn, main_panel, logout_btn],
    )

    logout_btn.click(
        fn=do_logout,
        inputs=None,
        outputs=[login_status, nim_input, pass_input, login_btn, main_panel, logout_btn],
    )

    forgot_btn.click(fn=forgot_password, inputs=[nim_input], outputs=[login_status])

demo.launch()
