@echo off
rem Criteris de validació de QGIS
rem Doc: https://plugins.qgis.org/docs/security-scanning

rem Configurem el path de distribució
set distrib_path=d:\public\git\qgisplugin
echo Validacio de carpeta de distribucio: %distrib_path%
echo.
rem Activem l'entorn i configurem el path de distribució
call conda activate qgis328

rem Executem detecció de secrets
echo *******************************************************************************
echo Test: detect-secrets
detect-secrets scan %distrib_path%
echo %errorlevel%
echo.

rem Executem test flake8
echo *******************************************************************************
echo Test: flake8
flake8 %distrib_path%
echo %errorlevel%
echo.

rem Executem test Bandit
echo *******************************************************************************
echo Test: bandit
bandit -r %distrib_path%
echo %errorlevel%
echo.

@pause
