from datetime import datetime
from src.container import db

class Dokumen(db.Model):
    __tablename__ = "dokumen"
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(255), nullable=False)
    penulis = db.Column(db.String(255), nullable=True)
    isi = db.Column(db.LongText, nullable=False)
    dibuat_pada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "judul": self.judul,
            "penulis": self.penulis,
            "dibuat_pada": self.dibuat_pada.isoformat(),
        }