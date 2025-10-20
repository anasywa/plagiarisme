import re
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def levenshtein_distance(str1, str2):
    len1, len2 = len(str1), len(str2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[len1][len2]

def similarity_score(str1, str2):
    distance = levenshtein_distance(str1, str2)
    max_len = max(len(str1), len(str2))
    return 1 - (distance / max_len) if max_len != 0 else 1.0

def split_sentences(teks):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', teks) if s.strip()]

def generate_pdf_hasil(teks_asli, teks_uji, output_path="hasil_plagiarisme.pdf"):
    asli_sentences = split_sentences(teks_asli)
    uji_sentences = split_sentences(teks_uji)

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    highlight_style = ParagraphStyle(
        "highlight",
        parent=styles["Normal"],
        textColor=colors.red,
        backColor=colors.yellow
    )

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    for kalimat in uji_sentences:
        is_plagiat = any(similarity_score(kalimat, ref) >= 0.7 for ref in asli_sentences)
        style = highlight_style if is_plagiat else normal_style
        story.append(Paragraph(kalimat, style))
        story.append(Spacer(1, 10))

    doc.build(story)
    return output_path
