"""Model Random Forest Regressor untuk prediksi waktu tunggu."""
import os

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "antrean_konsultasi.csv")
KATEGORI = ["dosen", "hari"]
NUMERIK = ["jam", "jumlah_mahasiswa", "nomor_antrean"]
TARGET = "waktu_tunggu"


def load_data():
    if not os.path.exists(DATA_PATH):
        from generate_dataset import generate
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        generate().to_csv(DATA_PATH, index=False)
    return pd.read_csv(DATA_PATH)


def train(df):
    X, y = df[KATEGORI + NUMERIK], df[TARGET]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    pre = ColumnTransformer(
        [("kat", OneHotEncoder(handle_unknown="ignore"), KATEGORI)],
        remainder="passthrough",
    )
    pipe = Pipeline([
        ("pre", pre),
        ("rf", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)),
    ])
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    metrik = {
        "mae": mean_absolute_error(y_te, pred),
        "r2": r2_score(y_te, pred),
        "n_train": len(X_tr),
        "n_test": len(X_te),
    }
    rf = pipe.named_steps["rf"]
    names = pipe.named_steps["pre"].get_feature_names_out()
    imp = (pd.DataFrame({"fitur": [n.split("__")[-1] for n in names],
                         "kepentingan": rf.feature_importances_})
           .sort_values("kepentingan", ascending=False))
    return pipe, metrik, imp


def predict_wait(pipe, dosen, hari, jam, jumlah, nomor):
    X = pd.DataFrame([{"dosen": dosen, "hari": hari, "jam": jam,
                       "jumlah_mahasiswa": jumlah, "nomor_antrean": nomor}])
    return max(float(pipe.predict(X)[0]), 0.0)


def kepadatan(jumlah):
    if jumlah <= 4:
        return "Rendah"
    if jumlah <= 9:
        return "Sedang"
    return "Tinggi"
