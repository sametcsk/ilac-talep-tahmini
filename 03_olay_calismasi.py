"""Ilac avro degeri guncellemelerinin ortalama fiyat ve hacme etkisi (olay calismasi).

Fikir  : Ilac fiyatlari aylik surekli degil, duzenleyici "avro degeri" guncellemeleriyle basamak basamak degisir.
         Bu yuzden kur ile aylik regresyon yerine, guncellemenin yururluge girdigi aya gore bir olay calismasi yapilir.
Girdi  : veri/avro_degeri_guncellemeleri.csv (9 guncelleme, 8 olay kumesi), veri/analiz_tablosu.csv
Cikti  : cikti/olay_calismasi_sonuclari.csv, cikti/olay_calismasi.png

Modeller
  Fiyat : dlog(ort. kutu fiyati)_t = c + sum_{k=0..3} b_k * dlog(avro degeri guncellemesi)_{t-k} + ay etkileri
          kumulatif gecis = sum b_k   (1 = tam gecis)
  Hacim : log(hacim)_t = takvim + ay etkileri + trend + b_-1*olay_{t+1} + b_0*olay_t + b_1*olay_{t-1} + b_2*olay_{t-2}
          (olay_{t+1} = onceki ay stoklama; olay_{t-1}, olay_{t-2} = sonraki aylarda dusus)
Standart hatalar HAC (Newey-West, 3 gecikme); olay sayisi cok az oldugu icin permutasyon testi ve
"bir olayi disarida birak" saglamlik kontrolu de verilir.
"""
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
KUMELER = ["2022-02", "2022-07", "2022-12", "2023-07", "2023-12", "2024-10", "2025-12", "2026-03"]  # 2026-03 ve 04 tek kume
GECIKME = 4


def veri_hazirla():
    ev = pd.read_csv(ROOT / "veri" / "avro_degeri_guncellemeleri.csv", parse_dates=["yururluk_tarihi"])
    a = pd.read_csv(ROOT / "veri" / "analiz_tablosu.csv")
    a["donem"] = pd.PeriodIndex(a["donem"], freq="M")
    a = a.set_index("donem")
    a["dev"] = 0.0  # yururluk ayindaki log avro degeri degisimi
    for _, r in ev.iterrows():
        a.loc[r.yururluk_tarihi.to_period("M"), "dev"] += np.log(r.avro_degeri_tl / r.onceki_deger_tl)
    a["dlp"] = a["log_fiyat"].diff()
    ay = pd.get_dummies(pd.Series([p.month for p in a.index], index=a.index), prefix="m", drop_first=True).astype(float)
    return a, ay


def fiyat_modeli(a, ay, dev=None, sezon=True, dis=None):
    dev = a["dev"] if dev is None else dev
    E = pd.concat([dev.shift(k).rename(f"l{k}") for k in range(GECIKME)], axis=1)
    X = sm.add_constant(pd.concat([E, ay], axis=1) if sezon else E)
    m = pd.concat([a["dlp"], X], axis=1).dropna()
    if dis is not None:
        m = m[~m.index.isin(dis)]
    return sm.OLS(m["dlp"], m[X.columns]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}), [f"l{k}" for k in range(GECIKME)]


def hacim_modeli(a, ay, dev=None, dis=None):
    dev = a["dev"] if dev is None else dev
    taban = pd.concat([a[["log_is_gunu", "bayram_is_gunu_kaybi"]], ay], axis=1)
    taban["t"] = np.arange(len(a))
    E = pd.concat([dev.shift(k) for k in (-1, 0, 1, 2)], axis=1)
    E.columns = ["onceki_ay", "ay0", "sonraki_ay1", "sonraki_ay2"]
    X = sm.add_constant(pd.concat([taban, E], axis=1))
    m = pd.concat([a["log_hacim"], X], axis=1).dropna()
    if dis is not None:
        m = m[~m.index.isin(dis)]
    return sm.OLS(m["log_hacim"], m[X.columns]).fit(cov_type="HAC", cov_kwds={"maxlags": 3}), list(E.columns)


def kumulatif(r, cols):
    L = np.zeros(len(r.params))
    for c in cols:
        L[list(r.params.index).index(c)] = 1
    t = r.t_test(L)
    return float(t.effect[0]), float(t.sd[0][0]), float(t.pvalue)


def kume_disi(a, kume):
    c = pd.Period(kume, "M")
    grp = [c, c + 1] if kume == "2026-03" else [c]
    dev = a["dev"].copy()
    dis = set()
    for g in grp:
        dev[g] = 0.0
        dis |= {g + k for k in range(-1, 4)}
    return dev, dis


def main() -> None:
    a, ay = veri_hazirla()
    satir = []

    print("== FIYAT: dlog(ort. kutu fiyati) ~ avro degeri guncellemesi (gecikmeler 0..3) ==")
    for sezon in (False, True):
        r, cols = fiyat_modeli(a, ay, sezon=sezon)
        etiket = "ay etkili" if sezon else "ay etkisiz"
        for c in cols:
            satir.append(dict(model=f"fiyat ({etiket})", terim=c, katsayi=r.params[c], se=r.bse[c], p=r.pvalues[c]))
        e, s, p = kumulatif(r, cols)
        satir.append(dict(model=f"fiyat ({etiket})", terim="KUMULATIF", katsayi=e, se=s, p=p))
        print(f"  {etiket:11s}: " + "  ".join(f"b{k}={r.params[c]:.2f}" for k, c in enumerate(cols)) +
              f"   kumulatif={e:.2f} (se {s:.2f}, p={p:.3f}), n={int(r.nobs)}")

    # permutasyon: ayni buyuklukteki guncellemeleri rastgele aylara koy
    rng = np.random.default_rng(0)
    mag = a["dev"][a["dev"] > 0].values
    n = len(a)

    def stat(dev):
        r, cols = fiyat_modeli(a, ay, dev=pd.Series(dev, index=a.index), sezon=False)
        return sum(r.params[c] for c in cols)

    gozlenen = stat(a["dev"].values)
    sim = []
    for _ in range(1000):
        dv = np.zeros(n)
        pos = rng.choice(np.arange(1, n - 1), size=len(mag), replace=False)
        dv[pos] = rng.permutation(mag)
        sim.append(stat(dv))
    sim = np.array(sim)
    p_perm = float((sim >= gozlenen).mean())
    print(f"  permutasyon (ay etkisiz): gozlenen kumulatif {gozlenen:.2f}, plasebo ort. {sim.mean():.2f} (sd {sim.std():.2f}), p={p_perm:.3f}")
    satir.append(dict(model="fiyat (permutasyon)", terim="KUMULATIF", katsayi=gozlenen, se=sim.std(), p=p_perm))

    print("\n== FIYAT saglamlik: bir olay kumesi disarida birakilir (kumulatif gecis, ay etkili) ==")
    loo = {}
    for k in KUMELER:
        dev, dis = kume_disi(a, k)
        r, cols = fiyat_modeli(a, ay, dev=dev, sezon=True, dis=dis)
        loo[k] = sum(r.params[c] for c in cols)
        satir.append(dict(model="fiyat (LOO)", terim=f"-{k}", katsayi=loo[k], se=np.nan, p=np.nan))
    print("  " + "  ".join(f"-{k}: {v:.2f}" for k, v in loo.items()), f"\n  aralik: {min(loo.values()):.2f} .. {max(loo.values()):.2f}")

    print("\n== HACIM: log(hacim) ~ takvim + ay + trend + olay (onceki ay, ay 0, sonraki 1-2 ay) ==")
    r, cols = hacim_modeli(a, ay)
    for c in cols:
        satir.append(dict(model="hacim", terim=c, katsayi=r.params[c], se=r.bse[c], p=r.pvalues[c]))
        print(f"  {c:12s} {r.params[c]:7.3f}  se {r.bse[c]:.3f}  p {r.pvalues[c]:.3f}")
    e, s, p = kumulatif(r, ["sonraki_ay1", "sonraki_ay2"])
    satir.append(dict(model="hacim", terim="SONRAKI_1+2", katsayi=e, se=s, p=p))
    print(f"  sonraki 1+2 ay toplami: {e:.2f} (se {s:.2f}, p={p:.3f}); n={int(r.nobs)}")
    for k in KUMELER:
        dev, dis = kume_disi(a, k)
        rr, _ = hacim_modeli(a, ay, dev=dev, dis=dis)
        satir.append(dict(model="hacim (LOO)", terim=f"-{k}: onceki_ay / sonraki_1+2",
                          katsayi=rr.params["sonraki_ay1"] + rr.params["sonraki_ay2"], se=np.nan, p=np.nan))
    pd.DataFrame(satir).round(4).to_csv(ROOT / "cikti" / "olay_calismasi_sonuclari.csv", index=False)

    # ---- grafik: olay zamaninda ortalama tepki (iki ayri panel, tek eksen) ----
    X = sm.add_constant(pd.concat([a[["log_is_gunu", "bayram_is_gunu_kaybi"]], ay], axis=1).assign(t=np.arange(len(a))))
    dis_m = ~(a["dev"].shift(-1).fillna(0).gt(0) | a["dev"].gt(0) | a["dev"].shift(1).fillna(0).gt(0) | a["dev"].shift(2).fillna(0).gt(0))
    ref = sm.OLS(a["log_hacim"][dis_m], X[dis_m]).fit()  # olay disi aylarla takvim+mevsim+trend
    anormal = (a["log_hacim"] - ref.predict(X)) * 100
    oz = a["dlp"] * 100
    ks = range(-3, 5)
    fig, eksen = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
    for ax, seri, baslik in ((eksen[0], oz, "Ortalama kutu fiyati, aylik log degisim (puan)"),
                             (eksen[1], anormal, "Hacim, olay disi aylara gore sapma (log puan)")):
        mat = []
        for c in KUMELER:
            c = pd.Period(c, "M")
            satir_ = [seri.get(c + k, np.nan) for k in ks]
            mat.append(satir_)
            ax.plot(list(ks), satir_, color="#b8bcc4", lw=1)
        ort = np.nanmean(np.array(mat), axis=0)
        ax.plot(list(ks), ort, color="#1f5fbf", lw=2.5, marker="o", ms=6)
        ax.axvline(0, color="#6b7280", lw=1, ls=":")
        ax.axhline(0, color="#6b7280", lw=0.8)
        ax.set_title(baslik, fontsize=10, loc="left")
        ax.set_xlabel("Guncellemenin yururluge girdigi aya gore ay (0 = guncelleme ayi)")
        ax.grid(axis="y", color="#e5e7eb", lw=0.7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.text(ks[-1], ort[-1], "  ortalama", color="#1f5fbf", fontsize=8, va="center")
    eksen[0].text(-3, eksen[0].get_ylim()[1] * 0.92, "gri: tek tek 8 olay", color="#6b7280", fontsize=8)
    fig.suptitle("Avro degeri guncellemesi etrafinda fiyat ve hacim", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(ROOT / "cikti" / "olay_calismasi.png", dpi=150)
    print("\nKaydedildi: cikti/olay_calismasi_sonuclari.csv, cikti/olay_calismasi.png")


if __name__ == "__main__":
    main()
