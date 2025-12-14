# <img src="https://raw.githubusercontent.com/OpenICGC/QgisPlugin/master/icon.png" alt="GeoFinder Logo" width="50" height="50"> GeoFinder

> **Geocodificador para Cataluña** usando el servicio del ICGC (Institut Cartogràfic i Geològic de Catalunya).

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL--2.0-yellow.svg)](LICENSE)
[![Fork](https://img.shields.io/badge/fork-OpenICGC%2FQgisPlugin-blue)](https://github.com/OpenICGC/QgisPlugin)

---

## 📜 Fork Attribution

This project is a **fork** of the [Open ICGC QGIS Plugin](https://github.com/OpenICGC/QgisPlugin), specifically extracting the `geofinder3` geocoding component as a standalone Python library.

**Original Project**: [OpenICGC/QgisPlugin](https://github.com/OpenICGC/QgisPlugin)  
**Original Author**: Institut Cartogràfic i Geològic de Catalunya (ICGC)  
**License**: GPL-2.0 (maintained)

See [FORK.md](FORK.md) for detailed fork information and changes.

---

## 📚 Guía Rápida

| Sección                                        | Descripción                   |
| ---------------------------------------------- | ----------------------------- |
| [🚀 Inicio Rápido](#-inicio-rápido)            | Instalación y primeros pasos  |
| [📖 API](#-api-principal)                      | Métodos principales           |
| [🔍 Tipos de Búsqueda](#-tipos-de-búsqueda)    | Qué puedes buscar             |
| [⚙️ Configuración](#️-configuración-avanzada)   | Opciones avanzadas            |
| [🤖 Servidor MCP](#-servidor-mcp)              | Integración con IA            |
| [🏗️ Arquitectura](#️-arquitectura)              | Documentación técnica interna |

---

## 🚀 Inicio Rápido

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/jccamel/geocoder-mcp.git
cd geocoder-mcp

# Instalación básica
pip install -e .

# Con transformación de coordenadas
pip install -e ".[pyproj]"

# Con servidor MCP para IA
pip install -e ".[mcp,pyproj]"
```

### Uso Básico

```python
from geofinder import GeoFinder

gf = GeoFinder()

# Buscar un lugar
results = gf.find("Barcelona")
for r in results:
    print(f"{r['nom']} - {r['nomTipus']}")
```

---

## 📖 API Principal

### `find(query, default_epsg=25831)` 🔍

Búsqueda general con detección automática del tipo.

```python
# Topónimos
gf.find("Montserrat")

# Coordenadas
gf.find("430000 4580000 EPSG:25831")

# Direcciones
gf.find("Barcelona, Diagonal 100")

# Carreteras
gf.find("C-32 km 10")
```

---

### `find_reverse(x, y, epsg=25831)` 📍

Geocodificación inversa (coordenadas → lugar).

```python
# Desde coordenadas UTM
results = gf.find_reverse(430000, 4580000, epsg=25831)

# Desde coordenadas GPS
results = gf.find_reverse(2.1734, 41.3851, epsg=4326)

# Con filtros de capa
results = gf.find_reverse(
    430000, 4580000,
    epsg=25831,
    layers="address,tops",
    size=10
)
```

---

### `autocomplete(partial_text, size=10)` ⌨️

Sugerencias de autocompletado.

```python
suggestions = gf.autocomplete("Barcel")
# Retorna: Barcelona, Barcelonès, etc.
```

---

## 🔍 Tipos de Búsqueda

| Tipo            | Ejemplo                       | Descripción                     |
| --------------- | ----------------------------- | ------------------------------- |
| **Topónimo**    | `"Barcelona"`, `"Montserrat"` | Cualquier nombre de lugar       |
| **Coordenadas** | `"430000 4580000 EPSG:25831"` | Punto con sistema de referencia |
| **Dirección**   | `"Barcelona, Diagonal 100"`   | Calle + número + municipio      |
| **Carretera**   | `"C-32 km 10"`                | Punto kilométrico               |
| **Rectángulo**  | `"X1 Y1 X2 Y2"`               | Área rectangular                |

### Formato de Resultados

Todos los métodos retornan una lista de diccionarios:

```python
{
    'nom': 'Barcelona',           # Nombre del lugar
    'nomTipus': 'Municipi',       # Tipo (Municipi, Carrer, etc.)
    'nomMunicipi': 'Barcelona',   # Municipio
    'nomComarca': 'Barcelonès',   # Comarca
    'x': 2.1734,                  # Longitud (WGS84)
    'y': 41.3851,                 # Latitud (WGS84)
    'epsg': 4326                  # Sistema de referencia
}
```

---

## ⚙️ Configuración Avanzada

### Opciones del Constructor

```python
import logging

# Habilitar logs de debug
logging.basicConfig(level=logging.DEBUG)

# Configuración personalizada
gf = GeoFinder(
    icgc_url="https://eines.icgc.cat/geocodificador",
    timeout=10,
    logger=logging.getLogger("mi_app")
)
```

### Sistemas de Coordenadas (EPSG)

| Código  | Sistema        | Uso                      |
| ------- | -------------- | ------------------------ |
| `4326`  | WGS84          | GPS estándar (lat/lon)   |
| `25831` | ETRS89 UTM 31N | Sistema oficial Cataluña |
| `3857`  | Web Mercator   | Mapas web                |
| `23031` | ED50 UTM 31N   | Sistema antiguo          |

### Transformación de Coordenadas

```python
# Requiere: pip install -e ".[pyproj]"

from geofinder.transformations import transform_point

# UTM → WGS84
lon, lat = transform_point(430000, 4580000, 25831, 4326)
print(f"WGS84: {lon}, {lat}")
```

---

## 🤖 Servidor MCP

GeoFinder puede ejecutarse como **servidor MCP** para integrarse con asistentes de IA como **Claude Desktop**.

### Instalación

```bash
pip install -e ".[mcp,pyproj]"
```

### Ejecutar Servidor

```bash
# STDIO (para Claude Desktop)
python -m geofinder.mcp_server

# HTTP (para testing)
python -m geofinder.mcp_server --transport http --port 8000
```

### Integración con Claude Desktop

Añade a `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "geofinder": {
      "command": "python",
      "args": ["-m", "geofinder.mcp_server"]
    }
  }
}
```

### Herramientas MCP Disponibles

- 🔍 `find_place` - Búsqueda general
- 📍 `find_reverse` - Geocodificación inversa
- ⌨️ `autocomplete` - Autocompletado
- 🏠 `find_address` - Búsqueda de direcciones
- 🗺️ `transform_coordinates` - Conversión EPSG

**📚 Documentación completa:** [README-MCP.md](README-MCP.md)

---

## 🏗️ Arquitectura

GeoFinder está estructurado en **3 capas principales** que separan responsabilidades:

### Capas del Sistema

```
┌─────────────────────────────────┐
│   Servidor MCP / API Pública    │  ← Capa de Presentación
├─────────────────────────────────┤
│   GeoFinder (Lógica Negocio)    │  ← Parsing, detección, transformaciones
├─────────────────────────────────┤
│   PeliasClient (HTTP)           │  ← Comunicación con ICGC
└─────────────────────────────────┘
```

### Componentes Principales

| Componente          | Responsabilidad                            | Archivo                                                        |
| ------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| **PeliasClient**    | Comunicación HTTP con servidor ICGC Pelias | [`geofinder/pelias.py`](geofinder/pelias.py)                   |
| **GeoFinder**       | Lógica de negocio, detección y parsing     | [`geofinder/geofinder.py`](geofinder/geofinder.py)             |
| **MCP Server**      | Exposición como herramientas para IA       | [`geofinder/mcp_server.py`](geofinder/mcp_server.py)           |
| **Transformations** | Conversión entre sistemas EPSG             | [`geofinder/transformations.py`](geofinder/transformations.py) |

### Flujo de Datos

```
Usuario → MCP/API → GeoFinder → PeliasClient → Servidor ICGC
                      ↓
              Detección automática
              Parsing de formatos
              Transformación coords
```

**📚 Documentación técnica completa:** [README-ARQ.md](README-ARQ.md)

---

## 📦 Dependencias

| Tipo           | Paquetes  | Propósito                           |
| -------------- | --------- | ----------------------------------- |
| **Requeridas** | Ninguna   | Solo librería estándar Python       |
| **Opcionales** | `pyproj`  | Transformación de coordenadas       |
|                | `GDAL`    | Alternativa a pyproj (más compleja) |
|                | `fastmcp` | Servidor MCP para IA                |

### Instalación por Uso

```bash
# Solo geocodificación
pip install -e .

# Con transformación de coordenadas
pip install -e ".[pyproj]"

# Con servidor MCP
pip install -e ".[mcp,pyproj]"

# Desarrollo completo
pip install -e ".[dev,mcp,pyproj]"
```

---

## 🛠️ Desarrollo

```bash
# Clonar repositorio
git clone https://github.com/jccamel/geocoder-mcp.git
cd geocoder-mcp

# Instalar con uv
uv pip install -e ".[dev,mcp,pyproj]"

# Ejecutar tests
uv run pytest

# Formatear código
uv run ruff format .
```

**Documentación:**

- [COOKBOOK.md](COOKBOOK.md) - 📚 Tutoriales y ejemplos prácticos
- [README-DEV.md](README-DEV.md) - Guía de desarrollo
- [README-MCP.md](README-MCP.md) - Servidor MCP
- [README-ARQ.md](README-ARQ.md) - Arquitectura técnica
- [FORK.md](FORK.md) - Información del fork

---

## 📚 Recursos

- [Documentación ICGC](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Proyecto Original](https://github.com/OpenICGC/QgisPlugin)
- [Repositorio Fork](https://github.com/jccamel/geocoder-mcp)
- [Issues](https://github.com/jccamel/geocoder-mcp/issues)
- [Model Context Protocol](https://modelcontextprotocol.io) (para MCP)

---

## 📄 Licencia

GPL-2.0 License - Fork del plugin OpenICGC del ICGC.

**Autores Originales:** ICGC (Institut Cartogràfic i Geològic de Catalunya)  
**Mantenedor del Fork:** Goalnefesh

Este proyecto mantiene la misma licencia GPL-2.0 que el proyecto original.
