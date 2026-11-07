# Faz 5 — Veri yeterliliği ve uygulanabilirlik

İnceleme tarihi: 7 Kasım 2026. Kullanıcı, bağımsız ve açıkça sentetik banka ağında
DebtRank ve stres senaryolarını onayladı. Bu kapsam uygulandı; Max-Flow ertelendi.
Gerçek BIS banka riski hesaplanmadı. Sayısal çıktılar ve test sonuçları
[Faz 5 çalışma raporundadır](phase5-results.md).

## 1. Yerel verinin yeniden kontrolü

`docs/datasets.md`, `docs/graph-model.md`, Faz 4 raporu, gerçek CSV/manifest dosyaları,
Algorithm Engine, benchmark karşılaştırması ve API/UI tipleri incelendi. Her iki gerçek
dosya mevcut BIS adaptörüyle yeniden doğrulandı; graf yeniden oluşturuldu.

| Dönem | Düğüm | Kenar | Finansal node özelliği bulunan düğüm | SHA-256 |
|---|---:|---:|---:|---|
| 2025-Q3 | 219 | 3095 | 0 | `fbaea23ae25b9f10747afc30c9fa5bab093c59ec5629de82d788af511b2c7509` |
| 2025-Q4 | 218 | 3094 | 0 | `685d173adc6d483df20b4c409409035d79554ef86621553a4d93b4c76673e144` |

Sürüm `WS_LBS_D_PUB/1.0`; birim milyon USD; bütün düğümler `country_or_territory`.
`available_financial_features` bütün düğümlerde boş. Gerçek kenar alanları:
`source`, `target`, `exposure`, `exposure_unit`, `period`, `source_metadata`.
Ham şemada banka özkaynağı, sermaye tamponu, ödeme kapasitesi veya vade alanı yok.

Seçim profili `L_POSITION=C`, `L_INSTR=G`, `L_CP_SECTOR=A`, `L_POS_TYPE=N`:
raporlayan bankaların başka ülkelerdeki **tüm sektörlere** sınır ötesi kredi/mevduat
alacak stokları. Ülke çifti tutarı mevcut; banka çifti exposure matrisi mevcut değil.
Grafın giriş ve çıkış tarafındaki kurum kümeleri farklıdır. Ülke düğümünü tek banka
gibi kabul etmek veya yalnızca sermaye alanı eklemek bu uyumsuzluğu gidermez.

BIS'in genel LBS ürünü varlık/yükümlülük pozisyonları içerir; bu projedeki alacak
kesiti tam bilanço değildir. Genel ürün kapsamını yerel dosyada mevcut alan sayamayız.
LBS yerleşiklik esaslı ve konsolide edilmemiş pozisyonları kapsar.
[BIS LBS metodoloji özeti](https://data.bis.org/topics/LBS).

## 2. Yöntem bazında yeterlilik kararı

| Yöntem | Gerekli alan/model | Mevcut | Eksik / veri kalitesi sınırı | Karar |
|---|---|---|---|---|
| Banka DebtRank | Aynı banka evreninde alacak matrisi, pozitif ve tanımı sabit sermaye/özkaynak, değer ağırlıkları, başlangıç şoku | İki dönem, yön, birim ve kısmi ülke çifti stokları | Banka kimliği, interbank kapsamı, sermaye, eşleşen değerleme/bilanço; yayımlanmayan çiftler | Gerçek BIS grafında uygun değil |
| Finansal Max-Flow/Min-Cut | İktisadi anlamı tanımlı kapasite, kaynak/hedef, zaman ufku, akış korunumu ve yön | Sayısal pozitif stok kenarları | Kullanılabilir likidite/ödeme limiti, vade, yeniden yönlendirme ve fon sağlama modeli | Likidite darboğazı olarak uygun değil |
| Finansal stres yayılımı | Seçilen modelin finansal girdileri, şokun birimi ve kanalı | Dönemli topoloji | Sermaye/bilanço ve şokun kayba dönüşüm kanalı; kurumsal kapsam eşleşmiyor | Gerçek banka stresi olarak uygun değil |
| Yapısal hassasiyet | Açık düğüm/kenar müdahalesi ve topolojik ölçüt | Doğrulanmış ülke ağı | Ekonomik kayıp/temerrüt yorumu için veri yok | Ayrı etiketle mümkün; banka stres testi sayılmaz |

Missing hücreler sıfır, ülke strength'i özkaynak, exposure akış kapasitesi olarak
atanmayacak. Özsermayeyi exposure'ın sabit yüzdesi kabul etme, ülkeye tek banka
kimliği verme ve sektörleri simetrikleştirme varsayımları onaylanmış değildir.
Mevcut sentetik demo ve Faz 3 generator ağları da sermaye veya kapasite taşımaz;
`synthetic` etiketi tek başına finansal model yeterliliği sağlamaz.

## 3. DebtRank varyantının matematiksel tanımı

Uygulama: **2012 tek geçişli dinamik, açıkça sentetik muhasebe özkaynağı tamponuyla**. Model ID: `debtrank-single-pass-book-equity`, sürüm `1.0.0`. Özgün uygulamadaki Tier 1/piyasa değeri girdileriyle özdeş olduğu iddia edilmez.
`A_ij`, alacaklı i'nin borçlu j üzerindeki alacağı; `E_i>0` açık tanımlı sermaye
tamponu olsun. Kaynak graf `i→j`; zarar etkisi `j→i` yönündedir:

\[
W_{ji}=\min(1,A_{ij}/E_i),\qquad
v_i=\frac{\sum_j A_{ij}}{\sum_{k,j}A_{kj}}.
\]

Payda sıfırsa değer ağırlığı tanımsızdır; eşit ağırlıkla sessizce tamamlanmaz.
`h_i(0)=ψ_i∈[0,1]`; pozitif şoklu düğümler D, diğerleri U başlar.
Her adımda eşzamanlı güncelleme:

\[
h_i(t+1)=\min\left(1,h_i(t)+\sum_{j:s_j(t)=D}W_{ji}h_j(t)\right).
\]

Önceki D düğümleri I olur; önceki U düğümlerinden pozitif distress alanlar D olur;
I yeniden yaymaz. D kalmayınca durulur; her düğüm en fazla bir kez yayar.

\[
H_0=\sum_i v_iψ_i,\quad H_T=\sum_i v_ih_i(T),\quad R=H_T-H_0.
\]

`0≤h_i≤1`, `0≤R≤1-H_0`. Ek yayılım başlangıç distress'inden ayrıdır.
`v` burada ağ içi alacak payıdır; toplam ekonomi varlık payı değildir.
Bu model distress yayılımıdır; ödeme tasfiyesi veya temerrüt olasılığı modeli değildir.
[Battiston ve diğerleri, 2012, Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC3412322/).

2015 muhasebe temelli varyant, `Λ_ij=A_ij/E_i` ve distress **artışları** üzerinden
tekrar yayılım kullanır. Tek geçişli kural ile aynı sonuçları vermesi beklenmez.
Bu varyant seçilirse yakınsama toleransı, maksimum adım, sermaye tanımı ve durma
durumu ayrı sürümde kaydedilmelidir; sonuçlar tek geçişli modelle birleştirilmez.
[Bardoscia ve diğerleri, 2015](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0130406).

## 4. Onaylanan sentetik uygulama sözleşmesi

Gerçek BIS ülke grafından bağımsız, `SYNTHETIC — NOT CALIBRATED TO BIS` etiketli
hayali banka ağı kullanılır. Düğümler `SYN-BANK-A` gibi kimlikler taşır; gerçek banka
veya ülke adına hayali sermaye eklenmez. Bütün finansal tutarlar aynı sentetik birimde olur.

Her banka için pozitif sermaye tamponu ve tanımı; tercih edilen bilanço modelinde
dış varlıklar, dış yükümlülükler ve muhasebe özkaynağı açıkça kaydedilir. Sermaye
tamponu ile muhasebe özkaynağı/Tier 1 otomatik eşitlenmez. Bilanço modeli kullanılacaksa
`dış varlık + Σ alacak − dış yükümlülük − Σ borç = muhasebe özkaynağı` doğrulanır.
Senaryo üreticisinin dağılımı, seed'i ve ürettiği finansal alanlar kaydedilir.

Onaylanan kapsam:

- Tek şoklu banka; sonra aynı anda birden fazla banka.
- Başlangıç şoku, açıkça sermaye tamponu üzerinden göreli distress `ψ` olarak tanımlanır.
  Yüzde 10 sermaye distress'i yüzde 10 toplam varlık kaybı olarak adlandırılmaz.
- Kullanıcı tarafından seçilen farklı `ψ` değerleri; hiçbir büyüklük gerçek veriyle
  kalibre edilmiş kabul edilmez.
- İki sentetik dönem ancak aynı kurum kimlikleri ve her dönemin sermaye/exposure
  kayıtlarıyla karşılaştırılır. Gerçek BIS Q3/Q4 için banka stresi sonucu üretilmez.

Kullanıcı ayrı sentetik banka modelini seçti. `synthetic-T0` ve `synthetic-T1`
aynı beş hayali kurumu içerir. Her ikisinde de beş alacak kenarı ve iki weak component
vardır; E bankası izoledir. Bu dönem etiketleri gerçek tarih değildir.

## 5. Max-Flow/Min-Cut kararı ve alternatif

Matematiksel akış için `0≤f_ij≤c_ij`, ara düğümlerde giriş=çıkış ve kaynak/hedef
gerekir. Min-cut, S'den T'ye yönlü kesit kenarlarının kapasite toplamıdır.
NetworkX kapasite alanı yoksa sonsuz kapasite varsayabilir; uygulama öncesinde
bütün kapasite alanları sonlu ve açık tanımlı doğrulanmalıdır.
[NetworkX maximum_flow sözleşmesi](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.maximum_flow.html).

Exposure stokunu `c_ij` seçmek matematiksel bir optimizasyon oluşturabilir; bu seçimin
ekonomik kapasiteyi temsil ettiğini doğrulamaz. Mevcut veriden finansal darboğaz sonucu çıkarılmayacak.

İkinci bir aşamada **ayrı sentetik fon transferi modeli** önerilebilir: belirli zaman
ufkunda kullanılabilir yönlü transfer limitleri, kaynak likiditesi, hedef ihtiyacı,
ara kurumlarda aktarım varsayımı. Bu modelde `capacity` exposure'dan bağımsız alandır;
netleştirme, teminat ve zamanlama yok sayılıyorsa açık yazılır. Source/target, max-flow,
flow haritası, cut partition/edges/capacity döndürülür. Finansal uygulanabilirlik
yalnızca bu tanımlanmış model içinde yorumlanır. İlk önerilen DebtRank kapsamına
otomatik dahil değildir.

## 6. Uygulanan model ve sonuç sözleşmesi

`backend/app/datasets/synthetic_banks.json` sürümlü, elle tanımlanmış ve tamamen
kurgusal girdidir; rastgele kalibrasyon yapılmaz. Bütün bankalarda dış varlık 200
sentetik parasal birimdir. Özsermaye ve dış yükümlülükler dosyada açıkça kayıtlıdır.
Validator, pozitif özsermayeyi, negatif olmayan dış kalemleri, tutarlı birim/dönemi,
tek banka evrenini, bilanço özdeşliğini ve sıfır olmayan değer ağırlığı paydasını kontrol eder.

T0 özsermayeleri A/B/C/D/E için 100/80/60/50/40; T1 için 80/60/50/45/40'tır.
T0 alacakları A→B=20, B→C=40, C→A=10, A→D=15, D→C=30; T1 alacakları
30/60/15/15/40'tır. Gözlenmeyen bir BIS çiftine sıfır atanmamıştır; bu bağımsız,
tam tanımlı kurgu ağda dosyada olmayan çiftlerin sıfır olduğu model varsayımıdır.

Algoritma ID `debtrank`; model `debtrank-single-pass-book-equity/1.0.0`.
İki çıktı hedefi açıkça ayrılır:

- `mode=scenario`: `initial_shocks` bankadan [0,1] distress'e eşler. Düğüm skoru son `h_i`;
  node metrics başlangıç ve ek distress'i içerir. Metadata'da H₀, Hₜ, R, şoklu küme,
  ek distress alan düğümler, durma nedeni, adım/durum geçmişi ve ters yönlü etkiler bulunur.
- `mode=impact_ranking`: her banka ayrı ayrı `shock_magnitude` ile şoklanır. Düğüm skoru
  o bankanın şokunun ürettiği R'dir; bu skoru senaryoda bankanın aldığı distress ile karıştırmayın.
  Her seed için sonuç ve model parametreleri saklanır. Bu modda `initial_shocks` boş olmalıdır.

Varsayılan mode scenario ve boş şok haritasıdır; boş şok sıfır yayılım verir. Scenario
modundaki büyüklükler yalnızca `initial_shocks` içindedir. Ranking büyüklüğü varsayılanı 1'dir.
Bilinmeyen parametre, banka veya geçersiz büyüklük hatadır. Model en fazla 500 bankayı kabul eder.

Hesaplama eşzamanlıdır. Önceki D düğümü bir sonraki adımda I olur. I düğümleri ek distress
alabilir ama tekrar yaymaz. Durma D kalmamasıdır; azami yayılım adımı banka sayısıyla sınırlıdır.
Matematiksel tarama maliyeti scenario için O(n(n+m)), seed ranking için O(n²(n+m)) üst sınırındadır. Bu Python sürümü deterministik kenar sıralaması da yapar; sıralama maliyeti için genel durumda her adımda ayrıca O(m log(m+1)) hesaba katılmalıdır.
Geçmişi tutulan senaryonun belleği en kötü O(n(n+m)); seed ranking geçmiş saklamaz fakat tüm
seed sonuçları nedeniyle O(n²) çıktı üretebilir. Değerler IEEE-754 float ile hesaplanır.

`v_i` yalnızca ağ içi alacak payıdır. İzole E'nin ağırlığı sıfırdır; E'ye başlangıç
şoku verildiğinde node distress görülebilir ama bu ağırlıkla aggregate katkısı sıfırdır.
Bu bir eksik veri tamamlama işlemi değildir ve toplam ekonomi zararını ölçmez.
Üçüncü taraf kurtarma, ödeme sırası, netleştirme, mevduat kaçışı, teminat ve fire sale yoktur.
Sermaye proxy'sinin muhasebe özkaynağı olması özgün Tier 1/piyasa değeri uygulamasıyla
sonuçların otomatik karşılaştırılabileceği anlamına gelmez.

## 7. Engine, benchmark, API ve arayüz

Yeni `DebtRank` modülü mevcut Algorithm Engine'e kaydedilir; salt okunur snapshot ve
hash kontrolü korunur. Sonuçlarda dataset/sürüm, dönem, graph hash, algorithm/model
sürümü, parametreler, varsayımlar, risk skorları, status ve experiment ID vardır.
`scenario_sha256` model, graph hash ve parametreleri bağlar. Finansal alan veya kurum
kapsamı yetersizse hesaplama reddedilir; sonuçlar uydurulmaz.

Benchmark, aynı yeni kaynak türü `synthetic_financial` üzerinden mevcut süreç temelli
runtime ve ayrı RSS ölçümünü kullanır. Risk/merkezilik veya farklı DebtRank şok/hedef
konfigürasyonları otomatik ranking karşılaştırmasına girmez. Hariç tutma gerekçesi
`summary.comparison_exclusions` içinde ve UI'da görünür. Süre/bellek maliyeti kıyaslamak
farklı yöntemlerin aynı finansal soruyu yanıtladığı anlamına gelmez. Existing BIS temporal
analizi aynen korunur; sentetik dönemler o tarihsel analiz yoluna sokulmaz.

PowerShell, proje kökünde:

```powershell
.\.venv\Scripts\python.exe -m app.benchmark.cli run --config configs/benchmarks/synthetic-debtrank.json
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Yeni API uçları:

- GET `/api/v1/datasets/{dataset}/periods/{period}/financial-eligibility`: uygunluk/gerekçe,
  sentetik finansal girdiler ve model varsayımları.
- POST `/api/v1/stress-tests`: dataset, periods, shocked_nodes, shock_magnitudes;
  HTTP 202 job döner. Her dönem/büyüklük için bir group scenario ve ayrı seed ranking hesaplanır.
- GET `/api/v1/stress-experiments?dataset=synthetic-bank-stress`: tamamlanmış kayıtlar.
- GET `/api/v1/stress-experiments/{id}/export?format=json|csv`: varsayım ve skorları içeren export.
- Mevcut `/analyses` ve `/benchmarks` uçları da `algorithm_id=debtrank` destekler.

Stress deneyleri `data/processed/web/stress` altında; benchmark deneyleri `experiments`
altındadır. Job timeout/iptal ve kaynak hash'inin yeniden kontrolü korunur. Uygunsuz BIS
isteği HTTP 422 döner. Max-Flow kaydı veya exposure→capacity dönüşümü eklenmedi.

Web: `synthetic-bank-stress` kaynağını ve kurgu dönemi seçin. Graph Explorer → Synthetic
financial stress lab bölümünde bankaları ve virgülle ayrılmış şok büyüklüklerini seçin.
Başlangıç varsayılanı C bankası, büyüklükler 0.1/0.5/1'dir; bunlar yalnızca kurgu ayarlarıdır.
İsterseniz T0/T1'i birlikte çalıştırın. Graph overlay'inde kırmızı çerçeve başlangıç şoku,
kehribar renk distress, kırmızı ters oklar seçilen adımdaki borçlu→alacaklı etkisidir.
Kenarın parasal exposure bilgisi değişmez. Geçmişteki `potential_distress_increment` bir
etki katkısıdır; h=1 kırpılması nedeniyle gerçekleşen ek distress ile aynı olmayabilir.
Risk overlay'i kapatılınca normal merkezilik görünümüne dönülür. Graph etiketlerinde
Bank A gibi kısaltmalar kullanılır; tablolar/arama/export tam SYN-BANK kimliklerini korur.

Results & Analysis aynı kayıtları, H₀/Hₜ/R karşılaştırmasını, senaryo parametrelerini ve
ayrı seed sistemik etki sıralamasını gösterir. Risk skorları merkezilik matrislerine
karıştırılmaz. Kaynak uygun değilse panel veri eksikliğini açıklar. Senaryo karşılaştırma
çubuğu H₀ ve R'yi ayrı gösterir; Hₜ ayrıca tabloda yazılıdır. Bütün finansal çıktılar sentetiktir.

## 8. Doğrulama ve sınırlar

Yeni testler iki banka aritmetiği, yön, zincir, cycle, eşzamanlı şoklar, izole bileşen,
D→I ve durma, bounds, başlangıç/ek distress ayrımı, eksik/bozuk sermaye/birim/bilanço,
bilinmeyen şok kimliği, tekrar üretim ve değişmez girdiyi kontrol eder. İki bankalı örnekte
A→B=20, E_A=100 ve B şoku 0.5 iken A'nın distress'i 0.1'dir. Bu sentetik matematiksel oracle'dır.
Gerçek süreçli benchmark testi risk ve strength arasındaki ranking karşılaştırmasının
hariç tutulduğunu ve 5 zaman + 5 bellek denemesinin tamamlandığını doğrular.
API testi çoklu şok/iki dönem sonuçlarını ve JSON/CSV export'u doğrular. Chromium testi
aynı akışı gerçek yerel backend üzerinde, API mock'u kullanmadan çalıştırır.

Test sayıları, çalıştırılmış örnekler, ortam ve gerçek üretilen graf sürümleri
[çalışma raporunda](phase5-results.md) bulunur. Model sentetik eğitim/araştırma senaryosudur;
gerçek banka kaybı, temerrüt olasılığı, likidite darboğazı veya düzenleyici stres testi sonucu değildir.
Gerçek uygulama için aynı banka evreninde dönemli bilateral maruziyet, tanımlı sermaye ve
uygun bilanço/şok kanalı gerekir. Böyle bir veri veya alternatif model eklenmesi bu sürüme
kendiliğinden yetki vermez. Faz 6 için ayrıca kullanıcı onayı beklenir.
