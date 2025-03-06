@echo off
setlocal enabledelayedexpansion

:: Variables
set VENV_DIR=venv
set PYTHON=%VENV_DIR%\Scripts\python.exe
set PIP=%VENV_DIR%\Scripts\pip.exe
set FLIT=%VENV_DIR%\Scripts\flit.exe
set PRE_COMMIT=%VENV_DIR%\Scripts\pre-commit.exe
set PYPROJECT=pyproject.toml

:: Check if no arguments provided
if "%1"=="" goto help

:: Process commands
if "%1"=="test" goto test
if "%1"=="lint" goto lint
if "%1"=="docs" goto docs
if "%1"=="clean" goto clean
if "%1"=="help" goto help

echo Unknown command: %1
goto help

:ensure_venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv %VENV_DIR%
    call %VENV_DIR%\Scripts\activate.bat
    %PIP% install --upgrade pip wheel
    %PIP% install flit
    %FLIT% install -s --deps develop
) else (
    call %VENV_DIR%\Scripts\activate.bat
)
goto :eof

:test
call :ensure_venv
%PYTHON% -m pytest tests
goto :eof

:lint
call :ensure_venv
%PRE_COMMIT% run --all-files
goto :eof

:docs
call :ensure_venv
%PIP% install -r docs\requirements.txt
if not exist "docs\_static" mkdir docs\_static
if not exist "docs\_templates" mkdir docs\_templates
%PYTHON% -m sphinx -b html docs docs\_build
goto :eof

:clean
::if exist %VENV_DIR% rmdir /s /q %VENV_DIR%
if exist .ruff_cache rmdir /s /q .ruff_cache
if exist dist rmdir /s /q dist
if exist docs\_build rmdir /s /q docs\_build
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
if exist coverage.xml del /q coverage.xml
if exist report.xml del /q report.xml
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .mypy_cache rmdir /s /q .mypy_cache
if exist .coverage del /q .coverage
if exist htmlcov rmdir /s /q htmlcov
goto :eof

:help
echo Makefile for eLxr Metrics project
echo.
echo Usage:
echo   make test      - Run tests
echo   make lint      - Lint the code
echo   make docs      - Generate documentation
echo   make clean     - Clean up generated files
echo   make help      - Show this help message
goto :eof

endlocal