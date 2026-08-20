import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build')
ICON_PATH = os.path.join(BASE_DIR, 'assets', 'icon.ico')


def clean_previous_builds():
    for d in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def run_build():
    clean_previous_builds()

    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name=MediaStudio',
        f'--icon={ICON_PATH}',
        '--add-data=ui;ui',
        '--add-data=assets;assets',
        '--collect-all=webview',
        '--collect-all=yt_dlp',
        '--collect-all=imageio_ffmpeg',
        '--collect-all=requests',
        'main.py'
    ]

    print("Running Windows build...")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\nBuild successful!")
        print(f"Output: {os.path.join(DIST_DIR, 'MediaStudio.exe')}")
    else:
        print(f"\nBuild error. Return code: {res.returncode}")
        sys.exit(res.returncode)


if __name__ == '__main__':
    run_build()
