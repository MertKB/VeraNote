[English](README.md) | [Türkçe](README.tr.md)

<p align="center">
  <img src="assets/app_icon.png" alt="Vera Note Logo" width="96" height="96" />
</p>

# Vera Note

Vera Note, özellikle ComfyUI ve Stable Diffusion ile çalışan geliştiriciler ve içerik üreticileri için tasarlanmış bir masaüstü düzenleme ve not alma aracıdır. Yapay zeka modellerinizi, ürettiğiniz görsellerdeki iş akışı (workflow) bilgilerini, prompt notlarınızı, günlük ajandanızı ve fikir panonuzu tek bir yerden kolayca yönetmenizi sağlar.

## Öne Çıkan Özellikler

**Model Kütüphanesi ve Otomatik Tarama:** Bilgisayarınızdaki Stable Diffusion ve ComfyUI model klasörlerini (Checkpoints, LoRAs vb.) otomatik olarak tarar, indeksler ve düzenler. SafeTensors model dosyalarının başlıklarını doğrudan okuyarak modelin içine gömülü tetikleyici kelimeleri (trigger words), temel model mimarisini (SD 1.5, SDXL, Flux vb.) ve eğitim bilgilerini dosyanın içinden otomatik olarak ayıklar. Modellerinize ait tetikleyici kelimeleri, özel etiketleri ve kullanım notlarını tek bir yerde kolayca görebilir ve saklayabilirsiniz.

**ComfyUI PNG Workflow ve Metadata Ayrıştırma:** ComfyUI ile üretilen PNG görsellerin içerisindeki gömülü akış bilgilerini otomatik olarak okur, kaydedebilir ve daha sonra tekrar kullanabilirsiniz. Tüm bunları sadece sürükle-bırak yöntemiyle kolayca yapabilirsiniz.

**Defterler ve Not Defteri:** İstem (prompt) fikirlerinizi, test sonuçlarınızı, parametre gruplarınızı veya günlük genel notlarınızı defterler altında hiyerarşik olarak düzenleyebilirsiniz. Entegre Markdown düzenleyicisi sayesinde notlarınızı dilediğiniz gibi biçimlendirebilirsiniz.

**Ajanda, Günlük Notlar ve Rutin Takibi:** Çalışma temponuzu tek bir takvim üzerinden yönetebilirsiniz. Her güne özel hızlı notlar düşebilir, yapılacak işlerinizi (Tasks) takip edebilir ve düzenli çalışma alışkanlıklarınız için tekrarlayan rutinler oluşturabilirsiniz.

**Mantar Pano (Corkboard):** Aklınıza gelen ani fikirleri, akış taslaklarını veya hatırlatıcıları serbestçe iğneleyebileceğiniz görsel bir panodur. Renkli kartlar ve iğnelerle fikirlerinizi özgürce görselleştirebilirsiniz.

**Esnek ve Modüler Arayüz:** Detay panellerini serbest pencerelere dönüştürebilir ya da ana pencereye geri kenetleyebilirsiniz (QDockWidget mimarisi). Koyu tema desteği ve kişiselleştirilebilir görünümü sayesinde çalışma ortamınıza kolayca uyum sağlar.

**Gizli Mod:** Ctrl + Shift + N kısayolunu kullanarak gizli modu hızlıca açabilir; ekran paylaşımı veya kayıt esnasında notlarınızı ve çalışma alanınızı gizlilik odaklı bir şekilde kullanabilirsiniz.

**Çoklu Dil Desteği:** Türkçe ve İngilizce dil seçenekleri mevcuttur. Ayarlar menüsünden dilediğiniz an değiştirebilirsiniz.

## Geliştirici Notu

> "Bu uygulamayı geliştirirken öncelikli hedefim, AI ve görsel üretim süreçlerinde kendim hissettiğim eksiklikleri gidermek oldu. Tam olarak isteklerimi karşılayan bir araç bulamadığım için, hem kendi ihtiyacımı karşılayacak hem de görünümünü ve yapısını dilediğim gibi kişiselleştirebileceğim bir proje olarak hayata geçirdim.  
> Görsel üretimiyle ilgilenmiyor olsanız dahi, sunduğu esnek yapısıyla genel not tutma ihtiyacınızı da rahatlıkla karşılayabileceğini düşünüyorum."

## Geri Bildirim ve Katkı

Vera Note gelişmeye açık bir projedir. Eklenmesini istediğiniz özellikler, önerileriniz veya geri bildirimleriniz için Issue açabilir ya da doğrudan iletişime geçebilirsiniz. Fikirlerinizi duymaktan her zaman mutluluk duyarım.

## Kurulum ve Kullanım

### Sistem Gereksinimleri
- Python 3.10 veya üzeri
- Windows 10 / 11

### Kaynak Koddan Çalıştırma

1. Repoyu klonlayın:
   ```bash
   git clone https://github.com/MertKB/VeraNote.git
   cd VeraNote
   ```

2. Sanal ortam (virtual environment) oluşturun ve etkinleştirin (önerilen):
   ```powershell
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Komut İstemi (CMD):
   .\.venv\Scripts\activate.bat
   ```

3. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

4. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

### Windows Bağımsız Uygulama (.exe) Derleme

Python yüklü olmayan ortamlarda çalıştırmak için PyInstaller ile tek parça `.exe` üretebilirsiniz:

1. **Derleme (`build.ps1`):**
   ```powershell
   .\build.ps1
   ```
   Çalıştırılabilir uygulama `dist/VeraNote/VeraNote.exe` dizininde oluşturulur.

2. **Kısayol Kurulumu (`install.ps1`):**
   ```powershell
   .\install.ps1
   ```
   Masaüstü ve Başlat Menüsüne `Vera Note` kısayollarını ekler.

## Proje Yapısı

```text
VeraNote/
├── assets/                  # Uygulama simgeleri ve görsel öğeler
├── ui/                      # PySide6 Qt arayüz bileşenleri ve stil tanımları
│   ├── agenda/              # Ajanda, takvim, günlük notlar ve rutinler
│   ├── corkboard/           # Mantar pano, görsel kartlar ve iğneler
│   ├── detail/              # Detay paneli bölümleri (Model, Not, Workflow)
│   ├── widgets/             # Yardımcı arayüz bileşenleri (Toast bildirimleri vb.)
│   ├── detail_panel.py      # Detay paneli kapsayıcısı
│   ├── library_view.py      # Model kütüphanesi görünümü
│   ├── main_window.py       # Ana pencere ve panel yönetimi
│   ├── notebooks_view.py    # Defter hiyerarşisi ve listesi
│   ├── notes_view.py        # Markdown not listesi ve düzenleyici
│   ├── settings_dialog.py   # Uygulama ayarları penceresi
│   ├── sidebar.py           # Yan gezinti menüsü
│   ├── styles.py            # Koyu tema QSS stilleri
│   ├── welcome_screen.py    # Başlangıç ve karşılama ekranı
│   └── workflow_view.py     # PNG Workflow ve metadata görünümü
├── utils/                   # Yardımcı araçlar ve okuyucular
│   ├── cache.py             # Görsel önbellekleme
│   ├── i18n.py              # Dil yönetimi (TR/EN)
│   ├── icon_manager.py      # Simge yöneticisi
│   ├── png_parser.py        # PNG metadata ayrıştırıcı
│   ├── safetensors_parser.py # SafeTensors başlık ayrıştırıcı
│   └── workflow_parser.py   # ComfyUI akış yapısı ayrıştırıcı
├── database.py              # SQLite veritabanı işlemleri
├── scanner.py               # Arka plan dosya tarama motoru
├── main.py                  # Uygulama giriş noktası
├── VeraNote.spec            # PyInstaller yapılandırma dosyası
├── requirements.txt         # Gereksinim duyulan Python paketleri
└── LICENSE                  # GNU General Public License v3.0
```

## Veri Gizliliği

- Veritabanı ve uygulama verileriniz bilgisayarınızdaki kullanıcı dizininde (`%USERPROFILE%\.veranote_data\veranote.db`) saklanır.
- Kod deposuna veya üçüncü taraf sunuculara kişisel verileriniz, model yollarınız veya notlarınız aktarılmaz.

## Lisans

Bu proje **GNU General Public License v3.0 (GPLv3)** altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasını inceleyebilirsiniz.
