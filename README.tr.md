[English](README.md) | [Türkçe](README.tr.md)

# Vera Note

    Vera Note, özellikle ComfyUI ve Stable Diffusion ile çalışan geliştiriciler ve içerik üreticileri için tasarlanmış bir masaüstü düzenleme aracıdır. Yapay zeka modellerinizi, ürettiğiniz görsellerdeki iş akışı (workflow) bilgilerini ve prompt notlarınızı tek bir yerden kolayca yönetmenizi sağlar.

Öne Çıkan Özellikler

    Model Kütüphanesi ve Otomatik Tarama: Bilgisayarınızdaki Stable Diffusion ve ComfyUI model klasörlerini (Checkpoints, LoRAs vb.) otomatik olarak tarar, indeksler ve düzenler. Modellerinize özel etiketler ve notlar ekleyebilirsiniz. 
    
    Modellerinize ait tetikleyici kelimeleri (trigger words), özel etiketleri ve kullanım notlarını tek bir yerde saklayabilirsiniz.

    ComfyUI PNG Workflow ve Metadata Ayrıştırma: ComfyUI ile ürettilen PNG görsellerin içerisindeki gömülü akış bilgilerini otomatik olarak okur, kaydedebilir ve daha sonra tekrar kullanabilirsiniz. Tüm bunları sadece "sürükle-bırak" yöntemi ile kolayca yapabilirsiniz.
    
    Not Defteri: İstem fikirlerinizi, test sonuçlarınızı, parametre gruplarınızı veya günlük genel notlarınızı kaydetmeniz için tasarlanmış entegre not alanı sunar.

    Esnek ve Modüler Arayüz: Detay panellerini serbest pencerelere dönüştürebilir ya da ana pencereye geri kenetleyebilirsiniz (QDockWidget mimarisi). Koyu tema desteği ve kişiselleştirilebilir görünümü sayesinde çalışma ortamınıza kolayca uyum sağlar.
    
    Gizli Mod: Ctrl + Shift + N kısayolunu kullanarak gizli modu hızlıca açabilir, notlarınızı ve çalışma alanınızı gizlilik odaklı bir şekilde kullanabilirsiniz.

    Çoklu Dil Desteği: Türkçe ve İngilizce dil seçenekleri mevcuttur. Ayarlar menüsünden dilediğiniz an değiştirebilirsiniz.

Geliştirici Notu

    "Bu uygulamayı geliştirirken öncelikli hedefim, AI ve görsel üretim süreçlerinde kendim hissettiğim eksiklikleri gidermek oldu. Tam olarak isteklerimi karşılayan bir araç bulamadığım için, hem kendi ihtiyacımı karşılayacak hem de görünümünü ve yapısını dilediğim gibi kişiselleştirebileceğim bir proje olarak hayata geçirdim.
    Görsel üretimiyle ilgilenmiyor olsanız dahi, sunduğu esnek yapısıyla genel not tutma ihtiyacınızı da rahatlıkla karşılayabileceğini düşünüyorum."

Geri Bildirim ve Katkı

    Vera Note gelişmeye açık bir projedir. Eklenmesini istediğiniz özellikler, önerileriniz veya geri bildirimleriniz için Issue açabilir ya da doğrudan iletişime geçebilirsiniz.


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
   ```bash
   python -m venv .venv
   # Windows üzerinde:
   .venv\Scripts\activate
   # Linux/macOS üzerinde:
   source .venv/bin/activate

   # Gerekli kütüphaneleri yükleyin
   pip install -r requirements.txt
   ```

3. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

### Windows Bağımsız Uygulama (.exe) Derleme

Python yüklü olmayan ortamlarda çalıştırmak için PyInstaller ile tek parça `.exe` üretebilirsiniz:

1. **Derleme (`build.ps1`)**:
   ```powershell
   .\build.ps1
   ```
   Çalıştırılabilir uygulama `dist/VeraNote/VeraNote.exe` dizininde oluşturulur.

2. **Kısayol Kurulumu (`install.ps1`)**:
   ```powershell
   .\install.ps1
   ```
   Masaüstü ve Başlat Menüsüne `Vera Note` kısayollarını ekler.

## Proje Yapısı

```text
veranote/
├── assets/                  # Uygulama simgeleri ve görsel öğeler
├── ui/                      # PySide6 Qt arayüz bileşenleri ve stil tanımları
│   ├── detail_panel.py      # Detay paneli (Model / Not / Workflow)
│   ├── library_view.py     # Model kütüphanesi görünümü
│   ├── main_window.py      # Ana pencere ve panel yönetimi
│   ├── notes_view.py        # Markdown not listesi ve düzenleyici
│   ├── settings_dialog.py   # Uygulama ayarları penceresi
│   ├── sidebar.py           # Yan gezinti menüsü
│   ├── styles.py            # Koyu tema QSS stilleri
│   ├── welcome_screen.py    # Başlangıç ve karşılama ekranı
│   └── workflow_view.py     # PNG Workflow ve metadata görünümü
├── utils/                   # Yardımcı araçlar ve okuyucular
│   ├── cache.py             # Görsel önbellekleme
│   ├── i18n.py              # Dil yönetimi (TR/EN)
│   ├── png_parser.py        # PNG metadata ayrıştırıcı
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
