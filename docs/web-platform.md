# Faz 4 — Yerel araştırma platformu

React 19, strict TypeScript, Vite 7, Tailwind CSS 4, Cytoscape.js, Apache ECharts ve
FastAPI kullanılır. Frontend bağımlılıkları `frontend/pnpm-lock.yaml`, Python sürümleri
`backend/requirements-lock.txt` içinde sabitlenmiştir. Kurulum ve başlatma README'dedir.
Üretim dağıtımı veya kullanıcı hesapları bu faza dahil değildir; sunucuyu 127.0.0.1'e bağlayın.

## Ekranlar ve veri anlamı

- Datasets: kayıtlı kaynak/dönem, gerçek/sentetik ayrımı, sürüm, sayılar, kaynak doğrulaması ve SHA-256.
- Graph Explorer: yönlü graf, arama, seçim, pan/zoom/fit, minimum maruziyet, Top-N skorları,
  komşu genişletme, bağlantılar ve tüm graf istatistikleri. Mobil başlangıç 30, masaüstü 60 düğüm;
  en fazla 250 düğüm ve en büyük 400 görünür kenar çizilir. Görünür/toplam sayılar gösterilir.
  Düğüm boyutu log(1 + total strength) ile sınırlanır; altın renk seçili yöntemin Top-N listesidir.
  Kenar çizgi genişliği sabittir; ok alacaklıdan borçluya gider. Analizler alt grafı kullanmaz.
- Benchmarks: strength, exact/approximate betweenness, inverse-exposure betweenness ve PageRank;
  tekrar, seed, timeout ve PageRank parametreleri. Aynı seçili graf üzerinde ayrık zaman/bellek denemeleri.
- Results & Analysis: deney seçimi, varsayılan olarak **aynı graf hash'i** ile filtreleme, Top10/20,
  zaman/bellek istatistikleri, overlap, Jaccard/Spearman, sentetik ölçek ve mevcut dönem karşılaştırması.
  Tüm dönemleri açmak farklı graf sürümlerini açık seçimle gösterir; skorlar birleştirilmez.
  CSV tüm sıralamaları, JSON tüm sıralamalar ve ham denemeleri içerir; grafikler SVG dışa aktarır.

BIS kapsamı ülke A'da yerleşik raporlayan bankalar → ülke B'deki **tüm sektörlerdir**.
Bireysel banka kimliği yoktur. Maruziyet birimi milyon USD'dir. Eksik/yayımlanmayan çiftler
sıfır değildir. Renkler iflas olasılığı veya doğrulanmış sistemik risk tahmini anlamına gelmez.
Betweenness ve PageRank ölçekleri strength ile doğrudan karşılaştırılmaz. PageRank borçlu yönüne akar.
Skor sadece tamamlanmış, eşleşen graf hash'li kayıttan gösterilir; aksi halde `Not calculated`.
Overlay strength total_strength, betweenness unweighted exact, PageRank weighted kayıtlarını kullanır;
aktif parametreler görünür. Diğer parametreler ve yaklaşık yöntemler deney sonuçlarında korunur.

## Kayıtlı kaynaklar

API, proje kökünü modül konumundan bulur; `FNB_PROJECT_ROOT` ile başka kök seçilebilir.
`data/raw/bis-all-sectors-*/observations.csv` + `manifest.json` BIS kaynaklarını kaydeder.
Dönem dosyanın gerçek TIME_PERIOD alanından okunur. Şema ve hash manifesti doğrulanır.
Yeni veri için önce Faz 1 CLI doğrulamasını çalıştırın, sonra API'yi yeniden başlatın.
Ham veri Git'e eklenmez. Tarayıcıdan dosya yükleme bu sürümde **kapalıdır**.
İstekler yalnızca kayıtlı dataset/dönem anahtarlarını kabul eder; istemci dosya yolu veremez.
`data/demo` ayrı sentetik kaynaktır. `experiments/*/configuration.json` içindeki sentetik
generator kaynakları hash'e göre tekilleştirilir. Bozuk kaynak kullanıcıya hata olarak görünür.
Kaynak önbelleği süreç ömrü boyuncadır; dosyalar değiştiğinde yeniden başlatma gerekir.

## API sözleşmesi

Taban `/api/v1`; canlı OpenAPI `/openapi.json`, etkileşimli belge `/docs`.
Python istek modelleri `backend/app/api/schemas.py`, TypeScript modelleri
`frontend/src/api/types.ts` içindedir; sözleşmeler API ve UI testleriyle doğrulanır.

| İşlev | Uç nokta |
|---|---|
| Sağlık / mod | GET `/health` |
| Kaynak listesi / ayrıntı / dönem | GET `/datasets`, `/datasets/{dataset}`, `/datasets/{dataset}/periods` |
| Doğrulama / istatistik | GET `/datasets/{dataset}/periods/{period}/validation` veya `/statistics` |
| Graf / arama / düğüm | Aynı dönem öneki + `/graph`, `/search?q=US`, `/nodes/US` |
| Hesaplanan skorlar / yöntemler | Aynı dönem öneki + `/analyses`; GET `/algorithms` |
| Hesaplama / benchmark | POST `/analyses`, `/benchmarks` → HTTP 202 job |
| İş durumu / iptal | GET `/jobs/{id}`, POST `/jobs/{id}/cancel` |
| Deney / sonuç / export | GET `/experiments`, `/experiments/{id}?top=20`, `/experiments/{id}/export?format=json` veya `csv` |
| Ölçek / dönem | GET `/analysis/scalability`, `/analysis/temporal` |

POST başlığı `X-FNB-Client: local-web` zorunludur. Origin varsa izin verilen yerel origin
olmalıdır; CORS/Host sınırları yereldir. JSON istek boyutu 64 KiB ile sınırlanır.
İstemci bu hataları kullanıcıya gösterir; bu kontrol internet üzerinde kimlik doğrulaması sağlamaz.
Algoritma isteği örneği (örnek bir **istektir**, hesaplanmış sonuç değildir):

```json
{"dataset":"synthetic-demo","period":"2025-Q4","algorithm_id":"pagerank","parameters":{"alpha":0.85,"weighted":true}}
```

## İş yönetimi ve hata davranışı

API tek bir yerel kuyruk iş parçacığı ve her iş için ayrı Python süreci kullanır; en fazla
8 bekleyen/çalışan iş kabul edilir. Benchmark supervisor mevcut Faz 3 deneme süreçlerini açar.
BLAS thread sınırları korunur. HTTP isteği hesaplama bitmesini beklemez. İlerleme dosyası
gerçek deneme bitişlerini içerir; belirsiz aşamalarda sahte yüzde üretilmez.

Durumlar queued, running, completed, failed, cancelled. İptal tüm alt süreç ağacını sonlandırır.
Her işin üst sınırı 30 dakikadır; algoritma deneme timeout'u ayrıca korunur.
Kısmen başarısız benchmark `failed` job olur; üretilmiş deney sonuçları yine incelenebilir.
Algoritma çalıştırılırken kaynak hash'i başvurudaki sürümle tekrar karşılaştırılır.
İşler `data/processed/web/jobs`, analizler `data/processed/web/analyses`, deneyler `experiments`
altında saklanır. API yeniden başlatılırsa eski aktif işler failed yapılır ve otomatik sürdürülmez.
Ani süreç/işletim sistemi çöküşünden sonra süreç kurtarma yapılmaz. Tek API worker kullanın.
Sayfa yenileme aktif job panelini geri yüklemez; tamamlanan deneyler Results'ta kalır ve job
kimliğiyle API'den durum sorgulanabilir. Bu ilk sürüm dağıtık kuyruk veya çok kullanıcılı hizmet değildir.

Yükleme, boş, hata ve başarı durumları gerçek HTTP/job durumuna dayanır. Test fixture'ları
yalnızca `frontend/tests` ve `tests` altındadır; production kodu bunları içe aktarmaz.
Matrislerde tanımsız korelasyonlar boş kalır; sıfırla doldurulmaz. Küçük pozitif tutarlar
yuvarlanıp sıfır görünmemesi için bilimsel gösterimle yazılır. RSS tüm süreç belleğidir,
yalnızca algoritmanın ek bellek ihtiyacı değildir. Ölçek çizgileri graph family ve case'e göre ayrılır;
parametre, seed, ortam ve zaman bütçeleri için JSON kayıtlarını kullanın.

## Testler

`python -m pytest -q` önceki fazları ve sentetik API entegrasyonunu içerir.
Frontend `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` komutlarıyla doğrulanır.
İki sunucu açıkken `pnpm test:e2e`, gerçek Chromium ile dataset → graf → PageRank →
benchmark → sonuç → JSON/SVG indirme ve mobil navigasyon/tema akışlarını çalıştırır.
İkinci tarayıcı testi yerel Q3/Q4 BIS dosyalarını ve Faz 3 deneylerini gerektirir;
unit/CI testleri dış veri indirmez. Tarayıcı görselleri `frontend/test-results` altında üretilir.

## Phase 6 validation
Frontend installation now uses npm ci and package-lock.json. Repository retains at most three graphs and bounded small-artifact caches; changed source files require restart. Statistics summary=true omits large arrays while default API/CLI remains full. See architecture.md and final-delivery-report.md.
