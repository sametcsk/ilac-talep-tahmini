# Veri sözlüğü

Kaynak: İlaç Endüstrisi İşverenler Sendikası (İEİS), Pazar Analiz Raporları, Ocak 2023 – Aralık 2024 (kaynak veri: IQVIA, SGK). Sayılar raporlardan çıkarılmıştır; doğrulama adımları için ana README'ye bakın.

## pazar_toplam_aylik.csv (36 satır)
| Alan | Anlam |
|---|---|
| donem | YYYY-AA |
| rapor_yili, rapor_ayi | Değerin alındığı rapor. 2022 ayları: 2023 raporlarının "önceki yıl" sütunu; 2023 ayları: 2024 raporlarının "önceki yıl" sütunu (en güncel revizyon); 2024 ayları: 2024 raporları |
| ilac_deger_milyon_tl | İlaç pazarı değeri, nominal, milyon TL |
| ilac_hacim_milyon_kutu | İlaç pazarı hacmi, milyon kutu |
| ort_fiyat_tl_kutu | değer / hacim (karma etkisi içerir) |
| imal_/ithal_ ..._turetilmis | Ocak–X kümülatif farkından türetilmiş aylık imal/ithal değer ve hacim (rapordaki değer değildir) |
| ithal_pay_deger_pct_turetilmis | İthal ürünlerin değer payı (%), türetilmiş |

## tedavi_gruplari_uzun.csv
`donem, grup, olcu, deger, rapor_yili, rapor_ayi, kaynak, uyari`. Her ay için raporda listelenen ilk 5 grup (kutu ve değer ayrı). `olcu`: `hacim_milyon_kutu` veya `deger_milyon_tl`. `kaynak`: `metin` (PDF metin katmanı) veya `goruntu_elle` (Mayıs 2023, gözle okundu). `uyari` doluysa o seri için ihtiyat gerekir.

## tedavi_gruplari_dengeli.csv (36 satır, 6 seri)
24 raporun hepsinde yer alan, vintage kırılması olmayan seriler: `antibiyotik_kutu, kardiyovaskuler_kutu, soguk_alginligi_kutu, onkoloji_tl, antibiyotik_tl, kardiyovaskuler_tl`.

## revizyon_karsilastirma_2023.csv
2023 ayları için 2023 ve 2024 raporlarındaki değerlerin karşılaştırması (aylık değer ve hacim, yüzde fark).

## analiz_tablosu.csv
`01_analiz_tablosu.py` çıktısı: pazar serisi + kur/TÜFE + `is_gunu`, `bayram_is_gunu_kaybi`, log serileri ve aylık log değişimler.
