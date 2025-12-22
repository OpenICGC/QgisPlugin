# <img src="pics/geofinder-logo 192x192.jpg" alt="GeoFinder Logo" width="50" height="50"> GeoFinder-ICGC

> **Geocodificador para Cataluña** usando el servicio del ICGC (Institut Cartogràfic i Geològic de Catalunya).
> 🔄 API dual: Async nativo + wrappers sync para scripts simples.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL--2.0-yellow.svg)](LICENSE)

---

**GeoFinder-ICGC** es un geocodificador avanzado para Cataluña diseñado para ser robusto, rápido y fácil de usar.

## 🚀 Instalación


```bash
# Instalación básica
pip install geofinder-icgc

# Con soporte para transformación de coordenadas (recomendado)
pip install geofinder-icgc[pyproj]

# Con soporte para servidor MCP (integración con IA)
pip install geofinder-icgc[mcp]
```

## 📖 Inicio Rápido

### Uso Síncrono (Scripts sencillos)
```python
from geofinder import GeoFinder

gf = GeoFinder()
results = gf.find_sync("Barcelona")

for r in results:
    print(f"{r.nom} ({r.nomTipus}) - {r.x}, {r.y}")
```

### Uso Asíncrono (Alto rendimiento)
```python
import asyncio
from geofinder import GeoFinder

async def main():
    async with GeoFinder() as gf:
        results = await gf.find("Diagonal 100, Barcelona")
        print(f"Encontrados: {len(results)}")

asyncio.run(main())
```

## 🔍 Manual de Funcionalidades

### 1. Búsqueda General (`find` / `find_sync`)
Detecta automáticamente el tipo de búsqueda según la entrada:
- **Topónimos:** `"Montserrat"`, `"Girona"`
- **Direcciones:** `"Carrer Aragó 50, Barcelona"`, `"Gran Via 123"`
- **Coordenadas:** `"430000 4580000 EPSG:25831"`, `"2.17 41.38 EPSG:4326"`
- **Carreteras:** `"C-32 km 10"`
- **Rectángulos:** `"X1 Y1 X2 Y2"`

### 2. Geocodificación Inversa (`find_reverse` / `find_reverse_sync`)
Encuentra lugares o direcciones a partir de coordenadas.
```python
# Soporta EPSG:25831 (por defecto) y EPSG:4326 (GPS)
results = await gf.find_reverse(430000, 4580000)
```

### 3. Autocompletado (`autocomplete` / `autocomplete_sync`)
Ideal para implementar buscadores en tiempo real.
```python
suggestions = await gf.autocomplete("Barcel")
```

### 4. Búsqueda de Proximidad (`search_nearby`)
Encuentra lugares en un radio determinado alrededor de un punto de referencia.
```python
# Busca todo en un radio de 2km de la Sagrada Família
nearby = await gf.search_nearby("Sagrada Família, Barcelona", radius_km=2.0)
```

### 5. Procesamiento por Lotes (`find_batch` / `find_reverse_batch`)
Ejecuta múltiples consultas en paralelo optimizando la concurrencia.
```python
queries = ["Barcelona", "Girona", "Lleida", "Tarragona"]
batch_results = await gf.find_batch(queries, max_concurrency=10)
```

### 6. Obtención de Respuestas con Metadatos (`find_response`)
Devuelve un objeto `GeoResponse` que incluye los resultados y metadatos de rendimiento como el tiempo de ejecución.

## ⚙️ Configuración

El constructor de `GeoFinder` permite ajustar el comportamiento de la librería:

| Parámetro | Tipo | Descripción |
| --------- | ---- | ----------- |
| `timeout` | `int` | Tiempo máximo de espera (defecto: 5s). |
| `cache_size` | `int` | Capacidad de la caché LRU (defecto: 128). |
| `cache_ttl` | `int` | Tiempo de vida de la caché en segundos (defecto: 3600). |
| `max_retries` | `int` | Número de reintentos en caso de fallo (defecto: 3). |
| `verify_ssl` | `bool` | Verificar certificados SSL (defecto: True). |


---

## 📚 Documentación

- [COOKBOOK.md](COOKBOOK.md) - Tutoriales y ejemplos prácticos
- [README-DEV.md](README-DEV.md) - Guía de desarrollo
- [README-MCP.md](README-MCP.md) - Servidor MCP
- [README-ARQ.md](README-ARQ.md) - Arquitectura técnica

---

## 📚 Recursos

- [Documentación ICGC](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Repositorio GitHub](https://github.com/jccamel/geofinder-icgc)
- [Issues](https://github.com/jccamel/geofinder-icgc/issues)
- [Model Context Protocol](https://modelcontextprotocol.io) (para MCP)

---


## ⚖️ Licencia

Distribuido bajo la licencia **GPL-2.0-or-later**. Basado en el trabajo original del ICGC adaptado para uso standalone.

---
© 2025 ICGC / Adaptado por Goalnefesh

Els petits canvis son poderosos 🤘 
