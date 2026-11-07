# Faz 3 — Ölçülmüş sonuçlar

Bu rapor scripts/report_phase3.py ile saklanmış gerçek ölçümlerden üretildi.
9 deney; trial durumları: {'completed': 260, 'timeout': 10}. Her case için 5 süre + 5 ayrı bellek tekrarı.
Tam ham kayıtlar experiments/<experiment_id>/runs/<run_id> altında korunur.

## Ölçüm ortamı

- Windows-10-10.0.26300-SP0; Python 3.11.1.
- OS bildirimi: AMD64 Family 23 Model 49 Stepping 0, AuthenticAMD; 32 fiziksel / 64 logical CPU; 47.90 GiB RAM.
- Paketler: {'networkx': '3.6.1', 'numpy': '2.4.6', 'pandas': '3.1.1', 'psutil': '7.2.2', 'pyarrow': '26.0.1', 'scipy': '1.17.1'}.
- Uygulama kaynak SHA-256: `c466b9033b4a9a382b89118234cea4eec48637572dc4611ef7fe400d84ab5d58`.
- Bütün run ortam kayıtları eşleşti; başarılı skor tekrarları eşleşti.

## Gerçek BIS 2025-Q4

Alacaklılar raporlayan bankalar, borçlular tüm karşı taraf sektörleridir; düğümler ülke/bölgedir.

| Case | Mean ms | Median ms | Std ms | Min–max ms | Örneklenen RSS medyan MiB | OS süreç tepe medyan MiB |
|---|---:|---:|---:|---|---:|---:|
| betweenness-exact | 22.929 | 22.898 | 0.180 | 22.765–23.212 | 105.39 | 109.74 |
| betweenness-inverse-exact | 57.740 | 58.067 | 1.184 | 55.764–58.915 | 106.41 | 110.17 |
| pagerank | 4.111 | 4.069 | 0.141 | 3.972–4.344 | 111.55 | 115.45 |
| strength | 3.354 | 3.394 | 0.118 | 3.201–3.474 | 105.46 | 109.72 |

Graf: 218 düğüm, 3094 kenar; hash `685d173adc6d483df20b4c409409035d79554ef86621553a4d93b4c76673e144`.
20 timing worker'ında veri okuma/doğrulama medyanı 324.213 ms; graf kurma medyanı 39.210 ms. Algoritma sürelerine dahil değildir.

## Sentetik ER ölçek deneyleri

Directed, weighted, m=4n, seed=42. Betweenness burada exact değil, k=32 unweighted kaynak örneklemesidir.

| n | m | Strength median ms | Betweenness k32 median ms | PageRank median ms |
|---:|---:|---:|---:|---:|
| 100 | 400 | 0.868 | 5.027 | 1.950 |
| 500 | 2000 | 4.086 | 24.651 | 3.407 |
| 1000 | 4000 | 8.496 | 49.890 | 5.052 |
| 5000 | 20000 | 45.757 | 355.548 | 56.939 |
| 10000 | 40000 | 101.507 | 853.868 | 95.165 |

İkinci topoloji: preferential attachment, 500 düğüm/996 kenar, durum completed. ER ile kenar sayısı farklı olduğundan tek başına nedensel topoloji karşılaştırması değildir.
Exact 10.000 düğüm senaryosu: {'timeout': 10}. Bir saniyelik bütçede tamamlanmadı; runtime özetleri null, sıfır değil. Bu, donanımda hiçbir zaman tamamlanamayacağı iddiası değildir.

## Gerçek graf: sıralama uyumu

| Case çifti | Overlap@5 | Jaccard@5 | Spearman |
|---|---:|---:|---:|
| betweenness-exact / betweenness-inverse-exact | 0.600 | 0.429 | 0.899785 |
| betweenness-exact / pagerank | 0.400 | 0.250 | 0.520125 |
| betweenness-exact / strength | 0.400 | 0.250 | 0.555748 |
| betweenness-inverse-exact / pagerank | 0.600 | 0.429 | 0.477520 |
| betweenness-inverse-exact / strength | 0.600 | 0.429 | 0.506597 |
| pagerank / strength | 0.800 | 0.667 | 0.983612 |

Uyum, doğruluk değildir. Cutoff eşitlikleri ve diğer K değerleri JSON kaydında bulunur.

## Dönemsel analiz

2025-Q3 → 2025-Q4: yoğunluk 0.06482762 → 0.06540397. Kaydedilen ortam eşit: True.
- betweenness-exact: ortak n=218, Spearman=0.999960, Overlap@5=1.0; yalnız önceki dönemde=['MS'], yalnız sonraki dönemde=[].
- betweenness-inverse-exact: ortak n=218, Spearman=0.999916, Overlap@5=1.0; yalnız önceki dönemde=['MS'], yalnız sonraki dönemde=[].
- pagerank: ortak n=218, Spearman=0.998083, Overlap@5=1.0; yalnız önceki dönemde=['MS'], yalnız sonraki dönemde=[].
- strength: ortak n=218, Spearman=0.998020, Overlap@5=1.0; yalnız önceki dönemde=['MS'], yalnız sonraki dönemde=[].

Düğüm kümesinin değişmesi örneklem/kapsam değişimidir; ülkenin veya bankanın ortadan kalktığı anlamına gelmez.

## Ölçüm sınırlamaları

- Runtime compute-only kapsamındadır; startup/veri yükleme/ortak sıralama dahil değildir.
- OS tepe RSS; kütüphane, graf, warm-up ve hazırlık belleğini de içerir. Saf algoritma tahsisi değildir.
- Bellek örnekleme hedefi 5 ms; bu suite içinde ölçülen en büyük örnek aralığı 96.923 ms. Kısa tepe değerleri kaçabilir.
- Beş tekrar sınırlı örneklemdir; dış yük, CPU frekansı/termal durum ve OS cache kontrol edilmedi.
- Sabit k ile ölçek deneyinde yaklaşık yöntemin örnekleme oranı değişir; kalite eşitliği varsayılmaz.
- Veriler arasında ham skor ölçekleri eşitlenmedi, accuracy veya temerrüt tahmini üretilmedi.

[Yöntem ve yeniden çalıştırma](benchmark-methodology.md). Kaynak: BIS LBS; açıklamalar resmî BIS çevirisi değildir.
