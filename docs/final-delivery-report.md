# Final delivery report — Faz 6

## Genel durum

Yerel araştırma platformu doğrulandı ve kullanıcı değerlendirmesine hazırlandı.
Yeni finansal yöntem eklenmedi. GitHub push ve production deployment yapılmadı.
GitHub-hosted CI koşusu bu nedenle doğrulanmış değildir; aşağıdaki açık madde korunur.

## Test ve ölçüm sonuçları

- Backend: **141 passed**, 55.64 s; Ruff ve iki modüllük strict mypy geçti; pip check başarılı.
- Frontend: **8 unit/component tests passed**; strict TypeScript, ESLint, Vite build başarılı.
- Temiz **npm ci** gerçekten çalıştırıldı; mevcut direct dependency sürümleri korundu.
- İzole, gerçek finansal veri içermeyen CI eşdeğer tarayıcı akışı: **3 passed, 1 skipped**, 45.0 s.
  Skip, orijinal BIS dosyaları/tarihsel deney gerektiren isteğe bağlı testtir. Önceki fazda
  gerçek veri tarayıcı akışı doğrulanmıştır; bu final izole koşusu onu yeniden çalıştırmadı.
- Cytoscape başlangıç/layout ölçümleri bu koşuda 20.9 ve 83.4 ms; görüntü 250/1000
  düğümle sınırlandı. Arama/zoom yeni layout başlatmadı; mobil taşma kontrolü geçti.
- Yeni iki final benchmark: **60/60 başarılı ölçüm**, tekrar skorları eşleşti.

## Performans

Beş tekrarlı aynı-process tanısal ölçümde BIS load/validate/build medyanı 391.95→280.35 ms;
sıcak katalog 11.30→3.45 ms; deney listesi 18.73→14.28 ms; BIS analyses 27.47→19.50 ms.
Son işlem RSS'i 252.14→231.84 MiB; bu değer peak veya yalnızca algoritma belleği değildir.
Üç graflık LRU nedeniyle evicted BIS grafının ilk graph isteği 354 ms'ye çıktı;
önbellek/bellek kazancının bu karşılığı gizlenmez. Graf kimlikleri ve dokuz skor digest'i aynı kaldı.

Stats summary: BIS 42452→968 byte; 1000-node sentetik 215015→759 byte. Aynı hash/count/density
korundu; tam API/CLI çıktısı kullanılabilir. Bu ASGI, ardışık, yükü kontrol edilmeyen ölçümlerdir;
genel hız üstünlüğü veya istatistiksel anlamlılık iddiası değildir. Ham profiller evidence index'tedir.

## Denetim bulguları

| Önem | Bulgu | Durum |
|---|---|---|
| Yüksek | E2E'nin gerçek BIS dosyalarına bağımlılığı | Düzeltildi: izole sentetik workspace ve optional gerçek test |
| Yüksek | JSON yazmada kısmi belge riski | Düzeltildi: atomik replace, geçersiz yazmada önceki dosya korunur |
| Orta | Windows eşzamanlı read/replace paylaşım ihlali | İlk yeni test başarısız oldu; bounded reader retry sonrası geçti |
| Orta | Eksik run kaynak arşivi / absolute trial yolları | Yeni protocol 1.1 koşularında arşiv, manifest, tam sürümler, relative yollar |
| Orta | İki CSV to_dict geçişi ve bütün grafların kalıcı cache'i | Tek geçiş, metadata cache, 3-graph LRU; ölçülmüş karşılıkları yukarıda |
| Orta | Chunked body limiti / hatalı Content-Length | 413/400 kontrolleri ve API regresyonu |
| Orta | Chart tekrar init; eski kaynağın yeni seçimde gösterilmesi | Instance reuse ve path/revision-key guard; yeni component testleri |
| Düşük | Matris köşegeninde undefined policy tutarsızlığı | k≥n/constant durumları backend politikasıyla hizalandı |
| Düşük | Lint/tip ve logging boşlukları | Ruff, kademeli mypy, job lifecycle logging; yedi unused import kaldırıldı |
| Düşük | npm kilidi oluştururken eski pnpm ağacı uyumsuzluğu | İlk komut başarısız oldu; temiz npm ağacında lock ve npm ci geçti |
| Açık | GitHub-hosted CI | Push/dispatch yapılmadı; çalışmış gibi raporlanmaz |
| Açık | Kod lisansı / sınırlı tip kapsamı / dev dependency deprecation | Sahip kararı ve sonraki kontrollü bakım; belgelenmiş sınırlar |

## Final acceptance checklist

| Madde | Durum | Kanıt / sınır |
|---|---|---|
| Veri yükleniyor | PASS | CSV/Parquet testleri, gerçek profil |
| Veri doğrulanıyor | PASS | Loader/API validation testleri |
| Yönlü/ağırlıklı graf | PASS | Hash ve direction oracles |
| Temel algoritmalar | PASS | Matematiksel unit/regression |
| Tekrarlanabilir benchmark | PASS | Yeni 60 trial, skor digest eşleşmesi |
| Süre/bellek | PASS | Ayrı timing/RSS series |
| Saklanan sonuçlar | PASS | Raw, summary, archive/manifest |
| Web arayüzü | PASS | Gerçek backend'li sentetik E2E |
| Etkileşimli graf | PASS | Arama, seçim, zoom, bounded layout |
| Algoritma karşılaştırması | PASS | Uygun hedefler; DebtRank ayrılır |
| Responsive | PASS | 390×844 smoke ve taşma kontrolü |
| Testler | PASS | 141 backend, 8 frontend, 3 CI browser; optional BIS skip açık |
| CI çalışıyor | FAIL | Workflow ve yerel eşdeğer geçerli; GitHub üzerinde koşu tetiklenmedi |
| Dokümantasyon | PASS | README 15 bölüm, mimari/repro/results/rapor/demo |
| Sonuçlar izlenebilir | PASS | Run/source/environment/hash/evidence index |
| Bilinen sınırlamalar | PASS | Gerçek/sentetik ayrımı, örnekleme, cache, arşiv ve lisans açık |
| Finansal Max-Flow | NOT APPLICABLE | Onaylanan kapsamda ertelendi; kapasite modeli yok |

## Teslim ve sonraki adımlar

Kurulum/başlatma komutları README'dedir. Araştırma taslağı `research-report.md`, sayısal
tablolar `experimental-results.md`, tam kayıt `evidence-index.json`, demo `demo-guide.md`.
Mevcut dataset/validation/model/algorithm belgeleri geçerlidir; yeni mimari ve tekrar
üretim sınırları architecture/reproducibility belgelerinde kayıtlıdır.

Hosted CI için kullanıcı izinli yayın/dispatch; public dağıtım için kod lisansı seçimi;
ardından dev paket bakım yükseltmeleri ve daha geniş tip/a11y/tarayıcı kapsamı önerilir.
NetworkX değişimi yapılmadı: igraph k/cutoff, normalization ve convergence eşdeğerliği
doğrulanmadan performans iddiası kurulmaz. Gerçek banka stresi için ek finansal veri gerekir.
