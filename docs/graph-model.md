# Graf modeli

`nx.DiGraph`: her snapshot tek dönem ve tek sabit seçim profili içerir.

## Düğüm

`node_id` ve `source_identifier` BIS ülke/bölge kodudur. `entity_type` değeri
`country_or_territory` olur; banka kimliği değildir. `dataset_id` ve `period`
kaydedilir. `available_financial_features` boş sözlüktür: veri sağlamadığı için
özkaynak veya sermaye uydurulmaz. Resmî ülke adı ve kapsam source metadata'dadır.

Düğüm listesi seçilen ülke çifti kayıtlarından türetilir. Eksik gözlem veya
açık sıfır dışlaması nedeniyle izole kalan düğümler korunur. Kaynakta hiç
görünmeyen ülkeler otomatik eklenmez.

## Kenar ve yön

`L_REP_CTY → L_CP_COUNTRY`: A ülkesindeki raporlayan bankalar, B ülkesindeki
tüm sektörlerdeki borçlular üzerinde alacak sahibidir. `OBS_VALUE`, milyon USD
cinsinden kredi/mevduat stokudur. Borç alan → alacaklı yönündeki olası zarar
yayılımı farklı bir modeldir; kenarlar otomatik ters çevrilmez/simetrikleştirilmez.

Alanlar: `source`, `target`, `exposure`, `exposure_unit`, `period`,
`source_metadata.original_fields`, `source_metadata.source_row`.

Aynı ülke düğümünün gelen ve giden tarafındaki kurumsal kapsam simetrik değildir.
Graf üzerindeki bir ülke yolu, aynı kurumların oluşturduğu fonlama veya temerrüt
zincirinin kanıtı sayılamaz. Bu veri **bankalar arası borç ağı** olarak etiketlenmez.

## Tekrarlanabilirlik

Düğümler ve kenarlar sıralanarak eklenir. Grafın SHA-256'sı düğümleri, kenarları,
orijinal alanları, kaynak dosya hash'ini, kaynak sürümünü ve seçim ayarlarını kapsar.
Aynı dosya/manifest/ayar aynı hash'i üretir. Dosya sırası, format veya erişim kaydı
değişirse provenans da değişir; eşdeğer CSV ve Parquet'in aynı graf hash'ini
üretmesi beklenmez. Düğüm/kenar değerleri ayrıca karşılaştırılabilir.

## İstatistikler

Node/edge count, NetworkX directed density, in/out degree histogramları,
düğüm başına weighted in/out strength, weak/strong bileşenler, self-loop sayısı,
ağırlık min/max/ortalama/medyan ve sıralı dağılımı, dönem ve birim JSON'a yazılır.
İzole düğümler sayımlara dahildir. Eksik gözlemler sıfır kenarlar değildir.
Self-loop açıkça tutulursa NetworkX yoğunluğu bunları içerir; n(n-1) paydası
nedeniyle yoğunluk 1'i aşabilir. Varsayılan self-loop politikası hatadır.

## Ağırlık dönüşüm sınırı

Exposure stok tutarıdır. Mesafe ve akış kapasitesi farklı kavramlardır.
`graph/weights.py` saf türetilmiş alan sağlayıcıları için sözleşme tanımlar.
Faz 2'de `inverse_exposure_view`, ayrı bir grafta c/exposure mesafesini hesaplar.
Merkezilik yöntemlerinin tanımları [algoritma belgesindedir](algorithms.md).
