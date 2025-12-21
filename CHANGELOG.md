# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2024-12-20

### Added
- **Dependency Injection**: Support for external `httpx.AsyncClient` injection
  - Allows sharing connection pools across multiple GeoFinder instances
  - Automatic ownership tracking (only closes clients it creates)
  - Ideal for high-performance web applications (FastAPI, etc.)
- **Custom Exception Hierarchy**: New `GeoFinderError` base class with specific subclasses
  - `ConfigurationError`: Configuration issues
  - `ParsingError`: Input parsing errors
  - `CoordinateError`: Coordinate validation errors
  - `ServiceError`: External service errors (with subclasses for connection, timeout, HTTP)
  - Backward-compatible aliases for legacy exceptions
- **Improved Address Parsing**: Enhanced parser supporting natural formats
  - Supports addresses without commas: "Gran Via 123 Barcelona"
  - Handles "s/n" (sin número) for unnumbered addresses
- **Response Metadata**: Added `time_ms` field to track request latency
- **Size Parameter Propagation**: `size` parameter now works across all methods

### Changed
- **Pydantic v2 Migration**: All models now use Pydantic v2 for validation
  - `GeoResult` and `GeoResponse` with strict validation
  - Dual access: by attribute (`r.nom`) and by key (`r['nom']`)
- **Enhanced Retry Strategy**: Exponential backoff with jitter
  - Configurable retry parameters
  - Smart retry logic (5xx errors, timeouts, connection issues)
- **MCP Server Improvements**: Added parameter validation and better error handling

### Fixed
- Coordinate validation edge cases
- SSL verification warnings
- Cache key robustness in concurrent scenarios

## [2.0.0] - 2024-12-16

### Changed
- **Full Async Migration**: Migrated entire codebase to asynchronous architecture
  - Replaced `requests` with `httpx` for async HTTP
  - All core methods now async by default
  - Added sync wrappers (`_sync` methods) for backward compatibility

### Added
- **Batch Processing**: New utilities for processing multiple queries
  - `find_batch()` and `find_reverse_batch()` with concurrency control
  - Automatic semaphore-based rate limiting
- **Thread-Safe Client Initialization**: Lazy loading with `asyncio.Lock`
- **Smart Caching**: LRU cache with TTL support
  - Configurable size and expiration
  - Async-safe implementation

### Removed
- Synchronous `requests` library dependency

## [1.4.0] - 2024-12-01

### Added
- Basic geocoding functionality for Catalonia
- Integration with ICGC Pelias service
- Support for multiple search types:
  - Place names and toponyms
  - Addresses
  - Coordinates (multiple EPSG systems)
  - Road kilometer points
- Reverse geocoding
- Autocomplete suggestions
- MCP server for AI integration
- Coordinate transformation support (optional with pyproj/GDAL)

---

[2.2.0]: https://github.com/jccamel/geofinder-icgc/compare/v2.0.0...v2.2.0
[2.0.0]: https://github.com/jccamel/geofinder-icgc/compare/v1.4.0...v2.0.0
[1.4.0]: https://github.com/jccamel/geofinder-icgc/releases/tag/v1.4.0
