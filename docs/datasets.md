# Veri sözleşmesi ve Faz 0 karar kaydı

## Onaylanan kararlar

Faz 0 raporu ve takip eden kullanıcı onayları bu sohbetten esas alındı:

1. AI4Risk yerine BIS LBS seçildi.
2. 2025-Q4 kamuya açık kesitinin banka-sektörü filtresinde doğrudan ikili
   ülke kayıtları bulunamadı; yalnızca toplamlar geldi. Toplamlar ikili kenar yapılamaz.
3. Kullanıcı, gerçek veri grafı için **raporlayan bankalar → karşı ülkedeki tüm
   borçlu sektörler** kapsamını açıkça onayladı.
4. Faz 1 algoritma, benchmark motoru ve web uygulaması içermez.

Bu tespit bütün BIS dönemlerinde ikili banka verisinin bulunmadığı iddiası değildir.
Şu anda yalnızca doğrulanan profil uygulanır; AI4Risk adaptörü eklenmedi.

## Kaynak, sürüm ve erişim

- Kurum: Bank for International Settlements (BIS), ulusal otoritelerden derlenen istatistikler.
- Kaynak: https://data.bis.org/topics/LBS
- Toplu indirme: https://data.bis.org/bulkdownload
- API: https://stats.bis.org/api-doc/v2/
- Veri akışı: `BIS/WS_LBS_D_PUB/1.0`.
- SDMX sözlük: https://stats.bis.org/api/v2/structure/dataflow/BIS/WS_LBS_D_PUB/1.0?references=all
- Şema ve sözlük erişim tarihi: 2026-11-07.
- Kullanım: https://data.bis.org/help/legal

Kod sözlüğünün kullanılan kopyası `backend/app/datasets/bis_codes.json` içinde
yer alır. Ülke kodları, BIS'in tarihsel kodlarını ve bölgelerini de içeren
sözlüğünden alınmıştır. İki harfli ülke/bölge kodları seçilir; EU, WA, XM ve XW
ülke toplam grupları ayrıca dışlanır. Tarihsel ülke kodları yeniden eşlenmez.

## Gerçek CSV başlıkları

Resmî API'nin CSV yanıtında şu alanlar doğrulandı:

`FREQ, L_MEASURE, L_POSITION, L_INSTR, L_DENOM, L_CURR_TYPE, L_PARENT_CTY,
L_REP_BANK_TYPE, L_REP_CTY, L_CP_SECTOR, L_CP_COUNTRY, L_POS_TYPE, DECIMALS,
UNIT_MEASURE, UNIT_MULT, AVAILABILITY, TITLE_GRP, TIME_FORMAT, COLLECTION,
ORG_VISIBILITY, TIME_PERIOD, OBS_VALUE, OBS_STATUS, OBS_CONF, OBS_PRE_BREAK`.

Bu adaptör kod içeren flat/SDMX CSV ve aynı tabloyu içeren Parquet okur.
Etiketli geniş zaman-serisi CSV'si veya ZIP doğrudan okunmaz; ZIP'i kullanıcı
açmalıdır. Bir kolonun adı farklıysa `--column-map` ile kaynak adından yukarıdaki
ada JSON eşlemesi verilir. Ham kolonlar kenarın `original_fields` alanında korunur.

## Sabit seçim profili

| Boyut | Kod | Anlam |
|---|---|---|
| FREQ | Q | Çeyreklik |
| L_MEASURE | S | Dönem sonu stok tutarı |
| L_POSITION | C | Alacaklar |
| L_INSTR | G | Krediler ve mevduatlar |
| L_DENOM | TO1 | Tüm para birimleri |
| L_CURR_TYPE | A | Tüm para birimi türleri |
| L_PARENT_CTY | 5J | Tüm ana banka ülkeleri |
| L_REP_BANK_TYPE | A | Tüm raporlayan banka türleri |
| L_CP_SECTOR | A | Tüm karşı taraf sektörleri |
| L_POS_TYPE | N | Sınır ötesi |
| UNIT_MEASURE | USD | Raporlama para birimi |
| UNIT_MULT | 6 | Milyon |

`L_DENOM=TO1`, tutarın orijinal sözleşmelerinin yalnızca USD olduğu anlamına
gelmez. USD raporlama birimidir. Exposure sayıları milyon USD olarak korunur;
1.000.000 ile otomatik çarpılmaz. DECIMALS çarpan değildir.

## Provenans ve yerel dosyalar

Manifestte `dataset_id`, `source_url`, `source_version`, `accessed_at`, `data_kind`
zorunlu; `sha256` verildiğinde doğrulanır. `data_kind`: `observed_aggregate` veya
`synthetic`. İşlemde gerçek dosya hash'i her durumda hesaplanır. Ham dosya URL'si,
indirme tarihi, varsa Last-Modified ve kaynak sürümü birlikte saklanmalıdır.
Kaynağın sürüm etiketi gerçek dosya içeriğinin değişmezliğini garanti etmez.

Gerçek dosyalar `data/raw`, çıktılar `data/processed` altında Git dışında tutulur.
Sentetik demo açıkça etiketli olup Git'e alınabilir. İndirme başarısızsa CLI yerel
dosyayla çalışır; sahte gerçek veri üretmez.

## Sınırlamalar

- Gerçek tekil bankalar, özkaynak ve banka kimliği eşlemesi bulunmaz.
- Giden maruziyet sadece raporlayan bankaları; gelen maruziyet tüm sektörleri kapsar.
- Örneklem açık kesitteki ülke çiftleriyle sınırlıdır; tam matris değildir.
- Yayımlanmayan hücreler sıfırla tamamlanmaz, ayna yükümlülük kayıtları eklenmez.
- Stok dönemleri toplanmaz. Dönem karşılaştırmalarında revizyon ve kırılmalar dikkate alınmalıdır.
- Sermaye/zarar karşılama tamponu bulunmadığından DebtRank girdileri mevcut sayılmaz.
