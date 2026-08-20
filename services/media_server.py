import os
import re
import mimetypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

_server_instance = None
_server_port = 0

class MediaStreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        file_path = qs.get('path', [None])[0]
        if not file_path:
            self.send_response(400)
            self.end_headers()
            return
            
        file_path = unquote(file_path)
        if file_path.startswith('/') and len(file_path) > 3 and file_path[2] == ':':
            file_path = file_path[1:]
        file_path = os.path.normpath(file_path)

        if not os.path.exists(file_path):
            self.send_response(404)
            self.end_headers()
            return
            
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'video/mp4'
            
        range_header = self.headers.get('Range')
        if range_header:
            range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1
                
                self.send_response(206)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(length))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    chunk_size = 65536
                    bytes_left = length
                    while bytes_left > 0:
                        to_read = min(chunk_size, bytes_left)
                        chunk = f.read(to_read)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except Exception:
                            break
                        bytes_left -= len(chunk)
                return

        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(file_size))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                try:
                    self.wfile.write(chunk)
                except Exception:
                    break

    def log_message(self, format, *args):
        pass

def start_media_server() -> int:
    global _server_instance, _server_port
    if _server_port > 0:
        return _server_port
    try:
        _server_instance = HTTPServer(('127.0.0.1', 0), MediaStreamHandler)
        _server_port = _server_instance.server_port
        t = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        t.start()
        return _server_port
    except Exception as e:
        print('Ошибка запуска локального медиасервера:', e)
        return 0

def get_media_url(file_path: str) -> str:
    port = start_media_server()
    if port > 0:
        import urllib.parse
        encoded = urllib.parse.quote(file_path)
        return f'http://127.0.0.1:{port}/stream?path={encoded}'
    return f'file://{file_path}'
