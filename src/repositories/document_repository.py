from typing import Iterable, Optional
from src.container import db
from src.models import Dokumen

class RepositoriDokumen:
    """Repository Dokumen (SQLAlchemy)."""

    def tambah(self, judul: str, penulis: str | None, isi: str) -> Dokumen:
        d = Dokumen(judul=judul, penulis=penulis, isi=isi)
        db.session.add(d)
        db.session.commit()
        return d

    def ambil(self, doc_id: int) -> Optional[Dokumen]:
        return db.session.get(Dokumen, doc_id)

    def semua(self) -> Iterable[Dokumen]:
        return Dokumen.query.order_by(Dokumen.dibuat_pada.desc()).all()

    def daftar_isi(self) -> list[str]:
        return [d.isi for d in Dokumen.query.all()]
