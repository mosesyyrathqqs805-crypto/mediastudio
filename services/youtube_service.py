import os
import re
import time
import threading
from typing import Dict, Any, Callable, Optional
import yt_dlp
from core.config import get_ffmpeg_path

class DownloadCancelledException(Exception):
    pass

class YouTubeService:
    def __init__(self):
        self.is_cancelled = False
        self._current_thread: Optional[threading.Thread] = None

    @staticmethod
    def format_duration(seconds: Optional[int]) -> str:
        if not seconds:
            return "00:00"
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def format_size(bytes_val: Optional[float]) -> str:
        if not bytes_val:
            return "0 MB"
        mb = bytes_val / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GB"
        return f"{mb:.1f} MB"

    @staticmethod
    def sanitize_filename(name: str) -> str:
        cleaned = re.sub(r'[\/*?:"<>|]', "", name)
        cleaned = cleaned.strip().rstrip('.')
        return cleaned if cleaned else "video"

    @staticmethod
    def get_base_ydl_opts() -> dict:
        ffmpeg_path = get_ffmpeg_path()
        return {
            'ffmpeg_location': ffmpeg_path,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],
                }
            },
            'quiet': True,
            'no_warnings': True,
        }

    def get_video_info(self, url: str) -> Dict[str, Any]:
        ydl_opts = self.get_base_ydl_opts()
        ydl_opts.update({
            'skip_download': True,
            'extract_flat': False,
        })
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {'success': False, 'error': 'Не удалось получить данные о видео'}

                formats = info.get('formats', [])
                heights = set()
                for f in formats:
                    h = f.get('height')
                    if h and f.get('vcodec') != 'none':
                        heights.add(h)
                
                available_qualities = []
                for res in [2160, 1440, 1080, 720, 480, 360]:
                    if any(h >= res for h in heights):
                        if res == 2160:
                            available_qualities.append({'id': '2160p', 'label': '4K (2160p)'})
                        elif res == 1440:
                            available_qualities.append({'id': '1440p', 'label': '2K (1440p)'})
                        elif res == 1080:
                            available_qualities.append({'id': '1080p', 'label': 'Full HD (1080p)'})
                        elif res == 720:
                            available_qualities.append({'id': '720p', 'label': 'HD (720p)'})
                        elif res == 480:
                            available_qualities.append({'id': '480p', 'label': '480p'})
                        elif res == 360:
                            available_qualities.append({'id': '360p', 'label': '360p'})

                if not available_qualities:
                    available_qualities.append({'id': 'best', 'label': 'Лучшее доступное'})
                else:
                    available_qualities.insert(0, {'id': 'best', 'label': 'Максимальное качество'})

                available_qualities.append({'id': 'audio_only', 'label': 'Только аудио (MP3)'})

                return {
                    'success': True,
                    'title': info.get('title', 'Без названия'),
                    'uploader': info.get('uploader') or info.get('channel', 'Неизвестный автор'),
                    'duration': info.get('duration', 0),
                    'duration_formatted': self.format_duration(info.get('duration')),
                    'thumbnail': info.get('thumbnail', ''),
                    'view_count': f"{info.get('view_count', 0):,}".replace(',', ' '),
                    'qualities': available_qualities,
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cancel_download(self):
        self.is_cancelled = True

    def start_download(
        self,
        url: str,
        quality: str,
        save_mode: str,
        output_dir: str,
        progress_cb: Callable[[Dict[str, Any]], None],
        completion_cb: Callable[[Dict[str, Any]], None]
    ):
        self.is_cancelled = False

        def _worker():
            try:
                base_opts = self.get_base_ydl_opts()
                base_opts.update({'skip_download': True})
                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'video') if info else 'video'
                
                safe_title = self.sanitize_filename(title)
                
                if save_mode == 'folder_split':
                    target_folder = os.path.join(output_dir, safe_title)
                    os.makedirs(target_folder, exist_ok=True)
                else:
                    target_folder = output_dir
                    os.makedirs(target_folder, exist_ok=True)

                def ydl_hook(d):
                    if self.is_cancelled:
                        raise DownloadCancelledException("Загрузка отменена пользователем")
                    
                    status = d.get('status')
                    if status == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes', 0)
                        percent = (downloaded / total * 100) if total > 0 else 0
                        speed = d.get('speed') or 0
                        speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else "-- MB/s"
                        eta = d.get('eta')
                        eta_str = f"{eta} сек" if eta else "--"

                        progress_cb({
                            'status': 'downloading',
                            'percent': round(percent, 1),
                            'speed': speed_str,
                            'eta': eta_str,
                            'downloaded': self.format_size(downloaded),
                            'total': self.format_size(total),
                            'stage': 'Скачивание...'
                        })
                    elif status == 'finished':
                        progress_cb({
                            'status': 'processing',
                            'percent': 99,
                            'speed': 'Обработка...',
                            'eta': '0 сек',
                            'stage': 'Сборка и конвертация...'
                        })

                format_selector = 'bestvideo+bestaudio/best'
                if quality == '2160p':
                    format_selector = 'bestvideo[height<=2160]+bestaudio/best[height<=2160]'
                elif quality == '1440p':
                    format_selector = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]'
                elif quality == '1080p':
                    format_selector = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
                elif quality == '720p':
                    format_selector = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
                elif quality == '480p':
                    format_selector = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
                elif quality == '360p':
                    format_selector = 'bestvideo[height<=360]+bestaudio/best[height<=360]'

                if save_mode == 'folder_split':
                    out_video_tmpl = os.path.join(target_folder, 'video.%(ext)s')
                    ydl_video_opts = self.get_base_ydl_opts()
                    ydl_video_opts.update({
                        'format': format_selector,
                        'outtmpl': out_video_tmpl,
                        'merge_output_format': 'mp4',
                        'progress_hooks': [ydl_hook],
                    })
                    progress_cb({'status': 'downloading', 'percent': 10, 'speed': 'Старт', 'eta': '--', 'stage': 'Скачивание видео (MP4)'})
                    with yt_dlp.YoutubeDL(ydl_video_opts) as ydl:
                        ydl.download([url])

                    out_audio_tmpl = os.path.join(target_folder, 'audio.%(ext)s')
                    ydl_audio_opts = self.get_base_ydl_opts()
                    ydl_audio_opts.update({
                        'format': 'bestaudio/best',
                        'outtmpl': out_audio_tmpl,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'progress_hooks': [ydl_hook],
                    })
                    progress_cb({'status': 'downloading', 'percent': 80, 'speed': 'Старт', 'eta': '--', 'stage': 'Извлечение аудио (MP3)'})
                    with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
                        ydl.download([url])

                    completion_cb({
                        'success': True,
                        'target_folder': target_folder,
                        'message': f'Видео и аудио успешно сохранены в папку: {safe_title}'
                    })

                else:
                    if quality == 'audio_only':
                        out_tmpl = os.path.join(target_folder, f'{safe_title}.%(ext)s')
                        ydl_opts = self.get_base_ydl_opts()
                        ydl_opts.update({
                            'format': 'bestaudio/best',
                            'outtmpl': out_tmpl,
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            }],
                            'progress_hooks': [ydl_hook],
                        })
                    else:
                        out_tmpl = os.path.join(target_folder, f'{safe_title}.%(ext)s')
                        ydl_opts = self.get_base_ydl_opts()
                        ydl_opts.update({
                            'format': format_selector,
                            'outtmpl': out_tmpl,
                            'merge_output_format': 'mp4',
                            'progress_hooks': [ydl_hook],
                        })
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])

                    completion_cb({
                        'success': True,
                        'target_folder': target_folder,
                        'message': f'Файл успешно сохранен: {safe_title}'
                    })

            except DownloadCancelledException:
                completion_cb({
                    'success': False,
                    'cancelled': True,
                    'message': 'Скачивание остановлено'
                })
            except Exception as e:
                completion_cb({
                    'success': False,
                    'cancelled': False,
                    'error': str(e),
                    'message': f'Ошибка скачивания: {str(e)}'
                })

        self._current_thread = threading.Thread(target=_worker, daemon=True)
        self._current_thread.start()
