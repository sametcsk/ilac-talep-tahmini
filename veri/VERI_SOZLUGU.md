# Veri sözlüğü

Kaynak: İlaç Endüstrisi İşverenler Sendikası (İEİS), Pazar Analiz Raporları, Ocak 2023 – Eylül 2026 (kaynak veri: IQVIA, SGK). Sayılar raporlardan çıkarılmıştır; doğrulama adımları için ana README'ye bakın.

## pazar_toplam_aylik.csv (57 satır, 2022-01 … 2026-09)
| Alan | Anlam |
|---|---|
| donem | YYYY-AA |
| rapor_yili, rapor_ayi | Değerin alındığı rapor. Kural: o ayı içeren en güncel rapor (ertesi yılın raporu varsa onun "önceki yıl" sütunu) |
| tarafi | `onceki_yil_sutunu` veya `cari_yil_sutunu` (değerin raporun hangi sütunundan alındığı) |
| ilac_deger_milyon_tl | İlaç pazarı değeri, nominal, milyon TL |
| ilac_hacim_milyon_kutu | İlaç pazarı hacmi, milyon kutu |
| ort_fiyat_tl_kutu | değer / hacim (ürün karması etkisi içerir) |
| imal_/ithal_ ..._turetilmis | Ocak–X kümülatif farkından türetilmiş aylık imal/ithal değer ve hacim (rapordaki değer değildir; kutuda ±1-2 yuvarlama gürültüsü vardır) |
| ithal_pay_deger_pct_turetilmis | İthal ürünlerin değer payı (%), türetilmiş |

## tedavi_gruplari_uzun.csv
`donem, grup, olcu, deger, rapor_yili, rapor_ayi, kaynak, uyari`. Her ay için raporda listelenen ilk 5 grup (kutu ve değer ayrı); her hücre için o ayı içeren en güncel rapor kullanılır. `olcu`: `hacim_milyon_kutu` veya `deger_milyon_tl`. `kaynak`: `metin` (PDF metin katmanı) veya `goruntu_elle` (tablosu görüntü olan raporlar, gözle okundu); `_onceki_yil` eki, değerin ertesi yıl raporunun önceki yıl sütunundan geldiğini gösterir. `uyari` doluysa o seri için ihtiyat gerekir (Antiromatizmal vintage kırılması; Onkoloji TL revizyonları).
Şubat 2025 ve Haziran 2025 raporlarının tabloları bayat olduğu için kullanılmadı (README).

## tedavi_gruplari_dengeli.csv (57 satır, 5 seri)
57 ayın tamamında ilk 5'te yer alan, vintage kırılması olmayan seriler: `antibiyotik_kutu, kardiyovaskuler_kutu, soguk_alginligi_kutu, onkoloji_tl, kardiyovaskuler_tl`.

## revizyon_karsilastirma.csv
İki rapor sürümünde de bulunan 33 ay için aylık değer ve hacmin karşılaştırması (eski rapor = kendi yılının raporu, yeni rapor = ertesi yılın "önceki yıl" sütunu).

## analiz_tablosu.csv
`01_analiz_tablosu.py` çıktısı: pazar serisi + kur/TÜFE + `is_gunu`, `bayram_is_gunu_kaybi`, log serileri ve aylık log değişimler. TÜFE 2026-02'den itibaren boştur.

## avro_degeri_guncellemeleri.csv
İlaç fiyatlandırmasında kullanılan avro değerinin (TL) güncellemeleri: `yayim_tarihi` (Resmî Gazete), `yururluk_tarihi`, `avro_degeri_tl`, `onceki_deger_tl`, `artis_pct`, `kaynak_notu`. Kaynak: Cumhurbaşkanı kararları (Resmî Gazete sayıları not sütununda). Şubat 2022 yürürlük tarihi haber kaynaklarına dayanır (resmî metin doğrulanmadı). 2026'da karar iki aşamalıdır (13 Mart ve 1 Nisan).
