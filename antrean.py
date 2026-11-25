"""Antrean konsultasi real-time + status dosen (disimpan di data/antrean.json & data/dosen.json).
Jumlah mahasiswa dalam antrean dihitung otomatis dari tiket berstatus 'menunggu'."""
import json
import os
from datetime import date, datetime

from generate_dataset import HARI

BASE = os.path.join(os.path.dirname(__file__), "data")
QUEUE_FILE = os.path.join(BASE, "antrean.json")
DOSEN_FILE = os.path.join(BASE, "dosen.json")

# Akun dengan email berikut masuk sebagai ADMIN (pengatur antrean).
ADMIN_EMAILS = ["admin@antrein.id"]
AKTIF = ("menunggu", "dipanggil")
STATUS_DOSEN = ["Hadir", "Istirahat", "Tidak hadir"]


def is_admin(email):
    return email.strip().lower() in ADMIN_EMAILS


def _today():
    return date.today().isoformat()


def _read(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _menit(a, b):
    if not a or not b:
        return None
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60


# ---------------- status & jadwal dosen ----------------
def info(dosen):
    """Info dosen. Status kehadiran/catatan/buka-tutup kembali ke default setiap hari baru."""
    stored = _read(DOSEN_FILE, {}).get(dosen, {})
    data = {"nama": dosen, "status": "Tidak hadir", "ruangan": "", "jam_mulai": "08:00",
            "jam_selesai": "15:00", "catatan": "", "antrean_dibuka": True}
    data.update(stored)
    if stored.get("tanggal") != _today():
        data.update({"status": "Tidak hadir", "catatan": "", "antrean_dibuka": True})
    data["nama"] = data.get("nama") or dosen
    return data


def nama(dosen):
    return info(dosen)["nama"]


def simpan_info(dosen, **kw):
    semua = _read(DOSEN_FILE, {})
    cur = info(dosen)
    cur.update(kw)
    cur["tanggal"] = _today()
    semua[dosen] = cur
    _write(DOSEN_FILE, semua)


def bisa_ambil(dosen):
    inf = info(dosen)
    if inf["status"] == "Tidak hadir":
        return False, "Dosen belum/tidak hadir hari ini, nomor antrean belum bisa diambil."
    if not inf["antrean_dibuka"]:
        return False, "Antrean sedang ditutup oleh admin."
    return True, "OK"


# ---------------- tiket antrean ----------------
def label(t):
    return f"{t['dosen'][-1]}-{t['no']:03d}"


def semua():
    return _read(QUEUE_FILE, [])


def hari_ini():
    return [t for t in semua() if t["tanggal"] == _today()]


def menunggu(dosen):
    return sorted((t for t in hari_ini() if t["dosen"] == dosen and t["status"] == "menunggu"),
                  key=lambda t: t["no"])


def jumlah_menunggu(dosen):
    return len(menunggu(dosen))


def dilayani(dosen):
    for t in hari_ini():
        if t["dosen"] == dosen and t["status"] == "dipanggil":
            return t
    return None


def tiket_aktif(email):
    email = email.strip().lower()
    for t in hari_ini():
        if t["email"] == email and t["status"] in AKTIF:
            return t
    return None


def tiket_terakhir(email):
    email = email.strip().lower()
    mine = [t for t in hari_ini() if t["email"] == email]
    return max(mine, key=lambda t: t["waktu_ambil"]) if mine else None


def posisi(t):
    """0 = sedang dipanggil; 1 = berikutnya; dst."""
    if t["status"] == "dipanggil":
        return 0
    ids = [x["id"] for x in menunggu(t["dosen"])]
    return ids.index(t["id"]) + 1 if t["id"] in ids else 0


def _tambah(tickets, dosen, email, nama_mhs, nim, demo=False):
    today = _today()
    no = max([t["no"] for t in tickets if t["tanggal"] == today and t["dosen"] == dosen], default=0) + 1
    jumlah = len([t for t in tickets if t["tanggal"] == today and t["dosen"] == dosen
                  and t["status"] == "menunggu"]) + 1
    t = {"id": f"{today}-{dosen[-1]}-{no}", "tanggal": today, "dosen": dosen, "no": no,
         "email": email.format(no=no).strip().lower(), "nama": nama_mhs, "nim": nim,
         "status": "menunggu", "waktu_ambil": _now(), "waktu_panggil": None,
         "waktu_selesai": None, "jumlah_saat_ambil": jumlah, "demo": demo}
    tickets.append(t)
    return t


def ambil_nomor(user, dosen):
    ok, pesan = bisa_ambil(dosen)
    if not ok:
        return None, pesan
    if tiket_aktif(user["email"]):
        return None, "Kamu masih punya nomor antrean aktif."
    tickets = semua()
    t = _tambah(tickets, dosen, user["email"], user["nama"], user["nim"])
    _write(QUEUE_FILE, tickets)
    return t, "OK"


def batalkan(email):
    tickets = semua()
    for t in tickets:
        if t["tanggal"] == _today() and t["email"] == email.strip().lower() and t["status"] in AKTIF:
            t["status"] = "batal"
            t["waktu_selesai"] = _now()
    _write(QUEUE_FILE, tickets)


def _akhiri_dilayani(dosen, status):
    tickets = semua()
    ada = False
    for t in tickets:
        if t["tanggal"] == _today() and t["dosen"] == dosen and t["status"] == "dipanggil":
            t["status"], t["waktu_selesai"] = status, _now()
            ada = True
    _write(QUEUE_FILE, tickets)
    return ada


def selesai_saat_ini(dosen):
    return _akhiri_dilayani(dosen, "selesai")


def lewati_saat_ini(dosen):
    return _akhiri_dilayani(dosen, "dilewati")


def panggil_berikutnya(dosen):
    """Menyelesaikan yang sedang dilayani lalu memanggil nomor berikutnya. Return tiket atau None."""
    selesai_saat_ini(dosen)
    tickets = semua()
    antre = sorted((t for t in tickets if t["tanggal"] == _today() and t["dosen"] == dosen
                    and t["status"] == "menunggu"), key=lambda t: t["no"])
    if not antre:
        return None
    antre[0]["status"], antre[0]["waktu_panggil"] = "dipanggil", _now()
    _write(QUEUE_FILE, tickets)
    return antre[0]


def batalkan_id(tid):
    tickets = semua()
    for t in tickets:
        if t["id"] == tid and t["status"] in AKTIF:
            t["status"], t["waktu_selesai"] = "batal", _now()
    _write(QUEUE_FILE, tickets)


def batalkan_semua(dosen):
    tickets = semua()
    n = 0
    for t in tickets:
        if t["tanggal"] == _today() and t["dosen"] == dosen and t["status"] in AKTIF:
            t["status"], t["waktu_selesai"] = "batal", _now()
            n += 1
    _write(QUEUE_FILE, tickets)
    return n


def tambah_manual(dosen, nama_mhs, nim):
    """Mahasiswa yang datang langsung (tanpa akun)."""
    tickets = semua()
    t = _tambah(tickets, dosen, "manual{no}@walkin.local", nama_mhs, nim or "-")
    _write(QUEUE_FILE, tickets)
    return t


def isi_contoh(dosen, n):
    tickets = semua()
    for _ in range(n):
        _tambah(tickets, dosen, f"contoh{dosen[-1].lower()}" + "{no}@demo.local",
                "Mahasiswa Contoh", "000000", demo=True)
    _write(QUEUE_FILE, tickets)


def reset_hari_ini():
    _write(QUEUE_FILE, [t for t in semua() if t["tanggal"] != _today()])


def dataset_latih():
    """Riwayat nyata (tanpa data demo) dalam format dataset model. Hanya tiket 'selesai'."""
    import pandas as pd
    rows = []
    for t in semua():
        if t.get("demo") or t["status"] != "selesai":
            continue
        tunggu, durasi = _menit(t["waktu_ambil"], t["waktu_panggil"]), _menit(t["waktu_panggil"], t["waktu_selesai"])
        ambil = datetime.fromisoformat(t["waktu_ambil"])
        if tunggu is None or durasi is None or ambil.weekday() > 4:
            continue
        rows.append({"dosen": t["dosen"], "hari": HARI[ambil.weekday()], "jam": min(max(ambil.hour, 8), 15),
                     "jumlah_mahasiswa": t["jumlah_saat_ambil"], "nomor_antrean": t["jumlah_saat_ambil"],
                     "durasi_konsultasi": round(durasi, 1), "waktu_tunggu": round(tunggu, 1)})
    return pd.DataFrame(rows, columns=["dosen", "hari", "jam", "jumlah_mahasiswa", "nomor_antrean",
                                       "durasi_konsultasi", "waktu_tunggu"])
