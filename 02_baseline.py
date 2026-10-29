"""Ilac pazari hacim tahmini: baseline modeller ve rolling-origin degerlendirme.

Hedef   : log(ilac hacmi, milyon kutu), aylik
Egitim  : 2022-01'den test ayinin bir oncesine kadar (genisleyen pencere)
Test    : 2024-01 .. 2024-12, her ay icin 1 adim ileri tahmin (model her adimda yeniden kurulur)
Girdi   : veri/analiz_tablosu.csv  (once 01_analiz_tablosu.py calistirilmali)
Cikti   : cikti/baseline_sonuclari.csv, cikti/hacim_tahmin_2024.png
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
    print("  Not: 36 gozlemde testlerin gucu dusuk; sonuclar yol gosterici.\n")


def main() -> None:
    df = pd.read_csv(ROOT / "veri" / "analiz_tablosu.csv")
    df["donem"] = pd.PeriodIndex(df["donem"], freq="M")
    df = df.set_index("donem")
    duraganlik(df)

    y = df["log_hacim"]
    takvim = ["log_is_gunu", "bayram_is_gunu_kaybi"]
    X = df[takvim]
    ml = df.assign(lag1=y.shift(1), ay=[p.month for p in df.index])
    test = [p for p in df.index if p.year == 2024]
    tahmin = {k: [] for k in ("Naif (gecen ay)", "Mevsimsel naif (gecen yil ayni ay)", "OLS (takvim)",
                              "SARIMAX (AR1 + takvim)", "Ridge (takvim + lag1)", "LightGBM (takvim + lag1 + ay)")}
    for t in test:
        i = df.index.get_loc(t)
        tr = slice(0, i)
        tahmin["Naif (gecen ay)"].append(y.iloc[i - 1])
        tahmin["Mevsimsel naif (gecen yil ayni ay)"].append(y.iloc[i - 12])
        ols = sm.OLS(y.iloc[tr], sm.add_constant(X.iloc[tr])).fit()
        tahmin["OLS (takvim)"].append(float(ols.predict(sm.add_constant(X, has_constant="add").iloc[[i]]).iloc[0]))
        sar = SARIMAX(y.iloc[tr], exog=X.iloc[tr], order=(1, 0, 0), trend="c").fit(disp=False)
        tahmin["SARIMAX (AR1 + takvim)"].append(float(sar.forecast(1, exog=X.iloc[[i]]).iloc[0]))
        egitim, hedef = ml.iloc[1:i], ml.iloc[[i]]  # ilk satirda lag1 yok
        f_ridge = takvim + ["lag1"]
        ridge = RidgeCV(alphas=np.logspace(-3, 2, 20)).fit(egitim[f_ridge], egitim["log_hacim"])
        tahmin["Ridge (takvim + lag1)"].append(float(ridge.predict(hedef[f_ridge])[0]))
        f_gbm = takvim + ["lag1", "ay"]
        gbm = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=4, min_child_samples=3,
                                verbose=-1, random_state=0).fit(egitim[f_gbm], egitim["log_hacim"])
        tahmin["LightGBM (takvim + lag1 + ay)"].append(float(gbm.predict(hedef[f_gbm])[0]))

    gercek = np.exp(y.loc[test].values)
    satirlar = []
    for ad, v in tahmin.items():
        p = np.exp(np.array(v))
        satirlar.append(dict(model=ad, rmse_milyon_kutu=round(float(np.sqrt(np.mean((p - gercek) ** 2))), 1),
                             mape_pct=round(float(np.mean(np.abs(p / gercek - 1)) * 100), 1)))
    sonuc = pd.DataFrame(satirlar).sort_values("rmse_milyon_kutu")
    sonuc.to_csv(ROOT / "cikti" / "baseline_sonuclari.csv", index=False)
    print("== Hacim tahmini, 1 adim ileri, test = 2024 (12 ay) ==")
    print(sonuc.to_string(index=False))

    ols_tam = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
    print("\n== Takvim etkisi (tum orneklem, HAC std. hata) ==")
    print(ols_tam.summary().tables[1])

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot([str(p) for p in test], gercek, "k-o", lw=2, label="Gerceklesen")
    for ad in ("Naif (gecen ay)", "SARIMAX (AR1 + takvim)", "LightGBM (takvim + lag1 + ay)"):
        ax.plot([str(p) for p in test], np.exp(tahmin[ad]), "--", marker=".", label=ad)
    ax.set_ylabel("Ilac hacmi (milyon kutu)")
    ax.set_title("1 adim ileri hacim tahmini, 2024 (rolling-origin)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "cikti" / "hacim_tahmin_2024.png", dpi=150)
    print("\nKaydedildi: cikti/baseline_sonuclari.csv, cikti/hacim_tahmin_2024.png")


if __name__ == "__main__":
    main()
