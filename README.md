# Elektrik Fiyat Takip Sistemi

Avrupa elektrik piyasalarına ait saatlik gün öncesi fiyatlarını ve üretim karması verilerini toplayıp depolayan, web tabanlı bir gerçek zamanlı izleme panelidir.

---

https://github.com/user-attachments/assets/3e4f8365-cf5a-41b3-a1b1-4dda810ce322

## Ne Yapar

Uygulama, açık kaynaklı elektrik piyasası API'lerinden canlı veri çeker, yerel bir veritabanında saklar ve bir web paneli aracılığıyla sunar. Ülkeler arasında geçiş yapılabilir; saatlik fiyat grafiği, üretim karması dağılımı, fiyat volatilitesi ve 24 saatlik fiyat tahmini görüntülenebilir. Veriler saatte bir otomatik olarak güncellenir.

---

## Veri Kaynakları

Tüm kaynaklar tamamen açıktır, kayıt gerektirmez, API anahtarı yoktur.

| Kaynak | Sağlayıcı | Veri |
|--------|-----------|------|
| [Energy-Charts API](https://api.energy-charts.info) | Fraunhofer ISE | Gün öncesi fiyatlar — DE, FR, IT, ES, PL |
| [SMARD](https://www.smard.de) | Bundesnetzagentur | Üretim karması (güneş, rüzgar, su, kömür, gaz, nükleer) — yalnızca DE |

Fiyatlar EUR/MWh cinsindendir. Son 48 saatlik veri tutulur, saatte bir yenilenir.

---

## Özellikler

- Son 24 saatin saatlik fiyat zaman serisi grafiği
- Üretim karması dağılımı (yalnızca Almanya)
- Yenilenebilir enerji oranı: güneş + rüzgar + su (yalnızca Almanya)
- Fiyat volatilite istatistikleri: ortalama, standart sapma, min/maks, varyasyon katsayısı
- Fiyat spike tespiti (eşik: 24 saatlik ortalamanın 1.5 katı)
- Tüm desteklenen piyasalar için 24 saatlik ortalama fiyat karşılaştırması
- Özel ARIMA implementasyonuyla 24 saatlik fiyat tahmini
- Arka planda saatte bir otomatik veri güncelleme
- Panel üzerinden manuel yenileme butonu

---

## Desteklenen Ülkeler

| Ülke | Fiyat | Üretim Karması |
|------|-------|----------------|
| Almanya (DE) | Var | Var |
| Fransa (FR) | Var | Yok |
| İtalya (IT) | Var | Yok |
| İspanya (ES) | Var | Yok |
| Polonya (PL) | Var | Yok |

---

## Kullanılan Teknolojiler

**Backend**
- Python 3.11
- Flask — web framework ve REST API
- Flask-CORS — cross-origin istek yönetimi
- PyMongo — MongoDB sürücüsü
- Requests — dış API istekleri için HTTP istemcisi

**Veritabanı**
- MongoDB — elektrik fiyatları ve üretim karması verilerini ülke + zaman damgası bileşik indeksiyle saklar

**Frontend**
- Vanilla JavaScript
- Chart.js — çizgi grafik, halka grafik, yatay çubuk grafik
- IBM Plex Mono / IBM Plex Sans

**Analitik** (harici ML kütüphanesi kullanılmadan özel implementasyon)
- ARIMA tabanlı fiyat tahmini (yalnızca NumPy)
- Volatilite ve spike tespiti (standart kütüphane `statistics`)
- Yenilenebilir enerji oranı hesaplama

**Veri Pipeline**
- `energy_charts_fetcher.py` — beş ülke için fiyat verisi çeker
- `smard_fetcher.py` — Almanya için üretim karması çeker

---

## Kurulum

**Gereksinimler**
- Python 3.11+
- Localhost'ta çalışan MongoDB (`27017` portu)

**Bağımlılıkları yükle**

```bash
pip install flask flask-cors pymongo requests numpy
```

**Veritabanını başlat**

```bash
python database/models.py
```

**Uygulamayı çalıştır**

```bash
python app.py
```

Sunucu `http://localhost:5000` adresinde başlar. Başlangıçta en güncel veri arka planda otomatik olarak çekilir; panel 15–30 saniye içinde hazır olur.

**Veriyi manuel çekmek için**

```bash
python data_pipeline/energy_charts_fetcher.py
python data_pipeline/smard_fetcher.py
```

---

## API Endpoint'leri

| Endpoint | Açıklama |
|----------|----------|
| `GET /api/prices/<country>` | Son 24 saatin saatlik fiyatları |
| `GET /api/generation/<country>` | En güncel üretim karması (yalnızca DE) |
| `GET /api/volatility/<country>` | Son 24 saatin volatilite istatistikleri |
| `GET /api/renewable/<country>` | Yenilenebilir enerji oranı (yalnızca DE) |
| `GET /api/comparison` | Tüm ülkeler için 24 saatlik ortalama fiyat |
| `GET /api/predict/<country>` | 24 saatlik fiyat tahmini |
| `GET /api/status` | Ülke bazında veri durumu |
| `GET /api/refresh` | Manuel veri yenileme tetikleyici |

Ülke kodları: `DE`, `FR`, `IT`, `ES`, `PL`
