# Development Guide - GeoFinder

## 🚀 Initial Setup with uv

### 1. Install the project in development mode

```bash
# Install the package in editable mode with development dependencies
uv pip install -e ".[dev,pyproj]"

# Or install everything (dev + pyproj + http + docs)
uv pip install -e ".[dev,pyproj,http,docs]"
```

### 2. Verify installation

```bash
# Verify that pytest is installed
uv run pytest --version

# Verify that ruff is installed
uv run ruff --version

# Verify that mypy is installed
uv run mypy --version
```

## 🛠️ Development Commands

### Testing

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run tests in watch mode (requires pytest-watch)
uv run pytest-watch

# Run a specific test
uv run pytest tests/test_geofinder.py::test_find_placename
```

### Linting and Formatting

```bash
# Check code with ruff
uv run ruff check .

# Automatically format code
uv run ruff format .

# Check and auto-fix issues
uv run ruff check --fix .
```

### Type Checking

```bash
# Check types with mypy
uv run mypy geofinder/
```

### Run Everything (Local CI)

```bash
# Format, lint and tests
uv run ruff format . && uv run ruff check --fix . && uv run pytest
```

## 📦 Dependency Management

### Adding a dependency

```bash
# Production dependency (edit pyproject.toml manually)
# Then sync:
uv pip install -e .

# Development dependency
# Add to [project.optional-dependencies.dev] in pyproject.toml
# Then:
uv pip install -e ".[dev]"
```

### Update dependencies

```bash
# Update all dependencies
uv pip install --upgrade -e ".[dev,pyproj]"
```

### View installed dependencies

```bash
uv pip list
```

## 🧪 Test Structure (Recommended)

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_geofinder.py        # GeoFinder tests
├── test_pelias.py           # PeliasClient tests
├── test_transformations.py  # Transformation tests
└── fixtures/
    └── mock_responses.json  # ICGC mock responses
```

## 📝 Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/new-functionality
   ```

2. **Make changes and verify**
   ```bash
   # Format code
   uv run ruff format .
   
   # Check linting
   uv run ruff check .
   
   # Run tests
   uv run pytest
   ```

3. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: change description"
   git push origin feature/new-functionality
   ```

## 🔧 IDE Configuration

### VS Code

Create `.vscode/settings.json`:

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

1. Settings → Project → Python Interpreter → Select `.venv`
2. Settings → Tools → Python Integrated Tools → Testing → pytest
3. Settings → Editor → Code Style → Python → Line length: 100

## 🌐 MCP Server Development

### Installation with MCP Dependencies

```bash
# Install with full MCP support
uv pip install -e ".[mcp,dev,pyproj]"

# Verify installation
geofinder-icgc --help
```

### Server Configuration

```bash
# Copy example configuration file
cp .env.example .env

# Edit configuration if necessary
# .env contains environment variables for the server
```

### Run the Server in Development

```bash
# STDIO mode (for integration with MCP clients)
python -m geofinder.mcp_server

# HTTP mode (for testing)
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
