# Fork Information

## Original Project

- **Name**: Open ICGC Plugin for QGIS
- **Repository**: https://github.com/OpenICGC/QgisPlugin
- **Author**: Institut Cartogràfic i Geològic de Catalunya (ICGC)
- **License**: GPL-2.0
- **Component Used**: `geofinder3/` (geocoding functionality)
- **Base Version**: v1.1.28 (2025-11-25)
- **Base Commit**: `7f8c283`

## This Fork

**Purpose**: Extract the geocoding component as a standalone Python library, removing QGIS dependencies and adding modern features.

### Files Derived from Original

| Current File | Original File | Modifications |
|--------------|---------------|---------------|
| `geofinder/geofinder.py` | `geofinder3/geofinder.py` | Removed cadastral search, simplified API, improved error handling |
| `geofinder/pelias.py` | `geofinder3/pelias.py` | Migrated from `urllib` to `requests`, added retry logic and custom exceptions |

### New Files (Not from Fork)

- `geofinder/mcp_server.py` - MCP server for AI integration (Claude Desktop)
- `geofinder/transformations.py` - Coordinate transformation utilities
- `tests/*` - Complete test suite with pytest
- `pyproject.toml` - Modern Python package configuration
- All extensive documentation (README-*.md, COOKBOOK.md)

### Major Changes

#### Removed Functionality
- ❌ QGIS plugin infrastructure and UI
- ❌ Cadastral reference search (Spanish land registry)
- ❌ SOAP client for cadastral services
- ❌ Map layer management and visualization
- ❌ Download tools for cartographic products
- ❌ Time series management
- ❌ Photo library integration

#### Added Functionality
- ✅ MCP (Model Context Protocol) server for AI assistants
- ✅ Modern HTTP client with automatic retries
- ✅ Comprehensive test suite (pytest)
- ✅ Extensive documentation and examples
- ✅ Environment-based configuration (.env support)
- ✅ Standalone Python package (pip installable)

#### Modernizations
- 🔄 HTTP client: `urllib` → `requests` with session management
- 🔄 Error handling: Generic exceptions → Specific exception classes
- 🔄 Dependencies: Heavy QGIS stack → Minimal (stdlib + optional pyproj)
- 🔄 Structure: QGIS plugin → Standard Python package
- 🔄 Documentation: Plugin docs → Comprehensive API docs

## GPL-2.0 Compliance

✅ **License Maintained**: Same GPL-2.0 license as original  
✅ **Attribution**: ICGC credited as original author in all files  
✅ **Source Available**: Public repository on GitHub  
✅ **Changes Documented**: This file and commit history  
✅ **Copyright Headers**: Added to all modified files

## Maintainer

**Goalnefesh**  
Email: goalnefesh@protonmail.com  
Repository: https://github.com/jccamel/geocoder-mcp

## Acknowledgments

This project would not exist without the excellent work of the ICGC team on the Open ICGC QGIS Plugin. Their geocoding implementation provided a solid foundation for this standalone library.

Special thanks to the ICGC for:
- Developing and maintaining the Pelias geocoding service for Catalonia
- Publishing their QGIS plugin as open source under GPL-2.0
- Creating comprehensive geocoding functionality for Catalan geographic data
