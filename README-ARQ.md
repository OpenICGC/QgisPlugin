# Arquitectura de GeoFinder ICGC

> **Documentación técnica del funcionamiento interno del proyecto GeoFinder**  
> Última actualización: 2025-12-11

---

## 📋 Tabla de Contenidos

- [Visión General](#-visión-general)
- [Arquitectura en Capas](#-arquitectura-en-capas)
- [Componentes Principales](#-componentes-principales)
- [Flujo de Datos](#-flujo-de-datos)
- [Mapeo de Herramientas](#-mapeo-de-herramientas)
- [Endpoints del ICGC](#-endpoints-del-icgc)
- [Ejemplos de Flujo Completo](#-ejemplos-de-flujo-completo)

---

## 🎯 Visión General

GeoFinder es un **geocodificador para Cataluña** que utiliza los servicios del ICGC (Institut Cartogràfic i Geològic de Catalunya). El proyecto está estructurado en **3 capas principales**:

1. **Capa de Presentación** - Servidor MCP y API pública
2. **Capa de Lógica de Negocio** - GeoFinder (parsing, detección, transformaciones)
3. **Capa de Comunicación** - PeliasClient (HTTP, reintentos, errores)

---

## 🏗️ Arquitectura en Capas

```
┌───────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN                    │
│  ┌──────────────────────┐  ┌──────────────────────────┐   │
│  │   Servidor MCP       │  │   API Pública Python     │   │
│  │  (mcp_server.py)     │  │   (geofinder.py)         │   │
│  │                      │  │                          │   │
│  │  - find_place()      │  │  - find()                │   │
│  │  - autocomplete()    │  │  - find_reverse()        │   │
│  │  - find_reverse()    │  │  - autocomplete()        │   │
│  │  - find_address()    │  │                          │   │
│  │  - find_road_km()    │  │                          │   │
│  │  - search_nearby()   │  │                          │   │
│  │  - etc...            │  │                          │   │
│  └──────────┬───────────┘  └───────┬──────────────────┘   │
└─────────────┼──────────────────────┼──────────────────────┘
              │                      │
              └──────────┬───────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│                 CAPA DE LÓGICA DE NEGOCIO                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              GeoFinder (geofinder.py)                │  │
│  │                                                      │  │
│  │  Métodos Públicos:                                   │  │
│  │  - find(text, epsg)                                  │  │
│  │  - find_reverse(x, y, epsg, layers, size)            │  │
│  │  - autocomplete(text, size)                          │  │
│  │                                                      │  │
│  │  Métodos Internos:                                   │  │
│  │  - _find_data()           → Detecta tipo búsqueda    │  │
│  │  - _parse_point()         → Parsea coordenadas       │  │
│  │  - _parse_rectangle()     → Parsea rectángulos       │  │
│  │  - _parse_road()          → Parsea carreteras        │  │
│  │  - _parse_address()       → Parsea direcciones       │  │
│  │  - _find_placename()      → Busca topónimos          │  │
│  │  - _find_address()        → Busca direcciones        │  │
│  │  - _find_road()           → Busca carreteras         │  │
│  │  - _find_point_coordinate_icgc() → Busca por coords  │  │
│  │  - _parse_icgc_response() → Parsea respuestas        │  │
│  └──────────────────────┬───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│                 CAPA DE COMUNICACIÓN HTTP                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            PeliasClient (pelias.py)                  │  │
│  │                                                      │  │
│  │  Métodos Principales:                                │  │
│  │  - geocode(query, **params)    → Búsqueda general    │  │
│  │  - reverse(lat, lon, **params) → Geocod. inversa     │  │
│  │  - autocomplete(query, **params) → Autocompletado    │  │
│  │                                                      │  │
│  │  Método Interno:                                     │  │
│  │  - call(endpoint, **params)    → Ejecuta HTTP GET    │  │
│  │                                                      │  │
│  │  Características:                                    │  │
│  │  ✓ Reintentos automáticos (3 intentos)               │  │
│  │  ✓ Backoff exponencial (0.3s, 0.6s, 1.2s)            │  │
│  │  ✓ Manejo de errores HTTP (429, 500, 502, 503, 504)  │  │
│  │  ✓ Gestión de timeouts                               │  │
│  │  ✓ Reutilización de conexiones (Session)             │  │
│  └──────────────────────┬───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   Servidor ICGC       │
              │   Pelias API          │
              │                       │
              │  /cerca               │
              │  /invers              │
              │  /autocompletar       │
              └───────────────────────┘
```

---

## 🔧 Componentes Principales

### 1. `pelias.py` - Cliente HTTP

**Responsabilidad:** Comunicación con el servidor Pelias del ICGC.

#### Clases:

- **`PeliasClient`** - Cliente principal
- **`PeliasError`** - Excepción base
- **`PeliasConnectionError`** - Error de conexión
- **`PeliasTimeoutError`** - Error de timeout

#### Métodos Públicos:

| Método | Descripción | Endpoint |
|--------|-------------|----------|
| `geocode(query, **params)` | Búsqueda general (texto → coordenadas) | `/cerca` |
| `reverse(lat, lon, **params)` | Geocodificación inversa (coords → lugar) | `/invers` |
| `autocomplete(query, **params)` | Sugerencias de autocompletado | `/autocompletar` |
| `call(endpoint, **params)` | Ejecuta petición HTTP genérica | Variable |
| `last_sent()` | Retorna última URL ejecutada (debug) | - |
| `close()` | Cierra sesión HTTP | - |

#### Características Técnicas:

- **Retry Strategy:** 3 reintentos con backoff exponencial
- **Status Codes Retry:** 429, 500, 502, 503, 504
- **Timeout:** Configurable (default: 5 segundos)
- **Session Management:** Reutiliza conexiones HTTP
- **Context Manager:** Soporte para `with` statement

---

### 2. `geofinder.py` - Lógica de Negocio

**Responsabilidad:** Detección de tipos de búsqueda, parsing, transformaciones y orquestación.

#### Clase Principal: `GeoFinder`

#### Métodos Públicos (API):

| Método | Descripción | Usa PeliasClient |
|--------|-------------|------------------|
| `find(text, epsg)` | Búsqueda inteligente con detección automática | ✅ Sí |
| `find_reverse(x, y, epsg, layers, size)` | Geocodificación inversa | ✅ Sí |
| `autocomplete(text, size)` | Autocompletado | ✅ Sí |

#### Métodos Internos de Parsing:

| Método | Descripción | Formato Detectado |
|--------|-------------|-------------------|
| `_parse_point(text)` | Detecta coordenadas de punto | `"X Y"`, `"X Y EPSG:código"` |
| `_parse_rectangle(text)` | Detecta rectángulo | `"X1 Y1 X2 Y2"`, `"X1 Y1 X2 Y2 EPSG:código"` |
| `_parse_road(text)` | Detecta carretera + km | `"C-32 km 10"`, `"AP7 km 150"` |
| `_parse_address(text)` | Detecta dirección | `"Barcelona, Diagonal 100"` |

#### Métodos Internos de Búsqueda:

| Método | Descripción | Llama a PeliasClient |
|--------|-------------|----------------------|
| `_find_placename(text)` | Busca topónimos | `geocode(text)` |
| `_find_address(municipality, street_type, street, number)` | Busca direcciones | `geocode(query, layers="address")` |
| `_find_road(road, km)` | Busca puntos kilométricos | `geocode(f"{road} {km}", layers="pk")` |
| `_find_point_coordinate(x, y, epsg)` | Busca en coordenadas | `reverse()` + lógica combinada |
| `_find_point_coordinate_icgc(x, y, epsg, layers, radius, size)` | Búsqueda avanzada por coords | `reverse(lat, lon, ...)` |
| `_find_rectangle(west, north, east, south, epsg)` | Busca en rectángulo | Usa `_find_point_coordinate()` |

#### Métodos de Utilidad:

| Método | Descripción |
|--------|-------------|
| `_parse_icgc_response(res_dict)` | Convierte respuesta ICGC a formato estándar |
| `is_rectangle(results)` | Verifica si resultado es rectángulo |
| `get_rectangle(results)` | Extrae coordenadas de rectángulo |
| `get_point(results, index)` | Extrae coordenadas de punto |
| `get_name(results, index)` | Extrae nombre de resultado |

---

### 3. `mcp_server.py` - Servidor MCP

**Responsabilidad:** Exponer funcionalidades de GeoFinder como herramientas MCP para asistentes de IA.

#### Herramientas MCP Disponibles:

| Herramienta | Descripción | Usa GeoFinder |
|-------------|-------------|---------------|
| `find_place(query, epsg)` | Búsqueda general inteligente | `gf.find()` |
| `autocomplete(text, max)` | Sugerencias de autocompletado | `gf.autocomplete()` |
| `find_reverse(lon, lat, epsg, layers, max)` | Geocodificación inversa | `gf.find_reverse()` |
| `find_by_coordinates(x, y, epsg, radius, layers, max)` | Búsqueda avanzada por coords | `gf._find_point_coordinate_icgc()` |
| `find_address(street, number, municipality, type)` | Búsqueda estructurada de direcciones | `gf._find_address()` |
| `find_road_km(road, km)` | Búsqueda de punto kilométrico | `gf._find_road()` |
| `search_nearby(place, radius, layers, max)` | Búsqueda cerca de un lugar | `gf.find()` + `gf._find_point_coordinate_icgc()` |
| `transform_coordinates(x, y, from_epsg, to_epsg)` | Transformación de coordenadas | `transform_point()` (NO usa Pelias) |
| `parse_search_query(query)` | Analiza tipo de búsqueda | Métodos `_parse_*()` (NO usa Pelias) |

---

### 4. `transformations.py` - Transformación de Coordenadas

**Responsabilidad:** Conversión entre sistemas de referencia (EPSG).

#### Función Principal:

```python
transform_point(x, y, from_epsg, to_epsg) -> (dest_x, dest_y)
```

**Backends soportados:**
- `pyproj` (preferido)
- `GDAL/OGR` (alternativo)

**Uso:** Convierte coordenadas entre sistemas EPSG (ej: UTM 31N ↔ WGS84).

---

## 🔄 Flujo de Datos

### Flujo Típico de una Búsqueda:

```
Usuario/IA
    ↓
[Herramienta MCP] find_place("Barcelona, Diagonal 100")
    ↓
[GeoFinder] find("Barcelona, Diagonal 100", epsg=25831)
    ↓
[GeoFinder] _find_data() → Detecta tipo: DIRECCIÓN
    ↓
[GeoFinder] _parse_address() → Extrae: municipality="Barcelona", street="Diagonal", number="100"
    ↓
[GeoFinder] _find_address() → Construye query: "Carrer Diagonal 100, Barcelona"
    ↓
[PeliasClient] geocode("Carrer Diagonal 100, Barcelona", layers="address")
    ↓
[PeliasClient] call("/cerca", text="...", layers="address")
    ↓
[HTTP GET] https://eines.icgc.cat/geocodificador/cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address
    ↓
[Servidor ICGC] Responde con GeoJSON
    ↓
[PeliasClient] Parsea JSON y retorna dict
    ↓
[GeoFinder] _parse_icgc_response() → Normaliza formato
    ↓
[Herramienta MCP] Retorna resultados al usuario/IA
```

---

## 📊 Mapeo de Herramientas

### Tabla Completa de Flujo de Llamadas:

| Herramienta MCP | Método GeoFinder | Método PeliasClient | Endpoint ICGC | Parámetros Clave |
|-----------------|------------------|---------------------|---------------|------------------|
| `find_place()` | `find()` | `geocode()` | `/cerca` | `text`, `layers` |
| `autocomplete()` | `autocomplete()` | `autocomplete()` | `/autocompletar` | `text`, `size` |
| `find_reverse()` | `find_reverse()` | `reverse()` | `/invers` | `lat`, `lon`, `layers`, `size` |
| `find_by_coordinates()` | `_find_point_coordinate_icgc()` | `reverse()` | `/invers` | `lat`, `lon`, `boundary.circle.radius` |
| `find_address()` | `_find_address()` | `geocode()` | `/cerca` | `text="Carrer..."`, `layers="address"` |
| `find_road_km()` | `_find_road()` | `geocode()` | `/cerca` | `text="C-32 10"`, `layers="pk"` |
| `search_nearby()` | `find()` + `_find_point_coordinate_icgc()` | `geocode()` + `reverse()` | `/cerca` + `/invers` | Combinado |
| `transform_coordinates()` | `transform_point()` | ❌ NO USA | - | Solo transformación local |
| `parse_search_query()` | `_parse_*()` | ❌ NO USA | - | Solo parsing con regex |

---

## 🌐 Endpoints del ICGC

El servidor Pelias del ICGC expone **3 endpoints principales**:

### 1. `/cerca` - Búsqueda General (Geocodificación)

**Método PeliasClient:** `geocode(query, **params)`

**Parámetros comunes:**
- `text` - Texto de búsqueda
- `layers` - Capas a buscar: `address`, `tops`, `pk`
- `size` - Número de resultados

**Ejemplos de uso:**
```python
# Topónimo
client.geocode("Barcelona")
# → GET /cerca?text=Barcelona

# Dirección
client.geocode("Carrer Diagonal 100, Barcelona", layers="address")
# → GET /cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address

# Carretera
client.geocode("C-32 10", layers="pk")
# → GET /cerca?text=C-32+10&layers=pk
```

---

### 2. `/invers` - Geocodificación Inversa

**Método PeliasClient:** `reverse(lat, lon, **params)`

**Parámetros comunes:**
- `lat` - Latitud (WGS84)
- `lon` - Longitud (WGS84)
- `layers` - Capas a buscar
- `size` - Número de resultados
- `boundary.circle.radius` - Radio de búsqueda en km

**Ejemplos de uso:**
```python
# Básico
client.reverse(41.3851, 2.1734)
# → GET /invers?lat=41.3851&lon=2.1734

# Con radio y capas
client.reverse(41.3851, 2.1734, layers="address,tops", size=10, **{"boundary.circle.radius": 0.05})
# → GET /invers?lat=41.3851&lon=2.1734&layers=address,tops&size=10&boundary.circle.radius=0.05
```

---

### 3. `/autocompletar` - Autocompletado

**Método PeliasClient:** `autocomplete(query, **params)`

**Parámetros comunes:**
- `text` - Texto parcial
- `size` - Número de sugerencias

**Ejemplos de uso:**
```python
# Autocompletado básico
client.autocomplete("Barcel", size=10)
# → GET /autocompletar?text=Barcel&size=10
```

---

## 💡 Ejemplos de Flujo Completo

### Ejemplo 1: Búsqueda de Dirección

```python
# Usuario ejecuta
find_address("Diagonal", "100", "Barcelona")

# Flujo interno:
# 1. mcp_server.py línea 381
gf._find_address("Barcelona", "Carrer", "Diagonal", "100")

# 2. geofinder.py línea 380-382
query = "Carrer Diagonal 100, Barcelona"

# 3. geofinder.py línea 385
res_dict = self.icgc_client.geocode(query, layers="address")

# 4. pelias.py línea 95-97
params_dict = {"text": "Carrer Diagonal 100, Barcelona", "layers": "address"}
return self.call(self.search_call, **params_dict)

# 5. pelias.py línea 153-157
url = "https://eines.icgc.cat/geocodificador/cerca"
response = self.session.get(url, params=params, timeout=5)

# 6. HTTP Request
GET https://eines.icgc.cat/geocodificador/cerca?text=Carrer+Diagonal+100,+Barcelona&layers=address

# 7. Respuesta ICGC (GeoJSON)
{
  "features": [
    {
      "properties": {
        "etiqueta": "Avinguda Diagonal 100, Barcelona",
        "municipi": "Barcelona",
        "comarca": "Barcelonès",
        ...
      },
      "geometry": {
        "coordinates": [2.1734, 41.3851]
      }
    }
  ]
}

# 8. geofinder.py línea 408-445
# Parsea respuesta y normaliza formato

# 9. Resultado final
[
  {
    "nom": "Avinguda Diagonal 100, Barcelona",
    "nomTipus": "Adreça",
    "nomMunicipi": "Barcelona",
    "nomComarca": "Barcelonès",
    "x": 2.1734,
    "y": 41.3851,
    "epsg": 4326
  }
]
```

---

### Ejemplo 2: Búsqueda de Coordenadas

```python
# Usuario ejecuta
find_by_coordinates(430000, 4580000, epsg=25831, search_radius_km=0.05)

# Flujo interno:
# 1. mcp_server.py línea 325
gf._find_point_coordinate_icgc(430000, 4580000, 25831, layers="address,tops,pk", search_radius_km=0.05, size=5)

# 2. geofinder.py línea 344
# Transforma UTM 31N → WGS84
query_x, query_y = transform_point(430000, 4580000, 25831, 4326)
# Resultado: (2.1734, 41.3851)

# 3. geofinder.py línea 355-356
extra_params = {"boundary.circle.radius": 0.05}
res_dict = self.icgc_client.reverse(41.3851, 2.1734, layers="address,tops,pk", size=5, **extra_params)

# 4. pelias.py línea 130-132
params_dict = {"lon": 2.1734, "lat": 41.3851, "layers": "address,tops,pk", "size": 5, "boundary.circle.radius": 0.05}
return self.call(self.reverse_call, **params_dict)

# 5. HTTP Request
GET https://eines.icgc.cat/geocodificador/invers?lat=41.3851&lon=2.1734&layers=address,tops,pk&size=5&boundary.circle.radius=0.05

# 6. Respuesta parseada y retornada
```

---

### Ejemplo 3: Búsqueda Inteligente (Detección Automática)

```python
# Usuario ejecuta
find_place("C-32 km 10")

# Flujo interno:
# 1. geofinder.py línea 120
results = self._find_data("C-32 km 10", default_epsg=25831)

# 2. geofinder.py línea 174-176
# Intenta detectar tipo
road, km = self._parse_road("C-32 km 10")
# Resultado: road="C-32", km="10"

# 3. geofinder.py línea 176
return self._find_road("C-32", "10")

# 4. geofinder.py línea 369
res_dict = self.icgc_client.geocode("C-32 10", layers="pk")

# 5. HTTP Request
GET https://eines.icgc.cat/geocodificador/cerca?text=C-32+10&layers=pk

# 6. Resultado retornado con tipo "Punt quilomètric"
```

---

## 🔑 Puntos Clave

### ✅ Separación de Responsabilidades

- **`pelias.py`** → Solo HTTP, reintentos, errores
- **`geofinder.py`** → Lógica de negocio, parsing, detección
- **`mcp_server.py`** → Exposición de funcionalidades como herramientas MCP
- **`transformations.py`** → Conversión de coordenadas

### ✅ Solo 3 Endpoints Reales

Aunque hay 9 herramientas MCP, todas usan solo:
- `/cerca` (búsqueda general)
- `/invers` (geocodificación inversa)
- `/autocompletar` (sugerencias)

### ✅ Inteligencia en la Capa de Negocio

`GeoFinder` añade:
- Detección automática de tipos de búsqueda
- Parsing de formatos complejos (coordenadas, direcciones, carreteras)
- Transformación de coordenadas entre sistemas EPSG
- Combinación de múltiples consultas
- Normalización de respuestas

### ✅ Robustez en la Capa de Comunicación

`PeliasClient` proporciona:
- Reintentos automáticos ante fallos temporales
- Manejo elegante de errores HTTP
- Reutilización de conexiones
- Timeouts configurables
- Debug con `last_sent()`

---

## 📚 Referencias

- **Código fuente:**
  - [`geofinder/pelias.py`](geofinder/pelias.py) - Cliente HTTP
  - [`geofinder/geofinder.py`](geofinder/geofinder.py) - Lógica de negocio
  - [`geofinder/mcp_server.py`](geofinder/mcp_server.py) - Servidor MCP
  - [`geofinder/transformations.py`](geofinder/transformations.py) - Transformaciones

- **Documentación:**
  - [`README.md`](README.md) - Guía de usuario
  - [`README-MCP.md`](README-MCP.md) - Servidor MCP
  - [`README-DEV.md`](README-DEV.md) - Desarrollo

- **Servicios externos:**
  - [ICGC Geocodificador](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
  - [Pelias Documentation](https://github.com/pelias/documentation)

---

**Autor:** Documentación generada para el proyecto GeoFinder ICGC  
**Licencia:** MIT
