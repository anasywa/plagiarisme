import os
import io
import re
import docx
import difflib
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from PyPDF2 import PdfReader
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session, send_from_directory, jsonify
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import A4

# Catatan: Saya HAPUS import 'src.services.pdf_generator' dan 'Levenshtein' 
# karena fungsi tersebut tidak disertakan atau sudah diganti dengan implementasi Anda sendiri.

app = Flask(__name__)
app.secret_key = "skripsi_plagiarisme_2025"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================================
# FUNGSI UTILITY (PEMBACAAN & PEMBERSIHAN)
# =====================================
def baca_pdf(path):
    teks = ""
    try:
        # Menggunakan PyMuPDF (fitz) karena sudah ada dan mendukung OCR
        doc = fitz.open(path)
        for page in doc:
            page_text = page.get_text("text")
            if not page_text.strip():
                # Jika teks kosong, coba OCR (pastikan pytesseract terinstal dan Tesseract di path)
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                page_text = pytesseract.image_to_string(img)
            teks += page_text + " "
        doc.close()
    except Exception as e:
        print("Error baca PDF:", e)
        teks = ""
    return teks

def baca_docx(path):
    try:
        doc = docx.Document(path)
        return " ".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print("Error baca DOCX:", e)
        return ""

def baca_dokumen(path):
    if path and path.endswith(".pdf"):
        return baca_pdf(path)
    elif path and path.endswith(".docx"):
        return baca_docx(path)
    return ""

def bersihkan_teks(teks):
    teks = teks.lower()
    # Hapus selain huruf, angka, dan spasi
    teks = re.sub(r'[^a-z0-9\s]', '', teks) 
    return teks.strip()

def split_sentences(teks):
    # Memisahkan teks menjadi kalimat-kalimat berdasarkan tanda baca (.!?)
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', teks) if s.strip()]

# =====================================
# FUNGSI ANALISIS PLAGIARISME
# =====================================
def levenshtein_distance(str1, str2):
    len1, len2 = len(str1), len(str2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1): dp[i][0] = i
    for j in range(len2 + 1): dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[len1][len2]

def similarity_score(str1, str2):
    distance = levenshtein_distance(str1, str2)
    max_len = max(len(str1), len(str2))
    if max_len == 0:
        return 1.0
    return 1 - (distance / max_len)

def levenshtein_similarity(teks1, teks2):
    # Menggunakan SequenceMatcher untuk perbandingan tingkat dokumen (berdasarkan karakter/kata)
    seq = difflib.SequenceMatcher(None, teks1, teks2)
    return seq.ratio() * 100 

def cbf_similarity(teks1, teks2):
    # Menggunakan TF-IDF dan Cosine Similarity (CBF)
    vectorizer = TfidfVectorizer()
    try:
        vectors = vectorizer.fit_transform([teks1, teks2])
        cosine_sim = cosine_similarity(vectors[0], vectors[1])[0][0]
        return cosine_sim * 100
    except ValueError:
        return 0.0

# =====================================
# DATA LOGIN
# =====================================
users = {
    "60200121055": "12345"
}

# =====================================
# ROUTE LOGIN / LOGOUT
# =====================================
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:
            session["user"] = username
            flash("Login berhasil!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Username atau password salah!", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Anda sudah logout!", "info")
    return redirect(url_for("login"))

# =====================================
# DASHBOARD
# =====================================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Silakan login dulu!", "warning")
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

# =====================================
# UPLOAD 2 FILE
# =====================================
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user" not in session:
        flash("Silakan login dulu!", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        file1 = request.files.get("skripsi1")
        file2 = request.files.get("skripsi2")
        
        if not file1 or not file2:
            flash("Harap upload kedua file skripsi!", "danger")
            return redirect(request.url)

        if not (file1.filename.endswith((".pdf", ".docx")) and file2.filename.endswith((".pdf", ".docx"))):
            flash("Format file harus PDF atau DOCX!", "danger")
            return redirect(request.url)

        # Hapus file lama di session
        session.pop("file1", None)
        session.pop("file2", None)

        # Simpan file
        filepath1 = os.path.join(app.config["UPLOAD_FOLDER"], file1.filename)
        filepath2 = os.path.join(app.config["UPLOAD_FOLDER"], file2.filename)
        
        # Pastikan nama file unik jika perlu, atau timpa file lama.
        file1.save(filepath1)
        file2.save(filepath2)

        session["file1"] = filepath1
        session["file2"] = filepath2
        
        # Clear any previous analysis results
        session.pop("analysis_results", None)
        session.pop("score", None)
        session.pop("hasil", None)
        
        flash("File berhasil diunggah, proses deteksi dimulai!", "success")
        return redirect(url_for("hasil"))

    return render_template("upload.html")

# =====================================
# HASIL ANALISIS & GENERATE PDF
# =====================================
@app.route("/hasil", methods=["GET", "POST"])
def hasil():
    if "user" not in session:
        flash("Silakan login dulu!", "warning")
        return redirect(url_for("login"))
    
    # GET request - Show page with loading state or existing results
    if request.method == "GET":
        # Check if we already have results in session
        existing_results = session.get("analysis_results")
        if existing_results:
            return render_template("hasil.html", hasil=existing_results)
        else:
            # Check if files are uploaded
            file1_path = session.get("file1")
            file2_path = session.get("file2")
            
            if not file1_path or not file2_path:
                flash("Harap upload file terlebih dahulu!", "warning")
                return redirect(url_for("upload"))
            
            # Show page with loading state (no results yet)
            return render_template("hasil.html", hasil=None)
    
    # POST request - Process the analysis
    elif request.method == "POST":
        file1_path = session.get("file1")
        file2_path = session.get("file2")
        
        if not file1_path or not file2_path:
            return jsonify({"error": "Files not found in session"}), 400
            
        try:
            # --- 1. Ambil Teks dari Dokumen ---
            teks_asli = baca_dokumen(file1_path)
            teks_uji = baca_dokumen(file2_path)
            
            if not teks_asli or not teks_uji:
                return jsonify({"error": "Failed to read document content"}), 400

            # 2. Pengecekan Teks (PENTING)
            if len(teks_asli) < 10 or len(teks_uji) < 10:
                print(f"DEBUG: Gagal membaca file. Path 1: {file1_path}, Teks 1: {len(teks_asli)} karakter.")
                print(f"DEBUG: Gagal membaca file. Path 2: {file2_path}, Teks 2: {len(teks_uji)} karakter.")
                return jsonify({"error": "Document content too short or empty"}), 400

            teks_bersih_asli = bersihkan_teks(teks_asli)
            teks_bersih_uji = bersihkan_teks(teks_uji)

            # --- 3. Hitung Skor ---
            skor_levenshtein = levenshtein_similarity(teks_bersih_asli, teks_bersih_uji)
            skor_cbf = cbf_similarity(teks_bersih_asli, teks_bersih_uji)
            
            skor_final = (skor_levenshtein + skor_cbf) / 2
            
            hasil_data = {
                "levenshtein": round(skor_levenshtein, 2),
                "cbf": round(skor_cbf, 2),
                "final": round(skor_final, 2),
            }
            
            # --- 4. Generate PDF ---
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], "hasil_plagiarisme.pdf")
            
            styles = getSampleStyleSheet()
            normal_style = styles["Normal"]
            highlight_style = ParagraphStyle(
                "highlight",
                parent=styles["Normal"],
                textColor=colors.red,
                backColor=colors.yellow
            )
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            story = []

            # Pisahkan kalimat untuk perbandingan detail
            asli_sentences = split_sentences(teks_asli)
            uji_sentences = split_sentences(teks_uji)

            story.append(Paragraph("Hasil Deteksi Plagiarisme", styles["Heading1"]))
            story.append(Spacer(1, 15))
            story.append(Paragraph(f"Skor Final: {hasil_data['final']}%", styles["Heading2"]))
            story.append(Paragraph(f"Levenshtein Similarity: {hasil_data['levenshtein']}%", normal_style))
            story.append(Paragraph(f"CBF Similarity: {hasil_data['cbf']}%", normal_style))
            story.append(Spacer(1, 20))
            story.append(Paragraph("Deteksi Kalimat Mirip (Threshold 0.7 Levenshtein):", styles["Heading2"]))
            story.append(Spacer(1, 12))

            # Bandingkan per kalimat (Levenshtein)
            detail_hasil = []
            for kalimat in uji_sentences:
                is_plagiat = any(similarity_score(kalimat, ref) >= 0.7 for ref in asli_sentences)
                style = highlight_style if is_plagiat else normal_style
                story.append(Paragraph(kalimat, style))
                story.append(Spacer(1, 6))
                
                # Simpan detail untuk download
                if is_plagiat:
                    detail_hasil.append(kalimat)
                    
            doc.build(story)
            
            # --- 5. Simpan Data ke Session ---
            session["score"] = hasil_data["final"]
            session["hasil"] = "\n".join(detail_hasil)
            session["analysis_results"] = hasil_data  # Cache results
            
            # Return JSON response for AJAX
            return jsonify(hasil_data)
            
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


# =====================================
# DOWNLOAD PDF
# =====================================
@app.route("/download-pdf")
def download_pdf():
    if "user" not in session:
        return redirect(url_for("login"))

    # Mengambil file yang sudah digenerate di rute /hasil
    pdf_filename = "hasil_plagiarisme.pdf"
    full_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
    
    if os.path.exists(full_path):
        return send_from_directory(app.config["UPLOAD_FOLDER"], pdf_filename, as_attachment=True)
    else:
        flash("File hasil PDF tidak ditemukan. Silakan ulangi analisis.", "danger")
        return redirect(url_for("hasil"))

# =====================================
# ROUTE SERVE UPLOADS (Opsional, jika Anda ingin menampilkan PDF langsung di browser)
# =====================================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# =====================================
# EKSEKUSI APLIKASI
# =====================================
if __name__ == "__main__":
    app.run(debug=True)