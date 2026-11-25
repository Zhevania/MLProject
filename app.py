"""Antre.in KRS - estimasi antrean konsultasi KRS dengan Random Forest Regressor."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import antrean
import auth
from generate_dataset import DOSEN, HARI, JAM
from model import kepadatan, load_data, predict_wait, train

NAVY, BLUE, TURQ, BG = "#0B1F4B", "#2F6BFF", "#1ABC9C", "#F2F6FF"
WARNA_KEPADATAN = {"Rendah": TURQ, "Sedang": "#F5A623", "Tinggi": "#E5484D"}
DOSEN_LIST = list(DOSEN)
MENU = ["Dashboard", "Prediksi Antrean", "Perencana Konsultasi",
        "Perbandingan Dosen", "Data & Model", "Simulasi Nomor Antrean"]

ADMIN_MENU = ["Ringkasan Admin", "Kelola Antrean", "Status & Jadwal Dosen",
              "Riwayat & Statistik", "Data & Model"]
WARNA_STATUS = {"Hadir": TURQ, "Istirahat": "#F5A623", "Tidak hadir": "#E5484D"}

st.set_page_config(page_title="Antre.in KRS", page_icon="🎓", layout="wide")

st.markdown(f"""
<style>
.stApp {{ background: {BG}; }}
[data-testid="stSidebar"] {{ background: {NAVY}; }}
[data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] * {{ color: {NAVY} !important; }}
.hero {{ background: linear-gradient(135deg,{NAVY},{BLUE}); color:#fff; padding:1.4rem 1.6rem;
        border-radius:18px; margin-bottom:1.2rem; }}
.hero h1 {{ color:#fff; margin:0; font-size:1.8rem; }}
.hero p {{ margin:.3rem 0 0; opacity:.9; }}
.card {{ background:#fff; border-radius:16px; padding:1.1rem 1.3rem;
        box-shadow:0 2px 10px rgba(11,31,75,.08); border-left:5px solid {TURQ}; }}
.card .lbl {{ color:#5B6B8C; font-size:.85rem; }}
.card .val {{ color:{NAVY}; font-size:1.7rem; font-weight:700; }}
.ticket {{ background:#fff; border:2px dashed {BLUE}; border-radius:18px; padding:1.4rem;
          text-align:center; }}
.ticket .no {{ font-size:3rem; font-weight:800; color:{NAVY}; letter-spacing:2px; }}
.badge {{ display:inline-block; padding:.2rem .8rem; border-radius:999px; color:#fff;
         font-weight:600; font-size:.85rem; }}
div.stButton > button, div[data-testid="stFormSubmitButton"] > button {{
    background:{BLUE}; color:#fff; border:0; border-radius:10px; font-weight:600; }}
</style>
""", unsafe_allow_html=True)


# ---------- util ----------
@st.cache_data
def get_data():
    return load_data()


@st.cache_resource
def get_model():
    return train(get_data())


def card(label, value):
    st.markdown(f'<div class="card"><div class="lbl">{label}</div><div class="val">{value}</div></div>',
                unsafe_allow_html=True)


def badge(level):
    return f'<span class="badge" style="background:{WARNA_KEPADATAN[level]}">{level}</span>'


def badge_status(s):
    return f'<span class="badge" style="background:{WARNA_STATUS[s]}">{s}</span>'


def flash():
    """Pesan singkat yang bertahan melewati st.rerun()."""
    msg = st.session_state.pop("flash", None)
    if msg:
        {"success": st.success, "warning": st.warning, "error": st.error}[msg[0]](msg[1])


def set_flash(jenis, teks):
    st.session_state["flash"] = (jenis, teks)


def hero(judul, sub):
    st.markdown(f'<div class="hero"><h1>{judul}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def jam_label(j):
    return f"{j:02d}.00"


def typical_queue(df, dosen, hari, jam):
    sub = df[(df.dosen == dosen) & (df.hari == hari) & (df.jam == jam)]
    if sub.empty:
        sub = df[(df.dosen == dosen) & (df.hari == hari)]
    return int(round(sub.jumlah_mahasiswa.mean())) if not sub.empty else 5


def status_text(menit):
    if menit <= 5:
        return "Bisa langsung masuk"
    return "Perlu menunggu"


# ---------- halaman login / registrasi ----------
def page_auth():
    hero("🎓 Antre.in KRS", "Perkirakan antrean konsultasi KRS dengan dosen pembimbing akademik.")
    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        tab_login, tab_reg = st.tabs(["Login", "Registrasi"])
        with tab_login:
            with st.form("form_login"):
                u = st.text_input("Email")
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Masuk", use_container_width=True):
                    profil, pesan = auth.login(u, p)
                    if profil:
                        st.session_state["user"] = profil
                        st.rerun()
                    else:
                        st.error(pesan)
        with tab_reg:
            with st.form("form_reg"):
                nama = st.text_input("Nama lengkap")
                nim = st.text_input("NIM")
                jur = st.text_input("Jurusan / Program studi")
                un = st.text_input("Email")
                pw = st.text_input("Password (min. 6 karakter)", type="password")
                kf = st.text_input("Konfirmasi password", type="password")
                if st.form_submit_button("Daftar", use_container_width=True):
                    ok, pesan = auth.register(nama, nim, jur, un, pw, kf)
                    (st.success if ok else st.error)(pesan)


# ---------- halaman utama ----------
def waktu_sekarang():
    """Hari & jam acuan model, diambil otomatis dari waktu sistem."""
    now = datetime.now()
    hari = HARI[now.weekday()] if now.weekday() < 5 else HARI[0]
    jam = min(max(now.hour, JAM[0]), JAM[-1])
    return hari, jam


def estimasi_baru(pipe, dosen, hari, jam):
    """Estimasi jika mahasiswa mengambil nomor sekarang (jumlah antrean dihitung sistem)."""
    n = antrean.jumlah_menunggu(dosen)
    return n, predict_wait(pipe, dosen, hari, jam, n + 1, n + 1)


def page_dashboard(user, df, pipe):
    hero(f"Halo, {user['nama'].split()[0]}! 👋", "Ringkasan kondisi antrean konsultasi KRS hari ini.")
    hari, jam = waktu_sekarang()
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Profil mahasiswa")
        st.markdown(f"**Nama:** {user['nama']}  \n**NIM:** {user['nim']}  \n"
                    f"**Jurusan:** {user['jurusan']}  \n**Email:** {user['email']}")
    with c2:
        st.subheader("Nomor antrean saya")
        t = antrean.tiket_aktif(user["email"])
        if t:
            pos = antrean.posisi(t)
            ket = "Giliranmu sekarang!" if pos == 0 else f"Posisi {pos} dalam antrean"
            card(f"{antrean.nama(t['dosen'])} · {antrean.label(t)}", ket)
        else:
            st.info("Kamu belum mengambil nomor antrean. Buka menu **Prediksi Antrean**.")

    rows = []
    for d in DOSEN_LIST:
        n, w = estimasi_baru(pipe, d, hari, jam)
        s = antrean.dilayani(d)
        rows.append({"Dosen": antrean.nama(d), "Status": antrean.info(d)["status"],
                     "Mahasiswa dalam antrean": n,
                     "Sedang dilayani": antrean.label(s) if s else "-",
                     "Estimasi tunggu (menit)": round(w), "Kepadatan": kepadatan(n)})
    r = pd.DataFrame(rows)

    st.subheader(f"Kondisi antrean · {hari}, {jam_label(jam)}")
    m1, m2, m3 = st.columns(3)
    with m1:
        card("Total mahasiswa dalam antrean", int(r["Mahasiswa dalam antrean"].sum()))
    with m2:
        card("Rata-rata estimasi tunggu", f"{r['Estimasi tunggu (menit)'].mean():.0f} menit")
    with m3:
        hadir = r[r["Status"] == "Hadir"]
        if hadir.empty:
            card("Antrean tersingkat", "Belum ada dosen hadir")
        else:
            terbaik = hadir.sort_values(["Estimasi tunggu (menit)", "Mahasiswa dalam antrean"]).iloc[0]
            card("Antrean tersingkat", f"{terbaik['Dosen']} ({terbaik['Estimasi tunggu (menit)']} mnt)")
    if st.button("🔄 Segarkan"):
        st.rerun()

    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(r, x="Dosen", y="Mahasiswa dalam antrean", color="Kepadatan",
                     color_discrete_map=WARNA_KEPADATAN, title="Jumlah mahasiswa dalam antrean per dosen")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = px.bar(r, x="Dosen", y="Estimasi tunggu (menit)", color="Kepadatan",
                     color_discrete_map=WARNA_KEPADATAN, title="Estimasi waktu tunggu per dosen")
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(r, use_container_width=True, hide_index=True)


def page_prediksi(user, df, pipe):
    hero("Prediksi Antrean", "Sistem menghitung jumlah mahasiswa dalam antrean dan memperkirakan waktu tunggumu.")
    hari, jam = waktu_sekarang()
    st.caption(f"Waktu acuan otomatis: {hari}, {jam_label(jam)}.")
    dosen = st.selectbox("Dosen pembimbing", DOSEN_LIST, format_func=antrean.nama)
    t = antrean.tiket_aktif(user["email"])
    n = antrean.jumlah_menunggu(dosen)
    s = antrean.dilayani(dosen)

    if t and t["dosen"] == dosen:
        pos = antrean.posisi(t)
        w = 0.0 if pos == 0 else predict_wait(pipe, dosen, hari, jam, max(n, pos), pos)
        nomor_txt = antrean.label(t)
        posisi_txt = "Giliranmu!" if pos == 0 else f"Posisi {pos}"
    else:
        w = predict_wait(pipe, dosen, hari, jam, n + 1, n + 1)
        nomor_txt, posisi_txt = "Belum ada", f"Posisi {n + 1} jika mengambil sekarang"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Mahasiswa dalam antrean", n)
    with c2:
        card("Nomor antrean kamu", nomor_txt)
    with c3:
        card("Estimasi tunggu", f"{w:.0f} menit")
    with c4:
        card("Kepadatan", kepadatan(n))
    st.write(f"{posisi_txt} · Sedang dilayani: **{antrean.label(s) if s else '-'}**")

    inf = antrean.info(dosen)
    jadwal = f"{inf['jam_mulai'].replace(':', '.')}–{inf['jam_selesai'].replace(':', '.')}"
    st.markdown(f"Status dosen: {badge_status(inf['status'])} &nbsp; Ruangan: **{inf['ruangan'] or '-'}** "
                f"&nbsp; Jam: **{jadwal}**" + (f" &nbsp; Catatan: *{inf['catatan']}*" if inf["catatan"] else ""),
                unsafe_allow_html=True)
    if t:
        if t["dosen"] != dosen:
            st.info(f"Kamu sudah punya nomor {antrean.label(t)} di {antrean.nama(t['dosen'])}. Batalkan dulu di "
                    "menu **Simulasi Nomor Antrean** jika ingin pindah dosen.")
    else:
        bisa, alasan = antrean.bisa_ambil(dosen)
        if not bisa:
            st.warning(alasan)
        elif st.button("Ambil nomor antrean", type="primary"):
            tiket, pesan = antrean.ambil_nomor(user, dosen)
            if tiket:
                st.rerun()
            else:
                st.error(pesan)
    if st.button("🔄 Segarkan", key="seg_pred"):
        st.rerun()
    st.caption("Jumlah antrean dihitung otomatis oleh sistem. Estimasi berasal dari model Random Forest dan bersifat perkiraan.")


def page_planner(df, pipe):
    hero("Perencana Konsultasi", "Bandingkan beberapa waktu dan pilih yang paling lengang.")
    a, b = st.columns(2)
    dosen = a.selectbox("Dosen pembimbing", DOSEN_LIST, format_func=antrean.nama)
    hari_pilih = b.multiselect("Hari yang dibandingkan", HARI, default=HARI)
    if not hari_pilih:
        st.info("Pilih minimal satu hari.")
        return
    rows = []
    for h in hari_pilih:
        for j in JAM:
            n = typical_queue(df, dosen, h, j)
            w = predict_wait(pipe, dosen, h, j, n + 1, n + 1)
            rows.append({"Hari": h, "Jam": jam_label(j), "Antrean umum": n,
                         "Estimasi tunggu (menit)": round(w), "Kepadatan": kepadatan(n)})
    r = pd.DataFrame(rows)
    best = r.sort_values(["Estimasi tunggu (menit)", "Antrean umum"]).head(3)
    st.success("Rekomendasi waktu paling lengang: " +
               "; ".join(f"{x.Hari} {x.Jam} (~{x['Estimasi tunggu (menit)']} mnt)" for _, x in best.iterrows()))
    pivot = r.pivot(index="Jam", columns="Hari", values="Estimasi tunggu (menit)")[hari_pilih]
    fig = px.imshow(pivot, text_auto=True, aspect="auto", color_continuous_scale=["#E6FBF6", BLUE, NAVY],
                    title="Estimasi waktu tunggu (menit)", labels={"color": "Menit"})
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Lihat tabel lengkap"):
        st.dataframe(r, use_container_width=True, hide_index=True)


def page_perbandingan(df, pipe):
    hero("Perbandingan Dosen", "Bandingkan kondisi antrean antar dosen pembimbing.")
    agg = df.groupby("dosen").agg(
        rata_antrean=("jumlah_mahasiswa", "mean"),
        rata_tunggu=("waktu_tunggu", "mean"),
        rata_durasi=("durasi_konsultasi", "mean"),
    ).reset_index()
    agg["Kepadatan"] = agg.rata_antrean.round().astype(int).map(kepadatan)
    tampil = agg.rename(columns={"dosen": "Dosen", "rata_antrean": "Rata-rata antrean",
                                 "rata_tunggu": "Rata-rata waktu tunggu (mnt)",
                                 "rata_durasi": "Durasi konsultasi (mnt)"}).round(1)
    tampil["Dosen"] = tampil["Dosen"].map(antrean.nama)
    st.dataframe(tampil, use_container_width=True, hide_index=True)
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(px.bar(tampil, x="Dosen", y="Rata-rata waktu tunggu (mnt)",
                               title="Rata-rata waktu tunggu", color_discrete_sequence=[BLUE]),
                        use_container_width=True)
    with g2:
        st.plotly_chart(px.bar(tampil, x="Dosen", y="Durasi konsultasi (mnt)",
                               title="Durasi konsultasi", color_discrete_sequence=[TURQ]),
                        use_container_width=True)
    st.subheader("Estimasi pada waktu tertentu")
    a, b = st.columns(2)
    hari = a.selectbox("Hari", HARI, key="cmp_hari")
    jam = b.selectbox("Jam", JAM, format_func=jam_label, key="cmp_jam")
    rows = []
    for d in DOSEN_LIST:
        n = typical_queue(df, d, hari, jam)
        rows.append({"Dosen": antrean.nama(d), "Antrean umum": n,
                     "Estimasi tunggu (menit)": round(predict_wait(pipe, d, hari, jam, n + 1, n + 1)),
                     "Kepadatan": kepadatan(n)})
    r = pd.DataFrame(rows)
    st.plotly_chart(px.bar(r, x="Dosen", y="Estimasi tunggu (menit)", color="Kepadatan",
                           color_discrete_map=WARNA_KEPADATAN), use_container_width=True)
    st.dataframe(r, use_container_width=True, hide_index=True)


def page_data_model(df, metrik, imp):
    hero("Data & Model Machine Learning", "Dataset, algoritma, dan evaluasi model.")
    st.warning("Dataset bawaan adalah data **sintetis** untuk simulasi. Ganti `data/antrean_konsultasi.csv` "
               "dengan data antrean nyata (kolom sama) lalu restart aplikasi.")
    st.subheader("A. Informasi dataset")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah baris", len(df))
    c2.metric("Data latih", metrik["n_train"])
    c3.metric("Data uji", metrik["n_test"])
    st.dataframe(df.head(50), use_container_width=True, hide_index=True)
    st.subheader("B. Algoritma: Random Forest Regressor")
    st.markdown("1. Membaca dataset antrean.\n2. One-hot encoding untuk data kategori (dosen, hari); data numerik (jam, jumlah, nomor) dipakai langsung.\n"
                "3. Membagi data: 80% latih, 20% uji.\n4. Melatih 200 decision tree.\n5. Rata-rata prediksi semua pohon menjadi estimasi waktu tunggu.")
    st.subheader("C. Evaluasi model")
    m1, m2 = st.columns(2)
    m1.metric("MAE (menit)", f"{metrik['mae']:.2f}")
    m2.metric("R² Score", f"{metrik['r2']:.3f}")
    st.caption("MAE = rata-rata kesalahan prediksi (makin kecil makin baik). R² = kemampuan model menjelaskan variasi data (makin dekat 1 makin baik).")
    st.plotly_chart(px.bar(imp, x="kepentingan", y="fitur", orientation="h",
                           title="Kepentingan fitur", color_discrete_sequence=[BLUE]),
                    use_container_width=True)


def page_simulasi(user, df, pipe):
    hero("Simulasi Nomor Antrean", "Pantau posisi dan estimasi tunggu nomor antreanmu.")
    t = antrean.tiket_aktif(user["email"])
    if not t:
        last = antrean.tiket_terakhir(user["email"])
        if last:
            ket = {"selesai": "sudah selesai dilayani", "batal": "dibatalkan",
                   "dilewati": "dilewati oleh admin (silakan ambil nomor baru)"}.get(last["status"], last["status"])
            st.info(f"Nomor {antrean.label(last)} ({antrean.nama(last['dosen'])}) {ket}.")
        st.info("Kamu belum punya nomor antrean aktif. Ambil nomor di menu **Prediksi Antrean**.")
        return
    hari, jam = waktu_sekarang()
    pos = antrean.posisi(t)
    n = antrean.jumlah_menunggu(t["dosen"])
    w = 0.0 if pos == 0 else predict_wait(pipe, t["dosen"], hari, jam, max(n, pos), pos)
    level = kepadatan(n)
    status = "Giliranmu! Silakan masuk" if pos == 0 else "Perlu menunggu"
    st.markdown(f"""
    <div class="ticket">
      <div class="lbl">NOMOR ANTREAN · {antrean.nama(t['dosen'])}</div>
      <div class="no">{antrean.label(t)}</div>
      <div>Posisi antrean: <b>{pos if pos else 'Sedang dipanggil'}</b> · Mahasiswa menunggu: <b>{n}</b></div>
      <div>Estimasi tunggu: <b>{w:.0f} menit</b></div>
      <div style="margin-top:.5rem">Kepadatan {badge(level)} · {status}</div>
    </div>""", unsafe_allow_html=True)
    a, b = st.columns(2)
    if a.button("🔄 Segarkan", use_container_width=True):
        st.rerun()
    if b.button("Batalkan nomor", use_container_width=True):
        antrean.batalkan(user["email"])
        st.rerun()


def _t(s):
    return datetime.strptime(s, "%H:%M").time()


def page_admin_ringkasan():
    hero("Panel Admin", "Ringkasan antrean dan kehadiran dosen hari ini.")
    flash()
    tk = antrean.hari_ini()
    hadir = sum(antrean.info(d)["status"] == "Hadir" for d in DOSEN_LIST)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        card("Dosen hadir", f"{hadir} / {len(DOSEN_LIST)}")
    with m2:
        card("Mahasiswa menunggu", sum(t["status"] == "menunggu" for t in tk))
    with m3:
        card("Sedang dilayani", sum(t["status"] == "dipanggil" for t in tk))
    with m4:
        card("Selesai hari ini", sum(t["status"] == "selesai" for t in tk))
    rows = []
    for d in DOSEN_LIST:
        inf, s = antrean.info(d), antrean.dilayani(d)
        rows.append({"Dosen": inf["nama"], "Status": inf["status"], "Ruangan": inf["ruangan"] or "-",
                     "Jam": f"{inf['jam_mulai']}–{inf['jam_selesai']}",
                     "Antrean": "Dibuka" if inf["antrean_dibuka"] else "Ditutup",
                     "Menunggu": antrean.jumlah_menunggu(d),
                     "Dilayani": antrean.label(s) if s else "-",
                     "Selesai": sum(t["dosen"] == d and t["status"] == "selesai" for t in tk),
                     "Catatan": inf["catatan"]})
    r = pd.DataFrame(rows)
    st.dataframe(r, use_container_width=True, hide_index=True)
    st.plotly_chart(px.bar(r, x="Dosen", y="Menunggu", color="Status", color_discrete_map=WARNA_STATUS,
                           title="Mahasiswa menunggu per dosen"), use_container_width=True)
    if st.button("🔄 Segarkan"):
        st.rerun()


def page_admin_antrean():
    hero("Kelola Antrean", "Panggil, selesaikan, lewati, atau tambah mahasiswa pada antrean dosen.")
    flash()
    dosen = st.selectbox("Dosen", DOSEN_LIST, format_func=antrean.nama)
    inf, s, n = antrean.info(dosen), antrean.dilayani(dosen), antrean.jumlah_menunggu(dosen)
    st.markdown(f"Status dosen: {badge_status(inf['status'])} · Antrean: **{'dibuka' if inf['antrean_dibuka'] else 'ditutup'}**",
                unsafe_allow_html=True)
    if inf["status"] == "Tidak hadir":
        st.warning("Dosen berstatus Tidak hadir. Ubah di menu **Status & Jadwal Dosen**.")
    c1, c2 = st.columns(2)
    with c1:
        card("Sedang dilayani", f"{antrean.label(s)} · {s['nama']}" if s else "-")
    with c2:
        card("Mahasiswa menunggu", n)
    b1, b2, b3 = st.columns(3)
    if b1.button("▶ Panggil berikutnya", type="primary", use_container_width=True):
        t = antrean.panggil_berikutnya(dosen)
        set_flash("success" if t else "warning",
                  f"Memanggil {antrean.label(t)} · {t['nama']}" if t else "Tidak ada mahasiswa yang menunggu.")
        st.rerun()
    if b2.button("✔ Selesai", use_container_width=True):
        ok = antrean.selesai_saat_ini(dosen)
        set_flash("success" if ok else "warning", "Konsultasi ditandai selesai." if ok else "Tidak ada yang sedang dilayani.")
        st.rerun()
    if b3.button("⏭ Lewati", use_container_width=True):
        ok = antrean.lewati_saat_ini(dosen)
        set_flash("success" if ok else "warning", "Nomor dilewati." if ok else "Tidak ada yang sedang dilayani.")
        st.rerun()

    with st.expander("➕ Tambah mahasiswa manual (datang langsung / tanpa akun)"):
        with st.form("form_manual", clear_on_submit=True):
            nm = st.text_input("Nama mahasiswa")
            nim = st.text_input("NIM (opsional)")
            if st.form_submit_button("Tambah ke antrean"):
                if not nm.strip():
                    st.error("Nama wajib diisi.")
                else:
                    t = antrean.tambah_manual(dosen, nm.strip(), nim.strip())
                    set_flash("success", f"{nm.strip()} ditambahkan dengan nomor {antrean.label(t)}.")
                    st.rerun()

    st.subheader("Daftar antrean hari ini")
    tk = [t for t in antrean.hari_ini() if t["dosen"] == dosen]
    if tk:
        st.dataframe(pd.DataFrame([{"Nomor": antrean.label(t), "Nama": t["nama"], "NIM": t["nim"],
                                    "Status": t["status"], "Ambil": t["waktu_ambil"][11:],
                                    "Dipanggil": (t["waktu_panggil"] or "")[11:]} for t in tk]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada antrean untuk dosen ini hari ini.")

    menung = antrean.menunggu(dosen)
    if menung:
        x, y = st.columns([3, 1])
        peta = {t["id"]: t for t in menung}
        pid = x.selectbox("Batalkan nomor tertentu", list(peta),
                          format_func=lambda i: f"{antrean.label(peta[i])} · {peta[i]['nama']}")
        if y.button("Batalkan nomor", use_container_width=True):
            antrean.batalkan_id(pid)
            set_flash("success", f"Nomor {antrean.label(peta[pid])} dibatalkan.")
            st.rerun()
    if tk:
        with st.expander("⚠️ Batalkan semua antrean dosen ini"):
            yakin = st.checkbox("Saya yakin ingin membatalkan seluruh antrean aktif dosen ini")
            if st.button("Batalkan semua", disabled=not yakin):
                set_flash("success", f"{antrean.batalkan_semua(dosen)} nomor dibatalkan.")
                st.rerun()

    with st.expander("🧪 Demo"):
        q1, q2 = st.columns(2)
        jml = q1.number_input("Jumlah mahasiswa contoh", 1, 20, 5)
        if q2.button("Isi antrean contoh", use_container_width=True):
            antrean.isi_contoh(dosen, int(jml))
            st.rerun()
        if st.button("Hapus semua antrean hari ini (semua dosen)"):
            antrean.reset_hari_ini()
            st.rerun()


def page_admin_dosen():
    hero("Status & Jadwal Dosen", "Input kehadiran, ruangan, jam praktik, dan buka/tutup antrean tiap dosen.")
    flash()
    st.caption("Status kehadiran, catatan, dan buka/tutup antrean otomatis kembali ke 'Tidak hadir' setiap hari baru, "
               "jadi perlu diisi lagi tiap hari. Mahasiswa hanya bisa mengambil nomor jika dosen Hadir/Istirahat dan antrean dibuka.")
    a, b = st.columns(2)
    if a.button("Tandai semua dosen Hadir", use_container_width=True):
        for d in DOSEN_LIST:
            antrean.simpan_info(d, status="Hadir")
        set_flash("success", "Semua dosen ditandai Hadir.")
        st.rerun()
    if b.button("Tandai semua dosen Tidak hadir", use_container_width=True):
        for d in DOSEN_LIST:
            antrean.simpan_info(d, status="Tidak hadir")
        set_flash("success", "Semua dosen ditandai Tidak hadir.")
        st.rerun()
    for d in DOSEN_LIST:
        inf = antrean.info(d)
        with st.expander(f"{inf['nama']} · {inf['status']} · antrean {'dibuka' if inf['antrean_dibuka'] else 'ditutup'}"):
            with st.form(f"form_info_{d}"):
                nama = st.text_input("Nama dosen (tampil di aplikasi)", inf["nama"])
                status = st.radio("Status kehadiran hari ini", antrean.STATUS_DOSEN,
                                  index=antrean.STATUS_DOSEN.index(inf["status"]), horizontal=True)
                c1, c2, c3 = st.columns(3)
                ruangan = c1.text_input("Ruangan", inf["ruangan"])
                mulai = c2.time_input("Jam mulai", _t(inf["jam_mulai"]))
                selesai = c3.time_input("Jam selesai", _t(inf["jam_selesai"]))
                catatan = st.text_input("Catatan (mis. rapat, kembali jam 13.00)", inf["catatan"])
                buka = st.toggle("Antrean dibuka", inf["antrean_dibuka"])
                if st.form_submit_button("Simpan"):
                    if selesai <= mulai:
                        st.error("Jam selesai harus setelah jam mulai.")
                    else:
                        antrean.simpan_info(d, nama=nama.strip() or d, status=status, ruangan=ruangan.strip(),
                                            jam_mulai=mulai.strftime("%H:%M"), jam_selesai=selesai.strftime("%H:%M"),
                                            catatan=catatan.strip(), antrean_dibuka=buka)
                        set_flash("success", f"Data {nama.strip() or d} disimpan.")
                        st.rerun()


def page_admin_statistik():
    hero("Riwayat & Statistik", "Rekap antrean, durasi layanan nyata, dan ekspor data.")
    tk = antrean.semua()
    if not tk:
        st.info("Belum ada riwayat antrean.")
        return
    d = pd.DataFrame(tk)
    d["Dosen"] = d["dosen"].map(antrean.nama)
    d["Tunggu (mnt)"] = (pd.to_datetime(d["waktu_panggil"]) - pd.to_datetime(d["waktu_ambil"])).dt.total_seconds() / 60
    d["Durasi (mnt)"] = (pd.to_datetime(d["waktu_selesai"]) - pd.to_datetime(d["waktu_panggil"])).dt.total_seconds() / 60
    tanggal = st.selectbox("Tanggal", ["Semua"] + sorted(d["tanggal"].unique(), reverse=True))
    if tanggal != "Semua":
        d = d[d["tanggal"] == tanggal]
    selesai = d[d["status"] == "selesai"]
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        card("Total nomor antrean", len(d))
    with m2:
        card("Selesai dilayani", len(selesai))
    with m3:
        card("Rata-rata tunggu", f"{selesai['Tunggu (mnt)'].mean():.0f} mnt" if len(selesai) else "-")
    with m4:
        card("Rata-rata durasi", f"{selesai['Durasi (mnt)'].mean():.0f} mnt" if len(selesai) else "-")
    ringkas = d.groupby(["Dosen", "status"]).size().reset_index(name="Jumlah")
    st.plotly_chart(px.bar(ringkas, x="Dosen", y="Jumlah", color="status", barmode="stack",
                           title="Status nomor antrean per dosen"), use_container_width=True)
    tabel = d[["tanggal", "Dosen", "no", "nama", "nim", "status", "Tunggu (mnt)", "Durasi (mnt)"]].rename(
        columns={"tanggal": "Tanggal", "no": "No", "nama": "Nama", "nim": "NIM", "status": "Status"}).round(1)
    st.dataframe(tabel, use_container_width=True, hide_index=True)
    st.download_button("⬇ Unduh riwayat (CSV)", tabel.to_csv(index=False).encode("utf-8"),
                       "riwayat_antrean.csv", "text/csv")
    latih = antrean.dataset_latih()
    st.subheader("Dataset nyata untuk melatih model")
    st.caption(f"{len(latih)} baris data nyata siap pakai (tiket selesai, tanpa data demo). Simpan sebagai "
               "`data/antrean_konsultasi.csv` lalu restart aplikasi untuk melatih ulang model dengan data asli. "
               "Disarankan menunggu data cukup banyak (ratusan baris) sebelum menggantinya.")
    if len(latih):
        st.download_button("⬇ Unduh dataset latih (CSV)", latih.to_csv(index=False).encode("utf-8"),
                           "antrean_konsultasi.csv", "text/csv")


# ---------- main ----------
def main():
    if "user" not in st.session_state:
        page_auth()
        return
    user = st.session_state["user"]
    df = get_data()
    pipe, metrik, imp = get_model()

    with st.sidebar:
        st.markdown("## 🎓 Antre.in KRS")
        st.markdown(f"**{user['nama']}**  \n{user['nim']} · {user['jurusan']}")
        st.divider()
        admin = antrean.is_admin(user["email"])
        st.markdown("🛠 **Admin / Pengatur antrean**" if admin else "")
        daftar = ADMIN_MENU if admin else MENU
        menu = st.radio("Navigasi", daftar, label_visibility="collapsed")
        st.divider()
        if st.button("Keluar", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if menu == "Ringkasan Admin":
        page_admin_ringkasan()
    elif menu == "Kelola Antrean":
        page_admin_antrean()
    elif menu == "Status & Jadwal Dosen":
        page_admin_dosen()
    elif menu == "Riwayat & Statistik":
        page_admin_statistik()
    elif menu == "Dashboard":
        page_dashboard(user, df, pipe)
    elif menu == "Prediksi Antrean":
        page_prediksi(user, df, pipe)
    elif menu == "Perencana Konsultasi":
        page_planner(df, pipe)
    elif menu == "Perbandingan Dosen":
        page_perbandingan(df, pipe)
    elif menu == "Data & Model":
        page_data_model(df, metrik, imp)
    else:
        page_simulasi(user, df, pipe)


main()
