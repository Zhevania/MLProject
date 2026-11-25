# Antre.in KRS

Aplikasi web (Python + Streamlit) untuk memperkirakan antrean konsultasi KRS dengan dosen
pembimbing akademik, memakai **Random Forest Regressor**.

## Fitur
Login dengan email & password, registrasi, profil mahasiswa, dashboard, prediksi antrean, perencana konsultasi,
perbandingan dosen, data & model (MAE, R²), simulasi nomor antrean, dan logout.

## Cara menjalankan
```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
Dataset sintetis dibuat otomatis saat pertama kali dijalankan (atau jalankan `python generate_dataset.py`).

## Cara kerja antrean
- Mahasiswa memilih dosen lalu menekan **Ambil nomor antrean**. Jumlah mahasiswa dalam antrean
  **dihitung otomatis oleh sistem**. Hari & jam diambil dari waktu sistem.
- Nomor hanya bisa diambil jika dosen berstatus **Hadir/Istirahat** dan antrean **dibuka** oleh admin.

## Akun admin (pengatur antrean)
1. Buka tab **Registrasi**, daftar dengan email `admin@antrein.id` (ubah di `antrean.py`, `ADMIN_EMAILS`).
   NIM dan jurusan boleh diisi bebas.
2. Login dengan email itu: menu berubah menjadi menu admin.
   - **Ringkasan Admin**: dosen hadir, jumlah menunggu/dilayani/selesai.
   - **Kelola Antrean**: panggil berikutnya, selesai, lewati, tambah mahasiswa manual, batalkan nomor, demo.
   - **Status & Jadwal Dosen**: input hadir/istirahat/tidak hadir, nama dosen, ruangan, jam, catatan, buka/tutup antrean.
     Status kembali ke "Tidak hadir" setiap hari baru, jadi diisi ulang tiap hari.
   - **Riwayat & Statistik**: rekap, durasi layanan nyata, unduh CSV, dan dataset nyata untuk melatih ulang model.
3. Data tersimpan di `data/antrean.json` dan `data/dosen.json` (dibuat otomatis).

## Struktur
- `antrean.py` – antrean real-time, status dosen, fungsi admin
- `app.py` – antarmuka & halaman
- `auth.py` – registrasi/login (PBKDF2-HMAC SHA-256 + salt acak, disimpan di `data/users.json`)
- `model.py` – pelatihan & prediksi Random Forest
- `generate_dataset.py` – pembuat dataset sintetis
- `data/antrean_konsultasi.csv` – dataset (ganti dengan data nyata)

## Catatan
Dataset bawaan **sintetis** (hanya untuk simulasi). Kolom data nyata:
`dosen, hari, jam, jumlah_mahasiswa, nomor_antrean, durasi_konsultasi, waktu_tunggu`.
