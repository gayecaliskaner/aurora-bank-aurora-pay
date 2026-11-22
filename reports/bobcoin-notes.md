# Aurora Pay - Bobcoin Tüketim ve Bütçe Karar Notları

## 1. Gerçek Tüketim Verileri ve Kaynak

Bu değerlendirmedeki veriler `reports/bob-run.json` dosyasındaki anlık `stats` nesnesinden ve **Bob Admin Portalı / Bobalytics Dashboard** kullanım metriklerinden alınmıştır.

- **Görev:** Aurora Pay (`services/core/main.py`) modül analizi ve uç nokta dokümantasyonu
- **Harcanan Bobcoin (session_costs):** `0.077972` Bobcoin (~0.078 Bobcoin / USD)
- **Tanımlı Tavan Bütçe (max_cost):** `2.0` Bobcoin
- **Çalışma Süresi (duration_ms):** `22,322` ms (~22.3 saniye)
- **Araç Çağrısı (tool_calls):** `2` adet
- **Veri Kaynağı:** `reports/bob-run.json` (`stats` çıktısı) ve Bob Admin / Bobalytics izleme paneli

---

## 2. Aurora Pay İçin Bütçe Kararı ve Harcama Sınırları

Yapılan tekil modül inceleme çalıştırmasında fiili harcama yalnızca **0.077972 Bobcoin** seviyesinde gerçekleşmiştir. Başlangıçta verilen `2.0` Bobcoinlik tavan sınır, bu tip standart görevler için gereğinden fazla serbestlik tanımaktadır.

Aurora Pay geliştirme süreçlerinde maliyet kontrolü sağlamak amacıyla belirlenen bütçe kararı ve önerilen sınırlar:

### A. Küçük Ölçekli Görevler (Tekil modül analizi, dokümantasyon, basit hata inceleme)
- **Önerilen Minimum Maliyet (Min Cost):** `0.02` - `0.05` Bobcoin
- **Tipik Harcama:** `~0.08` Bobcoin (Ölçülen: 0.077972 Bobcoin)
- **Önerilen `--max-cost` Sınırı:** `0.15` - `0.20` Bobcoin (Bu iş için `0.20` Bobcoin fazlasıyla yeterlidir)
- **Önerilen `--max-turns` Sınırı:** `3` - `5` tur

### B. Orta Ölçekli Görevler (Endpoint geliştirme, bug fix, birim test yazımı)
- **Önerilen Minimum Maliyet (Min Cost):** `0.10` Bobcoin
- **Tipik Harcama:** `0.20` - `0.40` Bobcoin
- **Önerilen `--max-cost` Sınırı:** `0.50` Bobcoin
- **Önerilen `--max-turns` Sınırı:** `8` - `10` tur

### C. Büyük Ölçekli Görevler (Yeni servis mimarisi, kapsamlı refactoring, entegrasyon testleri)
- **Önerilen `--max-cost` Sınırı:** `1.00` - `1.50` Bobcoin
- **Önerilen `--max-turns` Sınırı:** `15` tur

---

## 3. Ekip ve Finans (CFO) Yönetim Tavsiyeleri

1. **Bağlam (Context) Yönetimi:** Sohbet uzadıkça her turda iletilen token miktarı arttığından Bobcoin harcaması katlanarak yükselir. Aurora Pay üzerindeki farklı iş paketleri için her seferinde yeni sohbet/görev oturumu başlatılmalıdır.
2. **Kombine Sınır Kullanımı:** `--max-cost` tek başına çalışan bir turun ortasında kesinti yapamayabileceği için, her zaman `--max-turns` parametresi ile birlikte sınırlandırılmalıdır.
3. **İzleme:** Ekip liderleri ve CFO harcamaları Bob Admin portalı üzerinden anlık, Bobalytics üzerinden ise saatlik agregasyonlar ile takip etmelidir.
