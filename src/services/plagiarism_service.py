def cek(self, isi: str, jumlah_teratas: int = 5) -> List[HasilCocok]:
    self.pastikan_indeks()
    if not self.siap():
        return []

    q_norm = normalisasi(isi)
    q_vec = self._vectorizer.transform([q_norm])
    cos = cosine_similarity(q_vec, self._tfidf)[0]

    hasil: list[HasilCocok] = []
    for i, doc_id in enumerate(self._ids):
        judul, penulis = self._meta[doc_id]

        # Gunakan teks yang sudah dinormalisasi
        lev = Levenshtein.normalized_similarity(isi, self._teks_asli[doc_id])

        # Pastikan bobot tetap 1.0
        total_bobot = self.bobot_cosine + self.bobot_lev
        cosine_part = (self.bobot_cosine / total_bobot) * cos[i]
        lev_part = (self.bobot_lev / total_bobot) * lev

        # Gabungkan skor (0–1) lalu ubah ke 0–100
        skor = max(0.0, min(1.0, cosine_part + lev_part)) * 100

        hasil.append(HasilCocok(doc_id, judul, penulis, float(cos[i]), float(lev), skor))

    hasil.sort(key=lambda h: h.skor, reverse=True)
    return hasil[:jumlah_teratas]


def bandingkan(self, doc_id: int, isi: str) -> HasilCocok | None:
    d = self.repo.ambil(doc_id)
    if not d:
        return None

    q_norm = normalisasi(isi)
    self.pastikan_indeks()

    if self.siap():
        q_vec = self._vectorizer.transform([q_norm])
        try:
            idx = self._ids.index(doc_id)
            cos = cosine_similarity(q_vec, self._tfidf[idx])
            cosine_val = float(cos[0][0]) if cos.size else 0.0
        except ValueError:
            cosine_val = 0.0
    else:
        cosine_val = 0.0

    lev = Levenshtein.normalized_similarity(q_norm[:6000], normalisasi(d.isi)[:6000])

    total_bobot = self.bobot_cosine + self.bobot_lev
    skor = max(0.0, min(1.0,
        (self.bobot_cosine / total_bobot) * cosine_val +
        (self.bobot_lev / total_bobot) * lev
    )) * 100

    return HasilCocok(d.id, d.judul, d.penulis, cosine_val, float(lev), skor)
