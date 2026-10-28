import unittest
import json
import base64
from app import (
    app, db, Menu, Pesanan, ItemPesanan,
    DAPUR_USERNAME, DAPUR_PASSWORD
)


class RestoranAppTestCase(unittest.TestCase):
    def setUp(self):
        # Konfigurasi mode testing & in-memory SQLite database
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test-secret-key-12345"

        self.client = app.test_client()

        # Generate Basic Auth header
        credentials = f"{DAPUR_USERNAME}:{DAPUR_PASSWORD}"
        self.basic_auth_header = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}"
        }

        with app.app_context():
            db.create_all()
            # Buat sample menu item untuk pengujian
            m1 = Menu(
                nama="TEST BRISKET RICE",
                kategori="Makanan",
                track_code="TRACK // 01",
                harga=50000,
                deskripsi="Daging asap test",
                gambar_url="https://example.com/test.jpg",
                is_tersedia=True,
            )
            m2 = Menu(
                nama="TEST COLD BREW",
                kategori="Minuman",
                track_code="TRACK // 02",
                harga=25000,
                deskripsi="Minuman test",
                gambar_url="https://example.com/test2.jpg",
                is_tersedia=True,
            )
            db.session.add_all([m1, m2])
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_01_models_structure(self):
        """Memverifikasi 3 model database: Menu, Pesanan (status 'Menunggu'/'Selesai'), ItemPesanan."""
        with app.app_context():
            p = Pesanan(nomor_meja="01", total_harga=50000, status="Menunggu")
            db.session.add(p)
            db.session.flush()

            item = ItemPesanan(
                pesanan_id=p.id,
                menu_id=1,
                nama_menu="TEST BRISKET RICE",
                harga_satuan=50000,
                kuantitas=1,
                subtotal=50000
            )
            db.session.add(item)
            db.session.commit()

            # Verifikasi relasi one-to-many
            saved_pesanan = db.session.get(Pesanan, p.id)
            self.assertEqual(saved_pesanan.status, "Menunggu")
            self.assertEqual(len(saved_pesanan.items), 1)
            self.assertIsInstance(saved_pesanan.items[0], ItemPesanan)
            self.assertEqual(saved_pesanan.items[0].nama_menu, "TEST BRISKET RICE")

    def test_02_customer_menu_with_qr_parameter(self):
        """Menguji rute pelanggan dengan query parameter ?meja=08."""
        response = self.client.get("/?meja=08")
        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        self.assertIn("TABLE // 08", content)
        self.assertIn("TEST BRISKET RICE", content)
        self.assertIn("IDR 50.000", content)

    def test_03_api_post_checkout_json_and_sql_injection_safety(self):
        """
        Menguji route API POST /checkout menerima JSON keranjang belanja dari frontend,
        menyimpan ke database relasional dengan status 'Menunggu', dan aman dari SQL Injection.
        """
        # 1. Payload JSON valid dengan upaya SQL Injection pada parameter nomor_meja
        payload = {
            "nomor_meja": "12' OR '1'='1 -- <script>",
            "catatan": "Level pedas 2",
            "items": [
                {"menu_id": 1, "kuantitas": 2},  # 2 x 50.000 = 100.000
                {"menu_id": 2, "kuantitas": 1},  # 1 x 25.000 = 25.000
            ]
        }
        response = self.client.post(
            "/checkout",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "Menunggu")
        # Total harga dihitung aman di database
        self.assertEqual(data["total_harga"], 125000)

        # Nomor meja disanitasi sehingga karakter kutip dan script terbuang
        self.assertNotIn("'", data["nomor_meja"])
        self.assertNotIn("<script>", data["nomor_meja"])

        order_id = data["order_id"]

        # 2. Verifikasi langsung ke database SQLite via SQLAlchemy ORM
        with app.app_context():
            pesanan = db.session.get(Pesanan, order_id)
            self.assertIsNotNone(pesanan)
            self.assertEqual(pesanan.status, "Menunggu")
            self.assertEqual(pesanan.total_harga, 125000)
            self.assertEqual(len(pesanan.items), 2)
            self.assertEqual(pesanan.items[0].subtotal, 100000)
            self.assertEqual(pesanan.items[1].subtotal, 25000)

    def test_04_basic_authentication_access_control_dapur(self):
        """
        Menguji access control menggunakan Basic Authentication pada rute /dapur.
        Pelanggan/anonim ditolak dengan status 401 dan header WWW-Authenticate.
        """
        # 1. Akses tanpa kredensial ke /dapur -> 401 Unauthorized
        res_no_auth = self.client.get("/dapur")
        self.assertEqual(res_no_auth.status_code, 401)
        self.assertIn("WWW-Authenticate", res_no_auth.headers)
        self.assertIn("Basic", res_no_auth.headers["WWW-Authenticate"])

        # 2. Akses dengan kredensial salah -> 401 Unauthorized
        wrong_cred = base64.b64encode(b"pelanggan:rahasia").decode()
        res_wrong = self.client.get("/dapur", headers={"Authorization": f"Basic {wrong_cred}"})
        self.assertEqual(res_wrong.status_code, 401)

        # 3. Akses dengan Basic Authentication yang benar -> 200 OK
        res_auth = self.client.get("/dapur", headers=self.basic_auth_header)
        self.assertEqual(res_auth.status_code, 200)
        self.assertIn("KITCHEN DISPLAY SYSTEM", res_auth.get_data(as_text=True))

    def test_05_kitchen_polling_api_with_basic_auth(self):
        """Menguji polling API dapur /api/dapur/pesanan dilindungi Basic Auth."""
        # 1. Tanpa Basic Auth -> 401
        res = self.client.get("/api/dapur/pesanan")
        self.assertEqual(res.status_code, 401)

        # 2. Dengan Basic Auth -> 200 dan mengembalikan pesanan status 'Menunggu'
        with app.app_context():
            p = Pesanan(nomor_meja="03", status="Menunggu", total_harga=50000)
            db.session.add(p)
            db.session.commit()

        res_auth = self.client.get("/api/dapur/pesanan", headers=self.basic_auth_header)
        self.assertEqual(res_auth.status_code, 200)
        data = res_auth.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["total_antrean"], 1)
        self.assertEqual(data["pesanan"][0]["status"], "Menunggu")

    def test_06_kitchen_status_transition_menunggu_ke_selesai(self):
        """Menguji update status pesanan dari 'Menunggu' menjadi 'Selesai' via API."""
        with app.app_context():
            p = Pesanan(nomor_meja="09", status="Menunggu", total_harga=50000)
            db.session.add(p)
            db.session.commit()
            p_id = p.id

        # Ubah status via POST /api/dapur/pesanan/<id>/status
        res = self.client.post(
            f"/api/dapur/pesanan/{p_id}/status",
            data=json.dumps({"status": "Selesai"}),
            content_type="application/json",
            headers=self.basic_auth_header
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_baru"], "Selesai")

        # Verifikasi di database
        with app.app_context():
            p_check = db.session.get(Pesanan, p_id)
            self.assertEqual(p_check.status, "Selesai")


if __name__ == "__main__":
    unittest.main()
