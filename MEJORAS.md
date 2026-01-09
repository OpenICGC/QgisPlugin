# 🚀 Mejoras Propuestas para GeoFinder-ICGC

> **Última actualización:** 27 de diciembre de 2025  
> **Basado en:** Análisis profundo v1.0 - Valoración global 8.3/10 ⭐ (+0.2 por mejoras en tests)

Tras un análisis exhaustivo del proyecto (ver `analisis_profundo.md` para detalles), se han identificado mejoras priorizadas para optimizar robustez, rendimiento y facilidad de uso.

---

## ✅ Completadas en v2.3.0

### 1. Tests End-to-End y Funcionales para Servidor MCP
- [x] **Suite completa de herramientas**: Implementados tests para todas las herramientas MCP (`find_place`, `autocomplete`, `find_reverse`, etc.)
- [x] **Inyección de Dependencias en Servidor**: El servidor ahora soporta inyección del cliente `GeoFinder` facilitando el testeo mediante mocks.
- [x] **Validación Robusta**: Tests específicos para validación de parámetros Pydantic y manejo de errores del servicio.

### 2. Incremento Decisivo de Cobertura
- [x] **`mcp_server.py`**: Cobertura incrementada de **2% → 64%**.
- [x] **Global**: Cobertura global del proyecto incrementada de ~25% → 40%.
- [x] **Mantenimiento**: Eliminación de scripts de depuración y limpieza de deuda técnica en los tests de `FastMCP`.

---

## ✅ Completadas en v2.2.0

### 1. Reducción de Dependencias y Configuración Simplificada
- [x] **URL de la API hardcodeada**: `https://eines.icgc.cat/geocodificador` como valor por defecto
- [x] **Eliminación de `python-dotenv`**: Dependencias reducidas a 2 (pydantic, httpx)
- [x] **Valores por defecto robustos**: Timeouts y reintentos configurados de forma sensata

### 2. Arquitectura Moderna
- [x] **Inyección de Dependencias**: Implementada en v2.2.0 con soporte para `http_client` externo
- [x] **Pool de conexiones compartido**: Documentado en COOKBOOK.md con ejemplos FastAPI
- [x] **Jerarquía de excepciones personalizada**: `GeoFinderError` con contexto detallado
- [x] **Modelos Pydantic v2**: Validación automática de coordenadas y datos

---

## 🔴 Prioridad Alta (Crítico)

### 1. Continuar Incrementando Cobertura (Objetivo: 70-80%)

**Estado actual:** 40% global (~64% en `mcp_server.py`)

**Focos críticos restantes:**
- **`geofinder.py`**: 68% → 80%+
  - Cubrir bloques 520-562 (búsqueda de rectángulos)
  - Cubrir bloques 793-833 (parsing de direcciones complejas)
  - Edge cases en detección automática de tipos
  
- **`transformations.py`**: 33% → 75%+
  - Tests para EPSG menos comunes (23031, 3857)
  - Validación de rangos extremos
  - Pruebas sin dependencias opcionales (pyproj/gdal)

**Impacto:** Mayor confianza en refactorizaciones, detección temprana de bugs.

**Estimación:** 1-2 semanas (reducida tras v2.3.0)

---

## 🟡 Prioridad Media (Recomendado)

### 2. Tipado Estático Completo

**Cambios en `pyproject.toml`:**
```toml
[tool.mypy]
disallow_untyped_defs = true  # ✅ Cambiar de false a true
```

**Tareas:**
- Añadir type hints a todos los métodos internos
- Importar tipos de `typing` donde falten
- Verificar con mypy en CI/CD

**Impacto:** Mejor autocompletado IDE, menos errores en runtime.

**Estimación:** 1 semana

---

### 3. Logging Estructurado (JSON)

**Migración:**
```python
# Actual: logging.info("Petición completada en 150ms")
# Propuesto:
logger.info("request_completed", extra={
    "endpoint": "/cerca",
    "duration_ms": 150,
    "query": "Barcelona",
    "cached": False
})
```

**Beneficios:**
- Integración con ELK, Datadog, CloudWatch
- Mejor debugging en producción

**Impacto:** Operabilidad mejorada en entornos cloud.

**Estimación:** 1 semana

---

## 🟢 Prioridad Baja (Nice to Have)

### 4. Glosario de Términos GIS
**Impacto:** Reduce curva de aprendizaje para usuarios no GIS.
- **Estado:** ✅ COMPLETADO con fichero [README-GIS.md](README-GIS.md)

---

### 5. Ejemplos de Despliegue (Docker/K8s)
**Estimación:** 2-3 días

---

### 6. Benchmark y Tests de Carga
**Estimación:** 3-4 días

---

## 📊 Roadmap Sugerido

### Q4 2025 (Diciembre)
- ✅ Incrementar cobertura `mcp_server.py` al 60%+ (v2.3.0)
- ✅ Tests E2E para MCP server (v2.3.0)
- ✅ Glosario GIS (README-GIS.md)

### Q1 2026 (Enero - Marzo)
- ⚙️ Incrementar cobertura global al 70-80%
- ⚙️ Habilitar tipado estático estricto
- ⚙️ Migrar a logging estructurado JSON

---

## 🎯 Resumen de Prioridades

| Prioridad | Mejora | Impacto | Estimación | Estado |
|-----------|--------|---------|------------|--------|
| 🔴 Alta | Cobertura tests 70%+ | Alto | 1-2 sem | **Parcial** (MCP 64%) |
| 🔴 Alta | Tests E2E MCP | Alto | - | **Completado** |
| 🟡 Media | Tipado estático | Medio | 1 sem | Pendiente |
| 🟡 Media | Logging JSON | Medio | 1 sem | Pendiente |
| 🟢 Baja | Glosario GIS | Bajo | - | **Completado** |
| 🟢 Baja | Docker/K8s | Bajo | 2-3 días | Pendiente |
| 🟢 Baja | Benchmarks | Bajo | 3-4 días | Pendiente |

---

## 📖 Referencias

- **Documentación técnica:** [README-ARQ.md](README-ARQ.md)
- **Ejemplos de uso:** [COOKBOOK.md](COOKBOOK.md)
- **Guía de desarrollo:** [README-DEV.md](README-DEV.md)

---

**Próxima revisión sugerida:** Enero 2026
