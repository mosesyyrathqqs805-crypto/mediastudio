@echo off
chcp 65001 >nul
title MediaStudio — Сборка Windows .EXE (Nuitka C/C++)

echo ============================================================
echo   MediaStudio: Защищенная компиляция в Windows EXE
echo ============================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден в системе. Установите Python 3.10+ и добавьте в PATH.
    pause
    exit /b 1
)

echo [1/3] Проверка и установка зависимостей...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install nuitka zstandard ordered-set

echo.
echo [2/3] Запуск Nuitka компилятора...
python build_windows.py

echo.
echo [3/3] Готово! Исполняемый файл находится в папке dist\MediaStudio.exe
echo ============================================================
pause
