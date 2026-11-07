# Faz 5 sonuçları — 7 Kasım 2026

Onaylanan kapsam tamamlandı: **bağımsız ve açıkça sentetik banka ağı üzerinde
DebtRank ve stres senaryoları**. Max-Flow ertelendi. Gerçek BIS grafına sermaye,
banka kimliği veya risk skoru uydurulmadı. Üretim deployment/GitHub push yapılmadı.

Yerel uygulama: http://127.0.0.1:8000 · API: http://127.0.0.1:8000/docs.
Dataset: `synthetic-bank-stress`. Dönem: `synthetic-T0` veya `synthetic-T1`.
Graph Explorer ve Results & Analysis içindeki **Synthetic financial stress lab**
paneli çalıştırılmış kurgu deneylerini gösterir.

## Model ve veri durumu

Model `debtrank-single-pass-book-equity/1.0.0`: 2012 tek geçişli dinamiğin açıkça
sentetik muhasebe özkaynağı tamponu kullanan uygulaması. U/I/D durumları, eşzamanlı
güncelleme ve bir kez yayılım kuralı kullanılır. Bu bir distress yayılım modelidir;
temerrüt olasılığı veya ödeme tasfiyesi modeli değildir. Özgün Tier 1/piyasa değeri
uygulamaları ve 2015 tekrar yayılımlı modelle otomatik karşılaştırılmamalıdır.

Beş hayali banka, beş yönlü maruziyet, iki kurgu dönem. Başlangıç bilançolarının
varlık − yükümlülük = özkaynak özdeşliği doğrulanır. Varsayımlar ve tutarlar
`backend/app/datasets/synthetic_banks.json` içinde açıkça kayıtlıdır.
Kaynak BIS verisine kalibre edilmemiştir; tutarlar sentetik parasal birimlerdir.

| Dönem | Graf SHA-256 |
|---|---|
| synthetic-T0 | `605bfe5195251491853e5213878e330dcf6c940ab8e7d9a4bdf4eb588088d6b7` |
| synthetic-T1 | `fc44a53c1588f339a11ff69c5f095648cb47304633ae5a154d3f66c129fa7515` |

Mevcut BIS Q3/Q4 ülke ağı sermaye/özkaynak ve eşleşen banka evreni sağlamaz.
API bu kaynaklarda DebtRank'i reddeder; UI nedeni gösterir. Exposure stoğu kapasite
sayılmadı. Finansal Max-Flow veya gerçek banka stres testi sonucu üretilmedi.

## Hesaplanan örnek sonuçlar

**Yalnızca sentetik C bankasının özkaynağına 0.5 başlangıç distress'i:**

| Kurgu dönem | Başlangıç aggregate H₀ | Son aggregate Hₜ | Ek distress / DebtRank R | Adım |
|---|---:|---:|---:|---:|
| T0 | 0.04347826 | 0.23898551 | 0.19550725 | 3 |
| T1 | 0.04687500 | 0.42927517 | 0.38240017 | 3 |

T0 son node distress: A=0.095, B=0.25, C=0.51583333, D=0.3, E=0.
T1: A=0.27083333, B=0.5, C=0.58125, D=0.44444444, E=0.
Başlangıç C=0.5 ayrıca kaydedilir. Döngü geri etkisi nedeniyle C ek distress alır;
bu, C'nin ikinci kez yaydığı anlamına gelmez. Ek etkilenen küme A/B/C/D'dir.
İzole E'nin ağ içi alacak ağırlığı sıfırdır; aggregate değerler toplam ekonomik
zarar veya toplam banka özkaynak kaybı değildir.

Gerçek tarayıcı akışında B ve C aynı anda 0.1/0.5 ile şoklandı; iki dönem için
**4 group scenario ve 4 ayrı seed impact ranking** kaydedildi.
Suite: `stress-2c0b1e5d8e904b638a602bf1e832be4d`.
Her seed ranking'de bankalar tek tek şoklanır; bu sıralama grup senaryosundaki
bankaların aldığı distress sıralamasından ayrı bir hedeftir.

## Gerçek süreçlerle benchmark

Konfigürasyon: `configs/benchmarks/synthetic-debtrank.json`.
Experiment: `synthetic-debtrank-v1`; run: `20261107T181934-2d058b2c`.
Her hedef için 5 zaman + 5 ayrı RSS ölçümü; toplam **20/20 başarılı ölçüm**.
Her denemede 1 warmup ölçüm dışında tutuldu. Sıralamalar tekrar üretildi.

| Hedef | Medyan hesaplama süresi | Medyan sampled process peak RSS |
|---|---:|---:|
| Beş seed'in ayrı etki sıralaması, shock=1 | 0.3849 ms | 90.08984375 MiB |
| Tek C=0.5 senaryosu | 0.1836 ms | 89.82031250 MiB |

Bu iki hedef farklı miktarda iş yapar. Sayılar beş düğümlü kurgu örneğin bu
bilgisayardaki gözlemleridir; genel ölçeklenebilirlik sonucu değildir. RSS süreç
tabanını içerir; yalnızca ek algoritma belleği olarak yorumlanmaz.
Ham ölçümler, environment, kaynak sürümü ve tam parametreler deney klasöründedir.
DebtRank/merkezilik ve farklı risk hedeflerinin ranking karşılaştırmaları
`comparison_exclusions` ile ayrılır; maliyet ölçümleri skor eşdeğerliği iddiası taşımaz.

## Doğrulama

- **134 Python testi geçti**, 58.06 s. Yeni DebtRank modülü 23 test/parametre durumu içerir.
- **6 frontend unit/UI testi geçti**; son koşu 6.53 s.
- **3 Chromium uçtan uca testi geçti**, 42.7 s. API mock'u kullanılmadı.
- Strict TypeScript, ESLint ve Vite build başarılı.
- Yön ve iki banka aritmetiği; zincir/cycle; tek geçiş ve durma; çoklu şok;
  izole bileşen; score bounds; eksik/bozuk finansal alanlar; tekrar üretim ve
  salt okunur snapshot; hedeflerin ayrılması; JSON/CSV export doğrulandı.
- Tarayıcıda senaryo oluşturma, adım seçme, risk grafı, iki dönem/büyüklük
  karşılaştırması, seed ranking, gerçek risk benchmark'ı ve BIS uygunsuzluk
  mesajı doğrulandı. Önceki faz kullanıcı akışları da geçti.
- Son risk akışı ayrıca 390×844 mobil görünümde taşma kontrolü ve graf ekran
  görüntüsüyle tekrar doğrulandı: 1/1 test, 21.0 s.
- Python testlerinde önceki Starlette/httpx test-client deprecation uyarısı sürüyor;
  test başarısızlığı veya runtime hatası oluşmadı.

Makine tarafından okunabilir kayıt: [phase5-results.json](phase5-results.json).
Ekran görüntüleri: `frontend/test-results/synthetic-stress-desktop.png` ve
`synthetic-stress-mobile.png`; üretilmiş çıktılar Git dışında tutulur.

## Değiştirilen dosyalar

- `backend/app/datasets/financial.py`, `synthetic_banks.json`: bağımsız kurgu veri,
  finansal alan/bilanço doğrulaması.
- `backend/app/algorithms/debtrank.py`, `engine.py`, `base.py`: yeni modül,
  kayıt ve experiment ID alanı; mevcut üç algoritmanın hesapları yeniden yazılmadı.
- `backend/app/benchmark/{source,config,comparison,manager,worker}.py`:
  yeni kaynak, uygun karşılaştırma sınırları ve benchmark sonuç provenansı.
- `backend/app/api/{stress,schemas,main,repository,worker}.py`: uygunluk, asenkron
  stres suite'leri, export ve kaynak kaydı. Mevcut yerel süreç kuyruğu kullanılır.
- `frontend/src/components/{StressAnalysis,NetworkCanvas}.tsx`, sayfalar,
  API tipleri, App/version/style: senaryo girdileri, risk görselleştirmesi,
  hedeflerin ayrılması ve gerçek/sentetik kaynak açıklamaları.
- `tests/test_debtrank.py`, `tests/test_api.py`, frontend unit ve tarayıcı testleri;
  benchmark örnek konfigürasyonu, paket veri kaydı, README ve Faz 5 belgeleri.

## Sınırlar ve sonraki faz

Kurgu veri 5 bankadır; modelin v1 güvenlik sınırı 500 bankadır. Tam gerçek bilanço
ve kredi riski dinamiği modellenmez. Stres suite'i hesaplama kaydıdır; runtime/RSS
ölçümü için ayrıca benchmark çalıştırılır. Önceki yerel job/restart ve çok kullanıcılı
olmama sınırları geçerlidir. Yeni modeller veya gerçek banka verisi ayrı doğrulama
gerektirir. **Faz 6 için kullanıcı onayı beklenir.**
