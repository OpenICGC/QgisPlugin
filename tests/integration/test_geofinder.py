#!/usr/bin/env python
"""
Script de prueba completo para la biblioteca GeoFinder (Versión Async).

Este script prueba todas las funcionalidades de GeoFinder con ejemplos reales
del servicio de geocodificación del ICGC (Institut Cartogràfic i Geològic de Catalunya).

Requiere conexión a internet para acceder al servicio ICGC.
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from geofinder import GeoFinder


@pytest.fixture
async def gf():
    """Fixture para GeoFinder."""
    client = GeoFinder()
    yield client
    await client.close()


def print_section(title):
    """Imprime un separador de sección"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_results(description, results, max_results=3):
    """Imprime los resultados de una búsqueda"""
    if isinstance(results, list):
        print(f"\n✅ {description}: {len(results)} resultados")
        for i, result in enumerate(results[:max_results], 1):
            if hasattr(result, 'nom'):
                name = result.nom
                tipo = result.nomTipus
                lat = result.y
                lon = result.x
            else:
                name = result.get('nom', 'N/A')
                tipo = result.get('nomTipus', 'N/A')
                lat = result.get('y', 'N/A')
                lon = result.get('x', 'N/A')

            # Mostrar coordenadas en formato (lat, lon) para mayor claridad
            print(f"   {i}. {name} ({tipo}) - ({lat}, {lon})")
        if len(results) > max_results:
            print(f"   ... y {len(results) - max_results} más")
    else:
        print(f"\n✅ {description}: {results}")


async def test_basic_search(gf):
    """Prueba búsquedas básicas con find()"""
    print_section("1. BÚSQUEDAS BÁSICAS - find()")

    tests = [
        ("Topónimo (Barcelona)", "Barcelona"),
        ("Municipio pequeño (Girona)", "Girona"),
        ("Montaña (Montserrat)", "Montserrat"),
        ("Comarca (Barcelonès)", "Barcelonès"),
    ]

    for description, query in tests:
        print(f"\n📍 {description}")
        print(f"   Query: '{query}'")
        try:
            results = await gf.find(query)
            print_results(f"find('{query}')", results, max_results=2)
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_coordinate_search(gf):
    """Prueba búsquedas por coordenadas"""
    print_section("2. BÚSQUEDAS POR COORDENADAS")

    tests = [
        ("UTM 31N (Barcelona)", "430000 4580000 EPSG:25831"),
        ("WGS84 (Barcelona)", "2.1734 41.3851 EPSG:4326"),
        ("Sin EPSG (asume 25831)", "430000 4580000"),
    ]

    for description, query in tests:
        print(f"\n📍 {description}")
        print(f"   Query: '{query}'")
        try:
            results = await gf.find(query)
            print_results(f"find('{query}')", results, max_results=2)
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_address_search(gf):
    """Prueba búsquedas de direcciones"""
    print_section("3. BÚSQUEDAS DE DIRECCIONES")

    tests = [
        ("Dirección completa", "Barcelona, Diagonal 100"),
        ("Calle con tipo", "Carrer Aragó 50, Barcelona"),
        ("Avenida", "Avinguda Diagonal 686, Barcelona"),
    ]

    for description, query in tests:
        print(f"\n🏠 {description}")
        print(f"   Query: '{query}'")
        try:
            results = await gf.find(query)
            print_results(f"find('{query}')", results, max_results=2)
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_road_search(gf):
    """Prueba búsquedas de carreteras"""
    print_section("4. BÚSQUEDAS DE CARRETERAS")

    tests = [
        ("Carretera N-II", "N-II km 666"),
        ("Autopista AP-7", "AP-7 km 150"),
        ("Nacional", "N-II km 25"),
    ]

    for description, query in tests:
        print(f"\n🛣️  {description}")
        print(f"   Query: '{query}'")
        try:
            results = await gf.find(query)
            print_results(f"find('{query}')", results, max_results=2)
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_autocomplete(gf):
    """Prueba autocompletado"""
    print_section("5. AUTOCOMPLETADO")

    tests = [
        "Barcel",
        "Montserr",
        "Giro",
        "N-II",
    ]

    for query in tests:
        print(f"\n💡 Autocompletando: '{query}'")
        try:
            results = await gf.autocomplete(query, size=5)
            print_results(f"autocomplete('{query}')", results, max_results=5)
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_reverse_geocoding(gf):
    """Prueba geocodificación inversa"""
    print_section("6. GEOCODIFICACIÓN INVERSA")

    tests = [
        ("Barcelona (WGS84)", 2.1734, 41.3851, 4326),
        ("Barcelona (UTM31N)", 430000, 4580000, 25831),
        ("Girona (UTM31N)", 485000, 4650000, 25831),
    ]

    for description, x, y, epsg in tests:
        print(f"\n🔄 {description}")
        print(f"   Coordenadas: ({x}, {y}) EPSG:{epsg}")
        try:
            results = await gf.find_reverse(x, y, epsg=epsg, size=3)
            print_results(f"find_reverse({x}, {y}, {epsg})", results, max_results=3)
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_coordinate_transformation(gf):
    """Prueba transformación de coordenadas (Síncrono - utilidad pura)"""
    print_section("7. TRANSFORMACIÓN DE COORDENADAS")

    try:
        from geofinder.transformations import transform_point

        tests = [
            ("UTM31N → WGS84", 430000, 4580000, 25831, 4326),
            ("WGS84 → UTM31N", 2.1734, 41.3851, 4326, 25831),
        ]

        for description, x, y, from_epsg, to_epsg in tests:
            print(f"\n🔄 {description}")
            print(f"   Input: ({x}, {y}) EPSG:{from_epsg}")
            try:
                dest_x, dest_y = transform_point(x, y, from_epsg, to_epsg)
                if dest_x is not None and dest_y is not None:
                    print(f"   ✅ Output: ({dest_x:.6f}, {dest_y:.6f}) EPSG:{to_epsg}")
                else:
                    print("   ❌ Transformación falló")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    except ImportError:
        print("\n⚠️  Transformación de coordenadas no disponible")
        print("   Instala pyproj o GDAL: pip install pyproj")


async def test_parsing_methods(gf):
    """Prueba métodos de parsing internos (ahora async porque _find_data lo es, pero el parsing es estático)"""
    # Nota: Los métodos de parsing son estáticos y síncronos, se pueden llamar directamente
    print_section("8. MÉTODOS DE PARSING (Internos)")

    # Test _parse_point
    print("\n📍 Parsing de puntos:")
    point_tests = [
        "430000 4580000",
        "EPSG:25831 430000 4580000",
        "2.1734 41.3851 EPSG:4326",
    ]
    for query in point_tests:
        x, y, epsg = gf._parse_point(query)
        if x is not None:
            print(f"   ✅ '{query}' → x={x}, y={y}, epsg={epsg}")
        else:
            print(f"   ❌ '{query}' → No detectado")

    # Test _parse_address
    print("\n🏠 Parsing de direcciones:")
    address_tests = [
        "Barcelona, Diagonal 100",
        "Carrer Aragó 50, Barcelona",
        "C/ Diagonal nº 100, Barcelona",
    ]
    for query in address_tests:
        municipality, street_type, street, number = gf._parse_address(query)
        if street is not None:
            print(f"   ✅ '{query}'")
            print(f"      → Municipio: {municipality}, Tipo: {street_type}, Calle: {street}, Nº: {number}")
        else:
            print(f"   ❌ '{query}' → No detectado")

    # Test _parse_road
    print("\n🛣️  Parsing de carreteras:")
    road_tests = [
        "N-II km 666",
        "AP7 km 150",
        "N-II, 25",
    ]
    for query in road_tests:
        road, km = gf._parse_road(query)
        if road is not None:
            print(f"   ✅ '{query}' → Carretera: {road}, Km: {km}")
        else:
            print(f"   ❌ '{query}' → No detectado")


async def test_advanced_features(gf):
    """Prueba características avanzadas"""
    print_section("9. CARACTERÍSTICAS AVANZADAS")

    # Búsqueda con múltiples capas
    print("\n🔍 Búsqueda por coordenadas con capas específicas:")
    try:
        results = await gf.find_point_coordinate_icgc(
            430000, 4580000, 25831,
            layers="address,tops",
            size=3
        )
        print_results("Capas: address,tops", results, max_results=3)
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Búsqueda de dirección estructurada
    print("\n🏠 Búsqueda de dirección estructurada:")
    try:
        results = await gf.find_address("Barcelona", "Avinguda", "Diagonal", "100")
        print_results("find_address('Barcelona', 'Avinguda', 'Diagonal', '100')", results, max_results=2)
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Búsqueda de carretera
    print("\n🛣️  Búsqueda de carretera:")
    try:
        results = await gf.find_road("N-II", "666")
        print_results("find_road('N-II', '666')", results, max_results=2)
    except Exception as e:
        print(f"   ❌ Error: {e}")


async def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 80)
    print("  PRUEBAS COMPLETAS DE LA BIBLIOTECA GEOFINDER (ASYNC)")
    print("=" * 80)
    print("\nEste script prueba todas las funcionalidades de GeoFinder.")
    print("Requiere conexión a internet para acceder al servicio ICGC.\n")

    # Inicializar GeoFinder
    print("Inicializando GeoFinder...")
    gf = GeoFinder()
    print("✅ GeoFinder inicializado correctamente\n")

    try:
        await test_basic_search(gf)
        await test_coordinate_search(gf)
        await test_address_search(gf)
        await test_road_search(gf)
        await test_autocomplete(gf)
        await test_reverse_geocoding(gf)

        # Test síncrono
        test_coordinate_transformation(gf)
        await test_parsing_methods(gf)
        await test_advanced_features(gf)

        # Resumen final
        print("\n" + "=" * 80)
        print("  ✅ PRUEBAS COMPLETADAS")
        print("=" * 80)
        print("\nTodas las funcionalidades de GeoFinder han sido probadas.")
        print("Revisa los resultados arriba para verificar el funcionamiento.\n")

    except Exception as e:
        print(f"\n\n❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cerrar cliente
        await gf.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Pruebas interrumpidas por el usuario")
        sys.exit(1)
