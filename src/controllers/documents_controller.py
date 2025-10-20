from flask import Blueprint, jsonify, request, render_template, current_app
from src.file_fetcher import ambil_daftar_skripsi, unduh_skripsi_dan_simpan

# ... (variabel _repo, _layanan sudah ada di file controller)

@dokumen_bp.get("/api/daftar_skripsi")
def api_daftar_skripsi():
    base = request.args.get("base_url", "https://repositori.uin-alauddin.ac.id/")
    try:
        daftar = ambil_daftar_skripsi(base_url=base, limit=500)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"data": daftar})

@dokumen_bp.post("/api/import_skripsi")
def api_import_skripsi():
    data = request.get_json(force=True)
    url = data.get("url")
    judul = data.get("judul")
    penulis = data.get("penulis")
    if not url:
        return jsonify({"error": "URL wajib diisi"}), 400
    try:
        d = unduh_skripsi_dan_simpan(url, judul=judul, penulis=penulis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"data": d.to_dict()}), 201
