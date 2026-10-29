"""TCMB EVDS3 üzerinden aylık makro değişkenleri çeker ve macro_monthly.csv olarak kaydeder.

Gereksinim: ücretsiz EVDS API anahtarı (https://evds3.tcmb.gov.tr) -> EVDS_API_KEY ortam değişkeni.
Not: Eski evds2 API'si kapatıldı; bu yüzden borsapy (evds3 desteği) kullanılıyor.
Seri kodlarını EVDS arayüzünden doğrula; kodlar değişebilir.
"""
import os
import sys

import pandas as pd
import borsapy as bp

SERIES = {
    "usd_try": "TP.DK.USD.S.YTL",   # USD/TRY döviz satış (günlük)
    "eur_try": "TP.DK.EUR.S.YTL",   # EUR/TRY döviz satış (günlük)
    "tufe": os.environ.get("EVDS_TUFE_CODE", "TP.FG.J0"),   # TÜFE genel endeks (aylık),             # TÜFE genel endeks (aylık)
}
PERIOD = "10y"


def main() -> None:
    key = os.environ.get("EVDS_API_KEY")
    if not key:
        sys.exit("EVDS_API_KEY ortam değişkeni tanımlı değil.")
    bp.set_evds_key(key)

    frames = []
    for name, code in SERIES.items():
        try:
            df = bp.evds_series(code, period=PERIOD)
        except Exception as exc:  # seri kodu veya erişim sorunu
            print(f"[uyarı] {name} ({code}) çekilemedi: {exc}")
            continue
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        s = df.iloc[:, 0].astype(float).rename(name)
        # günlük seriyi aylık ortalamaya çevir; aylık seri zaten aylık kalır
        frames.append(s.resample("MS").mean())

    if not frames:
        sys.exit("Hiç seri çekilemedi.")

    out = pd.concat(frames, axis=1)
    out["tufe_yoy_pct"] = out["tufe"].pct_change(12) * 100 if "tufe" in out else None
    out.to_csv("macro_monthly.csv", index_label="donem")
    print(out.tail())
    print("Kaydedildi: macro_monthly.csv")


if __name__ == "__main__":
    main()
