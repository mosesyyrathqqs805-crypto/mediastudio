import os
import re
import time
import subprocess
import threading
import json
from typing import Dict, Any, Callable, Optional, List, Tuple
from core.config import get_ffmpeg_path

class CutterService:
    def __init__(self):
        self.is_cancelled = False
        self._current_process: Optional[subprocess.Popen] = None
        self._current_thread: Optional[threading.Thread] = None

    @staticmethod
    def parse_time_to_seconds(time_str: str) -> float:
        time_str = time_str.strip()
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        elif len(parts) == 1:
            return float(parts[0])
        return 0.0

    @staticmethod
    def format_seconds(seconds: float) -> str:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {'success': False, 'error': 'Файл не найден'}

        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-i', file_path,
            '-hide_banner'
        ]
        
        try:
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = res.stderr

            duration = 0.0
            dur_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', output)
            if dur_match:
                h, m, s = dur_match.groups()
                duration = int(h) * 3600 + int(m) * 60 + float(s)

            width, height = 0, 0
            res_match = re.search(r',\s*(\d{3,5})x(\d{3,5})', output)
            if res_match:
                width, height = int(res_match.group(1)), int(res_match.group(2))

            has_audio = 'Audio:' in output

            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            return {
                'success': True,
                'filename': os.path.basename(file_path),
                'path': file_path,
                'duration': duration,
                'duration_formatted': self.format_seconds(duration),
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}" if width else "Не определено",
                'has_audio': has_audio,
                'size_mb': f"{file_size_mb:.1f} MB"
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cancel_cutting(self):
        self.is_cancelled = True
        if self._current_process:
            try:
                self._current_process.terminate()
                time.sleep(0.2)
                if self._current_process.poll() is None:
                    self._current_process.kill()
            except Exception:
                pass

    def _build_ffmpeg_cmd(
        self,
        ffmpeg_path: str,
        start_time: float,
        clip_dur: float,
        video_path: str,
        audio_path: Optional[str],
        banner_info: Optional[Dict[str, Any]],
        format_mode: str,
        out_clip_path: str,
        src_width: int,
        src_height: int
    ) -> List[str]:
        cmd = [ffmpeg_path, '-y', '-ss', str(start_time), '-i', video_path]

        has_separate_audio = bool(audio_path and os.path.exists(audio_path))
        if has_separate_audio:
            cmd.extend(['-ss', str(start_time), '-i', audio_path])

        banner_path = banner_info.get('path') if banner_info else None
        has_banner = bool(banner_path and os.path.exists(banner_path))

        banner_input_idx = 2 if has_separate_audio else 1
        if has_banner:
            is_gif = banner_path.lower().endswith('.gif')
            if is_gif:
                cmd.extend(['-ignore_loop', '0', '-i', banner_path])
            else:
                cmd.extend(['-i', banner_path])

        cmd.extend(['-t', str(clip_dur)])

        out_w = 1080 if format_mode in ('blur_916', 'crop_916') else (src_width or 1080)
        out_h = 1920 if format_mode in ('blur_916', 'crop_916') else (src_height or 1920)

        filter_complex_parts = []

        if format_mode == 'blur_916':
            filter_complex_parts.append(
                '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];'
                '[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];'
                '[bg][fg]overlay=(W-w)/2:(H-h)/2[base_v]'
            )
            current_v = '[base_v]'
        elif format_mode == 'crop_916':
            filter_complex_parts.append(
                '[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920[base_v]'
            )
            current_v = '[base_v]'
        else:
            current_v = '[0:v]'

        if has_banner:
            pos_x_pct = float(banner_info.get('pos_x', 50.0)) / 100.0
            pos_y_pct = float(banner_info.get('pos_y', 82.0)) / 100.0
            width_pct = float(banner_info.get('width_pct', 40.0)) / 100.0
            opacity = max(0.1, min(1.0, float(banner_info.get('opacity', 100.0)) / 100.0))

            target_banner_w = max(40, int(out_w * width_pct))

            banner_scale = f'[{banner_input_idx}:v]format=rgba,colorchannelmixer=aa={opacity:.2f},scale={target_banner_w}:-1[banner_v]'
            filter_complex_parts.append(banner_scale)

            overlay_expr = f'{current_v}[banner_v]overlay=x=(W-w)*{pos_x_pct:.3f}:y=(H-h)*{pos_y_pct:.3f}:shortest=1[out_v]'
            filter_complex_parts.append(overlay_expr)
            current_v = '[out_v]'

        if filter_complex_parts:
            cmd.extend(['-filter_complex', ';'.join(filter_complex_parts)])
            cmd.extend(['-map', current_v])
        else:
            cmd.extend(['-map', '0:v:0'])

        if has_separate_audio:
            cmd.extend(['-map', '1:a:0?', '-c:a', 'aac', '-b:a', '192k'])
        else:
            cmd.extend(['-map', '0:a:0?', '-c:a', 'aac', '-b:a', '192k'])

        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-pix_fmt', 'yuv420p',
            out_clip_path
        ])
        return cmd

    def start_cutting(
        self,
        video_path: str,
        audio_path: Optional[str],
        mode: str,
        segment_duration: float,
        manual_intervals: List[Tuple[float, float]],
        format_mode: str,
        output_dir: str,
        banner_info: Optional[Dict[str, Any]],
        progress_cb: Callable[[Dict[str, Any]], None],
        completion_cb: Callable[[Dict[str, Any]], None]
    ):
        self.is_cancelled = False

        def _worker():
            ffmpeg_path = get_ffmpeg_path()
            try:
                info = self.get_file_info(video_path)
                if not info.get('success'):
                    completion_cb({'success': False, 'error': info.get('error')})
                    return

                total_duration = info.get('duration', 0.0)
                if total_duration <= 0:
                    completion_cb({'success': False, 'error': 'Не удалось определить длительность видео'})
                    return

                src_w = info.get('width', 1080)
                src_h = info.get('height', 1920)

                clips = []
                if mode == 'auto':
                    seg_len = max(5.0, segment_duration)
                    cur_start = 0.0
                    while cur_start < total_duration:
                        cur_end = min(cur_start + seg_len, total_duration)
                        if cur_end - cur_start >= 2.0:
                            clips.append((cur_start, cur_end))
                        cur_start += seg_len
                else:
                    clips = [c for c in manual_intervals if c[1] > c[0] and c[0] < total_duration]

                if not clips:
                    completion_cb({'success': False, 'error': 'Нет подходящих отрезков для нарезки'})
                    return

                base_name = os.path.splitext(os.path.basename(video_path))[0]
                sanitized_base = re.sub(r'[\/*?:"<>|]', "", base_name).strip()
                clips_folder = os.path.join(output_dir, f"нарезки_{sanitized_base}")
                os.makedirs(clips_folder, exist_ok=True)

                total_clips = len(clips)
                generated_files = []

                for idx, (start_time, end_time) in enumerate(clips, 1):
                    if self.is_cancelled:
                        break

                    clip_dur = end_time - start_time
                    out_filename = f"видео {idx}.mp4"
                    out_clip_path = os.path.join(clips_folder, out_filename)

                    overall_percent = int(((idx - 1) / total_clips) * 100)
                    progress_cb({
                        'status': 'cutting',
                        'current_clip': idx,
                        'total_clips': total_clips,
                        'percent': overall_percent,
                        'message': f'Обработка видео {idx} из {total_clips} ({self.format_seconds(start_time)} - {self.format_seconds(end_time)})...'
                    })

                    cmd = self._build_ffmpeg_cmd(
                        ffmpeg_path=ffmpeg_path,
                        start_time=start_time,
                        clip_dur=clip_dur,
                        video_path=video_path,
                        audio_path=audio_path,
                        banner_info=banner_info,
                        format_mode=format_mode,
                        out_clip_path=out_clip_path,
                        src_width=src_w,
                        src_height=src_h
                    )

                    self._current_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = self._current_process.communicate()

                    if self.is_cancelled:
                        if os.path.exists(out_clip_path):
                            try:
                                os.remove(out_clip_path)
                            except Exception:
                                pass
                        break

                    if self._current_process.returncode != 0:
                        pass
                    else:
                        generated_files.append(out_clip_path)

                if self.is_cancelled:
                    completion_cb({
                        'success': False,
                        'cancelled': True,
                        'message': 'Нарезка была остановлена'
                    })
                else:
                    progress_cb({
                        'status': 'finished',
                        'current_clip': total_clips,
                        'total_clips': total_clips,
                        'percent': 100,
                        'message': f'Готово! Нарезано файлов: {len(generated_files)}'
                    })
                    completion_cb({
                        'success': True,
                        'target_folder': clips_folder,
                        'clips_count': len(generated_files),
                        'message': f'Успешно сохранено {len(generated_files)} файлов в папку: {clips_folder}'
                    })

            except Exception as e:
                completion_cb({
                    'success': False,
                    'cancelled': False,
                    'error': str(e),
                    'message': f'Ошибка при нарезке: {str(e)}'
                })

        self._current_thread = threading.Thread(target=_worker, daemon=True)
        self._current_thread.start()
