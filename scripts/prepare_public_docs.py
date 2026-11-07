"""Prepare Turkish public documentation without publishing or assigning a license."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'README.md'
s=p.read_text(encoding='utf-8-sig')
headings={'1. Project Overview':'Projenin Amacı','2. Research Objectives':'Araştırma Soruları','3. Features':'Projenin Özellikleri','4. Technology Stack':'Teknolojiler','5. Architecture':'Sistem Mimarisi','6. Installation':'Kurulum Rehberi','7. Dataset Setup':'Veri Setleri ve Hazırlama','8. Running the Backend':'Backend Servisini Başlatma','9. Running the Frontend':'Web Arayüzünü Başlatma','10. Running Benchmarks':'Performans Karşılaştırması','11. Reproducing Experiments':'Deneylerin Yeniden Üretilmesi','12. Test Instructions':'Testler ve Kurulum Doğrulama','13. Project Limitations':'Bilinen Sınırlamalar','14. References':'Kullanılan Kaynaklar ve Atıf','15. License Information':'Lisans'}
for old,new in headings.items():s=s.replace('## '+old,'## '+new)
s=s.replace('# Financial Network Benchmark\n','# Financial Network Benchmark\n\n**Finansal Ağlarda Graf Tabanlı Darboğaz Tespiti ve Algoritma Performans Analizi**\n',1)
s=s.replace('Tüm','Tüm')
s+='''

## Araştırma Sorularının Kapsamı

1. Hangi ülke/bölge düğümleri yapısal olarak kritiktir?
2. Farklı yöntemlerin seçtiği düğümler hangi ölçüde örtüşür?
3. Çalışma süresi ve bellek tüketimi nasıl değişir?
4. Graf büyüdüğünde maliyet nasıl ölçeklenir?
5. Dönemler arasında sıralamalar nasıl değişir?
6. Benzerlikler hangi varsayımlarda anlamlıdır?

Gerçek veri ülke düzeyindedir; bireysel kurumların belirlenmesi iddia edilmez. Yazılım
kişisel yatırım veya finansal karar tavsiyesi üretmez.

## Uygulamanın Gerçek Ekran Görüntüleri

Aşağıdaki görseller çalışan uygulamadan alınmıştır. Görsellerdeki banka ağı ve
finansal tutarlar **açıkça sentetiktir**, gerçek banka verisi değildir.

### Veri Setleri
![Veri kaynakları, dönemler ve doğrulama bilgileri](docs/screenshots/datasets.png)
### Graf Keşif Ekranı
![Sentetik finansal ağın etkileşimli grafı](docs/screenshots/graph-explorer.png)
### Deney Yapılandırma Ekranı
![Yöntem seçimi ve deney parametreleri](docs/screenshots/benchmarks.png)
Bu ekran deneyi yapılandırır; süre ve bellek karşılaştırma grafikleri sonuçlar ekranındadır.
### Sonuçlar ve Analiz
![Tamamlanmış deneylerin ölçümleri ve düğüm sıralamaları](docs/screenshots/results.png)

## Veri Akışı

```mermaid
flowchart LR
 A[Veri seti ve kaynak kaydı] --> B[Veri doğrulama]
 B --> C[Yönlü ağırlıklı graf]
 C --> D[Salt okunur algoritma motoru]
 C --> E[Ayrı süreçlerle deney motoru]
 E --> D
 D --> F[JSON ve CSV sonuçları]
 F --> G[FastAPI]
 G --> H[React ve etkileşimli görselleştirme]
```

CSV/Parquet okuma ve doğrulama veri modülünde, graf kurma NetworkX katmanında,
yöntemler algoritma motorunda yürütülür. Deney motoru ham ölçümleri ve ortamı dosyalarda
saklar; SQLite kullanılmaz. Tarayıcı gerçek FastAPI sonuçlarını alır; sabit başarı
sonuçlarıyla gerçek hesaplama taklit edilmez.

## Graf Algoritmaları

| Yöntem | Girdi ve çıktı | Yorum |
|---|---|---|
| Ağırlıklı giriş/çıkış derecesi ve güç | Yön ve maruziyet; düğüm başına derece ve tutar toplamı | Maruziyet büyüklüğü |
| Arasındalık merkeziliği | Yönlü graf; birim adım veya açık c/exposure mesafesi; düğüm skoru | Yapısal kısa yol aracılığı; gerçek bulaşma kanıtı değil |
| PageRank | Yönlü ağırlıklı/ağırlıksız graf ve yakınsama ayarları | Borçlu yönünde önem; temerrüt olasılığı değil |
| DebtRank | Yalnızca bağımsız sentetik banka ağı ve özkaynak/şoklar | Alınan distress ile ayrı başlangıç düğümü etkisi ayrılır |

Max-Flow/Min-Cut uygulanmadı; maruziyet stoğu likidite kapasitesi sayılmaz.
Yöntemler aynı matematiksel sorunu çözmez. Süre, ayrı süreç RSS belleği, tekrar,
ortalama/medyan/standart sapma/minimum/maksimum, ölçeklenebilirlik, ilk K örtüşmesi,
Jaccard ve Spearman ölçülür. Sıralama benzerliği tek başına doğruluk kanıtı değildir.

## Kuruluma Başlamadan Önce

Doğrulanan ortam: Windows, Python 3.11.1, Node.js 24.22.1, npm 11.6.2.
Python minimum sürümü 3.11'dir. Git ve Node/npm PATH üzerinde olmalıdır.
Resmî kurulumlar: [Python](https://www.python.org/downloads/),
[Node.js](https://nodejs.org/en/download), [Git](https://git-scm.com/downloads).

```bash
git clone https://github.com/tubadeligoz/financial-network-benchmark.git
cd financial-network-benchmark
```

Hedef adres yayın planıdır; açık yayın onayından önce reponun mevcut olduğu iddia edilmez.

### macOS ve Ubuntu

Bu komutlar proje yapısına uyarlanmıştır; **bu oturumda macOS/Linux üzerinde çalıştırılmadı**.
Python 3.11+, Node 24 ve Git'i kurduktan sonra:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-lock.txt
python -m pip install --no-deps -e backend
cd frontend
npm ci --no-audit --no-fund
npm run build
cd ..
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell komutları yukarıdaki Kurulum Rehberi bölümündedir. Ortamı
etkinleştirmek isterseniz ` .\\.venv\\Scripts\\Activate.ps1 ` kullanın; yürütme ilkesi
engelliyorsa sistem ilkesini değiştirmek yerine belgelenmiş tam Python yolunu kullanın.
Sistem API anahtarı gerektirmez. `.env` otomatik yüklenmez; gerekirse `FNB_PROJECT_ROOT`
ortam değişkeniyle proje kökü seçilir. Gerçek gizli anahtar içeren örnek dosya yoktur.

### Yaygın Kurulum Hataları

| Sorun | Kontrol |
|---|---|
| Python/Node bulunamıyor | Kurulumdan sonra terminali yeniden açın; PATH ve sürümü doğrulayın |
| Port kullanımda | Aynı projeye ait önceki sunucuyu kapatın; başka süreçleri gelişigüzel sonlandırmayın |
| Backend bağlantısı/CORS | API 8000, geliştirme arayüzü 5173; belgelenmiş yerel adresleri kullanın |
| Veri bulunamadı | İndirme klasörünü ve manifesti kontrol edin; sentetik kaynaklarla başlayabilirsiniz |
| Python bağımlılığı eksik | Aynı sanal ortamın Python'u ile requirements dosyasını kurun |
| Web derleme hatası | Node/npm sürümünü doğrulayın ve frontend içinde npm ci çalıştırın |
| Kaynak değişti hatası | Dosya doğrulamasından sonra API'yi yeniden başlatın |

## Nasıl Kullanılır?

1. API ve arayüzü açın; veri setini ve dönemi seçin.
2. Doğrulama raporunu açın; kaynak kapsamını ve sentetik/gerçek ayrımını inceleyin.
3. Graf keşif ekranında düğüm arayın; düğüm/kenar seçimi, zoom ve filtreleri kullanın.
4. Yöntemi seçip hesaplayın; hesaplanmamış skorları sonuç sanmayın.
5. Deneyler ekranında yöntem, tekrar ve parametreleri belirleyip çalıştırın.
6. Gerçek iş durumu tamamlanınca sonuçları açın; uygun sıralama karşılaştırmalarını inceleyin.
7. JSON/CSV veya grafik SVG'sini indirin. Sentetik finansal stres için ayrı banka kaynağını seçin.

## Proje Klasör Yapısı

```text
financial-network-benchmark/
├── backend/       # Veri, graf, yöntemler, deney motoru ve API
├── frontend/      # React arayüzü ve tarayıcı testleri
├── configs/       # Çalıştırılabilir deney ayarları
├── data/demo/     # Açıkça sentetik küçük veri
├── tests/         # Python doğruluk ve entegrasyon testleri
├── docs/          # Araştırma, kullanım ve gerçek ekran görüntüleri
├── scripts/       # İndirme, ölçüm ve rapor araçları
└── README.md
```

Yerel `data/raw`, `data/processed` ve `experiments` klasörleri çalışırken oluşur;
varsayılan public dosya paketine dahil değildir.

## Deneysel Sonuçlar

Aşağıdakiler final Q4 BIS ülke grafının gerçek ölçümleridir (218 düğüm, 3094 kenar).

| Yöntem | Medyan süre (ms) | Medyan süreç RSS (MiB) |
|---|---:|---:|
| Güç | 3.5964 | 103.309 |
| PageRank | 4.3928 | 112.832 |
| Birim adımlı exact arasındalık | 22.9319 | 104.035 |
| Ters maruziyetli exact arasındalık | 57.9705 | 105.391 |

Her yöntem için 5 zaman ve 5 ayrı bellek denemesi yapıldı. Bunlar tek bilgisayardaki
gözlemlerdir; RSS süreç tabanını içerir. Ayrı sentetik DebtRank sonuçları, kritik düğüm
sıralamaları, benzerlikler ve tarihsel ölçek deneyleri [ayrıntılı raporlardadır](docs/experimental-results.md).
Ortam, donanım, sürümler ve kaynak hash'leri rapor kayıtlarında korunur. Rastgelelik tohumu
örnek ayarlarda 42, tekrar sayısı 5'tir; her koşunun asıl ayarı kendi dosyasında kayıtlıdır.

## Kullanılmayan Veri Adayları

AI4Risk ve HEIDIcell başlangıç adaylarıydı; mevcut uygulamada kullanılmazlar.
Birincil gerçek kaynak BIS LBS'dir. Banka ilişkileri bilanço verisinden yeniden
oluşturulmuş gibi sunulmaz; BIS'in yayımladığı ülke toplamları grafa yansıtılır.

## Projeye Katkıda Bulunma

Türkçe [katkı rehberini](CONTRIBUTING.md) izleyin. Onaylı ekip/yazar bilgileri ve
nihai kod lisansı yayın öncesi tamamlanacaktır. `CITATION.cff` bu bilgiler gelene kadar
açıkça işaretlenmiş bir taslaktır; bireysel katkılar veya yazarlar tahmin edilmez.
'''
if '## Araştırma Sorularının Kapsamı' not in p.read_text(encoding='utf-8-sig'):
 p.write_text(s,encoding='utf-8')
# Public documentation copies are redacted; original local experiment files remain intact.
def clean(v):
 if isinstance(v,str):return v.replace(str(root),'<PROJECT_ROOT>').replace(root.as_posix(),'<PROJECT_ROOT>').replace(str(Path.home()),'<USER_HOME>').replace(Path.home().as_posix(),'<USER_HOME>')
 if isinstance(v,list):return [clean(x) for x in v]
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 return v
for path in (root/'docs').glob('*.json'):
 value=json.loads(path.read_text(encoding='utf-8-sig'));path.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2),encoding='utf-8')
print('Turkish public README prepared; local paths redacted from documentation JSON copies.')
