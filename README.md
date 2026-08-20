# MediaStudio — YouTube Downloader & Shorts Slicer & Auto-Subtitles

Современное десктопное кроссплатформенное приложение для Windows и macOS:
- Скачивание видео с YouTube в качестве до 4K (2160p) и аудио в MP3.
- Нарезка видео на клипы 9:16 (Shorts / Reels / TikTok) с размытием фона или кропом.
- Наложение интерактивного баннера/логотипа (PNG, JPG, GIF) с перемещением и масштабированием за уголки.
- Автоматическая генерация субтитров (Cloudflare Whisper AI) с анимациями (Pop, Fade, Slide, Typewriter) и подсветкой активного слова.
- Генерация вирусных хештегов и описаний через Cloudflare AI.

---

## Установка и запуск из исходного кода

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Запустите приложение:
   ```bash
   python main.py
   ```

---

## Защищенная компиляция в автономный `.exe` (Windows)

Для максимальной защиты от декомпиляции и взлома используется **Nuitka**, которая транслирует весь Python-код в чистый C/C++ и компилирует в нативные машинные инструкции (исходного кода и байткода `.pyc` в бинарнике нет):

### Вариант 1: Запуск в 1 клик
Дважды кликните по файлу `build_windows.bat` в проводнике Windows.

### Вариант 2: Через командную строку
```cmd
pip install -r requirements.txt
pip install nuitka zstandard ordered-set
python build_windows.py
```
Готовый автономный файл с иконкой будет создан в папке:
`dist/MediaStudio.exe`

---

## Компиляция под macOS (.app)

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --noconsole --windowed --icon=assets/icon.icns --name="MediaStudio" --add-data "ui:ui" --add-data "assets:assets" main.py
```
Готовое приложение будет создано в:
`dist/MediaStudio.app`
