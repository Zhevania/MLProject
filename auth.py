"""Autentikasi mahasiswa: registrasi & login.
Password di-hash dengan PBKDF2-HMAC SHA-256 + salt acak, disimpan di JSON lokal."""
import hashlib
import hmac
import json
import os
import re
import secrets

USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "users.json")
ITERATIONS = 200_000
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _load():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def register(nama, nim, jurusan, email, password, konfirmasi):
    """Return (berhasil: bool, pesan: str)."""
    nama, nim, jurusan, email = nama.strip(), nim.strip(), jurusan.strip(), email.strip().lower()
    if not all([nama, nim, jurusan, email, password, konfirmasi]):
        return False, "Semua kolom wajib diisi."
    if not nim.isdigit():
        return False, "NIM hanya boleh berisi angka."
    if not EMAIL_RE.match(email):
        return False, "Format email tidak valid."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    if password != konfirmasi:
        return False, "Konfirmasi password tidak cocok."
    users = _load()
    if email in users:
        return False, "Email sudah terdaftar."
    if any(u["nim"] == nim for u in users.values()):
        return False, "NIM sudah terdaftar."
    salt = secrets.token_bytes(16)
    users[email] = {
        "nama": nama,
        "nim": nim,
        "jurusan": jurusan,
        "salt": salt.hex(),
        "hash": _hash(password, salt).hex(),
    }
    _save(users)
    return True, "Registrasi berhasil. Silakan login."


def login(email, password):
    """Return (profil dict | None, pesan)."""
    email = email.strip().lower()
    users = _load()
    u = users.get(email)
    if not u:
        return None, "Email atau password salah."
    expected = bytes.fromhex(u["hash"])
    got = _hash(password, bytes.fromhex(u["salt"]))
    if not hmac.compare_digest(expected, got):
        return None, "Email atau password salah."
    return {"email": email, "nama": u["nama"], "nim": u["nim"], "jurusan": u["jurusan"]}, "OK"
