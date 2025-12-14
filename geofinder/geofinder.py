"""
GeoFinder - Geocodificador para Cataluña
=========================================

Copyright (C) 2019-2025 Institut Cartogràfic i Geològic de Catalunya (ICGC)
Copyright (C) 2025 Goalnefesh

This file is part of geocoder-mcp, a fork of the Open ICGC QGIS Plugin.
Original project: https://github.com/OpenICGC/QgisPlugin

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

Clase principal para geocodificación usando los servicios del ICGC.
"""

import logging
import os
import re

from dotenv import load_dotenv

from .pelias import PeliasClient
from .transformations import transform_point

# Cargar variables de entorno
load_dotenv()


class GeoFinder:
    """Geocodificador para Cataluña usando el servicio del ICGC.

    Soporta búsqueda de:
        - Topónimos (municipios, comarcas, montañas, etc.)
        - Direcciones (calle + número + municipio)
        - Coordenadas (X Y EPSG:código)
        - Rectángulos (X1 Y1 X2 Y2)
        - Carreteras (C-32 km 10)

    Example:
        gf = GeoFinder()

        # Buscar un topónimo
        results = gf.find("Barcelona", 25831)

        # Buscar coordenadas
        results = gf.find("430000 4580000 EPSG:25831", 25831)

        # Buscar dirección
        results = gf.find("Barcelona, Diagonal 100", 25831)

    Attributes:
        timeout: Timeout en segundos para peticiones
        geoencoder_epsg: EPSG del geocodificador (4326 WGS84)
    """

    # Configuración del servicio
    timeout = 5
    geoencoder_epsg = 4326

    def __init__(
        self,
        logger=None,
        icgc_url=None,
        timeout=5,
    ):
        """Inicializa el geocodificador.

        Args:
            logger: Logger opcional para debug
            icgc_url: URL del geocodificador ICGC
            timeout: Timeout en segundos
        """
        self.timeout = timeout
        self._icgc_url = icgc_url if icgc_url is not None else os.getenv("ICGC_URL", "")
        self._icgc_client = None

        # Configurar logger
        if logger:
            self.log = logger
        else:
            self.log = logging.getLogger("geofinder")
            self.log.addHandler(logging.NullHandler())

    @property
    def icgc_client(self):
        """Cliente Pelias del ICGC (lazy loading)."""
        if self._icgc_client is None:
            self._icgc_client = PeliasClient(
                self._icgc_url,
                self.timeout,
                default_search_call="cerca",
                default_reverse_call="invers",
                default_autocomplete_call="autocompletar",
            )
        return self._icgc_client

    # =========================================================================
    # API Principal
    # =========================================================================

    def find(self, user_text, default_epsg=25831):
        """Busca ubicaciones a partir de un texto.

        Detecta automáticamente el tipo de búsqueda:
            - Coordenadas: "X Y" o "X Y EPSG:código"
            - Rectángulo: "X1 Y1 X2 Y2"
            - Carretera: "C-32 km 10"
            - Dirección: "Barcelona, Diagonal 100"
            - Topónimo: cualquier otro texto

        Args:
            user_text: Texto de búsqueda
            default_epsg: EPSG por defecto para coordenadas sin especificar

        Returns:
            list[dict]: Lista de resultados con estructura:
                {
                    'nom': str,          # Nombre del lugar
                    'nomTipus': str,     # Tipo (Municipi, Carrer, etc.)
                    'nomMunicipi': str,  # Municipio
                    'nomComarca': str,   # Comarca
                    'x': float,          # Coordenada X
                    'y': float,          # Coordenada Y
                    'epsg': int          # Código EPSG
                }
        """
        self.log.info("GeoFinder search: %s", user_text)
        results = self._find_data(user_text, default_epsg)
        self.log.debug("Found %d results", len(results))
        return results

    def find_reverse(self, x, y, epsg=25831, layers="address,tops,pk", size=5):
        """Geocodificación inversa: encuentra lugares en unas coordenadas.

        Args:
            x: Coordenada X
            y: Coordenada Y
            epsg: Código EPSG de las coordenadas
            layers: Capas a buscar (address, tops, pk)
            size: Número máximo de resultados

        Returns:
            list[dict]: Lista de resultados
        """
        return self._find_point_coordinate_icgc(x, y, epsg, layers, size=size)

    def autocomplete(self, partial_text, size=10):
        """Obtiene sugerencias de autocompletado.

        Args:
            partial_text: Texto parcial
            size: Número máximo de sugerencias

        Returns:
            list[dict]: Lista de sugerencias
        """
        try:
            res_dict = self.icgc_client.autocomplete(partial_text, size=size)
            return self._parse_icgc_response(res_dict)
        except Exception as e:
            self.log.exception("Autocomplete error: %s", e)
            raise

    # =========================================================================
    # Detección de tipo de búsqueda
    # =========================================================================

    def _find_data(self, text, default_epsg):
        """Detecta el tipo de búsqueda y ejecuta la consulta apropiada."""

        # Rectángulo de coordenadas
        west, north, east, south, epsg = self._parse_rectangle(text)
        if west and north and east and south:
            return self._find_rectangle(west, north, east, south, epsg or default_epsg)

        # Punto de coordenadas
        x, y, epsg = self._parse_point(text)
        if x and y:
            return self._find_point_coordinate(x, y, epsg or default_epsg)

        # Carretera y kilómetro
        road, km = self._parse_road(text)
        if road and km:
            return self._find_road(road, km)

        # Dirección
        municipality, street_type, street, number = self._parse_address(text)
        if municipality and street and number:
            return self._find_address(municipality, street_type, street, number)

        # Por defecto: topónimo
        return self._find_placename(text)

    @staticmethod
    def _parse_rectangle(text):
        """Detecta un rectángulo de coordenadas en el texto.

        Formatos aceptados:
            - X1 Y1 X2 Y2
            - EPSG:código X1 Y1 X2 Y2
            - X1 Y1 X2 Y2 EPSG:código
        """
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s*(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            epsg1, west, north, east, south, epsg2 = found.groups()
            return (
                float(west.replace(",", ".")),
                float(north.replace(",", ".")),
                float(east.replace(",", ".")),
                float(south.replace(",", ".")),
                int(epsg1 or epsg2) if (epsg1 or epsg2) else None,
            )
        return None, None, None, None, None

    @staticmethod
    def _parse_point(text):
        """Detecta coordenadas de un punto en el texto.

        Formatos aceptados:
            - X Y
            - EPSG:código X Y
            - X Y EPSG:código
        """
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s*([+-]?[0-9]*[.,]?[0-9]+)(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            epsg1, x, y, epsg2 = found.groups()
            return (
                float(x.replace(",", ".")),
                float(y.replace(",", ".")),
                int(epsg1 or epsg2) if (epsg1 or epsg2) else None,
            )
        return None, None, None

    @staticmethod
    def _parse_road(text):
        """Detecta una carretera y kilómetro.

        Formatos aceptados:
            - C-32 km 10
            - C32, 10
            - AP7 km 150
        """
        expression = r"^\s*([A-Za-z]+)-*(\d+)\s*(?:(?:km)|,|\s)\s*(\d+)\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            road, road_number, km = found.groups()
            return f"{road}-{road_number}", km
        return None, None

    @staticmethod
    def _parse_address(text):
        """Detecta una dirección.

        Formatos aceptados:
            - Barcelona, Diagonal 100
            - C/ Aragó 50, Barcelona
            - Barcelona, Avd. Diagonal nº 100
        """
        expression = r"^\s*(?:([\D\s]+)\s*,)?\s*([\w]+[./])?\s*([\D\s]+)\s+(?:nº)?\s*,*(\d[\d-]*)\s*(?:[,.]\s*([\D\s]+[\D]))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)

        if found:
            municipality1, street_type, street, number, municipality2 = found.groups()
            municipality = municipality1 or municipality2
            return municipality, street_type, street.strip(), number
        return None, None, None, None

    # =========================================================================
    # Métodos de búsqueda
    # =========================================================================

    def _find_rectangle(self, west, north, east, south, epsg):
        """Busca en un rectángulo de coordenadas."""
        self.log.info("Search rectangle: %s %s %s %s EPSG:%s", west, north, east, south, epsg)

        # Buscar en el punto central
        central_x = west + (east - west) / 2.0
        central_y = south + (north - south) / 2.0

        results = []
        for point_dict in self._find_point_coordinate(central_x, central_y, epsg, add_point=False):
            point_dict.update({"west": west, "north": north, "east": east, "south": south})
            results.append(point_dict)

        # Añadir entrada del rectángulo
        results.append(
            {
                "nom": f"Rectangle ({west} {north} {east} {south}) EPSG:{epsg}",
                "idTipus": "",
                "nomTipus": "Rectangle",
                "nomMunicipi": "",
                "nomComarca": "",
                "x": central_x,
                "y": central_y,
                "west": west,
                "north": north,
                "east": east,
                "south": south,
                "epsg": int(epsg),
            }
        )

        return results

    def _find_point_coordinate(self, x, y, epsg, add_point=True):
        """Busca lugares en un punto de coordenadas."""
        self.log.info("Search coordinate: %s %s EPSG:%s", x, y, epsg)

        results = []

        # Buscar direcciones y carreteras cercanas
        results += self._find_point_coordinate_icgc(
            x, y, epsg, layers="address,pk", search_radius_km=0.05, size=1
        )

        # Buscar topónimos
        results += self._find_point_coordinate_icgc(
            x, y, epsg, layers="tops", search_radius_km=None, size=9
        )

        # Añadir entrada del punto
        if add_point:
            municipality = results[0].get("nomMunicipi", "") if results else ""
            county = results[0].get("nomComarca", "") if results else ""

            format_str = "Punt %.2f %.2f EPSG:%s" if x > 100 else "Punt %.8f %.8f EPSG:%s"
            results.append(
                {
                    "nom": format_str % (x, y, epsg),
                    "idTipus": "",
                    "nomTipus": "Coordenada",
                    "nomMunicipi": municipality,
                    "nomComarca": county,
                    "x": x,
                    "y": y,
                    "epsg": epsg,
                }
            )

        return results

    def _find_point_coordinate_icgc(
        self, x, y, epsg, layers="address,tops,pk", search_radius_km=0.05, size=2
    ):
        """Busca en el geocodificador ICGC por coordenadas."""
        # Transformar a WGS84 para la consulta
        query_x, query_y = transform_point(x, y, epsg, self.geoencoder_epsg)

        if query_x is None or query_y is None:
            self.log.error("Coordinate transform error: %s %s EPSG:%s", x, y, epsg)
            raise ValueError(f"Error transformando coordenadas: {x} {y} EPSG:{epsg}")

        try:
            extra_params = {}
            if search_radius_km:
                extra_params["boundary.circle.radius"] = search_radius_km

            res_dict = self.icgc_client.reverse(
                query_y, query_x, layers=layers, size=size, **extra_params
            )
        except Exception as e:
            self.log.exception("ICGC geocoder error: %s", e)
            raise

        return self._parse_icgc_response(res_dict)

    def _find_road(self, road, km):
        """Busca un punto kilométrico de carretera."""
        self.log.info("Search road: %s km %s", road, km)

        try:
            res_dict = self.icgc_client.geocode(f"{road} {km}", layers="pk")
        except Exception as e:
            self.log.exception("Road search error: %s", e)
            raise

        return self._parse_icgc_response(res_dict, default_type="Punt quilomètric")

    def _find_address(self, municipality, street_type, street, number):
        """Busca una dirección."""
        self.log.info("Search address: %s, %s %s %s", municipality, street_type, street, number)

        query = f"Carrer {street} {number}"
        if municipality:
            query += f", {municipality}"

        try:
            res_dict = self.icgc_client.geocode(query, layers="address")
        except Exception as e:
            self.log.exception("Address search error: %s", e)
            raise

        return self._parse_icgc_response(res_dict, default_type="Adreça")

    def _find_placename(self, text):
        """Busca un topónimo."""
        self.log.info("Search placename: %s", text)

        try:
            res_dict = self.icgc_client.geocode(text)
        except Exception as e:
            self.log.exception("Placename search error: %s", e)
            raise

        return self._parse_icgc_response(res_dict)

    # =========================================================================
    # Parsing de respuestas
    # =========================================================================

    def _parse_icgc_response(self, res_dict, default_type=None):
        """Convierte respuesta ICGC a formato estándar."""
        results = []

        for feature in res_dict.get("features", []):
            props = feature.get("properties", {})
            addendum = props.get("addendum", {})
            coords = feature.get("geometry", {}).get("coordinates", [0, 0])

            # Extraer nombre
            nom = addendum.get("scn", {}).get("label") or props.get("etiqueta", "")

            # Extraer tipo
            id_tipus = (
                addendum.get("id_tipus")
                or (1000 if props.get("tipus_via") else None)
                or (1001 if props.get("km") else None)
            )

            nom_tipus = (
                addendum.get("tipus", default_type)
                or props.get("tipus_via", default_type)
                or ("Punt quilomètric" if props.get("km") else default_type)
            )

            results.append(
                {
                    "nom": nom,
                    "idTipus": id_tipus,
                    "nomTipus": nom_tipus,
                    "nomMunicipi": props.get("municipi", ""),
                    "nomComarca": props.get("comarca", ""),
                    "x": coords[0],
                    "y": coords[1],
                    "epsg": self.geoencoder_epsg,
                }
            )

        return results

    # =========================================================================
    # Utilidades
    # =========================================================================

    def is_rectangle(self, results):
        """Comprueba si los resultados son de tipo rectángulo."""
        return len(results) == 1 and results[0].get("west") is not None

    def get_rectangle(self, results):
        """Extrae coordenadas de un resultado de tipo rectángulo.

        Returns:
            tuple: (west, north, east, south, epsg)
        """
        r = results[0]
        return r["west"], r["north"], r["east"], r["south"], r["epsg"]

    def get_point(self, results, index=0):
        """Extrae coordenadas de un resultado.

        Returns:
            tuple: (x, y, epsg)
        """
        r = results[index]
        return r["x"], r["y"], r["epsg"]

    def get_name(self, results, index=0):
        """Extrae el nombre de un resultado."""
        return results[index]["nom"]
