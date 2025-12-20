# Guía de Desarrollo - GeoFinder

## 🚀 Configuración Inicial con uv

### 1. Instalar el proyecto en modo desarrollo

```bash
# Instalar el paquete en modo editable con dependencias de desarrollo
uv pip install -e ".[dev,pyproj]"

# O instalar todo (dev + pyproj + http + docs)
uv pip install -e ".[dev,pyproj,http,docs]"
```

### 2. Verificar instalación

```bash
# Verificar que pytest está instalado
uv run pytest --version

# Verificar que ruff está instalado
uv run ruff --version

# Verificar que mypy está instalado
uv run mypy --version
```

## 🛠️ Comandos de Desarrollo

### Testing

```bash
# Ejecutar todos los tests
uv run pytest

# Ejecutar tests con cobertura
uv run pytest --cov

# Ejecutar tests en modo watch (requiere pytest-watch)
uv run pytest-watch

# Ejecutar un test específico
uv run pytest tests/test_geofinder.py::test_find_placename
```

### Linting y Formateo

```bash
# Verificar código con ruff
uv run ruff check .

# Formatear código automáticamente
uv run ruff format .

# Verificar y auto-arreglar problemas
uv run ruff check --fix .
```

### Type Checking

```bash
# Verificar tipos con mypy
uv run mypy geofinder/
```

### Ejecutar Todo (CI Local)

```bash
# Formatear, lint y tests
uv run ruff format . && uv run ruff check --fix . && uv run pytest
```

## 📦 Gestión de Dependencias

### Añadir una dependencia

```bash
# Dependencia de producción (editar pyproject.toml manualmente)
# Luego sincronizar:
uv pip install -e .

# Dependencia de desarrollo
# Añadir a [project.optional-dependencies.dev] en pyproject.toml
# Luego:
uv pip install -e ".[dev]"
```

### Actualizar dependencias

```bash
# Actualizar todas las dependencias
uv pip install --upgrade -e ".[dev,pyproj]"
```

### Ver dependencias instaladas

```bash
uv pip list
```

## 🧪 Estructura de Tests (Recomendada)

```
tests/
├── __init__.py
├── conftest.py              # Fixtures compartidas
├── test_geofinder.py        # Tests de GeoFinder
├── test_pelias.py           # Tests de PeliasClient
├── test_transformations.py  # Tests de transformaciones
└── fixtures/
    └── mock_responses.json  # Respuestas mock del ICGC
```

## 📝 Workflow de Desarrollo

1. **Crear una rama**
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. **Hacer cambios y verificar**
   ```bash
   # Formatear código
   uv run ruff format .
   
   # Verificar linting
   uv run ruff check .
   
   # Ejecutar tests
   uv run pytest
   ```

3. **Commit y push**
   ```bash
   git add .
   git commit -m "feat: descripción del cambio"
   git push origin feature/nueva-funcionalidad
   ```

## 🔧 Configuración del IDE

### VS Code

Crear `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.linting.enabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  "ruff.lint.args": ["--config=pyproject.toml"],
  "mypy.runUsingActiveInterpreter": true
}
```


### PyCharm

1. Settings → Project → Python Interpreter → Seleccionar `.venv`
2. Settings → Tools → Python Integrated Tools → Testing → pytest
3. Settings → Editor → Code Style → Python → Line length: 100

## 🌐 Desarrollo del Servidor MCP

### Instalación con Dependencias MCP

```bash
# Instalar con soporte MCP completo
uv pip install -e ".[mcp,dev,pyproj]"

# Verificar instalación
geofinder-mcp --help
```

### Configuración del Servidor

```bash
# Copiar archivo de configuración de ejemplo
cp .env.example .env

# Editar configuración si es necesario
# .env contiene variables de entorno para el servidor
```

### Ejecutar el Servidor en Desarrollo

```bash
# Modo STDIO (para integración con clientes MCP)
python -m geofinder.mcp_server

# Modo HTTP (para testing)
python -m geofinder.mcp_server --transport http --port 8000

# Con logging detallado
python -m geofinder.mcp_server --log-level DEBUG

# Usando el CLI de FastMCP
fastmcp run geofinder/mcp_server.py:mcp --transport http --port 8000
```

### Testing del Servidor MCP

```bash
# 1. Verificar que el servidor arranca sin errores
python -m geofinder.mcp_server --help

# 2. Probar servidor HTTP
python -m geofinder.mcp_server --transport http --port 8000 &
# Verificar que responde (en otra terminal)
curl http://localhost:8000/

# 3. Probar con el cliente de FastMCP (si está disponible)
fastmcp test geofinder/mcp_server.py:mcp
```

### Estructura del Código MCP

```
geofinder/
├── __init__.py            # Exports públicos
├── geofinder.py           # 🔄 Core async + wrappers sync
├── pelias.py              # 🔄 Cliente HTTP async (httpx)
├── transformations.py     # Transformaciones (sync, CPU-bound)
└── mcp_server.py          # ⭐ Servidor MCP (herramientas async)
```

### Verificar Compatibilidad

```bash
# Las pruebas existentes deben seguir pasando
uv run pytest

# El uso como biblioteca (API sync) debe funcionar
python -c "from geofinder import GeoFinder; gf = GeoFinder(); print(gf.find_sync('Barcelona')[:1])"

# El uso como biblioteca (API async)
python -c "import asyncio; from geofinder import GeoFinder; gf = GeoFinder(); print(asyncio.run(gf.find('Barcelona'))[:1])"
```

### API Dual: Async vs Sync

```python
# API Async (recomendada para batch processing)
import asyncio
from geofinder import GeoFinder

async def batch_geocode():
    gf = GeoFinder()
    # Procesar múltiples queries en paralelo
    results = await asyncio.gather(
        gf.find("Barcelona"),
        gf.find("Girona"),
        gf.find("Lleida")
    )
    await gf.close()
    return results

# API Sync (para scripts simples)
from geofinder import GeoFinder
gf = GeoFinder()
results = gf.find_sync("Barcelona")  # Usa asyncio.run() internamente
```

## 🔐 Manejo de SSL

La clase `PeliasClient` y por extensión `GeoFinder` permiten desactivar la verificación SSL mediante el parámetro `verify_ssl=False`.

Implementación técnica:
- Se pasa el parámetro `verify` al `httpx.AsyncClient`.
- Si se desactiva, se usa `warnings.filterwarnings('ignore', category=InsecureRequestWarning)` para evitar ruido en los logs.
- **Importante**: Debido a la naturaleza del módulo `warnings` de Python, esta supresión es **global** para el proceso actual.

## 📚 Recursos

- [uv Documentation](https://github.com/astral-sh/uv)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [FastMCP Documentation](https://gofastmcp.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
