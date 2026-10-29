# İlaç Talep Tahmini: Ekonometri + Makine Öğrenmesi

Türkiye ilaç pazarında **aylık hacim (milyon kutu) ve değer (milyon TL)** serisini, takvim etkileri (iş günü, bayramlar) ve makro değişkenlerle (kur, TÜFE) modelleyen bir talep tahmini projesi. Klasik ekonometri (OLS/SARIMAX) ile ML (Ridge/LightGBM) aynı rolling-origin protokolüyle karşılaştırılır.

## Neden bu proje?
Türkiye'de ilaç fiyatları büyük ölçüde devlet tarafından belirlenir (referans fiyat / avro değeri sistemi). Bu yüzden **kur, enflasyon ve düzenleyici değişiklikler** değer serisini sürüklerken, **hacim** serisi esas olarak takvim ve talep dinamiklerini yansıtır. Veri bunu net gösteriyor: 2022 → 2024'te toplam değer yaklaşık 3 kat artarken (109,8 → 325,0 milyar TL), hacim yatay kaldı (2.556 → 2.570 milyon kutu).

## Veri
| Veri | Kaynak | Dönem | Dosya |
|---|---|---|---|
| Toplam ilaç pazarı (değer, hacim, imal/ithal) | İEİS Pazar Analiz Raporları (kaynak veri: IQVIA, SGK) | 2022-01 … 2024-12 (36 ay) | `veri/pazar_toplam_aylik.csv` |
| Tedavi grubu serileri | Aynı raporlar | 36 ay | `veri/tedavi_gruplari_dengeli.csv`, `veri/tedavi_gruplari_uzun.csv` |
| USD/TRY, EUR/TRY, TÜFE | TCMB EVDS 3 | aylık | `macro_monthly.csv` (`fetch_macro.py`, API anahtarı gerekir) |
| Resmi tatiller | `holidays` paketi (TR) | | `01_analiz_tablosu.py` içinde |

Alan tanımları: `veri/VERI_SOZLUGU.md`. **Kaynak:** İlaç Endüstrisi İşverenler Sendikası (İEİS), Pazar Analiz Raporları, Ocak 2023 – Aralık 2024. Raporların hakkı İEİS'e aittir; repoda PDF yoktur, yalnızca raporlardan çıkarılan sayılar vardır.

### Veriler nasıl çıkarıldı ve nasıl doğrulandı
Raporlar tek sayfalık infografiklerdir. Tedavi grubu tabloları metin katmanından, toplam pazar grafikleri OCR ile okundu. Her değer şu kontrollerden geçti:
1. **İmal + ithal = toplam** (kümülatif, her rapor için, yuvarlama toleransıyla)
2. **Rapordaki yüzde değişim etiketleri** ile hesaplanan değişim uyumu
3. **Ocak–X kümülatifinin ay ay sürekliliği** (kümülatif farkı = aylık değer)
4. **İki bağımsız kaynak karşılaştırması:** 2023 ayları hem 2023 raporlarında hem 2024 raporlarının "önceki yıl" sütununda var; aylık değerler en fazla %0,75 (TL) ve %0,52 (kutu) farkla tutuyor (`veri/revizyon_karsilastirma_2023.csv`)
5. OCR'ın binlik basamağı kaçırdığı 8 rapor ile tablosu görüntü olarak gömülü olan Mayıs 2023 **gözle okunup düzeltildi**.

## Veri sınırlılıkları (dürüstçe)
- **Sadece 36 ay.** Mevsimsel ARIMA (s=12) bu örneklemde kurulamaz; ML modelleri küçük örneklemde zorlanır. Aşağıdaki sonuçlar bu sınırın içinde okunmalı.
- Değerler **nominal TL**; hacim "ilaç" kategorisidir (özel tıbbi amaçlı gıda ve sağlık ürünleri hariç). Kapsam ayrıntısı için İEİS metodolojisine bakın.
- **Tedavi grupları:** raporlar her ay yalnızca ilk 5 grubu verir. 24 raporun hepsinde yer alan temiz seriler dengeli panelde: kutu için Antibiyotikler, Kardiyovasküler, Soğuk algınlığı/öksürük; değer için Onkoloji, Antibiyotikler, Kardiyovasküler.
- **Antiromatizmal serisinde vintage kırılması var:** 2024 raporları 2023 değerlerini 2023 raporlarından yaklaşık %20 yüksek veriyor (2023 toplamı 279 → 334 milyon kutu), muhtemelen grup tanımı değişti. Dengeli panelde **yok**, uzun dosyada uyarıyla duruyor.
- **Aylık imal/ithal değerleri türetilmiştir** (kümülatif farklarından), rapordaki değerler değildir.
- **İş günü değişkeni yalnızca resmi tatilleri içerir**, idari izinle uzatılan köprü günleri (ör. 9 günlük bayram tatilleri) dahil değildir.
- Sağlık Bakanlığı açıklamasına göre kutuların yaklaşık %17'si İTS'ye bildirilmeden satılmıştır; resmi satış verisi gerçek tüketimi tam yansıtmayabilir.

## İlk bulgular
Hacim tahmini, 1 adım ileri, test = 2024 (12 ay, model her ay yeniden kurulur):

| Model | RMSE (milyon kutu) | MAPE |
|---|---|---|
| SARIMAX (AR1 + takvim) | 16,8 | %5,7 |
| OLS (takvim) | 17,0 | %5,9 |
| Ridge (takvim + lag1) | 17,3 | %5,6 |
| LightGBM (takvim + lag1 + ay) | 22,0 | %8,6 |
| Naif (geçen ay) | 28,3 | %11,0 |
| Mevsimsel naif (geçen yıl aynı ay) | 30,2 | %11,8 |

- **Takvim çok açıklayıcı:** iş günü sayısının hacim esnekliği ≈ 1,6 (HAC p = 0,001). Takvimli modeller naif tahminin hatasını yaklaşık yarıya indiriyor. Bayram nedeniyle kaybedilen iş günü katsayısı pozitif (0,063; p = 0,016); iş günü zaten bayramı içerdiği için bu, bayram öncesi stoklama gibi bir etkiye işaret edebilir ama 36 gözlemde kesin söylenemez.
- **Küçük örneklemde ML doğrusal modelleri geçmiyor.** LightGBM burada gerilide; daha fazla veri ve grup düzeyinde panel ile yeniden denenmeli.
- **Açıklanamayan kısım:** 2024 Ağustos ve özellikle Kasım–Aralık düşüşleri takvimle açıklanmıyor (bkz. `cikti/hacim_tahmin_2024.png`).
- **Kur geçişkenliği henüz kanıtlanmadı:** ortalama kutu fiyatı üzerine aylık gecikmeli regresyon denendi, katsayılar kararsız ve ekonomik olarak anlamsız çıktı (kümülatif etki −0,91). Fiyatlar aylık sürekli değil, düzenleyici avro değeri güncellemeleriyle basamak basamak değişiyor; bu yüzden olay çalışması (event study) gerekiyor. Sonuç olarak sunulmuyor.

## Çalıştırma
```
pip install -r requirements.txt
$env:EVDS_API_KEY="..."        # PowerShell; anahtarı koda/repoya yazmayın
python fetch_macro.py           # macro_monthly.csv üretir
python 01_analiz_tablosu.py     # veri/analiz_tablosu.csv
python 02_baseline.py           # cikti/baseline_sonuclari.csv + grafik
```
Not: EVDS'de TÜFE'nin 2003=100 serisi Ocak 2026'da sona erdi (baz yılı 2025=100'e geçildi). Analiz penceresi (2022-2024) bundan etkilenmiyor.

## Yol haritası
- [x] Veri: aylık pazar serisi, tedavi grubu paneli, makro ve takvim değişkenleri
- [x] Durağanlık testleri, takvim etkisi, baseline modeller, rolling-origin değerlendirme
- [ ] **Veriyi uzat:** İEİS'in 2025 ve 2026 aylık Pazar Analiz raporları (varsa) aynı yöntemle eklenirse ~57 aya çıkar
- [ ] Tedavi grubu paneli üzerinde hiyerarşik/panel tahmin
- [ ] Kur geçişkenliği: ilaç avro değeri güncelleme tarihleriyle olay çalışması
- [ ] SHAP ile açıklama (daha fazla veriyle anlamlı)
- [ ] (Opsiyonel) Faz 2: gerçek toplama kalibre edilmiş sentetik ürün düzeyi simülasyon (açıkça etiketlenir)
