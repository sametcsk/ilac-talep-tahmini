# İlaç Talep Tahmini: Ekonometri + Makine Öğrenmesi

Türkiye ilaç pazarında **aylık hacim (milyon kutu) ve değer (milyon TL)** serisini, takvim etkileri (iş günü, bayramlar) ve makro değişkenlerle (kur, TÜFE) modelleyen bir talep tahmini projesi. Klasik ekonometri (OLS/SARIMAX) ile ML (Ridge/LightGBM) aynı rolling-origin protokolüyle karşılaştırılır.

## Neden bu proje?
Türkiye'de ilaç fiyatları büyük ölçüde devlet tarafından belirlenir (referans fiyat / avro değeri sistemi). Bu yüzden **kur, enflasyon ve düzenleyici değişiklikler** değer serisini sürüklerken, **hacim** serisi esas olarak takvim ve talep dinamiklerini yansıtır. Veri bunu net gösteriyor:

| | 2022 | 2023 | 2024 | 2025 | Ocak–Eylül 2026 |
|---|---|---|---|---|---|
| Hacim (milyon kutu) | 2.556 | 2.672 | 2.570 | 2.655 | 1.916 |
| Değer (milyar TL, nominal) | 109,8 | 211,0 | 324,6 | 431,0 | 451,8 |

Ocak–Eylül karşılaştırmasında 2022'den 2026'ya değer yaklaşık **6,1 kat** arttı, hacim yalnızca **%3** büyüdü. Ortalama kutu fiyatı (ürün karması etkisi dahil) Ocak 2022'de 28 TL iken Eylül 2026'da 246 TL; aynı sürede EUR/TRY 15,3'ten 56,0'a (3,7 kat) çıktı. Fiyat artışı yalnızca kurla açıklanmıyor, ürün karması ve düzenleyici fiyat güncellemeleri de içeriyor.

## Veri
| Veri | Kaynak | Dönem | Dosya |
|---|---|---|---|
| Toplam ilaç pazarı (değer, hacim, imal/ithal) | İEİS Pazar Analiz Raporları (kaynak veri: IQVIA, SGK) | 2022-01 … 2026-09 (**57 ay**) | `veri/pazar_toplam_aylik.csv` |
| Tedavi grubu serileri | Aynı raporlar | 57 ay | `veri/tedavi_gruplari_dengeli.csv`, `veri/tedavi_gruplari_uzun.csv` |
| USD/TRY, EUR/TRY, TÜFE | TCMB EVDS 3 | aylık | `macro_monthly.csv` (`fetch_macro.py`, API anahtarı gerekir) |
| Resmi tatiller | `holidays` paketi (TR) | | `01_analiz_tablosu.py` içinde |

Alan tanımları: `veri/VERI_SOZLUGU.md`. **Kaynak:** İlaç Endüstrisi İşverenler Sendikası (İEİS), Pazar Analiz Raporları, Ocak 2023 – Eylül 2026 (45 rapor; her rapor önceki yılın aynı ayını da içerdiği için seri 2022'den başlar). Raporların hakkı İEİS'e aittir; repoda PDF yoktur, yalnızca raporlardan çıkarılan sayılar vardır.

### Veriler nasıl çıkarıldı ve nasıl doğrulandı
Raporlar tek sayfalık infografiklerdir. Tedavi grubu tabloları metin katmanından, toplam pazar grafikleri OCR ile okundu. Her değer şu kontrollerden geçti:
1. **İmal + ithal = toplam** (kümülatif, her rapor için, yuvarlama toleransıyla)
2. **Rapordaki yüzde değişim etiketleri** ile hesaplanan değişim uyumu
3. **Ocak–X kümülatifinin ay ay sürekliliği** (kümülatif farkı = aylık değer)
4. **Rapor sürümleri arası karşılaştırma:** her ay iki raporda görünür (kendi raporunda ve ertesi yılın "önceki yıl" sütununda). 33 ayın karşılaştırmasında fark TL'de en fazla %0,75 (medyan %0,26), kutuda en fazla %0,81 (`veri/revizyon_karsilastirma.csv`)
5. OCR'ın yanlış okuduğu veya kaçırdığı grafik etiketleri (17 raporda) ve tablosu görüntü olarak gömülü raporlar (Mayıs 2023, Mayıs 2025, Ağustos 2026) **gözle okunup düzeltildi.**

**Sürüm kuralı:** her ay için en güncel rapor kullanılır (ör. 2024 ayları 2025 raporlarının "önceki yıl" sütunundan, Ocak–Eylül 2025 ayları 2026 raporlarından). Yalnızca henüz ertesi yıl raporu çıkmamış aylar (Ekim 2025 sonrası ve 2026) ilk yayın sürümündedir.

**İEİS raporlarındaki iki bayat tablo:** Şubat 2025 raporunun tedavi grubu tablosu hâlâ "Şubat 2023 | 2024" başlığını taşıyor (güncellenmemiş), Haziran 2025 raporunun tablosu ise Mayıs 2025 tablosunun kopyası. Bu iki raporun tabloları **kullanılmadı**; o ayların grup değerleri 2026 raporlarının "önceki yıl" sütunundan alındı. Toplam pazar grafikleri bu iki raporda doğru.

## Veri sınırlılıkları (dürüstçe)
- **57 ay**, ayrıca test penceresi 21 ay. Model sıralamaları bu yüzden istatistiksel olarak ayırt edilemiyor (bkz. bulgular).
- Değerler **nominal TL**; hacim "ilaç" kategorisidir (özel tıbbi amaçlı gıda ve sağlık ürünleri hariç).
- **TÜFE:** EVDS'de TÜFE'nin 2003=100 serisi Ocak 2026'da sona erdi (baz yılı 2025=100'e geçildi); Şubat 2026 sonrası için yeni seri kodu bulunamadı. Reel değer ve `dlog_tufe` 2026-02'den itibaren boş. Kur serileri tam.
- **Tedavi grupları:** raporlar her ay yalnızca ilk 5 grubu verir; bir grup ilk 5'ten düşerse o ay eksik kalır. Dengeli panelde 57 ayın tamamında bulunan 5 seri var: kutu için Antibiyotikler, Kardiyovasküler, Soğuk algınlığı/öksürük; değer için Onkoloji, Kardiyovasküler. Diğer gruplar (ör. Antibiyotikler TL: 52/57, Kanla ilgili ilaçlar TL: 54/57, Antidiabetikler TL: 44/57) yalnızca uzun dosyada.
- **Antiromatizmal serisinde vintage kırılması var:** 2024 raporları 2023 değerlerini 2023 raporlarından yaklaşık %20 yüksek veriyor, muhtemelen grup tanımı değişti. Dengeli panelde **yok**, uzun dosyada uyarıyla duruyor.
- **Onkoloji (TL)** rapor sürümleri arasında %1–4 revize ediliyor; 2026 raporları 2025 değerlerini yaklaşık %3 aşağı çekti. Ekim–Aralık 2025 için revize sürüm henüz yok, bu aylar uzun dosyada uyarıyla işaretli.
- **Aylık imal/ithal değerleri türetilmiştir** (kümülatif farklarından), rapordaki değerler değildir.
- **İş günü değişkeni yalnızca resmi tatilleri içerir**, idari izinle uzatılan köprü günleri (ör. 9 günlük bayram tatilleri) dahil değildir.
- Sağlık Bakanlığı açıklamasına göre kutuların yaklaşık %17'si İTS'ye bildirilmeden satılmıştır; resmi satış verisi gerçek tüketimi tam yansıtmayabilir.

## İlk bulgular
Hacim tahmini, 1 adım ileri; model her ay yalnızca o aya kadarki veriyle yeniden kurulur (genişleyen pencere). RMSE milyon kutu cinsinden, MAPE yüzde.

| Model | Test 2025-01…2026-09 (21 ay) RMSE / MAPE | Test 2024 (12 ay) RMSE / MAPE |
|---|---|---|
| LightGBM (takvim + lag1 + ay) | **16,6** / %5,6 | 20,8 / %8,2 |
| Ridge (takvim + lag1 + lag12) | 17,6 / %5,7 | 19,7 / %7,3 |
| SARIMAX (AR1 + takvim) | 19,8 / %6,2 | **17,3** / %5,9 |
| OLS (takvim) | 20,0 / %6,4 | 17,4 / %6,0 |
| Ridge (takvim + lag1) | 20,3 / %6,6 | 17,8 / %5,8 |
| Mevsimsel naif (geçen yıl aynı ay) | 21,5 / %7,3 | 30,3 / %11,9 |
| Naif (geçen ay) | 30,8 / %11,4 | 28,3 / %11,0 |

- **Takvim çok açıklayıcı:** iş günü sayısının hacim esnekliği ≈ 1,2 (HAC p < 0,001). Bayram nedeniyle kaybedilen iş günü katsayısı küçük ve pozitif (0,040; p = 0,045). İş günü zaten bayramı içerdiği için bu, bayram öncesi stoklama gibi bir etkiye işaret edebilir ama bu örneklemde kesin söylenemez.
- **Mevsimsellik var:** Eylül–Ekim hacim ortalaması (≈ 245 milyon kutu) Nisan–Ağustos'un (≈ 205) belirgin üstünde. Eğitim penceresi 36 ayı geçince mevsimi öğrenen modeller (LightGBM, `lag12`'li Ridge) öne geçiyor; 24–35 aylık eğitimde ise basit doğrusal modeller daha iyiydi.
- **Küçük farklar anlamlı değil:** ana pencerede LightGBM ile SARIMAX arasındaki fark Diebold–Mariano testinde anlamsız (p = 0,25), LightGBM–Ridge(`lag12`) için p = 0,68. LightGBM naif tahminden anlamlı biçimde iyi (p < 0,01), mevsimsel naiften farkı anlamsız (p = 0,14). Yani sonuç "ML ekonometriyi yendi" değil; **takvim ve mevsim bilgisi olan her model işe yarıyor, 21 aylık testle aralarında sıralama yapılamıyor.**
- **Açıklanamayan kısım:** Eylül 2025 (277 milyon kutu) ve Temmuz 2026 (184) en büyük hatalar, bunlar takvimle ve ay etkisiyle açıklanmıyor. Eylül 2025 dışarıda bırakılırsa RMSE'ler 14,5 (LightGBM) ile 16,9 (OLS) arasına iniyor. Grafik: `cikti/hacim_tahmin.png`.
- **Kur geçişkenliği henüz kanıtlanmadı:** ortalama kutu fiyatı üzerine aylık gecikmeli regresyon (36 aylık ilk örneklemde) kararsız ve ekonomik olarak anlamsız katsayılar verdi. Fiyatlar aylık sürekli değil, düzenleyici avro değeri güncellemeleriyle basamak basamak değişiyor; bu yüzden olay çalışması (event study) gerekiyor. Sonuç olarak sunulmuyor.

## Çalıştırma
```
pip install -r requirements.txt
$env:EVDS_API_KEY="..."        # PowerShell; anahtarı koda/repoya yazmayın
python fetch_macro.py           # macro_monthly.csv üretir
python 01_analiz_tablosu.py     # veri/analiz_tablosu.csv
python 02_baseline.py           # cikti/baseline_sonuclari.csv + cikti/hacim_tahmin.png
```

## Yol haritası
- [x] Veri: 57 aylık pazar serisi, tedavi grubu paneli, makro ve takvim değişkenleri
- [x] Durağanlık testleri, takvim etkisi, baseline modeller, iki pencerede rolling-origin değerlendirme
- [ ] **Kur geçişkenliği:** ilaç avro değeri güncelleme tarihleriyle olay çalışması (fiyat basamakları)
- [ ] Tedavi grubu paneli üzerinde hiyerarşik/panel tahmin (5 dengeli seri)
- [ ] TÜFE'nin yeni baz yıllı (2025=100) EVDS serisini bağla, reel değer analizini 2026'ya uzat
- [ ] SHAP ile açıklama (en iyi ML modeli için; 57 gözlemde dikkatli yorum)
- [ ] 2026'nın kalan aylarını rapor çıktıkça ekle
- [ ] (Opsiyonel) Faz 2: gerçek toplama kalibre edilmiş sentetik ürün düzeyi simülasyon (açıkça etiketlenir)
