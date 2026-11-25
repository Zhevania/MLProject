"""Membuat dataset antrean konsultasi KRS SINTETIS untuk simulasi.
Ganti data/antrean_konsultasi.csv dengan data nyata jika sudah ada
(kolom harus sama)."""
import os

import numpy as np
import pandas as pd

DOSEN = {
    "Dosen A": 9,    # rata-rata durasi konsultasi (menit)
    "Dosen B": 12,
    "Dosen C": 7,
    "Dosen D": 10,
    "Dosen E": 14,
}
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
JAM = list(range(8, 16))  # 08.00 - 15.00
HARI_RAMAI = {"Senin": 1.3, "Selasa": 1.0, "Rabu": 0.9, "Kamis": 1.1, "Jumat": 0.7}
JAM_RAMAI = {8: 0.7, 9: 1.2, 10: 1.4, 11: 1.0, 12: 0.5, 13: 0.9, 14: 1.1, 15: 0.8}


def generate(n=2500, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        dosen = rng.choice(list(DOSEN))
        hari = rng.choice(HARI)
        jam = int(rng.choice(JAM))
        lam = 5 * HARI_RAMAI[hari] * JAM_RAMAI[jam]
        jumlah = int(np.clip(rng.poisson(lam) + 1, 1, 20))
        nomor = int(rng.integers(1, jumlah + 1))
        durasi = float(np.clip(rng.normal(DOSEN[dosen], 2), 4, 25))
        tunggu = (nomor - 1) * durasi + rng.normal(0, 4)
        rows.append([dosen, hari, jam, jumlah, nomor, round(durasi, 1), round(max(tunggu, 0), 1)])
    return pd.DataFrame(
        rows,
        columns=["dosen", "hari", "jam", "jumlah_mahasiswa", "nomor_antrean",
                 "durasi_konsultasi", "waktu_tunggu"],
    )


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "data", "antrean_konsultasi.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    generate().to_csv(path, index=False)
    print("Dataset dibuat:", path)
