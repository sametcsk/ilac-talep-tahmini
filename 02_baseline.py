"""Ilac pazari hacim tahmini: baseline modeller ve rolling-origin degerlendirme.

Hedef   : log(ilac hacmi, milyon kutu), aylik, 2022-01 .. 2026-09 (57 ay)
Egitim  : 2022-01'den test ayinin bir oncesine kadar (genisleyen pencere)
Test    : iki pencere, her ay icin 1 adim ileri tahmin (model her adimda yeniden kurulur)
          - "2024 (12 ay)"           : 2024-01 .. 2024-12   (en az 24 ay egitim)
          - "2025-01..2026-09 (21 ay)": ana pencere         (en az 36 ay egitim)
Girdi   : veri/analiz_tablosu.csv  (once 01_analiz_tablosu.py calistirilmali)
Cikti   : cikti/baseline_sonuclari.csv, cikti/hacim_tahmin.png
"""
import warnings
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import RidgeCV
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
(ROOT / "cikti").mkdir(exist_ok=True)


def duraganlik(df: pd.DataFrame) -> None:
    print("== Duraganlik testleri (ADF: H0 birim kok; KPSS: H0 duragan) ==")
    for c in ("log_hacim", "log_deger", "log_fiyat"):
        for ad, s in ((c, df[c]), ("fark(" + c + ")", df[c].diff().dropna())):
            adf_p = adfuller(s, regression="c", autolag="AIC")[1]
            kpss_p = kpss(s, regression="c", nlags="auto")[1]
            print(f"  {ad:22s} ADF p={adf_p:.3f}   KPSS p={kpss_p:.3f}")
    print("  Not: 57 gozlemde testlerin gucu dusuk; sonuclar yol gosterici.\n")


PENCERELER = {"2024 (12 ay)": ("2024-01", "2024-12"), "2025-01..2026-09 (21 ay)": ("2025-01", "2026-09")}
MODELLER = ("Naif (gecen ay)", "Mevsimsel naif (gecen yil ayni ay)", "OLS (takvim)", "SARIMAX (AR1 + takvim)",
            "Ridge (takvim + lag1)", "Ridge (takvim + lag1 + lag12)", "LightGBM (takvim + lag1 + ay)")


def tek_adim(df, y, X, ml, i):
    """i. ay icin, yalnizca 0..i-1 bilgisiyle 1 adim ileri tahminler (log olcek)."""
    tr = slice(0, i)
    out = {"Naif (gecen ay)": y.iloc[i - 1], "Mevsimsel naif (gecen yil ayni ay)": y.iloc[i - 12]}
    ols = sm.OLS(y.iloc[tr], sm.add_constant(X.iloc[tr])).fit()
    out["OLS (takvim)"] = float(ols.predict(sm.add_constant(X, has_constant="add").iloc[[i]]).iloc[0])
    sar = SARIMAX(y.iloc[tr], exog=X.iloc[tr], order=(1, 0, 0), trend="c").fit(disp=False)
    out["SARIMAX (AR1 + takvim)"] = float(sar.forecast(1, exog=X.iloc[[i]]).iloc[0])
    hedef = ml.iloc[[i]]
    egitim = ml.iloc[1:i]  # ilk satirda lag1 yok
    f = takvim_kol + ["lag1"]
    ridge = RidgeCV(alphas=np.logspace(-3, 2, 20)).fit(egitim[f], egitim["log_hacim"])
    out["Ridge (takvim + lag1)"] = float(ridge.predict(hedef[f])[0])
    egitim12 = ml.iloc[12:i]  # lag12 icin ilk 12 satir dusulur
    f12 = takvim_kol + ["lag1", "lag12"]
    ridge12 = RidgeCV(alphas=np.logspace(-3, 2, 20)).fit(egitim12[f12], egitim12["log_hacim"])
    out["Ridge (takvim + lag1 + lag12)"] = float(ridge12.predict(hedef[f12])[0])
    fg = takvim_kol + ["lag1", "ay"]
    gbm = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=4, min_child_samples=3,
                            verbose=-1, random_state=0).fit(egitim[fg], egitim["log_hacim"])
    out["LightGBM (takvim + lag1 + ay)"] = float(gbm.predict(hedef[fg])[0])
    return out


takvim_kol = ["log_is_gunu", "bayram_is_gunu_kaybi"]


def main() -> None:
    df = pd.read_csv(ROOT / "veri" / "analiz_tablosu.csv")
    df["donem"] = pd.PeriodIndex(df["donem"], freq="M")
    df = df.set_index("donem")
    duraganlik(df)

    y = df["log_hacim"]
    X = df[takvim_kol]
    ml = df.assign(lag1=y.shift(1), lag12=y.shift(12), ay=[p.month for p in df.index])

    satirlar, tahminler = [], {}
    for ad, (bas, son) in PENCERELER.items():
        test = [p for p in df.index if pd.Period(bas, "M") <= p <= pd.Period(son, "M")]
        tahmin = {m: [] for m in MODELLER}
        for t in test:
            for m, v in tek_adim(df, y, X, ml, df.index.get_loc(t)).items():
                tahmin[m].append(v)
        gercek = np.exp(y.loc[test].values)
        tahminler[ad] = (test, tahmin, gercek)
        for m, v in tahmin.items():
            p = np.exp(np.array(v))
            satirlar.append(dict(test_donemi=ad, model=m,
                                 rmse_milyon_kutu=round(float(np.sqrt(np.mean((p - gercek) ** 2))), 1),
                                 mape_pct=round(float(np.mean(np.abs(p / gercek - 1)) * 100), 1)))
    sonuc = pd.DataFrame(satirlar).sort_values(["test_donemi", "rmse_milyon_kutu"])
    sonuc.to_csv(ROOT / "cikti" / "baseline_sonuclari.csv", index=False)
    for ad in PENCERELER:
        print(f"== Hacim tahmini, 1 adim ileri, test = {ad} ==")
        print(sonuc[sonuc.test_donemi == ad].drop(columns="test_donemi").to_string(index=False))
        print()

    ols_tam = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    print("== Takvim etkisi (tum orneklem, HAC std. hata) ==")
    print(ols_tam.summary().tables[1])

    test, tahmin, gercek = tahminler["2025-01..2026-09 (21 ay)"]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    etiket = [str(p) for p in test]
    ax.plot(etiket, gercek, "k-o", lw=2, label="Gerceklesen")
    for ad in ("Naif (gecen ay)", "SARIMAX (AR1 + takvim)", "Ridge (takvim + lag1 + lag12)", "LightGBM (takvim + lag1 + ay)"):
        ax.plot(etiket, np.exp(tahmin[ad]), "--", marker=".", label=ad)
    ax.set_ylabel("Ilac hacmi (milyon kutu)")
    ax.set_title("1 adim ileri hacim tahmini, 2025-01..2026-09 (rolling-origin)")
    ax.tick_params(axis="x", rotation=60)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "cikti" / "hacim_tahmin.png", dpi=150)
    print("\nKaydedildi: cikti/baseline_sonuclari.csv, cikti/hacim_tahmin.png")


if __name__ == "__main__":
    main()
