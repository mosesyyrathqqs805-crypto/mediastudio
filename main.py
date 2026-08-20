import os
import sys
import re
import json
import threading
import subprocess
from typing import Optional, List, Tuple
import webview

from core.config import DEFAULT_DOWNLOAD_DIR, get_ffmpeg_path
from services.youtube_service import YouTubeService
from services.cutter_service import CutterService
from services.subtitles_service import SubtitlesService
from services.media_server import get_media_url

class Api:
    def __init__(self):
        self.window: Optional[webview.Window] = None
        self.youtube_service = YouTubeService()
        self.cutter_service = CutterService()
        self.subtitles_service = SubtitlesService()

    def get_video_url(self, file_path: str) -> str:
        return get_media_url(file_path)

    def get_default_download_dir(self) -> str:
        return DEFAULT_DOWNLOAD_DIR

    def select_folder(self) -> Optional[str]:
        if not self.window:
            return None
        folder_dialog_type = getattr(webview, 'FileDialog', webview).FOLDER if hasattr(webview, 'FileDialog') else webview.FOLDER_DIALOG
        res = self.window.create_file_dialog(folder_dialog_type)
        if res and len(res) > 0:
            return res[0]
        return None

    def select_video_file(self) -> Optional[str]:
        if not self.window:
            return None
        open_dialog_type = getattr(webview, 'FileDialog', webview).OPEN if hasattr(webview, 'FileDialog') else webview.OPEN_DIALOG
        res = self.window.create_file_dialog(
            open_dialog_type,
            file_types=('Видеофайлы (*.mp4;*.mkv;*.mov;*.webm;*.avi;*.flv;*.m4v)', 'Все файлы (*.*)')
        )
        if res and len(res) > 0:
            return res[0]
        return None

    def select_audio_file(self) -> Optional[str]:
        if not self.window:
            return None
        open_dialog_type = getattr(webview, 'FileDialog', webview).OPEN if hasattr(webview, 'FileDialog') else webview.OPEN_DIALOG
        res = self.window.create_file_dialog(
            open_dialog_type,
            file_types=('Аудиофайлы (*.mp3;*.wav;*.m4a;*.aac;*.flac;*.ogg)', 'Все файлы (*.*)')
        )
        if res and len(res) > 0:
            return res[0]
        return None

    def select_banner_file(self) -> Optional[str]:
        if not self.window:
            return None
        open_dialog_type = getattr(webview, 'FileDialog', webview).OPEN if hasattr(webview, 'FileDialog') else webview.OPEN_DIALOG
        res = self.window.create_file_dialog(
            open_dialog_type,
            file_types=('Изображения и баннеры (*.png;*.jpg;*.jpeg;*.gif;*.webp)', 'Все файлы (*.*)')
        )
        if res and len(res) > 0:
            return res[0]
        return None

    def open_folder(self, folder_path: str):
        target = folder_path if os.path.exists(folder_path) else os.path.dirname(folder_path)
        if not os.path.exists(target):
            return
        if sys.platform == 'win32':
            try:
                os.startfile(target)
            except Exception:
                subprocess.Popen(['explorer', os.path.normpath(target)])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', target])
        else:
            subprocess.Popen(['xdg-open', target])

    def check_youtube_video(self, url: str) -> dict:
        return self.youtube_service.get_video_info(url)

    def start_youtube_download(self, url: str, quality: str, save_mode: str, output_dir: str):
        def on_progress(data: dict):
            if self.window:
                data_json = json.dumps(data)
                js_code = f"window.onYouTubeProgress({data_json});"
                self.window.evaluate_js(js_code)

        def on_complete(data: dict):
            if self.window:
                data_json = json.dumps(data)
                js_code = f"window.onYouTubeCompleted({data_json});"
                self.window.evaluate_js(js_code)

        self.youtube_service.start_download(
            url=url,
            quality=quality,
            save_mode=save_mode,
            output_dir=output_dir or DEFAULT_DOWNLOAD_DIR,
            progress_cb=on_progress,
            completion_cb=on_complete
        )
        return {'status': 'started'}

    def cancel_youtube_download(self):
        self.youtube_service.cancel_download()
        return {'status': 'cancelling'}

    def get_media_info(self, file_path: str) -> dict:
        return self.cutter_service.get_file_info(file_path)

    def start_cutting_video(
        self,
        video_path: str,
        audio_path: Optional[str],
        mode: str,
        segment_duration: float,
        manual_text: str,
        format_mode: str,
        output_dir: str,
        banner_info: Optional[dict] = None
    ):
        manual_intervals: List[Tuple[float, float]] = []
        if mode == 'manual' and manual_text:
            lines = manual_text.strip().splitlines()
            for line in lines:
                parts = line.split('-')
                if len(parts) == 2:
                    s = self.cutter_service.parse_time_to_seconds(parts[0])
                    e = self.cutter_service.parse_time_to_seconds(parts[1])
                    if e > s:
                        manual_intervals.append((s, e))

        def on_progress(data: dict):
            if self.window:
                data_json = json.dumps(data)
                js_code = f"window.onCutterProgress({data_json});"
                self.window.evaluate_js(js_code)

        def on_complete(data: dict):
            if self.window:
                data_json = json.dumps(data)
                js_code = f"window.onCutterCompleted({data_json});"
                self.window.evaluate_js(js_code)

        self.cutter_service.start_cutting(
            video_path=video_path,
            audio_path=audio_path,
            mode=mode,
            segment_duration=float(segment_duration),
            manual_intervals=manual_intervals,
            format_mode=format_mode,
            output_dir=output_dir or DEFAULT_DOWNLOAD_DIR,
            banner_info=banner_info,
            progress_cb=on_progress,
            completion_cb=on_complete
        )
        return {'status': 'started'}

    def cancel_cutting_video(self):
        self.cutter_service.cancel_cutting()
        return {'status': 'cancelling'}


    def get_cloudflare_settings(self) -> dict:
        cfg = self.subtitles_service.get_cloudflare_config()
        token = cfg.get('api_token', '')
        return {
            'account_id': cfg.get('account_id', ''),
            'api_token': token,
            'api_token_masked': self.subtitles_service.mask_token(token),
            'has_token': bool(token)
        }

    def save_cloudflare_settings(self, account_id: str, api_token: str) -> dict:
        self.subtitles_service.save_cloudflare_config(account_id, api_token)
        return {'success': True}

    def test_cloudflare_connection(self, account_id: str, api_token: str) -> dict:
        if not api_token:
            cfg = self.subtitles_service.get_cloudflare_config()
            api_token = cfg.get('api_token', '')
        return self.subtitles_service.verify_cloudflare(account_id, api_token)

    def start_transcription(self, video_path: str, language: str = 'auto', words_per_sub: int = 3):
        def _worker():
            try:
                media_info = self.cutter_service.get_file_info(video_path)
                if not media_info.get('has_audio'):
                    if self.window:
                        res_json = json.dumps({'success': False, 'error': 'В видео отсутствует аудиодорожка для распознавания'})
                        self.window.evaluate_js(f"window.onTranscriptionCompleted({res_json});")
                    return

                base_dir = os.path.dirname(os.path.abspath(__file__))
                temp_dir = os.path.join(base_dir, 'data', 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                wav_path = os.path.join(temp_dir, 'temp_speech.wav')

                if self.window:
                    prog_json = json.dumps({'status': 'extracting', 'percent': 10, 'message': 'Извлечение аудиодорожки...'})
                    self.window.evaluate_js(f"window.onTranscriptionProgress({prog_json});")

                extracted = self.subtitles_service.extract_audio_for_whisper(video_path, wav_path)
                if not extracted:
                    if self.window:
                        res_json = json.dumps({'success': False, 'error': 'Не удалось извлечь аудиодорожку из видео'})
                        self.window.evaluate_js(f"window.onTranscriptionCompleted({res_json});")
                    return

                def on_progress(data: dict):
                    if self.window:
                        data_json = json.dumps(data)
                        self.window.evaluate_js(f"window.onTranscriptionProgress({data_json});")

                res = self.subtitles_service.transcribe_audio(wav_path, language=language, progress_cb=on_progress)
                
                if os.path.exists(wav_path):
                    try:
                        os.remove(wav_path)
                    except Exception:
                        pass

                if res.get('success'):
                    data = res.get('data', {})
                    raw_segments = data.get('segments', [])
                    chunked_segments = self.subtitles_service.rechunk_words_per_subtitle(raw_segments, words_per_sub=words_per_sub)
                    res['data']['chunked_segments'] = chunked_segments

                if self.window:
                    res_json = json.dumps(res)
                    self.window.evaluate_js(f"window.onTranscriptionCompleted({res_json});")

            except Exception as e:
                if self.window:
                    res_json = json.dumps({'success': False, 'error': str(e)})
                    self.window.evaluate_js(f"window.onTranscriptionCompleted({res_json});")

        threading.Thread(target=_worker, daemon=True).start()
        return {'status': 'started'}

    def rechunk_transcription(self, raw_segments: list, words_per_sub: int) -> list:
        return self.subtitles_service.rechunk_words_per_subtitle(raw_segments, words_per_sub=words_per_sub)

    def start_subtitle_burn(
        self,
        video_path: str,
        segments: list,
        styles: dict,
        output_dir: str,
        quality_mode: str = 'fast'
    ):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        temp_dir = os.path.join(base_dir, 'data', 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        ass_path = os.path.join(temp_dir, 'subtitles_burn.ass')

        media_info = self.cutter_service.get_file_info(video_path)
        w = media_info.get('width', 1080)
        h = media_info.get('height', 1920)

        self.subtitles_service.generate_ass(segments, w, h, styles, ass_path)

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        out_folder = output_dir or DEFAULT_DOWNLOAD_DIR
        os.makedirs(out_folder, exist_ok=True)
        out_video_path = os.path.join(out_folder, f"субтитр_{base_name}.mp4")

        def on_progress(data: dict):
            if self.window:
                data_json = json.dumps(data)
                self.window.evaluate_js(f"window.onBurnProgress({data_json});")

        def on_complete(data: dict):
            if self.window:
                data_json = json.dumps(data)
                self.window.evaluate_js(f"window.onBurnCompleted({data_json});")

        self.subtitles_service.burn_subtitles_to_video(
            video_path=video_path,
            ass_path=ass_path,
            output_video_path=out_video_path,
            quality_mode=quality_mode,
            progress_cb=on_progress,
            completion_cb=on_complete
        )
        return {'status': 'started'}

    def cancel_subtitle_burn(self):
        self.subtitles_service.cancel_burn()
        return {'status': 'cancelling'}

    def select_save_subtitle_file(self, default_filename: str, format_type: str) -> Optional[str]:
        if not self.window:
            return None
        save_dialog_type = getattr(webview, 'FileDialog', webview).SAVE if hasattr(webview, 'FileDialog') else webview.SAVE_DIALOG
        fmt = format_type.lower()
        if fmt == 'ass':
            file_types = ('ASS субтитры (*.ass)', 'Все файлы (*.*)')
        elif fmt == 'srt':
            file_types = ('SRT субтитры (*.srt)', 'Все файлы (*.*)')
        elif fmt == 'vtt':
            file_types = ('VTT субтитры (*.vtt)', 'Все файлы (*.*)')
        else:
            file_types = ('Файлы субтитров (*.*)', 'Все файлы (*.*)')

        res = self.window.create_file_dialog(
            save_dialog_type,
            save_filename=default_filename,
            file_types=file_types
        )
        if res:
            if isinstance(res, (list, tuple)) and len(res) > 0:
                return res[0]
            if isinstance(res, str):
                return res
        return None

    def export_subtitles(self, segments: list, format_type: str, target_file_path: str, styles: Optional[dict] = None) -> dict:
        if not target_file_path:
            return {'success': False, 'error': 'Путь сохранения не указан'}

        out_dir = os.path.dirname(target_file_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        fmt = format_type.lower()
        if fmt == 'ass':
            self.subtitles_service.generate_ass(segments, 1080, 1920, styles or {}, target_file_path)
        elif fmt == 'srt':
            self.subtitles_service.export_srt(segments, target_file_path)
        elif fmt == 'vtt':
            self.subtitles_service.export_vtt(segments, target_file_path)
        else:
            return {'success': False, 'error': 'Неизвестный формат'}

        return {'success': True, 'file_path': target_file_path}

    def generate_ai_hashtags(self, text: str) -> dict:
        return self.subtitles_service.generate_hashtags_ai(text)

    def generate_ai_description(self, text: str) -> dict:
        return self.subtitles_service.generate_description_ai(text)

    def get_cloudflare_limits(self) -> dict:
        return self.subtitles_service.get_cloudflare_account_limits()


def set_app_icon(base_dir: str):
    icon_png = os.path.abspath(os.path.join(base_dir, 'assets', 'icon.png'))
    if sys.platform == 'darwin':
        try:
            from AppKit import NSApplication, NSImage
            app = NSApplication.sharedApplication()
            if os.path.exists(icon_png):
                img = NSImage.alloc().initWithContentsOfFile_(icon_png)
                if img:
                    app.setApplicationIconImage_(img)
        except Exception:
            pass
    elif sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('mediastudio.app.v1')
        except Exception:
            pass


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    set_app_icon(base_dir)

    webview.settings['ALLOW_FILE_URLS'] = True
    webview.settings['ALLOW_DOWNLOADS'] = True

    api = Api()
    html_path = os.path.join(base_dir, 'ui', 'index.html')

    window = webview.create_window(
        title='MediaStudio — YouTube Downloader & Shorts & Subtitles',
        url=html_path,
        js_api=api,
        width=1080,
        height=820,
        min_size=(920, 680),
        background_color='#0b0d13'
    )
    api.window = window

    webview.start(debug=False)


if __name__ == '__main__':
    main()
