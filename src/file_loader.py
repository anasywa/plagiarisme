import fitz  # PyMuPDF
import docx

def baca_pdf(path: str) -> str:
    """Ekstrak teks dari file PDF."""
    teks = []
    with fitz.open(path) as pdf:
        for halaman in pdf:
            teks.append(halaman.get_text())
    return "\n".join(teks)

def baca_docx(path: str) -> str:
    """Ekstrak teks dari file DOCX."""
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs])

def baca_file(path: str) -> str:
    """Deteksi jenis file dan kembalikan teks."""
    if path.lower().endswith(".pdf"):
        return baca_pdf(path)
    elif path.lower().endswith(".docx"):
        return baca_docx(path)
    else:
        raise ValueError("Format file tidak didukung (hanya PDF/DOCX)")
