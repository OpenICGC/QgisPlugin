# 📚 GeoFinder Cookbook

> **Practical guide with integration examples** for the Catalonia geocoder.

---

## 📋 Table of Contents

| Section                                                     | Description                |
| ----------------------------------------------------------- | -------------------------- |
| [🚀 Basic Examples](#-basic-examples)                       | Getting started and common usage |
| [🌐 Web Integration](#-web-integration)                     | FastAPI (Recommended)      |
| [📊 Data Analysis](#-data-analysis)                         | Pandas, GeoPandas          |
| [⚡ Batch Geocoding](#-batch-geocoding)                      | Bulk processing            |
| [🛡️ Error Handling](#️-error-handling)                      | Robust patterns            |
| [💾 Caching and Performance](#-caching-and-performance)     | Optimization               |
| [🏢 Real-World Use Cases](#-real-world-use-cases)           | Practical applications     |

---

## 🚀 Basic Examples

### Installation

```bash
# Basic installation
pip install -e .

# With coordinate transformation
pip install -e ".[pyproj]"

# With MCP server for AI
pip install -e ".[mcp,pyproj]"
```

### Simple Search (Async)

```python
import asyncio
from geofinder import GeoFinder

async def main():
    # Initialize with context manager
    async with GeoFinder() as gf:
        # Search for a municipality
        results = await gf.find("Barcelona")
        for r in results:
            print(f"{r.nom} ({r.nomTipus}) - {r.x}, {r.y}")
            # Dict-style access also works for compatibility:
            # print(r['nom'])

if __name__ == "__main__":
    asyncio.run(main())
# Output: Barcelona (Cap de municipi) - 2.177, 41.382
```

### Synchronous Search (Scripts)

```python
from geofinder import GeoFinder

gf = GeoFinder()
results = gf.find_sync("Montserrat")
for r in results:
    print(r.nom)
```

### Search with Different Formats

```python
from geofinder import GeoFinder

gf = GeoFinder()

# Disable SSL verification for servers with self-signed certificates
gf = GeoFinder(verify_ssl=False)

# 1. Toponym
results = gf.find("Montserrat")

# 2. Municipality + Street + Number
results = gf.find("Barcelona, Diagonal 100")

# 3. UTM Coordinates
results = gf.find("430000 4580000 EPSG:25831")

# 4. Road kilometer point
results = gf.find("C-32 km 10")

# 5. GPS Coordinates
results = gf.find("2.1734 41.3851 EPSG:4326")
```

### Reverse Geocoding

```python
async with GeoFinder() as gf:
    # From GPS coordinates → place information
    results = await gf.find_reverse(2.1734, 41.3851, epsg=4326)

    for r in results:
        print(f"📍 {r.nom}")
        print(f"   Municipality: {r.nomMunicipi}")
        print(f"   County: {r.nomComarca}")
        # Extra metadata now available
        print(f"   Municipality ID: {r.idMunicipi}")
```

### Autocomplete

```python
async with GeoFinder() as gf:
    # Suggestions as the user types
    suggestions = await gf.autocomplete("Barcel", size=5)

    for s in suggestions:
        print(f"💡 {s.nom} - {s.nomTipus}")
```

---

## 🌐 Web Integration

### FastAPI - Shared Connection Pool (Recommended)

**Why share the connection pool?**

When you have a web application with multiple endpoints using GeoFinder, creating a new HTTP client for each request is inefficient:

- ❌ **Without sharing**: Each request creates/closes connections → network overhead
- ✅ **With shared pool**: Reuses connections → lower latency, better performance

#### Complete Example with Shared Pool

```python
"""
FastAPI API with shared connection pool.
Run: uvicorn app:app --reload
"""
from fastapi import FastAPI, Query, HTTPException, Depends
from contextlib import asynccontextmanager
import httpx
from geofinder import GeoFinder
from geofinder.models import GeoResponse, GeoResult

# ============================================================================
# 1. CONNECTION POOL CONFIGURATION
# ============================================================================

# Shared HTTP client with optimized configuration
shared_http_client: httpx.AsyncClient | None = None

def get_shared_client() -> httpx.AsyncClient:
    """Gets the shared HTTP client."""
    if shared_http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return shared_http_client


# ============================================================================
# 2. APPLICATION LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application lifecycle."""
    global shared_http_client
    
    # STARTUP: Create shared client
    print("🚀 Starting connection pool...")
    shared_http_client = httpx.AsyncClient(
        timeout=10.0,
        limits=httpx.Limits(
            max_connections=100,        # Maximum total connections
            max_keepalive_connections=20  # Keep-alive connections
        ),
        follow_redirects=True
    )
    print(f"✅ Pool created: {shared_http_client.limits}")
    
    yield  # The application is running
    
    # SHUTDOWN: Close shared client
    print("⏳ Closing connection pool...")
    await shared_http_client.aclose()
    print("✅ Pool closed correctly")


# ============================================================================
# 3. FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="GeoFinder API",
    description="Geocoding API for Catalonia with shared pool",
    version="2.1.0",
    lifespan=lifespan  # ← Important: lifecycle management
)


# ============================================================================
# 4. DEPENDENCY INJECTION
# ============================================================================

def get_geofinder(
    client: httpx.AsyncClient = Depends(get_shared_client)
) -> GeoFinder:
    """
    Creates a GeoFinder instance with the shared client.
    
    IMPORTANT: GeoFinder will NOT close this client because it was injected.
    """
    return GeoFinder(http_client=client)


# ============================================================================
# 5. ENDPOINTS
# ============================================================================

@app.get("/search", response_model=GeoResponse)
async def search(
    q: str = Query(..., description="Text to search"),
    size: int = Query(10, ge=1, le=100, description="Number of results"),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Search for a place by name or address.
    
    Examples:
    - /search?q=Barcelona
    - /search?q=Diagonal 100, Barcelona&size=5
    """
    try:
        return await gf.find_response(q, size=size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reverse", response_model=list[GeoResult])
async def reverse(
    x: float = Query(..., description="X Coordinate / Longitude"),
    y: float = Query(..., description="Y Coordinate / Latitude"),
    epsg: int = Query(4326, description="Coordinate system"),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Reverse geocoding: coordinates → place.
    
    Examples:
    - /reverse?x=2.1734&y=41.3851&epsg=4326
    - /reverse?x=430000&y=4580000&epsg=25831
    """
    try:
        return await gf.find_reverse(x, y, epsg=epsg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2, description="Partial text"),
    size: int = Query(10, ge=1, le=50),
    gf: GeoFinder = Depends(get_geofinder)
):
    """
    Autocomplete suggestions.
    
    Example: /autocomplete?q=Barcel
    """
    try:
        suggestions = await gf.autocomplete(q, size=size)
        return {"suggestions": [s.nom for s in suggestions]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health(client: httpx.AsyncClient = Depends(get_shared_client)):
    """Health endpoint that shows the pool status."""
    return {
        "status": "healthy",
        "pool": {
            "max_connections": client.limits.max_connections,
            "max_keepalive": client.limits.max_keepalive_connections,
            "is_closed": client.is_closed
        }
    }


# ============================================================================
# 6. EXECUTION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### How Does the Shared Pool Work?

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Application                                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Request 1    │  │ Request 2    │  │ Request 3    │  │
│  │ /search      │  │ /reverse     │  │ /autocomplete│  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │          │
│         └──────────────────┼──────────────────┘          │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  Dependency    │                    │
│                    │  get_geofinder │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  GeoFinder     │                    │
│                    │  (http_client) │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│         ┌──────────────────┴──────────────────┐          │
│         │                                     │          │
│  ┌──────▼──────────────────────────────────┐  │          │
│  │  shared_http_client (httpx.AsyncClient) │  │          │
│  │  ┌────────────────────────────────────┐ │  │          │
│  │  │  Connection Pool                   │ │  │          │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐       │ │  │          │
│  │  │  │ Conn │ │ Conn │ │ Conn │  ...  │ │  │          │
│  │  │  └──────┘ └──────┘ └──────┘       │ │  │          │
│  │  │  (Reused between requests)        │ │  │          │
│  │  └────────────────────────────────────┘ │  │          │
│  └──────────────────────────────────────────┘  │          │
│                                                 │          │
└─────────────────────────────────────────────────┘
                         │
                         ▼
              ICGC Pelias Server
```

#### Shared Pool Advantages

| Aspect | Without Pool | With Shared Pool |
|---------|----------|---------------------|
| **Connections** | New per request | Reused |
| **Latency** | ~100-200ms | ~20-50ms |
| **Overhead** | High (TCP handshake) | Low (keep-alive) |
| **Resources** | Many sockets | Controlled |
| **Scalability** | Limited | High |

#### Pool Configuration

```python
# Adjust according to your needs
httpx.AsyncClient(
    timeout=10.0,  # Global timeout
    limits=httpx.Limits(
        max_connections=100,        # Total simultaneous connections
        max_keepalive_connections=20,  # Keep-alive connections
        keepalive_expiry=30.0       # Keep-alive lifetime
    )
)
```

**Recommendations**:
- **Low traffic API**: `max_connections=20`, `max_keepalive=5`
- **Medium traffic API**: `max_connections=50`, `max_keepalive=10`
- **High traffic API**: `max_connections=100`, `max_keepalive=20`

---

### FastAPI - Simple Version (No Shared Pool)

If you don't need extreme optimization, you can use the simple version:

```python
from fastapi import FastAPI, Query
from geofinder import GeoFinder

app = FastAPI()
gf = GeoFinder()  # Own client, managed internally

@app.get("/search")
async def search(q: str = Query(...)):
    return await gf.find_response(q)
```

> [!NOTE]
> This version is simpler but less efficient. Each `GeoFinder` instance has its own HTTP client.

---

## 📊 Data Analysis

### Pandas - Geocode DataFrame

```python
"""
Geocode a DataFrame of addresses.
"""
import pandas as pd
from geofinder import GeoFinder

# Example data
data = {
    'id': [1, 2, 3, 4],
    'address': [
        'Barcelona, Diagonal 100',
        'Girona, Carrer Nou 50',
        'Lleida, Plaça Paeria 1',
        'Tarragona, Rambla Nova 100'
    ]
}
df = pd.DataFrame(data)

# Initialize geocoder
gf = GeoFinder()


async def geocode_address(gf, address: str) -> dict:
    """Geocodes an address and returns coordinates."""
    try:
        results = await gf.find(address)
        if results:
            r = results[0]
            return {
                'lat': r.y,
                'lon': r.x,
                'municipality': r.nomMunicipi,
                'county': r.nomComarca,
                'type': r.nomTipus
            }
    except Exception as e:
        print(f"Error geocoding '{address}': {e}")
    return {'lat': None, 'lon': None, 'municipality': '', 'county': '', 'type': ''}


# Apply geocoding
geo_data = df['address'].apply(geocode_address).apply(pd.Series)
df = pd.concat([df, geo_data], axis=1)

print(df)
#    id                       address       lat       lon  municipality     county       type
# 0   1          Barcelona, Diagonal 100  41.3851    2.1734  Barcelona  Barcelonès     Adreça
# 1   2             Girona, Carrer Nou 50  41.9831    2.8249     Girona    Gironès      Adreça
# ...
```

### GeoPandas - Create GeoDataFrame

```python
"""
Create a GeoDataFrame with geometries for spatial analysis.
"""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from geofinder import GeoFinder

# Data
places = ['Barcelona', 'Girona', 'Lleida', 'Tarragona', 'Reus', 'Figueres']

gf = GeoFinder()

# Geocode
data = []
async with GeoFinder() as gf:
    for place in places:
        results = await gf.find(place)
        if results:
            r = results[0]
            data.append({
                'name': r.nom,
                'type': r.nomTipus,
                'county': r.nomComarca,
                'geometry': Point(r.x, r.y)
            })

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")

# Spatial operations
print(f"Extent: {gdf.total_bounds}")

# Save as GeoJSON
gdf.to_file("municipalities_catalonia.geojson", driver="GeoJSON")

# 10km buffer around Barcelona
barcelona = gdf[gdf['name'] == 'Barcelona'].geometry.iloc[0]
buffer_10km = barcelona.buffer(0.1)  # ~10km in degrees
```

### Visualization with Folium

```python
"""
Create interactive map with geocoded results.
"""
import folium
from geofinder import GeoFinder

gf = GeoFinder()

# Geocode points of interest
places = [
    'Sagrada Família, Barcelona',
    'Park Güell, Barcelona',
    'Montserrat',
    'Costa Brava',
    'Delta de l\'Ebre'
]

# Create map centered on Catalonia
map = folium.Map(location=[41.5, 1.5], zoom_start=8)

for place in places:
    results = gf.find_sync(place)
    if results:
        r = results[0]
        folium.Marker(
            location=[r.y, r.x],  # Folium uses lat, lon
            popup=f"<b>{r.nom}</b><br>{r.nomTipus}",
            tooltip=r.nom,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(map)

# Save map
map.save('map_catalonia.html')
print("Map saved to map_catalonia.html")
```

---

## ⚡ Batch Geocoding

### Using `find_batch` (Recommended)

`find_batch` is the most efficient and simple way to process multiple addresses. It automatically manages concurrency to avoid overwhelming the server.

```python
import asyncio
from geofinder import GeoFinder

async def main():
    async with GeoFinder() as gf:
        addresses = [
            "Barcelona",
            "Girona",
            "Lleida",
            "Tarragona",
            "Montserrat"
        ]
        
        # max_concurrency limits simultaneous requests (default: 5)
        results = await gf.find_batch(addresses, max_concurrency=10)
        
        for query, response in zip(addresses, results):
            if response.results:
                top = response.results[0]
                print(f"✅ {query} -> {top.nom} ({top.x}, {top.y})")
            else:
                print(f"❌ {query} not found")

if __name__ == "__main__":
    asyncio.run(main())
```

### Batch Reverse Geocoding

You can also efficiently process multiple coordinates.

```python
async with GeoFinder() as gf:
    coords = [
        (2.1734, 41.3851),
        (2.8249, 41.9794),
        (0.6231, 41.6176)
    ]
    
    # Process in parallel with controlled concurrency
    results = await gf.find_reverse_batch(coords, epsg=4326, max_concurrency=3)
    
    for c, res_list in zip(coords, results):
        if res_list:
            print(f"📍 {c} -> {res_list[0].nom}")
```

### Synchronous Version (Simple Scripts)

If you're not using `async/await`, you can use the `_sync` versions.

```python
from geofinder import GeoFinder

gf = GeoFinder()
addresses = ["Barcelona", "Girona"]

# Blocks until the entire batch is processed
results = gf.find_batch_sync(addresses)

for resp in results:
    if resp.results:
        print(resp.results[0].nom)
```

> [!TIP]
> **Synchronous Session Management**: The `_sync` calls internally manage the client lifecycle. You can make multiple sequential calls on the same `GeoFinder` instance without issues.

---

## 🛡️ Error Handling

### Complete Error Handling Pattern

```python
"""
Example of robust error handling with GeoFinder.
"""
from geofinder import GeoFinder
from geofinder.pelias import (
    PeliasError,
    PeliasConnectionError,
    PeliasTimeoutError
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def geocode_safely(query: str, gf: GeoFinder) -> dict:
    """Geocode safely with Pydantic models."""
    try:
        results = await gf.find(query)

        if not results:
            return {
                'success': False,
                'error': 'NOT_FOUND',
                'message': f"No results found for '{query}'"
            }

        best = results[0]
        return {
            'success': True,
            'data': best,
            'name': best.nom,
            'coords': (best.y, best.x)
        }
    except PeliasTimeoutError:
        return {'success': False, 'error': 'TIMEOUT', 'retry': True}
    except Exception as e:
        return {'success': False, 'error': 'ERROR', 'message': str(e)}
```

### Input Validation

```python
"""
Validate and normalize input before geocoding.
"""
import re
from typing import Optional, Tuple


def validate_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Validates and normalizes an address.

    Returns:
        (is_valid, normalized_address or error_message)
    """
    if not address or not isinstance(address, str):
        return False, "Address cannot be empty"

    # Normalize spaces
    address = ' '.join(address.split())

    # Minimum 3 characters
    if len(address) < 3:
        return False, "Address is too short"

    # Maximum 200 characters
    if len(address) > 200:
        return False, "Address is too long"

    # Detect invalid characters
    if re.search(r'[<>{}|\\^~\[\]]', address):
        return False, "Address contains invalid characters"

    return True, address


def validate_coordinates(
    x: float,
    y: float,
    epsg: int = 4326
) -> Tuple[bool, Optional[str]]:
    """
    Validates coordinates according to the EPSG system.
    """
    if epsg == 4326:  # WGS84
        # Catalonia approx: lon 0.2-3.3, lat 40.5-42.8
        if not (0.0 <= x <= 4.0):
            return False, f"Longitude {x} out of range for Catalonia"
        if not (39.0 <= y <= 43.0):
            return False, f"Latitude {y} out of range for Catalonia"

    elif epsg == 25831:  # UTM 31N
        # Catalonia approx: X 250000-550000, Y 4500000-4750000
        if not (200000 <= x <= 600000):
            return False, f"X coordinate {x} out of range for UTM 31N"
        if not (4400000 <= y <= 4800000):
            return False, f"Y coordinate {y} out of range for UTM 31N"

    return True, None


# Usage
address = "  Barcelona,   Diagonal 100  "
is_valid, result = validate_address(address)
if is_valid:
    print(f"Valid address: '{result}'")
    # Geocode...
else:
    print(f"Error: {result}")
```

---

## 💾 Caching and Performance

### Built-in Native Cache

GeoFinder includes an asynchronous LRU cache system with TTL. You don't need to implement anything external unless you require database persistence.

```python
"""
Configuration and usage of the native cache.
"""
from geofinder import GeoFinder

# 1. Configure at initialization
gf = GeoFinder(
    cache_size=200,    # Capacity for 200 results
    cache_ttl=3600     # 1 hour lifetime
)

async def demo_cache():
    # First time: MISS (network request)
    res1 = await gf.find("Barcelona")
    
    # Second time: HIT (instant from memory)
    res2 = await gf.find("Barcelona")
    
    # Force update (skip cache)
    res3 = await gf.find("Barcelona", use_cache=False)
    
    # Clear cache
    gf.clear_cache()
```

### DIY Persistent Cache (User Implementation)

> [!IMPORTANT]
> **Standalone Philosophy:** GeoFinder maintains only in-memory cache by default to be completely standalone without external dependencies. However, for long-running applications or specific use cases, you can easily implement your own persistent cache layer.

#### When Do You Need Persistent Cache?

| Scenario | In-Memory Cache | Persistent Cache |
|-----------|------------------|-------------------|
| **Occasional scripts** | ✅ Perfect | ❌ Unnecessary |
| **Interactive notebooks** | ✅ Sufficient | ❌ Overhead |
| **24/7 server** | ⚠️ Lost on restart | ✅ Recommended |
| **Repetitive CLI** | ⚠️ Each run = new cache | ✅ Useful |
| **Very static data** | ✅ Works | ✅ Optimizes latency |

#### Synchronous Implementation (SQLite)

Ideal for simple scripts and CLIs:

```python
"""
Persistent cache using SQLite for geocoding (sync version).
Saved in: examples/persistent_cache_sync.py
"""
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from geofinder import GeoFinder


class GeoCacheSQLite:
    """Geocoding cache with SQLite (sync)."""

    def __init__(self, db_path: str = "geocache.db", ttl_days: int = 30):
        """
        Initializes the SQLite cache.
        
        Args:
            db_path: Path to the database file
            ttl_days: Cache validity in days (30 by default)
        """
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.gf = GeoFinder()
        self._init_db()

    def _init_db(self):
        """Creates the cache table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS geocache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created
                ON geocache(created_at)
            """)

    def _hash_query(self, query: str, **kwargs) -> str:
        """Generates unique hash for the query including parameters."""
        # Normalize query
        normalized = query.lower().strip()
        
        # Include important parameters in the hash
        cache_key = f"{normalized}:{kwargs.get('epsg', 25831)}:{kwargs.get('size', 10)}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    def get(self, query: str, **kwargs) -> Optional[List]:
        """Gets result from cache if it exists and is valid."""
        query_hash = self._hash_query(query, **kwargs)
        min_date = datetime.now() - timedelta(days=self.ttl_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT result FROM geocache
                WHERE query_hash = ? AND created_at > ?
                """,
                (query_hash, min_date.isoformat())
            )
            row = cursor.fetchone()
            if row:
                # Reconstruct GeoResult objects from JSON
                results_json = json.loads(row[0])
                # For simplicity, we return the JSON directly
                # In production, you could reconstruct GeoResult objects
                return results_json
        return None

    def set(self, query: str, results: List, **kwargs):
        """Saves result to cache."""
        query_hash = self._hash_query(query, **kwargs)
        
        # Serialize results (convert GeoResult to dict)
        results_json = [
            {
                'nom': r.nom,
                'nomTipus': r.nomTipus,
                'nomMunicipi': r.nomMunicipi,
                'nomComarca': r.nomComarca,
                'x': r.x,
                'y': r.y,
                'epsg': r.epsg
            } for r in results
        ]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO geocache (query_hash, query, result)
                VALUES (?, ?, ?)
                """,
                (query_hash, query, json.dumps(results_json))
            )

    def find(self, query: str, **kwargs) -> List:
        """Geocodes with cache (synchronous wrapper)."""
        # Try cache first
        cached = self.get(query, **kwargs)
        if cached is not None:
            print(f"✅ CACHE HIT: {query}")
            return cached

        # Cache miss - call the service
        print(f"🌐 CACHE MISS: {query} (querying ICGC...)")
        results = self.gf.find_sync(query, **kwargs)

        # Save to cache
        if results:
            self.set(query, results, **kwargs)

        return results
    
    def clear_expired(self):
        """Removes expired entries from cache."""
        min_date = datetime.now() - timedelta(days=self.ttl_days)
        
        with sqlite3.connect(self.db_path) as conn:
            deleted = conn.execute(
                "DELETE FROM geocache WHERE created_at < ?",
                (min_date.isoformat(),)
            ).rowcount
            
        print(f"🧹 Deleted {deleted} expired entries")
        return deleted
    
    def stats(self):
        """Shows cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM geocache").fetchone()[0]
            
            min_date = datetime.now() - timedelta(days=self.ttl_days)
            valid = conn.execute(
                "SELECT COUNT(*) FROM geocache WHERE created_at > ?",
                (min_date.isoformat(),)
            ).fetchone()[0]
            
        return {
            'total_entries': total,
            'valid_entries': valid,
            'expired_entries': total - valid,
            'db_path': self.db_path,
            'ttl_days': self.ttl_days
        }


# ============================================================================
# PERSISTENT CACHE USAGE
# ============================================================================

if __name__ == "__main__":
    # Create instance with cache
    cache = GeoCacheSQLite(db_path="my_cache.db", ttl_days=7)

    # First search (cache miss)
    results1 = cache.find("Barcelona")
    print(f"Found: {len(results1)} results")

    # Second search (cache hit - instant)
    results2 = cache.find("Barcelona")
    print(f"Found: {len(results2)} results")

    # Show statistics
    stats = cache.stats()
    print(f"\n📊 Cache statistics:")
    print(f"  - Valid entries: {stats['valid_entries']}")
    print(f"  - Total entries: {stats['total_entries']}")
    print(f"  - File: {stats['db_path']}")

    # Clear expired
    cache.clear_expired()
```

#### Asynchronous Implementation (SQLite with aiosqlite)

For modern async applications (FastAPI, etc.):

```python
"""
Asynchronous persistent cache using aiosqlite.
Installation: pip install aiosqlite
"""
import aiosqlite
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from geofinder import GeoFinder


class AsyncGeoCacheSQLite:
    """Asynchronous geocoding cache with SQLite."""

    def __init__(self, db_path: str = "geocache_async.db", ttl_days: int = 30):
        self.db_path = db_path
        self.ttl_days = ttl_days
        self.gf = GeoFinder()
        self._initialized = False

    async def _ensure_init(self):
        """Lazily initializes the DB."""
        if not self._initialized:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS geocache (
                        query_hash TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        result TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created
                    ON geocache(created_at)
                """)
                await db.commit()
            self._initialized = True

    def _hash_query(self, query: str, **kwargs) -> str:
        """Generates unique hash for the query."""
        normalized = query.lower().strip()
        cache_key = f"{normalized}:{kwargs.get('epsg', 25831)}:{kwargs.get('size', 10)}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    async def get(self, query: str, **kwargs) -> Optional[List]:
        """Gets result from cache if it exists and is valid."""
        await self._ensure_init()
        
        query_hash = self._hash_query(query, **kwargs)
        min_date = datetime.now() - timedelta(days=self.ttl_days)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT result FROM geocache WHERE query_hash = ? AND created_at > ?",
                (query_hash, min_date.isoformat())
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None

    async def set(self, query: str, results: List, **kwargs):
        """Saves result to cache."""
        await self._ensure_init()
        
        query_hash = self._hash_query(query, **kwargs)
        
        # Serialize
        results_json = [
            {
                'nom': r.nom,
                'nomTipus': r.nomTipus,
                'x': r.x,
                'y': r.y,
                'epsg': r.epsg
            } for r in results
        ]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO geocache (query_hash, query, result) VALUES (?, ?, ?)",
                (query_hash, query, json.dumps(results_json))
            )
            await db.commit()

    async def find(self, query: str, **kwargs) -> List:
        """Geocodes with cache (asynchronous wrapper)."""
        # Try cache
        cached = await self.get(query, **kwargs)
        if cached is not None:
            return cached

        # Cache miss
        results = await self.gf.find(query, **kwargs)

        # Save
        if results:
            await self.set(query, results, **kwargs)

        return results


# ASYNC USAGE
async def async_example():
    cache = AsyncGeoCacheSQLite()
    
    # First time: queries ICGC
    results = await cache.find("Girona")
    
    # Second time: from SQLite
    results = await cache.find("Girona")
    
    await cache.gf.close()
```

#### Cache with Redis (Production)

For distributed applications with multiple instances:

```python
"""
Distributed cache with Redis.
Installation: pip install redis
"""
import redis
import json
from typing import Optional, List
from geofinder import GeoFinder


class GeoCacheRedis:
    """Geocoding cache with Redis."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = 86400  # 24 hours
    ):
        self.client = redis.from_url(redis_url)
        self.ttl = ttl_seconds
        self.gf = GeoFinder()

    def _cache_key(self, query: str, **kwargs) -> str:
        """Generates Redis key."""
        epsg = kwargs.get('epsg', 25831)
        size = kwargs.get('size', 10)
        return f"geo:{query.lower()}:{epsg}:{size}"

    def find(self, query: str, **kwargs) -> List:
        """Geocodes with Redis cache."""
        key = self._cache_key(query, **kwargs)
        
        # Try cache
        cached = self.client.get(key)
        if cached:
            print(f"✅ REDIS HIT: {query}")
            return json.loads(cached)

        # Cache miss
        print(f"🌐 REDIS MISS: {query}")
        results = self.gf.find_sync(query, **kwargs)

        # Save with TTL
        if results:
            results_json = [
                {'nom': r.nom, 'x': r.x, 'y': r.y, 'epsg': r.epsg}
                for r in results
            ]
            self.client.setex(
                key,
                self.ttl,
                json.dumps(results_json)
            )

        return results


# USAGE
cache_redis = GeoCacheRedis(redis_url="redis://localhost:6379/0")
results = cache_redis.find("Lleida")
```

#### Implementation Comparison

| Solution | Advantages | Disadvantages | Use Cases |
|----------|----------|-------------|--------------|
| **In-memory (default)** | ✅ No setup<br>✅ Fast<br>✅ Standalone | ❌ Not persistent | Scripts, notebooks, testing |
| **SQLite sync** | ✅ Persistent<br>✅ No extra deps<br>✅ Simple | ❌ Not parallel | CLIs, repetitive scripts |
| **SQLite async** | ✅ Persistent<br>✅ Async-friendly | ⚠️ Dep: aiosqlite | FastAPI, async applications |
| **Redis** | ✅ Distributed<br>✅ Very fast<br>✅ Automatic TTL | ❌ Requires Redis server | Microservices, horizontal scaling |

#### Best Practices

1. **Use in-memory cache by default** - It's sufficient for 90% of cases
2. **SQLite for local persistence** - Scripts that run regularly
3. **Redis for distributed production** - Multiple workers/pods
4. **Include parameters in the hash** - EPSG and size affect results
5. **Set reasonable TTL** - Municipalities don't change, but new addresses do
6. **Clean expired caches** - Avoid infinite DB growth

---

## 🏢 Real-World Use Cases

### 1. Postal Address Validator

```python
"""
Validate and enrich postal addresses.
Useful for: ecommerce, logistics, CRM.
"""
from geofinder import GeoFinder
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidatedAddress:
    """Validated and enriched address."""
    original: str
    is_valid: bool
    normalized: Optional[str] = None
    street: Optional[str] = None
    municipality: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None  # If available
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: float = 0.0
    error: Optional[str] = None


class AddressValidator:
    """Address validator for Catalonia."""

    def __init__(self):
        self.gf = GeoFinder()

    def validate(self, address: str) -> ValidatedAddress:
        """Validates and enriches an address."""
        try:
            results = self.gf.find(address)

            if not results:
                return ValidatedAddress(
                    original=address,
                    is_valid=False,
                    error="Address not found"
                )

            best = results[0]

            # Determine confidence based on type
            confidence = 1.0 if best.nomTipus == 'Adreça' else 0.7

            return ValidatedAddress(
                original=address,
                is_valid=True,
                normalized=best.nom,
                street=best.nomTipus,
                municipality=best.nomMunicipi,
                county=best.nomComarca,
                latitude=best.y,
                longitude=best.x,
                confidence=confidence
            )

        except Exception as e:
            return ValidatedAddress(
                original=address,
                is_valid=False,
                error=str(e)
            )


# Usage
validator = AddressValidator()

addresses = [
    "Barcelona, Passeig de Gràcia 43",
    "Girona, calle inventada 999",
    "Reus, Plaça del Mercadal 1"
]

for addr in addresses:
    result = validator.validate(addr)
    if result.is_valid:
        print(f"✅ {result.normalized}")
        print(f"   📍 {result.latitude}, {result.longitude}")
        print(f"   🏘️ {result.municipality}, {result.county}")
    else:
        print(f"❌ {addr}: {result.error}")
```

### 2. Nearby Services Finder

```python
"""
Find services/locations near a point.
Useful for: delivery apps, home services.
"""
from geofinder import GeoFinder
from geofinder.transformations import transform_point
from dataclasses import dataclass
from typing import List
import math


@dataclass
class NearbyResult:
    """Nearby search result."""
    name: str
    type: str
    distance_km: float
    latitude: float
    longitude: float


class NearbySearch:
    """Nearby locations finder."""

    def __init__(self):
        self.gf = GeoFinder()

    async def search_near_place(
        self,
        place_name: str,
        radius_km: float = 1.0,
        max_results: int = 10
    ) -> List[NearbyResult]:
        """
        Searches for places near a named location.

        Args:
            place_name: Reference location name
            radius_km: Search radius in km
            max_results: Maximum results
        """
        # Use the integrated core method for efficiency
        results = await self.gf.search_nearby(place_name, radius_km=radius_km, max_results=max_results)
        
        if not results:
            return []
            
        ref = results[0]
        return [
            NearbyResult(
                name=r.nom,
                type=r.nomTipus,
                distance_km=0.0, # Core doesn't calculate exact distances yet
                latitude=r.y,
                longitude=r.x
            ) for r in results
        ]

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        """Calculates distance in km between two points."""
        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c


# Usage
searcher = NearbySearch()

nearby = searcher.search_near_place("Plaça Catalunya, Barcelona", radius_km=0.5)

print("Places near Plaça Catalunya:")
for place in nearby[:5]:
    print(f"  📍 {place.name} ({place.type}) - {place.distance_km}km")
```

### 3. GPS Coordinate Converter

```python
"""
Tool for converting coordinates between formats.
Useful for: cartography, topography, surveying.
"""
from geofinder.transformations import transform_point, get_backend
from dataclasses import dataclass
from typing import Tuple


@dataclass
class CoordinateResult:
    """Coordinate conversion result."""
    x: float
    y: float
    epsg: int
    format_name: str
    formatted: str


class CoordinateConverter:
    """Coordinate converter with multiple formats."""

    FORMATS = {
        4326: "WGS84 (GPS)",
        25831: "ETRS89 UTM 31N",
        23031: "ED50 UTM 31N",
        3857: "Web Mercator",
        32631: "WGS84 UTM 31N"
    }

    def __init__(self):
        backend = get_backend()
        if not backend:
            raise ImportError(
                "Install pyproj or GDAL to use transformations"
            )
        print(f"Using backend: {backend}")

    def convert(
        self,
        x: float,
        y: float,
        from_epsg: int,
        to_epsg: int
    ) -> CoordinateResult:
        """Converts coordinates between systems."""
        dest_x, dest_y = transform_point(x, y, from_epsg, to_epsg)

        return CoordinateResult(
            x=dest_x,
            y=dest_y,
            epsg=to_epsg,
            format_name=self.FORMATS.get(to_epsg, f"EPSG:{to_epsg}"),
            formatted=self._format_coords(dest_x, dest_y, to_epsg)
        )

    def convert_to_all(
        self,
        x: float,
        y: float,
        from_epsg: int
    ) -> list[CoordinateResult]:
        """Converts to all available systems."""
        results = []
        for epsg in self.FORMATS:
            if epsg != from_epsg:
                try:
                    results.append(self.convert(x, y, from_epsg, epsg))
                except Exception:
                    pass  # Some systems may not be compatible
        return results

    def _format_coords(self, x: float, y: float, epsg: int) -> str:
        """Formats coordinates according to the system."""
        if epsg == 4326:
            # DMS format for GPS
            lat_dir = 'N' if y >= 0 else 'S'
            lon_dir = 'E' if x >= 0 else 'W'
            return f"{abs(y):.6f}°{lat_dir}, {abs(x):.6f}°{lon_dir}"
        else:
            return f"X: {x:.2f}, Y: {y:.2f}"


# Usage
converter = CoordinateConverter()

# Convert UTM to GPS
result = converter.convert(430000, 4580000, 25831, 4326)
print(f"{result.format_name}: {result.formatted}")

# View in all formats
print("\nSame coordinates in different systems:")
for r in converter.convert_to_all(430000, 4580000, 25831):
    print(f"  {r.format_name}: {r.formatted}")
```

---

## 📎 Additional Resources

### Related Documentation

- [README.md](README.md) - Quick installation and usage guide
- [README-DEV.md](README-DEV.md) - Development environment setup
- [README-ARQ.md](README-ARQ.md) - Internal technical architecture
- [README-MCP.md](README-MCP.md) - MCP Server for AI integration

### Useful Links

- [GitHub Repository](https://github.com/jccamel/geofinder-icgc)
- [ICGC Geocoder](https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC)
- [Pelias Documentation](https://github.com/pelias/documentation)
- [EPSG Registry](https://epsg.io/)

---

**Author:** Goalnefesh  
**License:** GPL-2.0-or-later
