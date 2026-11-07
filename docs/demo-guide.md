# Jüri / hoca demo akışı

Yaklaşık 8–10 dakika. Önce frontend build ve yerel API'yi açın; README komutlarını
kullanın. Gerçek BIS dosyaları yoksa demoyu yalnızca açıkça sentetik kaynaklarla
yapın; gerçek veri gösteriyormuş izlenimi vermeyin. Bu dosya yeni işlev vaat etmez.

1. **Araştırma amacı (1 dk).** Kritik düğüm tanımı yöntemle değişir. Çalışmanın
   sorusu sıralama uyumu, hesaplama maliyeti ve varsayım farkıdır; kriz tahmini değildir.
2. **Veri kaynağı (1 dk).** Datasets'te BIS LBS, sürüm, dönem, doğrulama ve SHA-256'yı
   gösterin. Ülke A bankaları → ülke B tüm sektörler kapsamını ve eksik hücrelerin
   sıfır olmadığını açıklayın. Validation report'u açın.
3. **Graf (1 dk).** Graph Explorer'da 2025-Q4, 60 node görünümü açın. Toplam 218/3094
   ile görünür alt graf ayrımını gösterin. Arama, düğüm ayrıntısı, zoom/fit ve minimum
   exposure filtresini kullanın. Analizin filtrelenmiş çizimden bağımsız olduğunu belirtin.
4. **Kritik düğümler (1 dk).** Strength, unweighted exact betweenness ve weighted
   PageRank overlay'lerini seçin. Eksikse gerçek hesaplamayı başlatın ve tamamlanmasını
   bekleyin. Ülke düğümünü bireysel banka olarak adlandırmayın.
5. **Sıralama karşılaştırması (1 dk).** Results'ta final-bis-2025q4-v1 deneyini seçin.
   Top10, farklı score ölçekleri, Jaccard/Spearman ve cutoff ties açıklamasını gösterin.
   Yüksek uyumun finansal tahmin doğruluğu olmadığını söyleyin.
6. **Maliyet (1 dk).** Zaman ve RSS grafiklerini, beş tekrar, raw/summary ayrımı ve
   kaynak/environment export'unu gösterin. RSS'in süreç tabanını da içerdiğini belirtin.
   CSV/JSON ve bir grafik SVG'sini indirin.
7. **Ayrı sentetik risk modeli (2 dk).** `synthetic-bank-stress`, T0/T1 seçin. C'ye
   0.5 distress veya B/C'ye çoklu şok uygulayın. Varsayımlar/bilanço tablosunu, H₀/Hₜ/R
   ayrımını ve ters yöndeki kırmızı etki oklarını gösterin. Seed impact ranking'in
   senaryoda alınan distress'ten farklı bir hedef olduğunu açıklayın. Sonuçlar kurgu;
   gerçek BIS DebtRank'i değildir. BIS seçimine dönünce uygun olmama gerekçesini gösterin.
8. **Sonuç ve sınırlar (1 dk).** Gerçek kapasite modeli olmadığı için Max-Flow'un
   ertelendiğini, interbank/bilanço verisi olmadan gerçek banka stres iddiası kurulmadığını
   ve exact büyük graf maliyetini açıklayın. Nihai kabul checklist'ini açın; GitHub
   CI koşusu ve kod lisansı gibi açık maddeleri gizlemeyin.

## Demo öncesi kontrol

- `npm run build`, backend testleri ve browser smoke kayıtları mevcut olmalı.
- 8000 portunda tek API açık olmalı; fixture test sunucusu ile proje kökünü karıştırmayın.
- Gösterilecek deneyin dataset/hash/dönemini kontrol edin; farklı koşuları birleştirmeyin.
- Eğer gerçek veri veya eski deney dosyası yoksa ilgili ekranı sentetik olarak sunun;
  ekran görüntüsünü canlı hesaplama sonucuymuş gibi kullanmayın.
- Sayısal bulgular için [experimental-results](experimental-results.md), akademik metin
  için [research-report](research-report.md), sınırlar için [final-delivery-report](final-delivery-report.md).
