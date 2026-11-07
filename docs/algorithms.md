# Faz 2 — Algoritma sözleşmesi ve matematiksel doğrulama

## Veri ve yorum sınırı

Girdi Faz 1'in pozitif exposure içeren
x.DiGraph` snapshot'ıdır. Yön:
alacaklı → borçlu. BIS profilinde düğümler banka değil ülke/bölgedir; giden
kenarlar raporlayan bankaların, gelenler tüm borçlu sektörlerin kapsamındadır.
Eksik gözlemler sıfır değildir. Bu asimetrik, kısmi ağ üzerindeki yollar gerçek
kurumların temerrüt veya fonlama zincirleri olarak yorumlanamaz.

Yüksek skor, ilgili graf ölçüsünde öne çıkmayı gösterir. Temerrüt olasılığı,
finansal doğruluk veya bütün finansal sistem için evrensel kritiklik ölçüsü değildir.
Algoritmaların farklı skor ölçekleri doğrudan karşılaştırılmaz.

## Ortak arayüz ve değişmez girdi

`AlgorithmSpec`: ID, isim, algoritma sürümü, varsayılan parametreler, desteklenen
graf türleri, ağırlık semantiği, execution method ve sonuç şema kimliği.
`Algorithm.resolve` parametreleri; `validate_graph_parameters` grafa bağlı
kısıtları doğrular. `compute(graph, parameters)` bir `Computation` döndürür.
Yeni yöntem kendi modülünde `Algorithm` sınıfından türetilir ve
`engine.register(CustomAlgorithm())` ile eklenir; mevcut algoritmalar değişmez.
`engine.catalog()` kayıtlı yöntemlerin açıklamalarını verir.

Motor veri provenansını, yönü, birimi ve pozitif sonlu ağırlıkları yeniden kontrol
eder. Kaydedilmiş hash güncel düğüm/kenar/metadata içeriğiyle eşleşmelidir.
Her çağrı sıralı ekleme düzenine sahip derin bir kopya alır. NetworkX yapısal
değişiklikleri engeller; graph/node/edge metadata salt okunur mapping'lere,
iç listeler tuple'a çevrilir. Böylece normal algoritma API'si kaynak grafı
değiştiremez. Bu, güvenilmeyen Python eklentileri için bir güvenlik sandbox'ı değildir.

Unweighted modlar da bozuk exposure içeren kaynak snapshot'ını kabul etmez.
Bozuk veriyi ağırlıkları yok sayarak geçerli gösteren gizli bir dönüşüm yapılmaz.

## 1. Strength / Weighted Degree

Algoritma ID: `strength`; sürüm: `1.0.0`.

Her düğüm i için:

- in_degree: gelen kenar sayısı.
- out_degree: giden kenar sayısı.
- in_strength = Σ_j X_ji.
- out_strength = Σ_j X_ij.
- total_strength = in_strength + out_strength.

X_ij aynı birimdeki exposure stokudur. In-strength ilgili ülkenin tüm borçlu
sektörlerine gelen raporlanmış kredi/mevduat alacağını; out-strength ilgili
ülkenin bankalarının diğer ülkelere alacağını gösterir. Birbirinin tam simetriği
değildir. Total strength iki tarafın toplamıdır, net pozisyon değildir.
Self-loop varsa toplam strength'te iki kez katkı yapar.

Parametre `sort_by`: `in_degree`, `out_degree`, `in_strength`, `out_strength`,
`total_strength` (varsayılan). Her satırın metrics alanında beş ölçü de saklanır.
Strength birimi milyon USD; degree birimi bağlantı sayısıdır.
Tüm düğümler için süre O(n+m), skor çıktısı O(n).

Kaynak: [NetworkX DiGraph.in_degree](https://networkx.org/documentation/stable/reference/classes/generated/networkx.DiGraph.in_degree.html).

## 2. Directed Betweenness

Algoritma ID: `betweenness`; sürüm: `1.0.0`.

C_B(v) = Σ_(s≠v≠t) σ_st(v) / σ_st.
σ_st en kısa s→t yollarının, σ_st(v) bunlardan v üzerinden geçenlerin sayısıdır.
Ulaşılamayan çiftler katkı yapmaz; endpoints=False sabittir. Normalize edilmiş
yönlü sonuç n>2 için (n-1)(n-2) paydasını kullanır. n≤2 için skorlar sıfırdır.

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| mode | unweighted | `unweighted` veya `inverse_exposure` |
| normalized | true | NetworkX yönlü normalizasyonu |
| k | null | null: tüm kaynaklar; pozitif k≤n: yaklaşık kaynak örneklemesi |
| seed | 42 | Yaklaşık örneklemede kullanılan negatif olmayan tamsayı |
| distance_scale | 1.0 | Yalnız weighted modda sonlu, pozitif c |

Unweighted referansta her kenar mesafesi 1'dir. Weighted modda:

**d_ij = c / X_ij**, yol uzunluğu = yolun d değerleri toplamı.

c ortak pozitif ölçektir; güçlü maruziyet daha kısa bağ varsayılır. Gerçek
coğrafi mesafe, işlem maliyeti, zarar olasılığı veya bulaşma zamanı değildir.
Exposure doğrudan yol mesafesi yapılmaz. Dönüşüm yeni distance-only grafta
hesaplanır; kaynak exposure alanı korunur. Sıfır/negatif/nonfinite exposure,
mesafe taşması veya sıfıra yuvarlanması reddedilir.

`k=null` sonucu `exact`; k verilen sonucu `approximate_source_sampling` olarak
etiketlenir. k=n olsa da örnekleme yolu etiketi korunur. Örneklenen kaynakların
kimlikleri, k ve seed metadata'da yer alır. Düğüm eklenme sırası kanonikleştirilir.
Buradaki exact, tüm kaynaklardan arama yapıldığı anlamındadır; keyfî hassasiyetli
aritmetik anlamına gelmez. Float mesafelerde eşit yol tespiti hassas olabilir;
gizli yuvarlama uygulanmaz. Mesafe ölçeği/precision duyarlılığı araştırmada ayrıca
ele alınmalıdır.

Brandes için ağırlıksız süre O(nm); kullanılan binary-heap Dijkstra yaklaşımında
weighted süre yaklaşık O(n(m+n) log n). k kaynakla dış çarpan n yerine k olur.
Çalışma belleği ve graf O(n+m), sonuç O(n). Motorun kopya/hash ve JSON maliyetleri
bu algoritmik sınırdan ayrıdır; bu fazda performans benchmark'ı yapılmaz.

Kaynaklar:
[NetworkX 3.6 betweenness](https://networkx.org/documentation/networkx-3.6/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html),
[Brandes 2001](https://doi.org/10.1080/0022250X.2001.9990249),
[Brandes ve Pich 2007](https://doi.org/10.1142/S0218127407018403).

## 3. PageRank

Algoritma ID: `pagerank`; sürüm: `1.0.0`.

p = α Pᵀ p + (1-α)u. u uniform dağılımdır. Weighted modda P_ij,
X_ij'nin i'nin toplam out-strength'ine bölünmesidir. Unweighted modda çıkış
komşuları eşit olasılıklıdır. Çıkışsız düğümlerin kütlesi uniform dağıtılır.

| Parametre | Varsayılan | Kısıt |
|---|---|---|
| alpha | 0.85 | 0<α<1 |
| tolerance | 1e-8 | 0<tolerance<1; global L1 iterate-difference eşiği |
| max_iterations | 1000 | Pozitif tamsayı |
| weighted | true | Exposure geçiş ağırlığı veya eşit kenar ağırlıkları |

NetworkX n*tol ile durur; motor `tol=tolerance/max(1,n)` gönderir. Bu eşik
iterasyonlar arası farkı belirtir; gerçek skor hatası için garanti değildir.
Yakınsamama
onconverged`, `pagerank_nonconvergence` hata kodu ve boş scores
ile döner. Yarım iterasyon sonucu yayımlanmaz. NetworkX'in döndürmediği gerçek
iterasyon sayısı uydurulmaz.

Alacaklı→borçlu yönünde yüksek PageRank, gelen bağlantılar ve kaynak düğümlerin
ağ konumu üzerinden borçlu konumundaki ülkeleri öne çıkarabilir. Bu özkaynak,
kredi notu veya temerrüt olasılığı değildir. Uniform teleportation, izole
düğümlere de pozitif temel skor verir. Bir düğümün tüm çıkış tutarlarını aynı
katsayıyla çarpmak, o satırın geçiş olasılıklarını değiştirmez; PageRank mutlak
maruziyet büyüklüğünü strength gibi ölçmez.

Seyrek uygulama: T iterasyon için yaklaşık O(T(n+m)) süre ve O(n+m) bellek.
SciPy bağımlılığı pyproject ve sürüm kaydına eklendi.

Kaynaklar:
[NetworkX PageRank](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html),
[Page ve diğerleri 1999](https://ilpubs.stanford.edu:8090/422/).

## Standart sonuç ve sıralama

`fnb.node-scores.v1`: algorithm_id/name/version, dataset_id/version, period,
graph_sha256, parameters, status, scores, metadata, error. Dataset version kaynak
etiketidir; değişmez kimlik için kaynak dosya SHA-256'sı ve graf hash'i de tutulur.
Metadata NetworkX/SciPy sürümlerini ve veri kapsamını kaydeder.

Skorlar azalan, tam eşitlikte node_id alfabetik/lexicographic artan sıralanır.
Rank 1'den başlayan ordinal sıradır; eşit skorlar farklı ordinal rank alır.
Yaklaşık eşit float skorlar gizlice eşitlenmez. Kullanıcı score değerini görerek
bağları değerlendirmelidir; ordinal rank bir finansal fark kanıtı değildir.

`result.top(N)` her pozitif N'yi destekler. JSON ayrıca Top 5/10/20 listelerini
barındırır; N düğüm sayısından büyükse tüm düğümler gelir. Boş graf completed ve
boş scores döndürür. Tek düğümde strength/betweenness=0, PageRank=1'dir.
Desteklenmeyen graf, eski hash, geçersiz parametre veya başarısız hesapta skor
yayımlanmaz. Status: completed, invalid_parameters, invalid_graph, nonconverged,
failed. Hatalı isteklerde nonfinite parametre değerleri JSON güvenliği için
metinsel gösterimle saklanabilir; bunlar hesaplanmış skor değildir.

## CLI

Proje kökünde, Faz 1 grafı mevcutken:

```powershell
.\.venv\Scripts\fnb-score.exe --graph data/processed/bis-all-2025q4/graph.json --algorithm strength --output data/processed/scoring/strength.json --top 10
.\.venv\Scripts\fnb-score.exe --graph data/processed/bis-all-2025q4/graph.json --algorithm betweenness --output data/processed/scoring/betweenness.json
.\.venv\Scripts\fnb-score.exe --graph data/processed/bis-all-2025q4/graph.json --algorithm pagerank --output data/processed/scoring/pagerank.json
```

İstenirse aynı komutlar `python -m app.algorithms.cli` ile çalışır. Parametreler
`--parameters-file` ile bir JSON nesnesinden okunur. Örneğin weighted betweenness:

```json
{"mode": "inverse_exposure", "normalized": true, "distance_scale": 1.0}
```

Yaklaşık sürüm için `{"k":64,"seed":42}`; PageRank için
`{"alpha":0.85,"tolerance":1e-8,"max_iterations":1000,"weighted":true}`.
Komut var olan sonuç dosyasının üzerine yazmaz. Başarı kodu 0; algoritma
başarısızlığında standart hata sonucu JSON'u ve kod 2 döner. Okunamayan/bozuk
snapshot dosyaları skorlamadan önce CLI hatasıyla reddedilir.

## Doğrulama

Sentetik küçük graflardaki elle hesaplanabilir referanslar:

- a→b=10, b→a=4, b→c=6: b in/out strength=10; total=20.
- a→b→c: b raw directed betweenness=1; 3 düğümde normalized=0.5.
- a→b ve a→c, b→d ve c→d: b ve c raw betweenness=0.5.
- a→b=4, b→c=4, a→c=1: unweighted b=0; inverse-exposure b=1 (raw).
- İki düğümlü karşılıklı döngü: PageRank=0.5/0.5.
- a→b, b dangling: p_a=1/(2+α), p_b=(1+α)/(2+α).
- a→b=3, a→c=1, b→a=1, c→a=1 ve α=0.5:
  weighted p=(4/9,1/3,2/9); unweighted p=(4/9,5/18,5/18).

Testler ayrıca boş/tek/izole düğümleri, birden çok bileşeni, tüm geçersiz ağırlık
türlerini, yakınsamamayı, eşit skorları, Top-N'yi, readonly davranışını, eski hash'i,
eklenti kaydını ve örnekleme sırasının tekrar üretimini denetler. Sadece aynı
NetworkX fonksiyonunu ikinci kez çağırmak matematiksel oracle olarak kullanılmaz.

Gerçek BIS 2025-Q4: 218 düğüm, 3.094 kenar. Kaynak graf hash'i:
`685d173adc6d483df20b4c409409035d79554ef86621553a4d93b4c76673e144`.
Strength, exact unweighted/weighted betweenness, k=64 seed=42 approximate
betweenness ve weighted PageRank bu aynı grafta çalıştırıldı. Her yapılandırma
aynı ortamda tekrarlandı; sonuçlar eşleşti ve kaynak graf değişmedi.
[Doğrulama kaydı](phase2-verification.json) Top 5'leri ve parametreleri içerir.
Tam skorlar yerel `data/processed/phase2` dizinindedir; Git dışında tutulur.

## Synthetic financial extension
The registered debtrank method is restricted to explicit synthetic bank balance sheets. See [advanced financial analysis](advanced-financial-analysis.md); received distress and seed impact are separate objectives.
