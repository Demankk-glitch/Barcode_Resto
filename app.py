import os
import re
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, Response
)
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Muat variabel lingkungan dari file .env (jika tersedia)
load_dotenv()

app = Flask(__name__)

# Konfigurasi Secret Key untuk keamanan sesi
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-streetwear-indie-bistro-2026-secure"
)

# Konfigurasi Database Relasional (SQLite / PostgreSQL cloud-ready)
raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///restoran.db")
# Penyesuaian skema legacy postgres:// menjadi postgresql:// untuk SQLAlchemy 2.x
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Kredensial HTTP Basic Authentication untuk Kontrol Akses Rute /dapur
DAPUR_USERNAME = os.environ.get("DAPUR_USERNAME", "admin")
DAPUR_PASSWORD = os.environ.get("DAPUR_PASSWORD", "dapur123")


# ==============================================================================
# 3 MODEL DATABASE RELASIONAL (FLASK-SQLALCHEMY)
# ==============================================================================

class Menu(db.Model):
    """
    Model 1: Menu hidangan makanan & minuman.
    """
    __tablename__ = "menu"

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(120), nullable=False)
    kategori = db.Column(db.String(50), nullable=False, default="Makanan")
    track_code = db.Column(db.String(20), nullable=False, default="TRACK // 01")
    harga = db.Column(db.Integer, nullable=False)
    deskripsi = db.Column(db.Text, nullable=True)
    gambar_url = db.Column(db.String(300), nullable=True)
    is_tersedia = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nama": self.nama,
            "kategori": self.kategori,
            "track_code": self.track_code,
            "harga": self.harga,
            "deskripsi": self.deskripsi,
            "gambar_url": self.gambar_url,
            "is_tersedia": self.is_tersedia,
        }


class Pesanan(db.Model):
    """
    Model 2: Pesanan pelanggan (nomor meja, total harga, status 'Menunggu'/'Selesai').
    """
    __tablename__ = "pesanan"

    id = db.Column(db.Integer, primary_key=True)
    nomor_meja = db.Column(db.String(20), nullable=False)
    total_harga = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="Menunggu")  # 'Menunggu' | 'Selesai'
    catatan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relasi one-to-many ke ItemPesanan
    items = db.relationship(
        "ItemPesanan",
        backref="pesanan",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nomor_meja": self.nomor_meja,
            "status": self.status,
            "total_harga": self.total_harga,
            "catatan": self.catatan or "",
            "created_at": self.created_at.strftime("%H:%M:%S"),
            "items": [item.to_dict() for item in self.items],
        }


class ItemPesanan(db.Model):
    """
    Model 3: Rincian item pesanan (relasi one-to-many dari Pesanan).
    """
    __tablename__ = "item_pesanan"

    id = db.Column(db.Integer, primary_key=True)
    pesanan_id = db.Column(db.Integer, db.ForeignKey("pesanan.id"), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey("menu.id"), nullable=False)
    nama_menu = db.Column(db.String(120), nullable=False)  # Snapshot nama
    harga_satuan = db.Column(db.Integer, nullable=False)   # Snapshot harga
    kuantitas = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "menu_id": self.menu_id,
            "nama_menu": self.nama_menu,
            "harga_satuan": self.harga_satuan,
            "kuantitas": self.kuantitas,
            "subtotal": self.subtotal,
        }

# Alias backwards compatibility
PesananItem = ItemPesanan


# ==============================================================================
# SEEDING DATA AWAL (Katalog Menu Bergaya Indie Album Streetwear)
# ==============================================================================
def seed_initial_data():
    """Mengisi katalog menu awal jika database masih kosong."""
    if Menu.query.first() is None:
        initial_menus = [
            Menu(
                nama="WAGYU SMOKED BRISKET RICE",
                kategori="Makanan",
                track_code="TRACK // 01",
                harga=68000,
                deskripsi="Daging brisket asap 12 jam dengan sambal matah bakar, telur mata sapi renyah, dan nasi aromatik.",
                gambar_url="https://images.unsplash.com/photo-1544025162-d76694265947?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
            Menu(
                nama="ACID NASI GORENG RAWON",
                kategori="Makanan",
                track_code="TRACK // 02",
                harga=52000,
                deskripsi="Nasi goreng bumbu kluwek hitam legam, empal suwir gurih, tauge pendek, dan kerupuk udang renyah.",
                gambar_url="https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
            Menu(
                nama="TRUFFLE BUTTER CHICKEN KATSU",
                kategori="Makanan",
                track_code="TRACK // 03",
                harga=58000,
                deskripsi="Fillet ayam katsu ultra renyah, lumuran saus kari jepang wangi minyak truffle putih dan salad kubis.",
                gambar_url="https://images.unsplash.com/photo-1562967914-608f82629710?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
            Menu(
                nama="CARBON MATCHA ESPRESSO FUSION",
                kategori="Minuman",
                track_code="TRACK // 04",
                harga=38000,
                deskripsi="Gradasi estetik arang aktif (charcoal), matcha murni Uji, susu oat creamy, dan dobel shot espresso.",
                gambar_url="https://images.unsplash.com/photo-1536256263959-770b48d82b0a?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
            Menu(
                nama="NEON ACID CITRUS COLD BREW",
                kategori="Minuman",
                track_code="TRACK // 05",
                harga=35000,
                deskripsi="Cold brew arabika 18 jam dengan perasan jeruk yuzu jepang, sirup mint kaktus, dan sparkling soda.",
                gambar_url="https://images.unsplash.com/photo-1517256064527-09c73fc73e38?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
            Menu(
                nama="DARK CHOCOLATE LAVA TOAST",
                kategori="Penutup",
                track_code="TRACK // 06",
                harga=42000,
                deskripsi="Roti brioche bakar arang isi lelehan cokelat Belgia 70%, ditaburi sea salt flakes dan es krim vanila.",
                gambar_url="https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop&q=80",
                is_tersedia=True,
            ),
        ]
        db.session.add_all(initial_menus)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_initial_data()


# ==============================================================================
# HELPER KEAMANAN & ACCESS CONTROL (BASIC AUTHENTICATION)
# ==============================================================================
def sanitize_table_number(table_raw):
    """
    Sanitasi ketat nomor meja: hanya mengizinkan alfanumerik, strip, dan garis bawah.
    Mencegah injeksi karakter berbahaya / XSS / SQLi.
    """
    if not table_raw:
        return None
    cleaned = re.sub(r"[^a-zA-Z0-9\-_]", "", str(table_raw).strip())
    return cleaned[:10] if cleaned else None


def basic_auth_required(f):
    """
    Decorator Kontrol Akses Keamanan dengan HTTP Basic Authentication.
    Melindungi rute /dapur dan API dapur agar tidak dapat diakses oleh pelanggan.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == DAPUR_USERNAME and auth.password == DAPUR_PASSWORD):
            return Response(
                "Akses Ditolak: Kredensial Staf Dapur (Basic Authentication) diperlukan.",
                401,
                {"WWW-Authenticate": 'Basic realm="Area Operasional Dapur Restoran"'}
            )
        return f(*args, **kwargs)
    return decorated


# ==============================================================================
# ROUTE PELANGGAN & E-MENU
# ==============================================================================
@app.route("/")
@app.route("/menu")
def index():
    """
    Halaman e-menu pelanggan (index.html).
    Mengekstrak query parameter ?meja= dari URL (hasil scan QR code)
    dan mengoper nomor meja yang tersanitasi ke template.
    """
    raw_meja = request.args.get("meja", default=None)
    meja = sanitize_table_number(raw_meja)

    # Ambil daftar menu aktif dari database relasional
    menu_items = Menu.query.filter_by(is_tersedia=True).order_by(Menu.id.asc()).all()

    return render_template("index.html", meja=meja, menu_items=menu_items)


# ==============================================================================
# ROUTE API POST /checkout (DATA KERANJANG JSON DENGAN PERLINDUNGAN SQL INJECTION)
# ==============================================================================
@app.route("/checkout", methods=["POST"])
@app.route("/pesan", methods=["POST"])
def checkout():
    """
    Endpoint API untuk menerima data keranjang belanja berformat JSON dari frontend.
    
    Keamanan Database (Anti SQL-Injection):
    1. Menggunakan ORM SQLAlchemy murni (parameterized queries).
    2. Input nomor meja disanitasi secara eksplisit.
    3. Input menu_id dan kuantitas divalidasi ketat (tipe integer).
    4. Integritas Finansial: Harga diambil langsung dari database Menu,
       bukan mempercayai kalkulasi sisi klien (Anti Price-Tampering).
    5. Transaksi atomik: commit hanya jika semua item valid, rollback otomatis jika error.
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        # Dukungan pengiriman formulir HTML biasa
        data = request.form

    # Ekstraksi dan sanitasi nomor meja
    raw_meja = data.get("nomor_meja") or data.get("meja") or request.args.get("meja")
    meja = sanitize_table_number(raw_meja)

    if not meja:
        if request.is_json:
            return jsonify({
                "success": False,
                "error": "Nomor meja tidak valid atau belum ditentukan."
            }), 400
        flash("Nomor meja wajib ditentukan sebelum memesan! Pastikan scan QR meja Anda.", "error")
        return redirect(url_for("index"))

    catatan = str(data.get("catatan", "")).strip()[:250]

    # Parsing item keranjang dari data JSON atau Form
    # Item diproses sebagai daftar tuple: (menu_model, kuantitas)
    items_to_order = []

    if request.is_json:
        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            return jsonify({
                "success": False,
                "error": "Format data items harus berupa array JSON."
            }), 400

        for item in raw_items:
            try:
                m_id = int(item.get("menu_id"))
                qty = int(item.get("kuantitas") if "kuantitas" in item else item.get("qty", 0))
                if 1 <= qty <= 50:
                    # Query ORM SQLAlchemy aman dari SQL Injection
                    menu = db.session.get(Menu, m_id)
                    if menu and menu.is_tersedia:
                        items_to_order.append((menu, qty))
            except (ValueError, TypeError):
                continue
    else:
        for key, value in data.items():
            if key.startswith("qty_"):
                try:
                    m_id = int(key.replace("qty_", ""))
                    qty = int(value)
                    if 1 <= qty <= 50:
                        menu = db.session.get(Menu, m_id)
                        if menu and menu.is_tersedia:
                            items_to_order.append((menu, qty))
                except (ValueError, TypeError):
                    continue

    if not items_to_order:
        if request.is_json:
            return jsonify({
                "success": False,
                "error": "Keranjang belanja kosong atau item tidak valid. Minimal pesan 1 hidangan."
            }), 400
        flash("Keranjang belanja Anda masih kosong! Pilih minimal 1 menu.", "warning")
        return redirect(url_for("index", meja=meja))

    # Transaksi Database Atomik menggunakan SQLAlchemy ORM
    try:
        total_harga = 0
        pesanan_baru = Pesanan(
            nomor_meja=meja,
            status="Menunggu",  # Status default sesuai spesifikasi: 'Menunggu'
            total_harga=0,
            catatan=catatan
        )
        db.session.add(pesanan_baru)
        db.session.flush()  # Ambil ID yang dihasilkan otomatis

        for menu, qty in items_to_order:
            subtotal = menu.harga * qty
            total_harga += subtotal

            item_pesanan = ItemPesanan(
                pesanan_id=pesanan_baru.id,
                menu_id=menu.id,
                nama_menu=menu.nama,
                harga_satuan=menu.harga,
                kuantitas=qty,
                subtotal=subtotal
            )
            db.session.add(item_pesanan)

        pesanan_baru.total_harga = total_harga
        db.session.commit()

        if request.is_json:
            return jsonify({
                "success": True,
                "order_id": pesanan_baru.id,
                "nomor_meja": meja,
                "total_harga": total_harga,
                "status": pesanan_baru.status,
                "message": "Pesanan berhasil disimpan ke database!"
            }), 201

        flash(f"Pesanan berhasil dikirim ke dapur! [No Order #{pesanan_baru.id}]", "success")
        return redirect(url_for("index", meja=meja, order_success=pesanan_baru.id))

    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({
                "success": False,
                "error": "Terjadi kesalahan internal saat menyimpan pesanan ke database."
            }), 500
        flash("Gagal memproses pesanan Anda. Silakan coba kembali.", "error")
        return redirect(url_for("index", meja=meja))


# ==============================================================================
# ROUTE /dapur (ACCESS CONTROL DENGAN BASIC AUTHENTICATION)
# ==============================================================================
@app.route("/dapur")
@basic_auth_required
def dashboard_dapur():
    """
    Dashboard dapur untuk melihat pesanan masuk.
    Dilindungi oleh HTTP Basic Authentication agar tidak bisa diakses oleh pelanggan.
    """
    pesanan_masuk = Pesanan.query.filter_by(status="Menunggu").order_by(Pesanan.created_at.asc()).all()
    pesanan_selesai = Pesanan.query.filter_by(status="Selesai").order_by(Pesanan.created_at.desc()).limit(15).all()

    return render_template(
        "dapur.html",
        pesanan_masuk=pesanan_masuk,
        pesanan_selesai=pesanan_selesai
    )


@app.route("/dapur/logout")
def logout_dapur():
    """Mengakhiri otentikasi staf dapur dengan mengirim response 401."""
    return Response(
        "Anda telah keluar dari Kitchen Display System.",
        401,
        {"WWW-Authenticate": 'Basic realm="Area Operasional Dapur Restoran"'}
    )


# ==============================================================================
# API REAL-TIME POLLING & STATUS UPDATE UNTUK LAYAR DAPUR
# ==============================================================================
@app.route("/api/pesanan", methods=["GET"])
@app.route("/api/dapur/pesanan", methods=["GET"])
def api_get_pesanan():
    """
    Rute GET /api/pesanan:
    Mengembalikan data pesanan berstatus 'Menunggu' dalam format JSON.
    """
    pesanan_list = Pesanan.query.filter_by(status="Menunggu").order_by(Pesanan.created_at.asc()).all()
    return jsonify({
        "status": "success",
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "total_antrean": len(pesanan_list),
        "pesanan": [p.to_dict() for p in pesanan_list]
    })


@app.route("/selesaikan/<int:id>", methods=["POST"])
@app.route("/api/dapur/pesanan/<int:id>/status", methods=["POST"])
def selesaikan_pesanan(id):
    """
    Rute POST /selesaikan/<id>:
    Mengubah status pesanan di database menjadi 'Selesai'.
    """
    pesanan = db.session.get(Pesanan, id)
    if not pesanan:
        return jsonify({"success": False, "error": f"Pesanan #{id} tidak ditemukan."}), 404

    try:
        pesanan.status = "Selesai"
        db.session.commit()
        return jsonify({
            "success": True,
            "order_id": pesanan.id,
            "status": pesanan.status,
            "status_baru": pesanan.status,
            "message": f"Status pesanan #{pesanan.id} berhasil diubah menjadi '{pesanan.status}'."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": "Gagal memperbarui status di database."}), 500


# ==============================================================================
# MAIN ENTRYPOINT (PENGEMBANGAN LOKAL)
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"\n[SERVER] Restoran Web Server berjalan di: http://127.0.0.1:{port}")
    print(f"[MENU]   Halaman Pelanggan (QR Meja 07): http://127.0.0.1:{port}/?meja=07")
    print(f"[DAPUR]  Dashboard Dapur (Basic Auth): http://127.0.0.1:{port}/dapur")
    print(f"[AUTH]   Username: {DAPUR_USERNAME} | Password: {DAPUR_PASSWORD}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
