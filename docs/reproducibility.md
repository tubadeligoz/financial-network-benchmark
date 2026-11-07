# Reproducibility protocol

## Inputs and identity

Deney tekrarı aynı kaynak dosyası/manifest, preprocessing politikası, graph hash,
algoritma/model sürümü, parametre, seed ve pinned matematik kütüphanelerini gerektirir.
Veri akışı etiketi tek başına değişmez veri sürümü değildir. BIS revizyonu veya
manifest erişim kaydı değişirse graph hash farklı olabilir. Eski hash'i elde etmek
için yeni verinin provenansını değiştirmeyin; orijinal kaynak arşivini kullanın.

Gerçek Q4 örneği için CSV/manifest `data/raw/bis-all-sectors-2025q4` altında olmalıdır.
Bu dosyalar Git dışındadır. Üç düğümlü demo ve beş bankalı finansal kurgu izole,
etiketli ve depoda mevcuttur; CI gerçek finansal dosya veya API anahtarı gerektirmez.

## New run layout, benchmark protocol 1.1.0

```text
experiments/<experiment_id>/
  configuration.json
  runs/<timestamp-uuid>/
    configuration.json
    environment.json
    source-report.json
    source-code.zip
    source-manifest.json
    schedule.json
    raw-measurements.json
    raw-measurements.csv
    rankings/<case>.json
    summary.json
    comparisons.json
    status.json
    trials/<index>/{job,phase,worker-result,trial}.json
```

Effective configuration kaynak yollarını, missing/zero/self-loop politikalarını,
generator ayarlarını, graph identity, algoritma parametrelerini, seed, tekrar,
warmup, timeout ve bellek limitlerini tutar. Source report gerçek doğrulama raporunu
ve seçimi içerir. Ranking JSON algoritma sürümü, çözümlenmiş parametre, kaynak dosya
hash'i, dataset/kind/dönem ve graf hash'i taşır. Sentetik finansal metadata model
sürümünü, sermaye tanımını, varsayımları, şokları ve yayılımın hedefini ayrıca içerir.

Environment Python/platform/CPU/core/RAM, matematik paketleri, kurulu paket sürümleri,
thread limitleri ve uygulama kaynak hash'ini saklar. Kaynak hash'ine artık paket JSON
varlıkları da dahildir. `source-code.zip` backend app Python/JSON dosyalarını,
pyproject/requirements ve frontend paket kilidini içerir; raw veri, `.env`, sanal
ortam veya kullanıcı gizli dosyaları dahil edilmez. Arşiv digest'i environment'dadır;
her üyenin digest'i source-manifest'tedir. Bu bir backend deney kaynak arşividir,
tüm frontend/repo geçmişinin Git kopyası değildir. Çalışma sırasında kodu değiştirmeyin.

Raw trial'lar özetlerden ayrıdır. Yeni `result_path`, run klasörüne göredir; run
taşındığında trial dosyaları bulunabilir. Eski absolute yollar tarihsel kayıtlarda
kalır. Araçlar eski ve yeni yolu ayırt etmelidir. Ham veri hash'leri ve kaynak sürümü
korunur; dış verinin dağıtım hakkı kod arşiviyle verilmiş sayılmaz.

## Commands

```powershell
# Sentetik, indirmesiz deney:
.\.venv\Scripts\python.exe -m app.benchmark.cli run --config configs/benchmarks/synthetic-100.json
# Açık varsayımlı finansal kurgu:
.\.venv\Scripts\python.exe -m app.benchmark.cli run --config configs/benchmarks/synthetic-debtrank.json
# Final teyit; önceki çıktıyı korumak için yeni index adı:
.\.venv\Scripts\python.exe scripts/run_final_experiments.py --include-bis --output data/processed/final-replay-index.json
```

Kaynak arşivini ayrı dizine çıkarıp o backend'i kurarak algoritma kodunu koruyun.
Orijinal veri/manifesti temin edin; effective config'teki dosya yollarını yeni ortama
uyarlarken orijinal manifest ve preprocessing içeriğini değiştirmeyin. Önce graph
identity'yi kontrol edin. Yeni experiment ID ile tekrar koşup skorlar/ranklar ve
status sayımlarını karşılaştırın. Sürelerin bire bir aynı olması beklenmez.

## What repeatability means

Aynı ayarlarda deneme skor digest'leri birbirine karşı kontrol edilir; failed/timeout
trial tekrar üretilebilir başarılı sonuç sayılmaz. CPU/OS/BLAS ve floating-point
farkları yüzünden platformlar arası tam byte eşitliği garanti edilmez. Skor toleransı,
sıralama bağları ve kütüphane sürümleri ayrıca incelenmelidir. Seed, gerçek veri
eksikliğini gidermez veya yaklaşık betweenness'i exact yapmaz.

Zamanlama, bellek ve preprocessing ayrı sınırlar kullanır. RSS örneklemesi çok kısa
geçici zirveleri kaçırabilir; OS peak süreç ömrünü kapsar. Warmup, dosya cache'i ve
diğer sistem yükü koşullarını açıklayın. Beş tekrarlı descriptive istatistik, tek
başına anlamlılık veya donanımdan bağımsız hız üstünlüğü kanıtı değildir.

## Historical evidence and CI

Faz 3 ve 5 kayıtlarının environment/hash'leri kendi zamanlarına aittir. Bu kayıtlar
şimdiki kodla ölçülmüş gibi etiketlenmez. Eski koşuların kaynak kod arşivi yoktur;
tam eski uygulama bitlerini hash'ten geri üretmek mümkün değildir. Eski rapordaki
`measured_source_matches_current` alanı rapor üretildiği anın kontrolüdür, bugünün
iddiası değildir. Faz 6 yeni koşuları yeni source archive ile bu boşluğu kapatır.

CI Windows/Python 3.11/Node 24/npm 11.6.2 üzerinde pinned install, lint, kademeli
mypy, pytest, strict TS, unit/build ve sentetik browser iş akışını tanımlar. Test
API'si izole fixture dizininde 4173 portunda başlar. `FNB_REAL_DATA=1` gerektiren
BIS testi CI'da bilinçli skip'tir; yerel gerçek kaynak testi ayrıca çalıştırılır.
Workflow'un burada yerel eşdeğer komutları çalıştırılır. GitHub-hosted run ancak
izinli push/dispatch sonrasında gerçekten doğrulanabilir; bu teslimde push yapılmaz.
