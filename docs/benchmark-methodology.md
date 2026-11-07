# Faz 3 — Scientific Benchmark Engine

## Kapsam ve konfigürasyon

Amaç ortak graf üzerinde hesaplama maliyeti, sıralama uyumu ve boyuta bağlı
davranıştır. Yeni risk tahmin modeli, frontend veya dashboard geliştirilmez.
Farklı algoritmalar farklı problemler çözer; hızlı olmak finansal doğruluk değildir.

JSON konfigürasyon örnekleri `configs/benchmarks` içindedir. Komutlar proje
kökünden çalışır. Kaynak yolları çözülmüş absolute biçimleriyle kaydedilir.

| Alan | Anlam |
|---|---|
| experiment_id | Tek bir konfigürasyona ait güvenli deney adı |
| source | BIS CSV/Parquet+manifest, Faz 1 snapshot veya sentetik üretim |
| expected_graph | Dataset ID/version, dönem, hash ve kapsam beklentileri |
| algorithms | Benzersiz case_id, algorithm_id ve algoritma parametreleri |
| repeat_count | En az 5 süre tekrarı; varsayılan 5 |
| random_seed | 0..2^32-1; algoritma sırası ve worker Python hash seed'i |
| warmup_count | Her worker'da ölçümsüz 0..10 çağrı; varsayılan 1 |
| timeout | Trial ve compute/warmup süre bütçeleri |
| measurement | En az 5 ayrı bellek tekrarı, örnekleme aralığı, RSS sınırı |
| top_k | Varsayılan 5, 10, 20 |

Ön inceleme kaynağı doğrular ve veri kimliği/sürümü, dönem, hash, gerçek n/m,
yoğunluk ve observed/synthetic sınıfını etkin konfigürasyona ekler. Beklenen
kimlik uyuşmazsa çalışmaz. Aynı experiment_id, değişmiş kaynak veya ayarlarla
yeniden kullanılamaz. Aynı konfigürasyon yeni run ID ile tekrar çalışır.
Parametre doğrulaması Faz 2 modüllerine aittir. Yaklaşık betweenness seed'i açık
verilmemişse deney seed'i kullanılır. Sabit seed'li tekrarlar örnekleme
belirsizliğini ölçmez; farklı seed deneyi ayrı yapılandırma olmalıdır.

## Deney protokolü

Her trial yeni bir OS sürecidir; aynı anda tek worker çalışır. Tekrar blokları
içinde algoritma sırası seed ile rastgeleleştirilir; gerçekleşen sıra kaydedilir.
Önce süre serisi, sonra ayrı bellek serisi çalışır.

1. Worker başlatılır ve paketler yüklenir.
2. Veri okunup doğrulanır; graf kurulur veya snapshot okunur.
3. Graf kimliği ana süreçteki ön incelemeyle eşleştirilir.
4. Ölçümsüz warm-up yapılır; sonuçları serbest bırakılır ve GC collect çağrılır.
5. Faz 2 motoru hash kontrolü ve salt okunur graf hazırlığını tamamlar.
6. Yalnız `algorithm.compute` yüksek çözünürlüklü monotonik sayaçla ölçülür.
7. Ortak sıralama ve JSON/disk yazımı ölçüm aralığının dışında kalır.

Compute, bütün düğüm skorlarının ve Computation nesnesinin oluşmasını kapsar.
Weighted betweenness'in mesafe grafı ve PageRank'in seyrek matrisi compute içinde
oluştuğundan dahildir. Motorun doğrulama/kopyalama/sıralama maliyetleri dahil
değildir; daha geniş `engine_elapsed_seconds` ayrıca kaydedilir.

Saat `time.perf_counter_ns`; CPU zamanı `time.process_time_ns` ile ölçülür.
Etkin CPU yüzdesi 100*CPU/duvar saati olup çok iş parçacığında 100'ü aşabilir.
Çok kısa işlerde OS CPU saati çözünürlüğü nedeniyle CPU zamanı sıfır olabilir;
bu, gerçek duvar saatinin sıfır olduğu anlamına gelmez.

Kaynak aşamaları ayrı alanlardır:

- `dataset_load_validation_seconds`: dosya/hash/adapter/doğrulama.
- `graph_build_seconds`: Faz 1 graf kurulumu ve fingerprint.
- `snapshot_read_seconds`: mevcut JSON'un okunması; ilk veri yüklemesi yerine geçmez.
- `synthetic_generation_seconds`: sentetik üretim; gerçek veri yüklemesi değildir.

Uygulanmayan aşamalar null'dır. Ön inceleme ölçümleri worker tekrarlarıyla
birleştirilmez. Başarılı süre tekrarlarında count, mean, median, sample standard
deviation (ddof=1), min/max üretilir. Tek başarıda std null; hiç başarı yoksa
özet değerleri null'dır. Başarı sayısı ve complete bayrakları da okunmalıdır.

## Bellek protokolü

Bellek byte olarak saklanır; MiB dönüşümü byte/1024^2'dir. `tracemalloc` kullanılmaz.

| Alan | Kapsam |
|---|---|
| baseline_rss_bytes | Compute öncesi worker resident memory |
| sampled_peak_rss_bytes | Ayrı bellek trial'ında compute çevresinde örneklenen RSS tepesi |
| sampled_peak_delta_bytes | Örneklenen tepe eksi baseline; saf tahsis miktarı değildir |
| process_peak_rss_bytes | Import/veri/graf/warm-up dahil OS süreç high-water mark'ı |
| parent_sampled_peak_worker_rss_bytes | Supervisor'ın tüm trial boyunca gördüğü tepe; trial.json içinde |

OS high-water mark Windows'ta `peak_wset`, mevcut Unix platformlarında
`resource.ru_maxrss` üzerinden, platform birimi normalize edilerek alınır.
Algoritma sonucunun oluştuğu noktaya kadardır; izole compute tepe belleği değildir.
Yöntem her trial'da kaydedilir; desteklenmeyen yerde değer null olur.

Worker içi psutil thread'i yalnız bellek serisinde varsayılan 5 ms aralıkla RSS
örnekler. Başlangıç/son örnekleri, örnek sayısı ve gerçek maksimum zaman aralığı
kaydedilir. GIL/OS zamanlaması aralığı uzatabilir; kısa sıçramalar kaçabilir.
Bu yüzden örneklenen tepe kesin interval high-water mark değil, alt gözlemdir.
Örnekleyici thread'in kendi belleği de worker'a dahildir. Warm-up sonrası
allocator/cache sayfaları baseline'da kalabilir; delta toplam algoritma belleği
olarak yorumlanmaz. Süre serisinde bu örnekleme thread'i çalışmaz.

Her iki seride dış supervisor yaklaşık 5 ms'de bir RSS/bütçe kontrolü yapar.
Bunun sistem yükü etkisinin sıfır olduğu varsayılmaz. Bellek serisinin süreleri
süre istatistiğine katılmaz; bellek özetleri de yalnız bellek serisinden gelir.

## Timeout ve kaynak sınırı

Varsayılan trial bütçesi 60 saniye (startup/yükleme/warm-up/compute/yazma dahil),
compute/warmup bütçesi 20 saniye ve RSS sınırı 2.048 MiB'dir. Warm-up bütçesi
o warm-up motor çağrısını kapsar; ölçülen compute bütçesi hook sınırında başlar.
Supervisor aşımda worker ve alt süreçlerini sonlandırır. Kontrol polling tabanlı
best-effort'tür; OS job/cgroup hard limit'i değildir ve kısa bellek sıçramalarını
kaçırabilir. Tamamlanmış compute'un ölçülen süresi de bütçeyle karşılaştırılır.

Timeout/resource-limit/worker-error/yakınsamamada başarılı runtime null'dır;
hata, durdurulan aşama ve varsa kısmi gözlemler saklanır. Toplam trial duvar saati
başarılı algoritma süresi diye gösterilmez. Başarısız denemeler ortalamaya sıfır
olarak eklenmez. İlk başarılı sıralama saklanır, diğer başarıların skor hash'leri
karşılaştırılır. Fark varsa repeatability false olur.

## Ölçeklenebilirlik ve sentetik veri

Gerçek BIS Q4 grafı 218 düğümdür; daha büyük gerçek bankacılık ağı varmış gibi
sunulmaz. Ayrı sentetik hedefler: 100, 500, 1.000, 5.000, 10.000 düğüm.

- `erdos_renyi`: NetworkX G(n,m); edge_count veya density. Density kenar sayısına
  yuvarlanır; gerçekleşen n/m kayıtlıdır.
- `preferential_attachment`: Barabási–Albert iskeleti, attachment_m parametresi.
  Directed seçiminde her bağ seed'li rastgele yönlenir. Bu gözlenmiş bankacılık
  modeli veya yönlü BA için tek kanonik model değildir.
- Directed/undirected ve weighted/unit seçenekleri vardır. Faz 2 algoritmaları
  sadece directed destekler; undirected deney uygunluk hatası verir, sessizce çevrilmez.
- Ağırlıklar Uniform(1,100) veya sabit 1; birim `synthetic units`.
- Seed, model, yapılandırma ve hash kaydedilir; gerçek banka kimliği/tarih üretilmez.
- Yerel güvenlik üst sınırı 100.000 düğüm/250.000 kenardır. Daha yoğun istek ön
  incelemede reddedilir; bu sınır ölçülmüş ölçeklenebilirlik sonucu değildir.

Referans suite ER için m=4n, strength, weighted PageRank ve k=32 unweighted
approximate betweenness kullanır. İkinci topoloji 500 düğümlü preferential
attachment'tır. Yaklaşık betweenness gerçek verideki exact yöntemle aynı yöntem
olarak etiketlenmez. Ayrı 10.000 düğümlü exact senaryoda 1 saniyelik compute
bütçesi vardır; timeout olağan, açıkça saklanan bir sonuçtur.

## Sıralama ve dönem karşılaştırması

Aynı snapshot ve aynı düğüm evreni gerekir; ham skorlar eşitlenmez.

- Overlap@K = |A_K∩B_K|/K.
- Jaccard@K = |A_K∩B_K|/|A_K∪B_K|.
- Spearman: skorların ortalama bağlı sıralarının korelasyonu (SciPy).

Sıra skor azalan, eşitlikte node_id artandır; Top-K cutoff eşitlikleri ayrı
bayraklarla gösterilir. Sabit skor vektöründe Spearman/Top-K uyumu anlamlı sayı
olarak üretilmez. K>=evren büyüklüğünde trivial örtüşme raporlanmaz. Tanımsız
değer null ve neden alanıyla saklanır. Eşit boyutlu kümelerde
Jaccard=Overlap/(2-Overlap), yani iki bağımsız kanıt değildir. Ground truth yoktur;
accuracy veya düğümler bağımsızmış gibi p-value üretilmez.

Dönemsel analizde algoritmalar kendi tam dönem grafında çalışır. Sonra ortak
düğümler üzerinde skorlar yeniden sıralanır; giren/çıkan kimlikler ayrıca
listelenir. Eksik düğümler sıfır/son sıra almaz. Aynı algoritma sürümü/parametre
ve tutarlı veri kapsamı gerekir; sentetik etiketler gerçek tarih sayılamaz.
Yoğunluk, Top-K, Spearman, dönemsel medyan süre ve kaydedilen ortam eşitliği
raporlanır. Ortam eşitliği aynı anlık yük/termal durum garantisi değildir.
Değişen süre finansal risk artışı anlamına gelmez; n/m ve sistem gürültüsü etkilidir.

## Ortam, saklama ve tekrar üretim

Environment dosyası OS, Python/executable, işlemci tanımı, fiziksel/logical CPU,
RAM, paket sürümleri, uygulama Python kaynak SHA-256'sı, saat ve thread limitlerini
içerir. BLAS/OpenMP ortam değişkenleri worker için 1'e sabitlenir. CPU affinity,
frekans/güç/termal durum, dış uygulamalar ve OS dosya cache'i kontrol edilmez.

```text
experiments/<experiment_id>/configuration.json
experiments/<experiment_id>/runs/<run_id>/
  configuration.json, environment.json, source-report.json, schedule.json
  raw-measurements.json, raw-measurements.csv, summary.json, comparisons.json
  status.json, rankings/<case_id>.json
  trials/<order>/job.json, phase.json, worker-result.json, trial.json, *.log
```

Deney kimliğiyle sonuç yolu doğrudan bulunur. Eski run üzerine yazılmaz. Her
trial tam sıralama/ölçüm/hata taşır; raw dosyalar bunlara bağlantı veren kompakt
JSON/CSV'dir. Kesilirse interrupted/failed durumu ve bitmiş ham kayıtlar korunur.

```powershell
.\.venv\Scripts\python.exe -m pip install -e "backend[test]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\fnb-benchmark.exe run --config configs/benchmarks/bis-2025q4.json
.\.venv\Scripts\python.exe -B scripts/run_phase3.py
```

Komut kaydedilmediyse `python -m app.benchmark.cli` kullanılabilir. Başarısız
trial varsa run CLI kod 2 verir. Referans suite kontrollü exact-timeout deneyini
de içerip bütün durumları indeksler. Suite öncesinde Q3/Q4 yerel girdileri
bulunmalıdır; `scripts/fetch_bis.py --period 2025-Q3 --output <yeni-klasör>` ile
indirilebilir. Yerel dosya desteği vardır; BIS revizyonunda eski hash beklentisi
sessizce değiştirilmez. Temporal CLI iki veya daha fazla run dizini kabul eder:
`fnb-benchmark temporal --runs <run1> <run2> --output <yeni-json>`.

Windows test artifact'ları proje içindeki kısa `.pytest-tmp` dizinindedir;
yalnız testler içindir ve Git dışında tutulur. Testler internet/gerçek BIS'e
bağımlı değildir. Matematiksel oracle'lar sentetik; worker/timeout/RSS ve tekrar
testleri gerçek OS süreçlerinde yürütülür.

## Kaynaklar

[Python saat](https://docs.python.org/3/library/time.html#time.perf_counter_ns),
[psutil](https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_info),
[SciPy Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html),
[NetworkX G(n,m)](https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.gnm_random_graph.html),
[NetworkX BA](https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.barabasi_albert_graph.html),
[BIS LBS](https://data.bis.org/topics/LBS), [BIS kullanım koşulları](https://data.bis.org/help/legal).
Türkçe açıklama resmî BIS çevirisi değildir. Önceki [algoritma](algorithms.md) ve
[veri sözleşmesi](datasets.md) sınırlamaları geçerlidir.

## Final protocol 1.1
New runs archive backend source/JSON assets, dependency versions and run-relative trial paths. See [reproducibility](reproducibility.md). Historical results retain their original environments; no cross-version pooling is performed.
