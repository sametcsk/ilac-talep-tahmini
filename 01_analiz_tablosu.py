"""Pazar verisi (IEIS) + makro (TCMB EVDS) + takvim degiskenlerini tek analiz tablosunda birlestirir.

Girdi : veri/pazar_toplam_aylik.csv, macro_monthly.csv (fetch_macro.py ile uretilir)
Cikti : veri/analiz_tablosu.csv  (57 ay: 2022-01 .. 2026-09)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import holidays

ROOT = Path(__file__).resolve().parent


def is_gunu_say(donem: pd.Period, tr_tatil) -> tuple[int, int]:
    """Ay icindeki resmi is gunu sayisi ve bayram (Ramazan/Kurban) nedeniyle kaybedilen hafta ici gunu."""
    gunler = pd.date_range(donem.start_time, donem.end_time.normalize(), freq="D")
    hafta_ici = [g for g in gunler if g.weekday() < 5]
    tatil = [g for g in hafta_ici if g.date() in tr_tatil]
    bayram = [g for g in tatil if any(k in tr_tatil.get(g.date()) for k in ("Ramazan Bayramı", "Kurban Bayramı"))]
    return len(hafta_ici) - len(tatil), len(bayram)


def main() -> None:
    pazar = pd.read_csv(ROOT / "veri" / "pazar_toplam_aylik.csv")
    pazar["donem"] = pd.PeriodIndex(pazar["donem"], freq="M")

    macro = pd.read_csv(ROOT / "macro_monthly.csv", parse_dates=["donem"])
    macro["donem"] = macro["donem"].dt.to_period("M")
    macro = macro[["donem", "usd_try", "eur_try", "tufe"]]

    df = pazar.merge(macro, on="donem", how="left")
    if df[["usd_try", "eur_try"]].isna().any().any():
        raise SystemExit("Kur verisinde eksik ay var; fetch_macro.py'yi tekrar calistirin (PERIOD='10y').")
    # TUFE (2003=100) serisi Ocak 2026'da bitti (baz yili 2025=100'e gecti): sonraki aylar NaN kalir
    if df["tufe"].isna().any():
        print(f"Uyari: TUFE {int(df['tufe'].isna().sum())} ayda eksik ({df.loc[df['tufe'].isna(), 'donem'].iloc[0]} sonrasi); "
              "reel deger ve dlog_tufe bu aylarda bos.")

    tr_tatil = holidays.TR(years=sorted({p.year for p in df["donem"]}))
    sayilar = [is_gunu_say(p, tr_tatil) for p in df["donem"]]
    df["is_gunu"] = [s[0] for s in sayilar]
    df["bayram_is_gunu_kaybi"] = [s[1] for s in sayilar]

    # log seviyeler ve buyume oranlari
    df["log_hacim"] = np.log(df["ilac_hacim_milyon_kutu"])
    df["log_deger"] = np.log(df["ilac_deger_milyon_tl"])
    df["log_fiyat"] = np.log(df["ort_fiyat_tl_kutu"])
    df["log_eur"] = np.log(df["eur_try"])
    df["log_usd"] = np.log(df["usd_try"])
    df["log_tufe"] = np.log(df["tufe"])
    df["log_is_gunu"] = np.log(df["is_gunu"])
    # makro buyume: ilk ay icin onceki ayi makro tablodan al (2021-12)
    m = macro.set_index("donem").sort_index()
    for ad, kol in (("dlog_eur", "eur_try"), ("dlog_usd", "usd_try"), ("dlog_tufe", "tufe")):
        d = np.log(m[kol]).diff()
        df[ad] = df["donem"].map(d)
    # reel (TUFE'ye gore deflate) deger: ilk ay = 100 bazli endeks degil, 2022-01 TL cinsinden
    df["reel_deger_2022_01_tl"] = df["ilac_deger_milyon_tl"] / (df["tufe"] / df["tufe"].iloc[0])
    df["donem"] = df["donem"].astype(str)
    out = ROOT / "veri" / "analiz_tablosu.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} satir, {df.shape[1]} sutun -> {out}")
    print(df[["donem", "is_gunu", "bayram_is_gunu_kaybi", "ilac_hacim_milyon_kutu", "ilac_deger_milyon_tl",
              "eur_try", "dlog_eur", "dlog_tufe"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
