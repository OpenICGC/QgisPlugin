# 📦 Guía de Publicación en PyPI: geofinder-icgc

Esta guía detalla los pasos necesarios para publicar el paquete `geofinder-icgc` en [PyPI](https://pypi.org/).

## 1. Requisitos Previos

### Cuentas
1.  **PyPI**: Crea una cuenta en [pypi.org](https://pypi.org/account/register/).
2.  **TestPyPI** (Recomendado): Crea una cuenta en [test.pypi.org](https://test.pypi.org/account/register/) para probar la subida sin afectar al repositorio real.

### Herramientas
Asegúrate de tener instaladas las herramientas de construcción:
```bash
pip install --upgrade build twine
```

---

## 2. Preparación del Proyecto

### Metadatos en `pyproject.toml`
El archivo `pyproject.toml` ya está configurado. Asegúrate de que la versión en `geofinder/__init__.py` sea la correcta antes de construir.

### README y Enlaces
> [!IMPORTANT]
> PyPI no renderiza bien los enlaces relativos a archivos locales (ej. `[License](LICENSE)`). Es recomendable usar URLs absolutas de GitHub para que los usuarios puedan navegar desde PyPI.

---

## 3. Construcción del Paquete

Desde la raíz del proyecto, ejecuta:
```bash
python3 -m build
```
Esto generará una carpeta `dist/` con dos archivos:
-   Un archivo `.tar.gz` (Source Distribution)
-   Un archivo `.whl` (Built Distribution)

---

## 4. Subida a PyPI

### Opción A: Probar en TestPyPI (Recomendado la primera vez)
```bash
python3 -m twine upload --repository testpypi dist/*
```
*Puedes instalarlo para probar:* `pip install --index-url https://test.pypi.org/simple/ geofinder-icgc`

### Opción B: Publicar en PyPI Real
```bash
python3 -m twine upload dist/*
```

---

## 5. Mejores Prácticas: Tokens de API

En lugar de usar tu contraseña, genera un **API Token** en PyPI:
1.  Ve a `Account Settings` -> `API Tokens`.
2.  Crea un token con alcance limitado al proyecto (o "All projects" la primera vez).
3.  Usa `__token__` como nombre de usuario y el valor del token como contraseña cuando `twine` te lo pida.

---

## 6. Automatización (GitHub Actions)

Para que el paquete se publique automáticamente al crear una "Release" en GitHub, puedes usar este flujo de trabajo:

Crea un archivo `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

> [!TIP]
> Configura el secreto `PYPI_API_TOKEN` en los ajustes de tu repositorio en GitHub (`Settings > Secrets and variables > Actions`).

---

## 7. Verificación Final
Después de publicar, verifica que:
1.  La página en PyPI se ve correctamente.
2.  La instalación funciona: `pip install geofinder-icgc`.
3.  El comando MCP funciona: `geofinder-mcp --help`.
