# <img src="assets/pics/geofinder-logo 192x192.jpg" alt="GeoFinder Logo" width="50" height="50"> GeoFinder-ICGC

> **Geocoder for Catalonia** using the ICGC service (Institut Cartogràfic i Geològic de Catalunya).
> 🔄 Dual API: Native async + sync wrappers for simple scripts.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL--2.0-yellow.svg)](LICENSE)

---

**GeoFinder-ICGC** is an advanced geocoder for Catalonia designed to be robust, fast, and easy to use.

## 🚀 Installation


```bash
# Basic installation
pip install geofinder-icgc

# With coordinate transformation support (recommended)
pip install geofinder-icgc[pyproj]

# With MCP server support (AI integration)
pip install geofinder-icgc[mcp]
```

## 📖 Quick Start

### Synchronous Usage (Simple scripts)
```python
from geofinder import GeoFinder

gf = GeoFinder()
results = gf.find_sync("Barcelona")

for r in results:
    print(f"{r.nom} ({r.nomTipus}) - {r.x}, {r.y}")
```

### Asynchronous Usage (High performance)
```python
import asyncio
from geofinder import GeoFinder

async def main():
    async with GeoFinder() as gf:
        results = await gf.find("Diagonal 100, Barcelona")
        print(f"Found: {len(results)}")

asyncio.run(main())
```

## 🔍 Features Guide

### 1. General Search (`find` / `find_sync`)
Automatically detects the search type based on input:
- **Toponyms:** `"Montserrat"`, `"Girona"`
- **Addresses:** `"Carrer Aragó 50, Barcelona"`, `"Gran Via 123"`
- **Coordinates:** `"430000 4580000 EPSG:25831"`, `"2.17 41.38 EPSG:4326"`
- **Roads:** `"C-32 km 10"`
- **Rectangles:** `"X1 Y1 X2 Y2"`

### 2. Reverse Geocoding (`find_reverse` / `find_reverse_sync`)
Find places or addresses from coordinates.
```python
# Supports EPSG:25831 (default) and EPSG:4326 (GPS)
results = await gf.find_reverse(430000, 4580000)
```

### 3. Autocomplete (`autocomplete` / `autocomplete_sync`)
Ideal for implementing real-time search suggestions.
```python
suggestions = await gf.autocomplete("Barcel")
```

### 4. Proximity Search (`search_nearby`)
Find places within a given radius around a reference point.
```python
# Search everything within 2km of Sagrada Família
nearby = await gf.search_nearby("Sagrada Família, Barcelona", radius_km=2.0)
```

### 5. Batch Processing (`find_batch` / `find_reverse_batch`)
Execute multiple queries in parallel with optimized concurrency.
```python
queries = ["Barcelona", "Girona", "Lleida", "Tarragona"]
batch_results = await gf.find_batch(queries, max_concurrency=10)
```

### 6. Response with Metadata (`find_response`)
Returns a `GeoResponse` object that includes results and performance metadata such as execution time.

## ⚙️ Configuration

The `GeoFinder` constructor allows customizing the library behavior:

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| `timeout` | `int` | Maximum wait time (default: 5s). |
| `cache_size` | `int` | LRU cache capacity (default: 128). |
| `cache_ttl` | `int` | Cache time-to-live in seconds (default: 3600). |
| `max_retries` | `int` | Number of retries on failure (default: 3). |
| `verify_ssl` | `bool` | Verify SSL certificates (default: True). |


---

## 📚 Documentation

- [COOKBOOK.md](COOKBOOK.md) - Tutorials and practical examples
- [README-DEV.md](README-DEV.md) - Development guide
- [README-MCP.md](README-MCP.md) - MCP Server
- [README-ARQ.md](README-ARQ.md) - Technical architecture

---

## 📚 Resources

- [ICGC Documentation](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [GitHub Repository](https://github.com/jccamel/geofinder-icgc)
- [Issues](https://github.com/jccamel/geofinder-icgc/issues)
- [Model Context Protocol](https://modelcontextprotocol.io) (for MCP)

---


## ⚖️ License

Distributed under the **GPL-2.0-or-later** license. Based on the original ICGC work adapted for standalone use.

---
© 2025 ICGC / Adapted by Goalnefesh

Small changes are powerful 🤘 
