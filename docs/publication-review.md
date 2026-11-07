# Yayın öncesi inceleme — Faz 7

Henüz repository oluşturulmadı, public ayarı yapılmadı veya push gönderilmedi.
Bu belge somut yerel dosya paketinin incelemesidir; yayın sonrası başarı raporu değildir.

## Hedef ayarlar

- Hesap: `tubadeligoz`; repository: `financial-network-benchmark`.
- Hedef: https://github.com/tubadeligoz/financial-network-benchmark
- Görünürlük: Public; varsayılan dal: main; Issues açık.
- Açıklama: Finansal ağlarda graf tabanlı darboğaz tespiti, algoritma karşılaştırması
  ve tekrarlanabilir performans analizleri için araştırma platformu.
- Konular: financial-networks, graph-algorithms, network-analysis, benchmarking,
  systemic-risk, graph-visualization, python, react, academic-research.

## Yayın paketi

Backend ve frontend kaynakları, sabit bağımlılık kayıtları, configs, scripts, tests,
sentetik `data/demo`, belgeler, README, CONTRIBUTING, CITATION ve MIT LICENSE.
Tam dosya listesi `docs/publication-files.txt` içindedir. Ham BIS verisi, yerel deneyler,
iş çıktıları, bağımlılıklar, sanal ortam, cache ve loglar dışlanır.
Dokümantasyon JSON kopyalarında yerel kullanıcı/çalışma alanı yolları maskelendi;
asıl yerel deney dosyaları değiştirilmedi.

## README ve görseller

README başlıkları ve açıklamalar Türkçedir; komutlar ve kod adları özgün biçimindedir.
Windows için denenmiş, macOS/Linux için bu ortamda doğrulanmamış kurulum ayrıdır.
Dört gerçek PNG `docs/screenshots` altındadır. Görseller yalnızca açıkça sentetik
banka verisi gösterir. Deney ekranı yapılandırmayı; sonuçlar ekranı gerçek tamamlanmış
ölçümleri gösterir. GitHub'da görüntüleme ancak yayın sonrasında doğrulanabilir.

## Lisans ve ekip

MIT seçimi kullanıcı tarafından açıkça onaylandı. Bu lisans üçüncü taraf paket veya
BIS verisinin koşullarını değiştirmez. BIS atfı ve bağımsız sentetik model ayrımı korunur.
Onaylanan isimler: Tuba Rukiye Dan, Aysu Nacakcı, Özge Çelik, Edanur Aysan.
Kullanıcı bu dört ismin ekip listesinin tamamı olduğunu açıkça teyit etti.
Katkı rolleri ve ORCID bilgileri verilmediğinden uydurulmadı.

## Git ve doğrulama sınırları

Başlangıçta yerel dal master, remote yok, commit/HEAD ve takip edilen dosya yoktu.
Dolayısıyla incelenecek önceki commit geçmişi bulunmuyor; herhangi bir geçmiş silinmedi.
Yayın onayından sonra main oluşturulabilir; force push kullanılmayacak.

Faz 6 kanıtı: 141 backend, 8 frontend testi; sentetik CI eşdeğerinde 3 tarayıcı testi
başarılı ve bir isteğe bağlı BIS testi atlandı. Faz 7 yeniden doğrulama sonuçları
ayrıca kaydedilir. GitHub Actions sunucusunda koşu henüz tetiklenmedi.
macOS/Linux ve GitHub üzerindeki README/PNG görüntüleme doğrulanmış sayılmaz.
Bilinen sınırlar: yerel tek-worker kuyruk, kısmi BIS ülke grafı, gerçek banka sermayesi
yokluğu, sentetik DebtRank, kademeli backend tip kapsamı ve dev bağımlılık uyarıları.

## Yayın kapısı

Dosyalar incelendikten, ekip listesi teyit edildikten ve kullanıcı açık yayın onayı
verdikten sonra repository/remote/main/push, public erişim, görseller ve hosted CI
kontrol edilir. Bu hazırlık talimatı kendi başına yayın onayı değildir.

## Faz 7 son kontrol kaydı

141 Python testi (58.25 s), 8 frontend testi, lint/typecheck ve build yeniden başarılı.
Windows soket kısıtı nedeniyle ilk sandbox test koşusu durduruldu; gerekli izinle tam
koşu tamamlandı. macOS/Linux çalıştırılmadı. Dört PNG gerçek uygulamadan alındı ve
geçerli PNG oldukları doğrulandı; README yolları yerel dosyalara karşı kontrol edildi.

284 yerel Git nesnesi de credential örüntüleriyle incelendi; eşleşme yok. HEAD/branch
geçmişi yoktur ancak erişilemeyen blob/tree nesneleri mevcuttur; bunlar silinmedi.
Bu nesneler yeni main commit'ine kendiliğinden dahil edilmez. Örüntü taraması kapsamlı
bir güvenlik garantisi değildir. `publication-audit.json` bulgu sayılarını içerir.
MIT kullanıcı tarafından onaylandı; üçüncü taraf sürüm/lisans metadata özeti
`third-party-licenses.json` içindedir. Veri ve üçüncü taraf lisansları ayrı kalır.
Yerel README görsel yolları 4/4 doğrulandı; en büyük yayın adayı 194 KB civarındadır. GitHub üzerinde render ve CI onay sonrası ayrıca kontrol edilecektir.

## Kullanıcı yayın onayı

2026-11-08 tarihinde kullanıcı dört kişilik ekip listesini, Public/main yayınını ve push işlemini açıkça onayladı. Ek yayın izni beklenmiyor. GitHub bağlayıcısı Unknown tool hatası döndürüyor; kullanılabilir tarayıcıda oturum açık olmadığından giriş bekleniyor. Repository oluşturma, push ve hosted CI henüz tamamlanmadı.
