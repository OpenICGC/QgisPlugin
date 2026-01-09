# Glosario de Términos GIS

Este documento proporciona definiciones claras de los términos y conceptos GIS (Geographic Information Systems) utilizados en GeoFinder. Está diseñado para reducir la curva de aprendizaje para usuarios que no están familiarizados con sistemas de información geográfica.

---

## Sistemas de Referencia de Coordenadas

### EPSG
**European Petroleum Survey Group** - Organización que creó y mantiene un registro de códigos numéricos para sistemas de referencia de coordenadas.

Cada código EPSG identifica de manera única un sistema de coordenadas específico. Por ejemplo:
- `EPSG:4326` para WGS84
- `EPSG:25831` para ETRS89 UTM 31N

**Uso en GeoFinder:**
```python
# Las coordenadas se pueden especificar con códigos EPSG
finder.find_by_coordinates(lat=41.9876, lon=2.8260, epsg=4326)
```

---

### WGS84 (EPSG:4326)
**World Geodetic System 1984** - Sistema de coordenadas geográficas global estándar utilizado por GPS.

**Características:**
- Usa **latitud** y **longitud** en grados decimales
- Latitud: `-90°` a `+90°` (Sur a Norte)
- Longitud: `-180°` a `+180°` (Oeste a Este)
- Es el sistema más común en aplicaciones web y móviles

**Ejemplo:**
```python
# Coordenadas de Barcelona en WGS84
lat = 41.3851  # Latitud (grados decimales)
lon = 2.1734   # Longitud (grados decimales)

result = finder.find_reverse(lat=lat, lon=lon)
```

**¿Cuándo usar WGS84?**
- Datos de GPS
- APIs web (Google Maps, OpenStreetMap)
- Aplicaciones móviles
- Cuando trabajas con coordenadas globales

---

### ETRS89 UTM 31N (EPSG:25831)
**European Terrestrial Reference System 1989 - Universal Transverse Mercator Zone 31 North**

**Características:**
- Sistema oficial de coordenadas en **Cataluña** y España
- Usa **metros** en lugar de grados
- Coordenada X (Este): ~200,000 a ~900,000 metros
- Coordenada Y (Norte): ~4,000,000 a ~5,000,000 metros
- Más preciso para mediciones locales y cálculos de distancia

**Ejemplo:**
```python
# Coordenadas de Barcelona en ETRS89 UTM 31N
x = 431394  # Este (metros)
y = 4582357 # Norte (metros)

result = finder.find_by_coordinates(lat=y, lon=x, epsg=25831)
```

**¿Cuándo usar ETRS89 UTM 31N?**
- Proyectos en Cataluña o España
- Cartografía oficial española
- Cálculos precisos de distancia y área
- Datos del Institut Cartogràfic i Geològic de Catalunya (ICGC)

---

## Operaciones de Geocodificación

### Geocodificación
**Texto → Coordenadas**

Proceso de convertir una dirección o nombre de lugar en coordenadas geográficas (latitud, longitud).

**Ejemplo:**
```python
# De texto a coordenadas
result = finder.find_address(
    street="Carrer de Balmes",
    number="1",
    city="Barcelona"
)

# Resultado: lat=41.3851, lon=2.1734
print(f"Coordenadas: {result.lat}, {result.lon}")
```

**Casos de uso:**
- Localizar direcciones en un mapa
- Calcular rutas entre direcciones
- Obtener coordenadas para almacenar en base de datos
- Validar direcciones ingresadas por usuarios

---

### Geocodificación Inversa
**Coordenadas → Texto**

Proceso inverso: convertir coordenadas geográficas en una dirección o descripción de lugar.

**Ejemplo:**
```python
# De coordenadas a dirección
result = finder.find_reverse(
    lat=41.3851,
    lon=2.1734
)

# Resultado: "Carrer de Balmes, 1, Barcelona"
print(f"Dirección: {result.label}")
```

**Casos de uso:**
- Mostrar dirección de la ubicación del usuario
- Etiquetar fotos con ubicación
- Convertir puntos GPS en direcciones legibles
- Análisis de datos geoespaciales

---

## Términos Adicionales

### Bbox (Bounding Box)
Rectángulo definido por coordenadas que limita el área de búsqueda.

**Formato:** `[lon_min, lat_min, lon_max, lat_max]`

**Ejemplo:**
```python
# Buscar solo dentro de Barcelona
bbox = [2.0522, 41.3201, 2.2280, 41.4694]
result = finder.find_place(text="hospital", bbox=bbox)
```

---

### Punto Focal (Focus Point)
Coordenadas que priorizan resultados cercanos a ese punto.

**Ejemplo:**
```python
# Buscar "cafetería" cerca de mi ubicación
result = finder.find_place(
    text="cafetería",
    focus_lat=41.3851,
    focus_lon=2.1734
)
```

---

### Autocompletado
Sugerencias de lugares mientras el usuario escribe.

**Ejemplo:**
```python
# Sugerencias mientras escribes "barcel..."
suggestions = finder.autocomplete(text="barcel")
# → ["Barcelona", "Barcelona, Carrer de Barcelona", ...]
```

---

## Conversión entre Sistemas

### De WGS84 a ETRS89 UTM 31N

GeoFinder maneja la conversión automáticamente cuando especificas el código EPSG:

```python
# Entrada en WGS84
result = finder.find_reverse(lat=41.3851, lon=2.1734, epsg=4326)

# El sistema convierte internamente según sea necesario
```

### De ETRS89 UTM 31N a WGS84

```python
# Entrada en ETRS89 UTM 31N (metros)
result = finder.find_by_coordinates(lat=4582357, lon=431394, epsg=25831)

# Los resultados se devuelven en el sistema original
```

---

## Preguntas Frecuentes

### ¿Qué sistema de coordenadas debo usar?

| Situación | Sistema Recomendado |
|-----------|-------------------|
| App móvil con GPS | WGS84 (EPSG:4326) |
| Proyecto en Cataluña | ETRS89 UTM 31N (EPSG:25831) |
| Mapa web global | WGS84 (EPSG:4326) |
| Datos oficiales españoles | ETRS89 UTM 31N (EPSG:25831) |
| Cálculos de distancia precisos | ETRS89 UTM 31N (EPSG:25831) |

### ¿Cómo sé en qué sistema están mis coordenadas?

- **Valores entre -180 y 180:** Probablemente WGS84 (grados)
- **Valores en cientos de miles:** Probablemente ETRS89 UTM (metros)

### ¿GeoFinder convierte entre sistemas automáticamente?

Sí, GeoFinder acepta coordenadas en diferentes sistemas EPSG y las procesa correctamente. Sin embargo, los resultados se devuelven en el mismo sistema que la entrada.

---

## Recursos Adicionales

- [EPSG.io](https://epsg.io/) - Explorador de códigos EPSG
- [Documentación Oficial ICGC](https://www.icgc.cat/) - Instituto Cartográfico de Cataluña
- [Pelias Geocoder](https://pelias.io/) - Motor de geocodificación usado por GeoFinder

---

## Ejemplos Prácticos

### Buscar un lugar por nombre
```python
from geofinder import GeoFinder

finder = GeoFinder()

# Geocodificación: texto → coordenadas
result = finder.find_place(text="Sagrada Familia, Barcelona")
print(f"Ubicación: {result.lat}, {result.lon}")
```

### Obtener dirección de coordenadas GPS
```python
# Geocodificación inversa: coordenadas → texto
result = finder.find_reverse(lat=41.4036, lon=2.1744)
print(f"Estás en: {result.label}")
```

### Buscar dirección completa
```python
# Búsqueda estructurada de dirección
result = finder.find_address(
    street="Passeig de Gràcia",
    number="92",
    city="Barcelona",
    postcode="08008"
)
print(f"Coordenadas: {result.lat}, {result.lon}")
print(f"Dirección completa: {result.label}")
```

---

**¿Tienes dudas?** Consulta el [README.md](README.md) principal o el [COOKBOOK.md](COOKBOOK.md) para más ejemplos de uso.
