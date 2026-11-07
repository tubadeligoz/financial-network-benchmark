# Faz 4 çalışma raporu — 7 Kasım 2026

Yerel web platformu tamamlandı. DebtRank veya yeni araştırma algoritması eklenmedi.
GitHub push ve üretim deployment yapılmadı. Faz 5 onayı bekleniyor.

## Çalışan uygulama

- Derlenmiş uygulama: http://127.0.0.1:8000
- Geliştirme arayüzü: http://127.0.0.1:5173
- API belgesi: http://127.0.0.1:8000/docs

Datasets, Graph Explorer, Benchmarks ve Results & Analysis gerçek yerel API'ye bağlıdır.
Etkileşimli yönlü graf, skor overlay'i, komşu genişletme, filtreler, asenkron süreç işleri,
ölçüm grafikleri, sıralama matrisleri ve CSV/JSON/SVG export çalışır. Açık/koyu tema,
masaüstü 1440×1000 ve mobil 390×844 görünümleri Chromium ile doğrulandı.

## Kullanılan veri

Yeni BIS indirmesi yapılmadı; önceki fazlarda doğrulanan yerel kaynaklar kullanıldı.

| Kaynak | Dönem | Düğüm | Kenar | Graf SHA-256 |
|---|---|---:|---:|---|
| Gerçek BIS LBS, WS_LBS_D_PUB/1.0 | 2025-Q4 | 218 | 3094 | `685d173adc6d483df20b4c409409035d79554ef86621553a4d93b4c76673e144` |
| Gerçek BIS LBS, WS_LBS_D_PUB/1.0 | 2025-Q3 | 219 | 3095 | `fbaea23ae25b9f10747afc30c9fa5bab093c59ec5629de82d788af511b2c7509` |
| Açıkça sentetik demo, demo-v1 | 2025-Q4 | 3 | 3 | `52083dc3058fb5c9681c070c8394ea56cd07cddec7b2f9f8e1c0de967cecd59f` |

BIS yönü A ülkesindeki raporlayan bankalar → B ülkesindeki **tüm borçlu sektörlerdir**.
Bireysel banka ağı değildir. Eksik/suppressed gözlemler sıfır yapılmaz; doğrulama uyarıları gösterilir.
Faz 3'ün 100–10000 düğümlü sentetik generator ağları ayrı etiketlerle sunulur.
Geçmiş deneylerin ölçüm ortamı kendi kayıtlarında korunur; yeni web işleriyle ölçümler birleştirilmez.

## Doğrulama sonuçları

- Python regresyon ve API testleri: **110 passed**, 32.70 s.
- Frontend unit/UI testleri: **5 passed**, 6.22 s toplam.
- Strict TypeScript: başarılı; ESLint: başarılı.
- Vite build: başarılı; index, Cytoscape ve ECharts ayrı bundle'larda.
- Gerçek API'li Chromium testleri: **2 passed**; son derlenmiş uygulama koşusu **21.4 s**.
- Kontroller: veri/dönem seçimi, düğüm arama/seçim, PageRank hesabı, yöntem seçimi,
  benchmark başlatma ve gerçek ilerleme, sonuç tablosu, JSON ve SVG indirme, sonuçtan
  graf düğümüne dönüş, mobil menü/tema, yatay sayfa taşması ve tarayıcı JavaScript hataları.
- Test fixture'ları sentetik olarak işaretli ve yalnızca test klasörlerinde; gerçek tarayıcı
  kullanıcı akışında API mock'u kullanılmadı.

Son gerçek uçtan uca sentetik deney:

- Experiment ID: `web-89cca04cffe641d6`; API ID: `968f6249cf2454dcaebd`.
- Run ID: `20261107T174903-5df432d6`.
- 5 zaman + 5 bellek denemesi tamamlandı; warmup ölçümlere dahil edilmedi.
- Strength medyanı: **0.0756 ms**; sampled process peak RSS medyanı: **95985664 byte**.
- Tüm sıralamalar tekrar üretildi. Bunlar üç düğümlü sentetik demo ölçümleridir;
  gerçek BIS performansı veya finansal risk bulgusu olarak yorumlanmamalıdır.
- Ayrı gerçek PageRank işi tamamlandı; üç skor toplamı API testinde 1 olarak doğrulandı.

Ekran görüntüleri yeniden üretilebilir: `frontend/test-results/datasets-desktop.png`,
`graph-desktop.png`, `results-desktop.png`, `datasets-mobile-dark.png`, `graph-mobile-dark.png`.
Üretilmiş veriler, deneyler, ekran görüntüleri ve bağımlılıklar Git dışındadır.

## Dosya kapsamı

- `backend/app/api/{main,repository,schemas,jobs,worker}.py`: API, kayıtlı kaynak erişimi,
  istek şemaları, yerel kuyruk ve ayrı süreç yürütme.
- `frontend/src/App.tsx`, `pages/{Datasets,Explorer,Benchmarks,Results}.tsx`:
  yerleşim, seçimler ve dört ekran.
- `frontend/src/components/{NetworkCanvas,Chart,States}.tsx`, `api/*`, `hooks/*`, `styles.css`:
  Cytoscape/ECharts, gerçek durum yönetimi, istemci sözleşmeleri ve responsive temalar.
- `frontend/package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, Vite/TypeScript/ESLint/Playwright
  yapılandırmaları ve frontend testleri.
- `tests/test_api.py`, Python bağımlılık kayıtları, `.gitignore`, CI workflow, README,
  `docs/web-platform.md` ve bu rapor.

## Bilinen sınırlar

Dosya yükleme kapalıdır; kayıtlı yerel kaynaklar kullanılır. Kaynak değişince API yeniden
başlatılmalıdır. Kuyruk tek yerel süreç içindir; API yeniden başlatılan işleri sürdürmez.
Sayfa yenileme aktif job panelini geri getirmez, ancak tamamlanan deneyler saklanır.
Graf çizimi en fazla 250 düğüm/400 kenardır ve görünür kapsam açıkça yazılır; hesaplamalar
tüm grafı kullanır. Uzun işlerin 30 dakika üst sınırı vardır. Tam erişilebilirlik denetimi
ve çok tarayıcılı test yapılmadı; Chromium masaüstü/mobil kontrolleri yapıldı.
Python testlerinde Starlette'in httpx test istemcisi için bir deprecation uyarısı vardır;
test başarısızlığı veya uygulama çalışma hatası oluşmadı.
