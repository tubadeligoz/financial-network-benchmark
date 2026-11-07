# Veri doğrulama

CLI her kaynak dosya ve seçilen dönem için JSON validation report üretir.
Sözdizimi/okuma hatası da raporlanır; uygun olmayan girdiden graf oluşturulmaz.

| Kontrol | Davranış |
|---|---|
| Zorunlu kolon | Eksik veya yinelenen kolon hata |
| Kolon eşleme | Yalnızca açık kaynak→kanonik eşleme; işlem kaydı |
| Dönem | YYYY-Q1..Q4; YYYYQn açık normalizasyonuyla kabul edilir |
| Kimlik | BIS sözlüğündeki ülke/bölge kodu; bilinmeyen kod hata |
| Toplam gruplar | Tanımlı projection dışında; sayıları raporlanır |
| Tekrarlı kayıt | Aynı ülke çifti/dönem hata; toplam veya son satırla ezme yapılmaz |
| Node referansı | Eksik uç veya yinelenen node kimliği hata |
| Sayısal değer | Sonlu sayı zorunlu; negatif hata |
| Eksik gözlem | Varsayılan hata; açık exclude seçimiyle satır bazlı uyarı ve dönüşüm kaydı |
| Sıfır | Varsayılan hata; açık exclude seçimiyle uyarı ve dönüşüm kaydı |
| Self-loop | Varsayılan hata; açık keep ile uyarılı koruma |
| Birim | USD ve UNIT_MULT=6 zorunlu; bilinmeyen birim hata |
| Gizlilik | OBS_CONF=F dışında unavailable; sıfır sayılmaz |
| Kaynak durumu | A normal; B/D/E/I/P/U korunur ve uyarılır; desteklenmeyen durum hata |
| SHA-256 | Manifestte varsa dosyayla eşleşmeli |

`--missing-policy exclude` rastgele bozuk metni veya infinity'yi kabul etmez.
Yalnızca tanımlı boş/NaN/NA/n.a./:/.. değerleri ve nonpublic gözlemler dışlanır.
Bu politika imputasyon değildir. Seçilen tüm kayıtlardaki düğümler korunur;
gözlenen kenar ağı eksik kapsamlı olarak etiketlenir.

Raporda provenans, adapter sürümü, input/selected row sayıları, seçim profili,
politikalar, kolon eşlemesi, satır numarasıyla sorunlar ve dönüşümler bulunur.
`source_row`, başlık dahil tablo satır sırasını belirtir; CSV çok satırlı quoted
alanları varsa fiziksel metin satır numarası değildir. Projection dışlamaları
neden bazında sayılır; kaynak dosya korunur. Hatalı kayıtlar sessizce silinmez.

Başka dönem ve başka boyutlar kapsam dışıdır; bu kayıtların finansal doğruluğunun
doğrulandığı iddia edilmez. Toplu dosyadaki tüm dönemler için CLI ayrı çağrılır.

Gerçek 2025-Q4 kontrolünde strict politika 753 eksik gözlem nedeniyle grafı
reddetti. Açık missing-exclude politikasıyla bu kayıtlar uyarılı olarak dışlandı;
10 kaynak durum uyarısı daha korundu. Ayrıntılı kayıtlar yerel processed klasöründedir.
