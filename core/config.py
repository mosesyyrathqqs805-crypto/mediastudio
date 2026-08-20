import os
import sys
import shutil
from pathlib import Path
import imageio_ffmpeg

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(BASE_DIR, 'bin')

paths_to_add = [
    BIN_DIR,
    '/usr/local/bin',
    '/opt/homebrew/bin',
    '/usr/bin',
    '/bin',
    r'C:\ffmpeg\bin',
    r'C:\ProgramData\chocolatey\bin'
]

current_path = os.environ.get('PATH', '')
for p in paths_to_add:
    if os.path.exists(p) and p not in current_path.split(os.pathsep):
        current_path = p + os.pathsep + current_path
os.environ['PATH'] = current_path

DEFAULT_DOWNLOAD_DIR = str(Path.home() / 'Downloads')

def get_user_data_dir() -> str:
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            path = os.path.join(appdata, 'MediaStudio')
        else:
            path = os.path.join(str(Path.home()), '.mediastudio')
    elif sys.platform == 'darwin':
        path = os.path.join(str(Path.home()), 'Library', 'Application Support', 'MediaStudio')
    else:
        path = os.path.join(str(Path.home()), '.config', 'mediastudio')
    os.makedirs(path, exist_ok=True)
    return path

def get_config_file_path() -> str:
    local_cfg = os.path.join(BASE_DIR, 'data', 'config.json')
    if os.path.exists(local_cfg):
        return local_cfg
    user_data_dir = get_user_data_dir()
    return os.path.join(user_data_dir, 'config.json')

def get_cache_dir() -> str:
    local_cache = os.path.join(BASE_DIR, 'data', 'cache')
    if os.path.exists(os.path.join(BASE_DIR, 'data')):
        os.makedirs(local_cache, exist_ok=True)
        return local_cache
    user_cache = os.path.join(get_user_data_dir(), 'cache')
    os.makedirs(user_cache, exist_ok=True)
    return user_cache

def get_ffmpeg_path() -> str:
    exe_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
    local_bin = os.path.join(BIN_DIR, exe_name)
    if os.path.exists(local_bin):
        return local_bin
    
    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass

    which_path = shutil.which(exe_name) or shutil.which('ffmpeg')
    if which_path:
        return which_path

    return exe_name
