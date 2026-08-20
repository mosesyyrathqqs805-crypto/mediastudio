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
        '-m', 'nuitka',
        '--standalone',
        '--onefile',
        '--windows-disable-console',
        f'--windows-icon-from-ico={ICON_PATH}',
        '--windows-company-name=MediaStudio',
        '--windows-product-name=MediaStudio',
        '--windows-file-version=1.0.0.0',
        '--windows-product-version=1.0.0.0',
        '--windows-file-description=MediaStudio',
        '--include-data-dir=ui=ui',
        '--include-data-dir=assets=assets',
        '--include-package=pywebview',
        '--include-package=yt_dlp',
        '--include-package=imageio_ffmpeg',
        '--include-package=requests',
        '--enable-plugin=anti-bloat',
        '--lto=no',
        f'--output-dir={DIST_DIR}',
        '--output-filename=MediaStudio.exe',
        '--assume-yes-for-downloads',
        'main.py'
    ]

    print("Running Nuitka Windows compilation (Python -> C/C++ -> Windows PE Binary)...")
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\nBuild successful!")
        print(f"Output: {os.path.join(DIST_DIR, 'MediaStudio.exe')}")
    else:
        print(f"\nBuild error. Return code: {res.returncode}")
        sys.exit(res.returncode)


if __name__ == '__main__':
    run_build()
