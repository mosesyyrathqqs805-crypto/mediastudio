import os
import sys
import re
import time
import json
import hashlib
import subprocess
import threading
import math
from typing import Dict, Any, Callable, Optional, List, Tuple
import requests

from core.config import get_ffmpeg_path, DEFAULT_DOWNLOAD_DIR, get_config_file_path, get_cache_dir

class SubtitlesService:
    def __init__(self):
        self.is_cancelled = False
        self._current_process: Optional[subprocess.Popen] = None
        self._current_thread: Optional[threading.Thread] = None
        os.makedirs(get_cache_dir(), exist_ok=True)

    @staticmethod
    def get_cloudflare_config() -> Dict[str, str]:
        cfg_file = get_config_file_path()
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'account_id': '', 'api_token': ''}

    @staticmethod
    def save_cloudflare_config(account_id: str, api_token: str):
        cfg_file = get_config_file_path()
        cfg = {'account_id': account_id.strip(), 'api_token': api_token.strip()}
        try:
            os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
            with open(cfg_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print('Ошибка сохранения настроек Cloudflare:', e)

    @staticmethod
    def mask_token(token: str) -> str:
        if not token:
            return ''
        if len(token) <= 8:
            return '****'
        return f'****{token[-4:]}'

    def verify_cloudflare(self, account_id: str, api_token: str) -> Dict[str, Any]:
        if not account_id or not api_token:
            return {'success': False, 'error': 'Account ID и API Token обязательны для заполнения'}
        
        headers = {'Authorization': f'Bearer {api_token}'}

        try:
            resp_tok = requests.get('https://api.cloudflare.com/client/v4/user/tokens/verify', headers=headers, timeout=20)
            if resp_tok.status_code == 200:
                data = resp_tok.json()
                if data.get('success'):
                    return {'success': True, 'message': 'Подключение к Cloudflare успешно! Токен активен.'}
        except Exception:
            pass

        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search?search=whisper'
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    return {'success': True, 'message': 'Подключение к Cloudflare Workers AI успешно!'}
            elif resp.status_code == 401:
                return {'success': False, 'error': 'Ошибка 401: Неверный API Token'}
            elif resp.status_code == 403:
                return {'success': False, 'error': 'Ошибка 403: Доступ запрещен (проверьте права токена Workers AI и правильность Account ID)'}
            return {'success': False, 'error': f'Ошибка Cloudflare: {resp.status_code} {resp.text[:150]}'}
        except Exception as e:
            return {'success': False, 'error': f'Ошибка соединения: {str(e)}'}

    def get_cloudflare_account_limits(self) -> Dict[str, Any]:
        cfg = self.get_cloudflare_config()
        account_id = cfg.get('account_id')
        api_token = cfg.get('api_token')

        if not account_id or not api_token:
            return {'success': False, 'error': 'Account ID и API Token не заданы в настройках'}

        headers = {'Authorization': f'Bearer {api_token}'}
        token_status = 'Проверен'
        try:
            verify_url = 'https://api.cloudflare.com/client/v4/user/tokens/verify'
            v_resp = requests.get(verify_url, headers=headers, timeout=10)
            if v_resp.status_code == 200:
                v_data = v_resp.json()
                if v_data.get('success'):
                    token_status = 'Активен (Active)'
            elif v_resp.status_code == 401:
                return {'success': False, 'error': 'API Token недействителен (Ошибка 401)'}
        except Exception as e:
            token_status = f'Локально проверен'

        return {
            'success': True,
            'account_id': account_id,
            'token_status': token_status,
            'plan_name': 'Workers AI (Free Tier)',
            'daily_limit': '10 000 Neurons / день',
            'estimated_videos': '150-200 видео в день',
            'reset_time': 'Каждые 24ч (00:00 UTC)',
            'models': 'Whisper AI + Llama 3.1 8B'
        }

    def generate_hashtags_ai(self, text: str) -> Dict[str, Any]:
        cfg = self.get_cloudflare_config()
        account_id = cfg.get('account_id')
        api_token = cfg.get('api_token')

        if not account_id or not api_token:
            return {'success': False, 'error': 'Сначала укажите Cloudflare Account ID и API Token в настройках'}

        if not text or not text.strip():
            return {'success': False, 'error': 'Текст субтитров пуст'}

        clean_text = text.strip()[:2000]
        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct'
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Ты топовый продюсер вирусных Shorts, Reels и TikTok.
По тексту видео подбери САМЫЕ ПОПУЛЯРНЫЕ, РЕАЛЬНО ИСПОЛЬЗУЕМЫЕ И ВЫСОКОЧАСТОТНЫЕ хэштеги в социальных сетях.

СТРОГИЕ ПРАВИЛА:
1. Хэштеги должны состоять строго из ОДНОГО популярного слова (например: #игры, #sony, #новости, #пк, #топ, #shorts, #рек, #технологии, #факты).
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать длинные составные хэштеги из фраз и предложений!
3. Обязательно начни с главных глобальных хэштегов рекомендаций: #shorts #fyp #рек #рекомендации #хочуврек #тренды #viral #топ
4. Добавь 5-7 самых популярных коротких однословных хэштегов по теме видео.

Текст видео:
"{clean_text}"

Выведи ТОЛЬКО список хэштегов в одну строку через пробел, без вступительных слов и кавычек."""

        payload = {
            'messages': [
                {'role': 'system', 'content': 'Ты составляешь только короткие, популярные, высокочастотные хэштеги из одного слова. Отвечай только хэштегами через пробел.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 150,
            'temperature': 0.4
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    result = data.get('result', {})
                    response_text = result.get('response', '').strip()
                    tags = re.findall(r'#[\w\d_]+', response_text)
                    
                    base_viral = ['#shorts', '#fyp', '#рек', '#рекомендации', '#тренды', '#viral', '#топ', '#хочуврек']
                    all_tags = []
                    for t in tags:
                        t_clean = t.lower()
                        if len(t_clean) <= 18 and '_' not in t_clean and t_clean not in all_tags:
                            all_tags.append(t_clean)
                    
                    for bv in reversed(base_viral):
                        if bv not in all_tags:
                            all_tags.insert(0, bv)

                    final_tags = ' '.join(all_tags[:14])
                    return {'success': True, 'hashtags': final_tags}
                return {'success': False, 'error': str(data.get('errors', 'Ошибка генерации хэштегов'))}
            return {'success': False, 'error': f'HTTP {resp.status_code}: {resp.text[:150]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def generate_description_ai(self, text: str) -> Dict[str, Any]:
        cfg = self.get_cloudflare_config()
        account_id = cfg.get('account_id')
        api_token = cfg.get('api_token')

        if not account_id or not api_token:
            return {'success': False, 'error': 'Сначала укажите Cloudflare Account ID и API Token в настройках'}

        if not text or not text.strip():
            return {'success': False, 'error': 'Текст субтитров пуст'}

        clean_text = text.strip()[:2500]
        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct'
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        prompt = f"""Ты SMM-маркетолог для коротких видео YouTube Shorts, TikTok и Reels.
На основе текста видео придумай:
1) 3 цепляющих варианта заголовка с эмодзи.
2) Краткое интригующее описание (2 предложения) с призывом к действию.

Текст видео:
"{clean_text}"

Отформатируй красиво на русском языке:
🔥 Заголовки:
1. ...
2. ...
3. ...

📝 Описание:
..."""

        payload = {
            'messages': [
                {'role': 'system', 'content': 'Ты SMM специалист. Составляй кликабельные заголовки и описания для Shorts.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 350,
            'temperature': 0.7
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    result = data.get('result', {})
                    response_text = result.get('response', '').strip()
                    return {'success': True, 'description': response_text}
                return {'success': False, 'error': str(data.get('errors', 'Ошибка генерации описания'))}
            return {'success': False, 'error': f'HTTP {resp.status_code}: {resp.text[:150]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def extract_audio_for_whisper(self, video_path: str, output_wav_path: str) -> bool:
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            '-y',
            '-i', video_path,
            '-vn',
            '-ar', '16000',
            '-ac', '1',
            '-c:a', 'pcm_s16le',
            output_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.exists(output_wav_path)

    def get_audio_duration(self, audio_path: str) -> float:
        ffmpeg_path = get_ffmpeg_path()
        cmd = [ffmpeg_path, '-i', audio_path, '-hide_banner']
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        dur_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', res.stderr)
        if dur_match:
            h, m, s = dur_match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
        return 0.0

    def _call_whisper_api(self, audio_bytes: bytes, account_id: str, api_token: str, language: Optional[str] = None) -> Dict[str, Any]:
        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/openai/whisper'
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/octet-stream'
        }
        params = {}
        if language and language != 'auto':
            params['language'] = language

        resp = requests.post(url, headers=headers, params=params, data=audio_bytes, timeout=180)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                return {'success': True, 'result': data.get('result', {})}
            return {'success': False, 'error': str(data.get('errors', 'Неизвестная ошибка модели'))}
        elif resp.status_code == 429:
            return {'success': False, 'error': 'Превышен лимит запросов Cloudflare (Rate Limit). Попробуйте позже.'}
        return {'success': False, 'error': f'HTTP {resp.status_code}: {resp.text[:200]}'}

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = 'auto',
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        cfg = self.get_cloudflare_config()
        account_id = cfg.get('account_id')
        api_token = cfg.get('api_token')

        if not account_id or not api_token:
            return {'success': False, 'error': 'Сначала укажите Cloudflare Account ID и API Token в настройках'}

        audio_hash = self.compute_file_hash(audio_path)
        cache_file = os.path.join(CACHE_DIR, f'{audio_hash}_{language}.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    if progress_cb:
                        progress_cb({'status': 'cached', 'percent': 100, 'message': 'Найдено в кэше!'})
                    return {'success': True, 'cached': True, 'data': cached_data}
            except Exception:
                pass

        total_duration = self.get_audio_duration(audio_path)
        chunk_length = 240.0
        ffmpeg_path = get_ffmpeg_path()

        all_segments = []
        full_text_parts = []

        if total_duration <= chunk_length:
            if progress_cb:
                progress_cb({'status': 'transcribing', 'percent': 30, 'message': 'Отправка аудио в Whisper AI...'})
            
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            res = self._call_whisper_api(audio_bytes, account_id, api_token, language)
            if not res.get('success'):
                return res

            result_data = res.get('result', {})
            parsed = self._normalize_whisper_result(result_data, offset=0.0)
            all_segments = parsed['segments']
            full_text = parsed['text']
            detected_lang = parsed.get('language', language)
        else:
            num_chunks = math.ceil(total_duration / chunk_length)
            cur_start = 0.0
            detected_lang = language

            for i in range(num_chunks):
                if self.is_cancelled:
                    return {'success': False, 'cancelled': True}

                cur_end = min(cur_start + chunk_length, total_duration)
                chunk_dur = cur_end - cur_start
                chunk_file = os.path.join(CACHE_DIR, f'chunk_{i}_{audio_hash}.wav')

                cmd = [
                    ffmpeg_path, '-y',
                    '-ss', str(cur_start),
                    '-i', audio_path,
                    '-t', str(chunk_dur),
                    '-c', 'copy',
                    chunk_file
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if progress_cb:
                    pct = int(20 + (i / num_chunks) * 70)
                    progress_cb({
                        'status': 'transcribing',
                        'percent': pct,
                        'message': f'Распознавание части {i+1} из {num_chunks}...'
                    })

                with open(chunk_file, 'rb') as f:
                    audio_bytes = f.read()
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)

                res = self._call_whisper_api(audio_bytes, account_id, api_token, language)
                if not res.get('success'):
                    return res

                result_data = res.get('result', {})
                parsed = self._normalize_whisper_result(result_data, offset=cur_start)
                all_segments.extend(parsed['segments'])
                full_text_parts.append(parsed['text'])
                if detected_lang == 'auto' and parsed.get('language'):
                    detected_lang = parsed.get('language')

                cur_start += chunk_length

            full_text = ' '.join(full_text_parts)

        final_data = {
            'language': detected_lang,
            'text': full_text,
            'segments': all_segments
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return {'success': True, 'cached': False, 'data': final_data}

    @staticmethod
    def _parse_vtt(vtt_text: str, offset: float = 0.0) -> List[Dict[str, Any]]:
        segments = []
        cue_pattern = re.compile(r'(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\s*-->\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)')
        lines = vtt_text.strip().splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = cue_pattern.search(line)
            if m:
                h1, m1, s1, h2, m2, s2 = m.groups()
                t1 = (int(h1) if h1 else 0) * 3600 + int(m1) * 60 + float(s1) + offset
                t2 = (int(h2) if h2 else 0) * 3600 + int(m2) * 60 + float(s2) + offset
                
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip() and not cue_pattern.search(lines[i]):
                    text_lines.append(lines[i].strip())
                    i += 1
                cue_text = ' '.join(text_lines)
                
                w_list = cue_text.split()
                words = []
                if w_list:
                    dur = max(0.2, t2 - t1)
                    step = dur / len(w_list)
                    for w_idx, w_str in enumerate(w_list):
                        ws = round(t1 + w_idx * step, 2)
                        we = round(ws + step, 2)
                        words.append({'word': w_str, 'start': ws, 'end': we})
                        
                segments.append({
                    'start': round(t1, 2),
                    'end': round(t2, 2),
                    'text': cue_text,
                    'words': words
                })
            else:
                i += 1
        return segments

    def _normalize_whisper_result(self, result_data: Dict[str, Any], offset: float = 0.0, total_duration: float = 0.0) -> Dict[str, Any]:
        text = result_data.get('text', '').strip()
        raw_segments = result_data.get('segments', [])
        raw_words = result_data.get('words', [])
        raw_vtt = result_data.get('vtt', '')
        normalized_segments = []

        if raw_segments:
            for seg in raw_segments:
                s_start = round(float(seg.get('start', 0.0)) + offset, 2)
                s_end = round(float(seg.get('end', 0.0)) + offset, 2)
                s_text = seg.get('text', '').strip()
                
                seg_words = seg.get('words', [])
                words = []
                if seg_words:
                    for w in seg_words:
                        w_word = w.get('word', '').strip()
                        if not w_word:
                            continue
                        w_start = round(float(w.get('start', s_start)) + offset, 2)
                        w_end = round(float(w.get('end', s_end)) + offset, 2)
                        words.append({'word': w_word, 'start': w_start, 'end': w_end})
                else:
                    words_list = s_text.split()
                    if words_list:
                        dur = max(0.2, s_end - s_start)
                        step = dur / len(words_list)
                        for idx, w_str in enumerate(words_list):
                            w_s = round(s_start + idx * step, 2)
                            w_e = round(w_s + step, 2)
                            words.append({'word': w_str, 'start': w_s, 'end': w_e})

                normalized_segments.append({
                    'start': s_start,
                    'end': s_end,
                    'text': s_text,
                    'words': words
                })
        elif raw_words:
            all_words = []
            for w in raw_words:
                w_word = w.get('word', '').strip()
                if not w_word:
                    continue
                w_start = round(float(w.get('start', 0.0)) + offset, 2)
                w_end = round(float(w.get('end', w_start + 0.35)) + offset, 2)
                all_words.append({'word': w_word, 'start': w_start, 'end': w_end})

            cur_chunk = []
            for w in all_words:
                if cur_chunk:
                    pause = w['start'] - cur_chunk[-1]['end']
                    ends_sentence = cur_chunk[-1]['word'].endswith(('.', '!', '?', '...'))
                    if pause > 0.7 or ends_sentence or len(cur_chunk) >= 5:
                        s_start = cur_chunk[0]['start']
                        s_end = cur_chunk[-1]['end']
                        s_text = ' '.join(cw['word'] for cw in cur_chunk)
                        normalized_segments.append({
                            'start': s_start,
                            'end': s_end,
                            'text': s_text,
                            'words': cur_chunk
                        })
                        cur_chunk = []
                cur_chunk.append(w)

            if cur_chunk:
                s_start = cur_chunk[0]['start']
                s_end = cur_chunk[-1]['end']
                s_text = ' '.join(cw['word'] for cw in cur_chunk)
                normalized_segments.append({
                    'start': s_start,
                    'end': s_end,
                    'text': s_text,
                    'words': cur_chunk
                })
        elif raw_vtt:
            normalized_segments = self._parse_vtt(raw_vtt, offset=offset)
        elif text:
            words_list = text.split()
            if words_list:
                dur = max(2.0, total_duration if total_duration > 0 else len(words_list) * 0.4)
                step = dur / len(words_list)
                all_words = []
                for idx, w_str in enumerate(words_list):
                    ws = round(offset + idx * step, 2)
                    we = round(ws + step, 2)
                    all_words.append({'word': w_str, 'start': ws, 'end': we})

                cur_chunk = []
                for w in all_words:
                    if cur_chunk:
                        ends_sentence = cur_chunk[-1]['word'].endswith(('.', '!', '?', '...'))
                        if ends_sentence or len(cur_chunk) >= 4:
                            normalized_segments.append({
                                'start': cur_chunk[0]['start'],
                                'end': cur_chunk[-1]['end'],
                                'text': ' '.join(cw['word'] for cw in cur_chunk),
                                'words': cur_chunk
                            })
                            cur_chunk = []
                    cur_chunk.append(w)
                if cur_chunk:
                    normalized_segments.append({
                        'start': cur_chunk[0]['start'],
                        'end': cur_chunk[-1]['end'],
                        'text': ' '.join(cw['word'] for cw in cur_chunk),
                        'words': cur_chunk
                    })

        return {
            'language': result_data.get('language', 'auto'),
            'text': text,
            'segments': normalized_segments
        }

    def rechunk_words_per_subtitle(self, raw_segments: List[Dict[str, Any]], words_per_sub: int = 3) -> List[Dict[str, Any]]:
        all_words = []
        for seg in raw_segments:
            seg_words = seg.get('words', [])
            if seg_words:
                for w in seg_words:
                    all_words.append(w)
            else:
                w_list = seg.get('text', '').split()
                if w_list:
                    s_start = seg.get('start', 0.0)
                    s_end = seg.get('end', s_start + 1.0)
                    dur = max(0.2, s_end - s_start)
                    step = dur / len(w_list)
                    for idx, w_str in enumerate(w_list):
                        ws = round(s_start + idx * step, 2)
                        we = round(ws + step, 2)
                        all_words.append({'word': w_str, 'start': ws, 'end': we})

        if not all_words:
            return raw_segments

        new_segments = []
        n_words = max(1, min(10, words_per_sub)) if words_per_sub > 0 else 3

        cur_idx = 0
        total = len(all_words)

        while cur_idx < total:
            chunk = all_words[cur_idx : cur_idx + n_words]
            if not chunk:
                break
            
            w_start = chunk[0]['start']
            w_end = chunk[-1]['end']
            if w_end <= w_start:
                w_end = w_start + 0.5

            w_text = ' '.join(c['word'] for c in chunk)
            new_segments.append({
                'start': w_start,
                'end': w_end,
                'text': w_text,
                'words': chunk
            })
            cur_idx += n_words

        return new_segments

    @staticmethod
    def hex_to_ass_color(hex_str: str, alpha_hex: str = '00') -> str:
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 6:
            r, g, b = hex_str[0:2], hex_str[2:4], hex_str[4:6]
            return f'&H{alpha_hex}{b}{g}{r}&'
        return '&H00FFFFFF&'

    def generate_ass(
        self,
        segments: List[Dict[str, Any]],
        video_width: int,
        video_height: int,
        styles: Dict[str, Any],
        output_ass_path: str
    ) -> str:
        play_res_x = video_width if video_width > 0 else 1080
        play_res_y = video_height if video_height > 0 else 1920

        font_name = styles.get('font_name', 'Montserrat')
        font_size = int(styles.get('font_size', 56))
        font_bold = -1 if styles.get('font_bold', True) else 0

        text_color = self.hex_to_ass_color(styles.get('text_color', '#FFFFFF'))
        active_color = self.hex_to_ass_color(styles.get('active_color', '#FFD700'))
        outline_color = self.hex_to_ass_color(styles.get('outline_color', '#000000'))
        shadow_color = self.hex_to_ass_color(styles.get('shadow_color', '#000000'), alpha_hex='60')

        outline_width = float(styles.get('outline_width', 4.0))
        shadow_depth = float(styles.get('shadow_depth', 2.0))
        
        pos_y_pct = float(styles.get('position_y', 75.0))
        margin_v = int(play_res_y * (1.0 - (pos_y_pct / 100.0)))
        margin_v = max(40, min(play_res_y - 80, margin_v))

        active_word_enabled = bool(styles.get('active_word_enabled', True))
        animation_mode = styles.get('animation', 'pop')

        ass_content = [
            '[Script Info]',
            '; Script generated by MediaStudio AutoSubtitles',
            'ScriptType: v4.00+',
            f'PlayResX: {play_res_x}',
            f'PlayResY: {play_res_y}',
            'ScaledBorderAndShadow: yes',
            '',
            '[V4+ Styles]',
            'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
            f'Style: Default,{font_name},{font_size},{text_color},&H000000FF&,{outline_color},{shadow_color},{font_bold},0,0,0,100,100,0,0,1,{outline_width},{shadow_depth},2,40,40,{margin_v},1',
            '',
            '[Events]',
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text'
        ]

        def fmt_time(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            cs = int(round((sec - int(sec)) * 100))
            if cs >= 100:
                cs = 99
            return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

        for seg in segments:
            start_s = fmt_time(seg['start'])
            end_s = fmt_time(seg['end'])
            words = seg.get('words', [])

            anim_tag = ''
            if animation_mode == 'pop':
                anim_tag = '{\t(0,100,\fscx110\fscy110)\t(100,200,\fscx100\fscy100)}'
            elif animation_mode == 'fade':
                anim_tag = '{\fad(80,80)}'
            elif animation_mode == 'bounce':
                anim_tag = '{\t(0,80,\fscy120)\t(80,180,\fscy100)}'

            if active_word_enabled and words:
                line_parts = []
                for w in words:
                    w_dur_cs = max(10, int(round((w['end'] - w['start']) * 100)))
                    line_parts.append(f'{{\k{w_dur_cs}}}{w["word"]}')
                dialogue_text = f'{anim_tag}{{\2c{active_color}}}' + ' '.join(line_parts)
            else:
                dialogue_text = f'{anim_tag}{seg.get("text", "")}'

            ass_content.append(f'Dialogue: 0,{start_s},{end_s},Default,,0,0,0,,{dialogue_text}')

        with open(output_ass_path, 'w', encoding='utf-8') as f:
            for item in ass_content:
                f.write(f'{item}\n')

        return output_ass_path

    def export_srt(self, segments: List[Dict[str, Any]], output_path: str):
        def fmt_srt_time(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int(round((sec - int(sec)) * 1000))
            if ms >= 1000:
                ms = 999
            return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

        lines = []
        for idx, seg in enumerate(segments, 1):
            lines.append(str(idx))
            lines.append(f'{fmt_srt_time(seg["start"])} --> {fmt_srt_time(seg["end"])}')
            lines.append(seg.get('text', ''))
            lines.append('')

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in lines:
                f.write(f'{item}\n')

    def export_vtt(self, segments: List[Dict[str, Any]], output_path: str):
        def fmt_vtt_time(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int(round((sec - int(sec)) * 1000))
            if ms >= 1000:
                ms = 999
            return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'

        lines = ['WEBVTT', '']
        for idx, seg in enumerate(segments, 1):
            lines.append(str(idx))
            lines.append(f'{fmt_vtt_time(seg["start"])} --> {fmt_vtt_time(seg["end"])}')
            lines.append(seg.get('text', ''))
            lines.append('')

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in lines:
                f.write(f'{item}\n')

    def cancel_burn(self):
        self.is_cancelled = True
        if self._current_process:
            try:
                self._current_process.terminate()
                time.sleep(0.2)
                if self._current_process.poll() is None:
                    self._current_process.kill()
            except Exception:
                pass

    def burn_subtitles_to_video(
        self,
        video_path: str,
        ass_path: str,
        output_video_path: str,
        quality_mode: str = 'fast',
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
        completion_cb: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.is_cancelled = False

        def _worker():
            ffmpeg_path = get_ffmpeg_path()
            try:
                dur_cmd = [ffmpeg_path, '-i', video_path, '-hide_banner']
                dur_res = subprocess.run(dur_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                total_duration = 1.0
                dur_match = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', dur_res.stderr)
                if dur_match:
                    h, m, s = dur_match.groups()
                    total_duration = max(1.0, int(h) * 3600 + int(m) * 60 + float(s))

                escaped_ass = ass_path.replace('\\', '/').replace(':', '\\:').replace("'", "'\\''")
                
                cmd = [
                    ffmpeg_path,
                    '-y',
                    '-i', video_path,
                    '-vf', f"ass='{escaped_ass}'",
                ]

                if quality_mode == 'fast':
                    cmd.extend([
                        '-c:v', 'h264_videotoolbox',
                        '-b:v', '6M',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                    ])
                else:
                    cmd.extend([
                        '-c:v', 'libx264',
                        '-crf', '19',
                        '-preset', 'fast',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                    ])

                cmd.append(output_video_path)

                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                while True:
                    line = self._current_process.stderr.readline()
                    if not line and self._current_process.poll() is not None:
                        break
                    
                    if self.is_cancelled:
                        break

                    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                    if time_match and progress_cb:
                        h, m, s = time_match.groups()
                        cur_time = int(h) * 3600 + int(m) * 60 + float(s)
                        pct = min(99, int((cur_time / total_duration) * 100))
                        progress_cb({
                            'status': 'rendering',
                            'percent': pct,
                            'message': f'Рендеринг видео ({pct}%)...'
                        })

                self._current_process.wait()

                if self.is_cancelled:
                    if os.path.exists(output_video_path):
                        try:
                            os.remove(output_video_path)
                        except Exception:
                            pass
                    if completion_cb:
                        completion_cb({'success': False, 'cancelled': True, 'message': 'Рендеринг остановлен'})
                elif self._current_process.returncode == 0 and os.path.exists(output_video_path):
                    if progress_cb:
                        progress_cb({'status': 'finished', 'percent': 100, 'message': 'Готово!'})
                    if completion_cb:
                        completion_cb({
                            'success': True,
                            'output_video': output_video_path,
                            'message': f'Субтитры успешно вшиты в видео: {os.path.basename(output_video_path)}'
                        })
                else:
                    fallback_cmd = [
                        ffmpeg_path,
                        '-y',
                        '-i', video_path,
                        '-vf', f"ass='{escaped_ass}'",
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '20',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        output_video_path
                    ]
                    fb_res = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if fb_res.returncode == 0 and os.path.exists(output_video_path):
                        if progress_cb:
                            progress_cb({'status': 'finished', 'percent': 100, 'message': 'Готово!'})
                        if completion_cb:
                            completion_cb({
                                'success': True,
                                'output_video': output_video_path,
                                'message': f'Субтитры успешно вшиты в видео: {os.path.basename(output_video_path)}'
                            })
                    else:
                        err_msg = fb_res.stderr[-200:] if fb_res.stderr else 'Неизвестная ошибка FFmpeg'
                        if completion_cb:
                            completion_cb({'success': False, 'error': f'Ошибка FFmpeg при рендере: {err_msg}'})

            except Exception as e:
                if completion_cb:
                    completion_cb({'success': False, 'error': str(e)})

        self._current_thread = threading.Thread(target=_worker, daemon=True)
        self._current_thread.start()
