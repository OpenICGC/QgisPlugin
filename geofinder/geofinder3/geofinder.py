# -*- coding: utf-8 -*-
"""
*******************************************************************************
*******************************************************************************
"""

import re
import logging
import math
from importlib import reload
from osgeo import ogr, osr

# Support to SOAP connections
import suds
from suds import null
from suds.client import Client

# Support to Pelias connections
from . import pelias
reload(pelias)
from .pelias import PeliasClient



class GeoFinder(object):
    """ Plugin for accessing open data published by ICGC """

    ###########################################################################
    # Service management
    timeout = 5 # seconds
    geoencoder_epsg = 4326
    cadastral_epsg = 25381

    ## Web Service Cadastre (alternative)
    #cadastral_streets_client = None
    #def get_cadastral_streets_client(self):
    #    if not self.cadastral_streets_client:
    #        # SOAP client configuration
    #        # Available functions: [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #        self.cadastral_streets_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?wsdl") # [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #    return self.cadastral_streets_client

    # Web Service Cadastre. Available functions to call: client.wsdl.services[0].ports[0].methods.keys()
    cadastral_coordinates_client = None
    def get_cadastral_coordinates_client(self):
        if not self.cadastral_coordinates_client:
            # SOAP client configuration
            # Available functions: [Consulta_CPMRC, Consulta_RCCOOR_Distancia, Consulta_RCCOOR]
            self.cadastral_coordinates_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx?wsdl", timeout=self.timeout)
        return self.cadastral_coordinates_client

    # ICGC geocodificador Pelias. Documentació:
    # https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC
    icgc_geoencoder_client = None
    def get_icgc_geoencoder_client(self):
        if not self.icgc_geoencoder_client:
            self.icgc_geoencoder_client = PeliasClient(
                "https://eines.icgc.cat/geocodificador", self.timeout, \
                default_search_call="cerca", default_reverse_call="invers", \
                default_autocomplete_call="autocompletar")
        return self.icgc_geoencoder_client


    def __init__(self, logger=None):
        # Initializer class logger
        if logger:
            self.log = logger
        else:
            # Default is dummy logger
            self.log = logging.getLogger('dummy')
            self.log.addHandler(logging.NullHandler())


    ###########################################################################
    # Search implementation

    def find(self, user_text, default_epsg):
        """ Find the text indicated in the different web services available.
            Show results in a dialog and center the map on the item selected by the user """
        # Find text and return a list of dictionaries with results
        self.log.info("Geoencoder find text: %s", user_text)
        dict_list = self.find_data(user_text, default_epsg)
        self.log.debug("Geoencoder found %d: %s %s", len(dict_list), ", ".join([data_dict['nom'] for data_dict in dict_list[:10]]), "..." if len(dict_list) > 10 else "")
        return dict_list

    def find_data(self, text, default_epsg, find_all=False):
        """ Returns a list of dictionaries with the sites found from the indicated text """

        # Let's see if we pass a ground rectangle
        west, north, east, south, epsg = self.get_rectangle_coordinate(text)
        if west and north and east and south:
            return self.find_rectangle_coordinates(west, north, east, south, epsg if epsg else default_epsg)

        # We detect if we pass a ground coordinate
        x, y, epsg = self.get_point_coordinate(text)
        if x and y:
            return self.find_point_coordinate(x, y, epsg if epsg else default_epsg)

        # Let's see if we pass a road
        road, km = self.get_road(text)
        if road and km:
            return self.find_road(road, km)

        # # Let's see if we pass a crossroads
        # municipality, type1, name1, type2, name2 = self.get_crossing(text)
        # if municipality and name1 and name2:
        #     return self.find_crossing(municipality, type1, name1, type2, name2, find_all)

	    # Let's see if we pass an address
        municipality, type, name, number = self.get_address(text)
        if municipality and name and number:
            return self.find_adress(municipality, type, name, number, find_all)

	    # We detect if we pass a cadastral reference
        cadastral_ref = self.get_cadastral_ref(text)
        if cadastral_ref:
            return self.find_cadastral_ref(cadastral_ref);

        # If you do not meet any of the above, we are looking for a place name
        return self.find_placename(text)

    @classmethod
    def get_rectangle_coordinate(self, text):
        """ Detects a coordinate rectangle from the text
            Accept texts with 4 reals and optionally an epsg code
            For example: 1.0 2.0 3.0 4.0 EPSG:0
                         EPSG:0 1.0 2.0 3.0 4.0
                         1.0 2.0 3.0 4.0
            Return west, north, east, south, epsg """

        # We detect 4 reals (and EPSG code) with a regular expression
        # [EPSG:<int>] <real> <real> <real> <real> [EPSG:<int>]
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s*(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            epsg1, west, north, east, south, epsg2 = found.groups()
            west = float(west.replace(',', '.'))
            north = float(north.replace(',', '.'))
            east = float(east.replace(',', '.'))
            south = float(south.replace(',', '.'))
            epsg = epsg1 if epsg1 else epsg2

        else:
            west, north, east, south, epsg = None, None, None, None, None

        return west, north, east, south, epsg

    @classmethod
    def get_point_coordinate(self, text):
        """ Detects a coordinate from the text
            Accepts texts with 2 reals and optionally an epsg code
            For example: 1.0 2.0 EPSG:0
                         EPSG:0 1.0 2.0 EPSG:0
                         1.0 2.0
            return x, y, epsg """

        # We detect 2 reals (and EPSG code) with a regular expression
        # [EPSG:<int>] <real> <real> [EPSG:<int>]
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s*([+-]?[0-9]*[.,]?[0-9]+)(?:\s+EPSG:(\d+))?\s*$"
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            epsg1, x, y, epsg2 = found.groups()
            epsg = int(epsg1) if epsg1 else int(epsg2) if epsg2 else None
            x = float(x.replace(',', '.'))
            y = float(y.replace(',', '.'))
        else:
            x, y, epsg = None, None, None

        return x, y, epsg

    @classmethod
    def get_road(self, text):
        """ Detects a road from the text
            Accept road / km
            For example: C32 km 10
                         C32, 10
                         C-32, 10
            return road, km """

        # We use regular expression
        # <road> [km|,] <int>
        expression = r'^\s*([A-Za-b]+)-*(\d+)\s*(?:(?:km)|,|\s)\s*(\d+)\s*$'
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            road, road_number, km = found.groups()
            road = f"{road}-{road_number}"
        else:
            road, km = None, None

        return road, km

#     @classmethod
#     def get_crossing(self, text):
#         """ Detects a crossword from the text
#             Accept information of crossroads (municipality, street, street)
#             For example: Barcelona, Muntaner, C/ Aragó
#             return municipality, type1, name1, type2, name2 """

#         # We use regular expression
#         # <municipality>, [street_type] <street>, [street_type] <street>
#         expression = r"\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*"
#         found = re.search(expression, text, re.IGNORECASE)
#         if found:
#             municipality, type1, street1, type2, street2 = found.groups()
#         else:
#             municipality, type1, street1, type2, street2 = None, None, None, None, None

#         return municipality, type1, street1, type2, street2

    @classmethod
    def get_address(self, text):
        """ Detects an adress from the text
            Accept information about the address of a municipality
            For example: Barcelona, Aribau 86
                         Aribau 86, Barcelona
                         Barcelona, C/ Aribau nº 86
                         Barcelona, Avd. Diagonal nº 86
                         Barcelona, C/ Aragó 1-5
            return municipality, type, name, number """

        # We use regular expression
        # [<municipality>, [street_type] <street> [nº] <number> | [street_type] <street> [nº] <number>, <municipality>]
        # To accept accents I use the range: \ u00C0- \ u017F
        expression = r"^\s*(?:([\D\s]+)\s*,)?\s*([\w]+[./])?\s*([\D\s]+)\s+(?:nº)?\s*,*([\d-]+)\s*(?:[,.]\s*([\D\s]+[\D]))?\s*$" # [ciutat,] [C/] <carrer> <numero> [, ciutat]
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            municipality1, type, street, number, municipality2 = found.groups()
            municipality = municipality1 if municipality1 else municipality2
        else:
            municipality, type, street, number = None, None, None, None

        return municipality, type, street, number

    @classmethod
    def get_cadastral_ref(self, text):
        """ Detects a cadastral reference from the text
            Accept a cadastral reference code in the 3 official formats
            For example: 9872023 VH5797S 0001 WX
                 13 077 A 018 00039 0000 FP
                 13077A018000390000FP (also works with the first 14 digits)
            return cadastra_ref """

        # No spaces should occupy 14 or 20 alphanumeric characters
        cleaned_text = text.replace(' ', '')
        if len(cleaned_text) not in (14, 20):
            return None
        # Validate that there are at least 8 digits
        if len([char for char in cleaned_text if char in "0123456789"]) < 8:
            return None
        # Validate that it do not have symbols with a regular expression
        expression = r'(\w+)'
        found = re.search(expression, cleaned_text, re.IGNORECASE)
        if found:
            cadastral_ref = found.groups()[0]
        else:
            cadastral_ref = None

        return cadastral_ref

    def find_rectangle_coordinates(self, west, north, east, south, epsg, add_rect_to_res=True, show_log=True):
        """ Returns a list with a dictionary with the coordinates of the rectangle """

        if show_log:
            self.log.info("Geoencoder find rectangle: %s %s %s %s EPSG:%s", west, north, east, south, epsg)

        # Find central point (exclude last result: "Point x, y")
        central_x = west + (west-east) / 2.0
        central_y = south + (north-south) / 2.0
        dict_list = [{
            'west': float(west),
            'north': float(north),
            'east': float(east),
            'south': float(south),
            **point_dict
            } for point_dict in self.find_point_coordinate(central_x, central_y, epsg, add_point_to_res=False)]
        # If not results, inject an entry with point
        if add_rect_to_res:
            dict_list.append({
                'nom':'Rectangle (%s %s %s %s) EPSG:%s' % (west, north, east, south, epsg),
                'idTipus': u'',
                'nomTipus': u'',
                'nomMunicipi': u'',
                'nomComarca': u'',
                'x': central_x,
                'y': central_y,
                'west': float(west),
                'north': float(north),
                'east': float(east),
                'south': float(south),
                'epsg': int(epsg)
                })
        return dict_list

    def find_point_coordinate(self, x, y, epsg, \
        search_icgc=True, search_cadastral_ref=True, add_point_to_res=True, show_log=True):
        """ Returns a list of dictionaries with the sites found at the indicated point """
        if show_log:
            self.log.info("Geoencoder find coordinate: %s %s EPSG:%s", x, y, epsg)
        dict_list = []

        # Search ICGC geocoder on point
        if search_icgc:
            # First search streets and roads
            dict_list += self.find_point_coordinate_icgc(x, y, epsg, \
                layers="address,pk", search_radious_km=0.05, size=1)
            # Second generic placements
            dict_list += self.find_point_coordinate_icgc(x, y, epsg, \
                layers="tops", search_radious_km=None, size=9)
        
            # Search cadastral ref on point
        if search_cadastral_ref:
            dict_list += self.find_point_coordinate_catastro(x, y, epsg)

        # Add coordinate point entry
        if add_point_to_res:
            municipality = dict_list[0].get('nomMunicipi', "") if dict_list else ""
            county = dict_list[0].get('nomComarca', "") if dict_list else ""
            dict_list.append({
                'nom': ("Punt %.2f %.2f EPSG:%s" if x > 100 \
                    else "Punt %.8f %.8f EPSG:%s") % ( \
                    x, y, epsg),
                'idTipus': '',
                'nomTipus': 'Coordenada',
                'nomMunicipi': municipality,
                'nomComarca': county,
                'x': x,
                'y': y,
                'epsg': epsg
                })
        return dict_list

    def find_point_coordinate_icgc(self, x, y, epsg, \
        layers="address,tops,pk", search_radious_km=0.05, size=2):
        """ Returns a list of dictionaries with the sites found at the indicated point """

        # We convert the coordinates to geoencoder EPSG to do the query
        nom = "Point: %s %s (EPSG:%s)" % (x, y, epsg),
        query_x, query_y = self.transform_point(x, y, epsg, self.geoencoder_epsg)
        if query_x is None or query_y is None:
            self.log.exception("Coordinates error: %s %s EPSG:%s", x, y, epsg)
            raise(Exception("Coordinates error: %s %s EPSG:%s" % (x, y, epsg)))

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_icgc_geoencoder_client().url)
        try:
            extra_params_dict = {"boundary.circle.radius": search_radious_km}
            res_dict = self.get_icgc_geoencoder_client().reverse(query_y, query_x,
                layers=layers, size=size, **extra_params_dict)
        except Exception as e:
            self.log.exception("Geoencoder error: %s Request: %s", e, self.get_icgc_geoencoder_client().last_sent())
            raise e
        self.log.debug("Geoencoder Request: %s", self.get_icgc_geoencoder_client().last_sent())

        # We convert the result to a unique format
        dict_list = self.get_icgc_generalized_response(res_dict)
        return dict_list

    def find_point_coordinate_catastro(self, x, y, epsg):
        """ Returns a list of dictionaries with cadastral reference at the indicated point """

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_cadastral_coordinates_client().wsdl.url)
        try:
            res_dict = self.get_cadastral_coordinates_client().service.Consulta_RCCOOR(
                CoorX = x,
                CoorY = y,
                SRS = "EPSG:%s" % epsg)
        except Exception as e:
            self.log.exception("Geoencoder error: %s SOAP Request: %s", e, self.get_cadastral_coordinates_client().last_sent())
            raise e
        if res_dict['control']['cuerr'] != '0':
            error_text = str(res_dict['lerr']['err']['des'])
            self.log.exception("Geoencoder error: %s SOAP Request: %s", error_text, self.get_cadastral_coordinates_client().last_sent())
            return []

        # We evaluate the result
        dict_list = self.get_catastro_generalized_response(res_dict)
        return dict_list

    def transform_point(self, x, y, source_epsg, destination_epsg):
        """ Converteix un punt d'un EPSG a un altre """
        if str(source_epsg) == str(destination_epsg) and str(destination_epsg) != "4326":
            return x, y
        # Definim els sistemes de coordenades a utilitzar
        source_crs = osr.SpatialReference()
        source_crs.ImportFromEPSG(int(source_epsg))
        destination_crs = osr.SpatialReference()
        destination_crs.ImportFromEPSG(int(destination_epsg))
        # EN GDAL 3 al convertir una coordenada a 4326 gira x<->y per evitar-ho canviar WGS84 per CRS84!!
        # La sintaxis "normal" de 4326 és lat, lon, primer la y i després la x
        # per tant els paràmetres venen girats x=lat i y=lon. Per arreglar-ho convertim la sortida
        # a CRS84 en format x=lon, y=lat
        if destination_epsg == 4326:
            destination_crs.SetWellKnownGeogCS("CRS84")
        # Convertim les coordenades
        ct = osr.CoordinateTransformation(source_crs, destination_crs)
        destination_x, destination_y, _h = ct.TransformPoint(x, y)
        destination_x = None if math.isinf(destination_x) else destination_x
        destination_y = None if math.isinf(destination_y) else destination_y
        return destination_x, destination_y

    def find_road(self, road, km):
        """ Returns a list of dictionaries with the roads found with the indicated nomenclature """

        self.log.info("Geoencoder find road: %s %s", road, km)

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_icgc_geoencoder_client().url)
        try:
            res_dict = self.get_icgc_geoencoder_client().geocode(f"{road} {km}", layers="pk")
        except Exception as e:
            self.log.exception("Geoencoder error: %s SOAP Request: %s", e, self.get_icgc_geoencoder_client().last_sent())
            raise e
        self.log.debug("Geoencoder Request: %s", self.get_icgc_geoencoder_client().last_sent())

        # We convert the result to a unique format
        return self.get_icgc_generalized_response(res_dict, "Punt quilomètric")

    # def find_crossing(self, municipality, type1, street1, type2, street2, find_all):
    #     """ Returns a list of dictionaries with crossings found with the indicated nomenclature """

    #     self.log.info("Geoencoder find crossing %s, %s %s / %s %s", municipality, type1, street1, type2, street2)

    #     # We execute the query
    #     self.log.debug("Geoencoder URL: %s", self.get_icgc_geoencoder_client().url)
    #     try:
    #         res_dict = self.get_icgc_geoencoder_client().service.localitzaCruilla(
    #             Poblacio = municipality,
    #             Vies = [{'Tipus':type1, 'Nom':street1},
    #             {'Tipus':type2, 'Nom':street2}],
    #             TrobaTots = ("SI" if find_all else "NO"))
    #     except Exception as e:
    #         self.log.exception("Geoencoder error: %s SOAP Request: %s", e, self.get_icgc_geoencoder_client().last_sent())
    #         raise e
    #
    #     # We convert the result to a unique format
    #     return self.get_icgc_generalized_response(res_dict)

    def find_adress(self, municipality, type, street, number, find_all):
        """ Returns a list of dictionaries with the addresses found with the indicated nomenclature """

        self.log.info("Geoencoder find adress: %s, %s %s %s", municipality, type, street, number)

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_icgc_geoencoder_client().url)
        try:
            res_dict = self.get_icgc_geoencoder_client().geocode(
                f"Carrer {street} {number}, {municipality}", layers="address")
        except Exception as e:
            self.log.exception("Geoencoder error: %s SOAP Request: %s", e, self.get_icgc_geoencoder_client().last_sent())
            raise e
        self.log.debug("Geoencoder Request: %s", self.get_icgc_geoencoder_client().last_sent())

        # We convert the result to a unique format
        return self.get_icgc_generalized_response(res_dict, "Adreça")

    def find_cadastral_ref(self, cadastral_ref):
        """ Returns a list with a dictionary with the indicated cadastral reference """

        self.log.info("Geoencoder find cadastral ref: %s", cadastral_ref)
        # Examples of cadastral reference:
        # 9872023 VH5797S 0001 WX
        # 13 077 A 018 00039 0000 FP
        # 13077A018000390000FP

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_cadastral_coordinates_client().wsdl.url)
        clean_cadastra_ref = cadastral_ref.replace(' ', '')[:14]
        try:
            res_dict = self.get_cadastral_coordinates_client().service.Consulta_CPMRC(
                Provincia = "",
                Municipio = "",
                SRS = "EPSG:%s" % self.cadastral_epsg,
                RefCat = clean_cadastra_ref) ##Provincia, municipio, srs, ref catastral
        except Exception as e:
            self.log.exception("Geoencoder error: %s SOAP Request: %s", e, self.get_cadastral_coordinates_client().last_sent())
            raise e
        if res_dict['control']['cuerr'] != '0': # Error code
            raise Exception(str(res_dict['lerr']['err']['des'])) # Error text

        # We evaluate the result
        dict_list = self.get_catastro_generalized_response(res_dict)
        return dict_list

    def get_catastro_generalized_response(self, res_dict):
        """ Returns standard response for Catastro geocoder queries """
        dict_list = []

        coord_dict_list = res_dict['coordenadas']['coord'] if type(res_dict['coordenadas']['coord']) is list else [res_dict['coordenadas']['coord']]
        for coord_dict in coord_dict_list:
            # If we have found a match int the response, we separate the street, municipality and district
            adress = str(coord_dict['ldt'])
            expression = r"([\D]+ \d+) ([\D]+) \(([\D]+)\)"
            found = re.search(expression, adress, re.IGNORECASE)
            if not found:
                expression = r"(.+)\.([\D]+) \(([\D]+)\)"
                found = re.search(expression, adress, re.IGNORECASE)
            if not found:
                expression = r"(.+)()\(([\D]+)\)"
                found = re.search(expression, adress, re.IGNORECASE)
            if found:
                street, municipality1, municipality3 = found.groups()
                municipality1 = municipality1[0:1].upper() + municipality1[1:].lower() # Municipi
                municipality2 = '' # Comarca (no la retorna)
                municipality3 = municipality3[0:1].upper() + municipality3[1:].lower() # Província
            else:
                street = adress
                municipality1 = ''
                municipality2 = ''
                municipality3 = ''

            # We convert the result to a unique format
            dict_list.append({
                'nom': "%s%s (%s)" % (coord_dict['pc']['pc1'], coord_dict['pc']['pc2'], street),
                'idTipus': 1002, # CODI 1002 PROPI DE GEOFINDER!
                'nomTipus': 'Ref. cadastral',
                'nomMunicipi': municipality1,
                'nomComarca': municipality2,
                'nomProvincia': municipality3,
                'x': float(coord_dict['geo']['xcen']),
                'y': float(coord_dict['geo']['ycen']),
                'epsg': int(coord_dict['geo']['srs'].replace('EPSG:', ''))
                })

        return dict_list

    def find_placename(self, text):
        """ Returns a list of dictionaries with the toponyms found with the indicated nomenclature """

        self.log.info("Geoencoder find placement: %s", text)

        # We execute the query
        self.log.debug("Geoencoder URL: %s", self.get_icgc_geoencoder_client().url)
        try:
            res_dict = self.get_icgc_geoencoder_client().geocode(text)
        except Exception as e:
            self.log.exception("Geoencoder error: %s Request: %s", e, self.get_icgc_geoencoder_client().last_sent())
            raise e
        self.log.debug("Geoencoder Request: %s", self.get_icgc_geoencoder_client().last_sent())

        # We convert the result to a unique format
        return self.get_icgc_generalized_response(res_dict)

    def get_icgc_generalized_response(self, res_dict, default_type=None):
        """ Returns standard response for ICGC geocoder queries """
        dict_list = [{
            'nom': feature_dict['properties'].get('addendum', {}).get('scn', {}).get('label', None)
                or feature_dict['properties']['etiqueta'],
            'idTipus': feature_dict['properties'].get('addendum',{}).get('id_tipus', None)
                or (1000 if feature_dict['properties'].get("tipus_via", None) else None) # CODI 1000 i 1001 PROPI DE GEOFINDER!
                or (1001 if feature_dict['properties'].get("km", None) else None), # CODI 1001 PROPI DE GEOFINDER!
            'nomTipus': feature_dict['properties'].get('addendum', {}).get('tipus', default_type)
                or feature_dict['properties'].get("tipus_via", default_type)
                or ("Punt quilomètric" if feature_dict['properties'].get("km", None) else default_type),
            'nomMunicipi': feature_dict['properties'].get('municipi', None),
            'nomComarca': feature_dict['properties'].get('comarca', None),
            'x': feature_dict['geometry']['coordinates'][0],
            'y': feature_dict['geometry']['coordinates'][1],
            'epsg': self.geoencoder_epsg
            } for feature_dict in res_dict["features"]]
        return dict_list

    def is_rectangle(self, dict_list):
        """ Check if dict_list is of rectangle type """
        return len(dict_list) == 1 and dict_list[0].get("west", None)

    def get_rectangle(self, dict_list):
        """ Returns rectangle coordinates of dict_list type rectangle.
            return west, north, east, south, epsg
            """
        west = dict_list[0]['west']
        north = dict_list[0]['north']
        east = dict_list[0]['east']
        south = dict_list[0]['south']
        epsg = dict_list[0]['epsg']

        return west, north, east, south, epsg

    def get_point(self, dict_list, selection):
        """ Returns point coordinates of selected dict_list item.
            return x, y, epsg
            """
        x = dict_list[selection]['x']
        y = dict_list[selection]['y']
        epsg = dict_list[selection]['epsg']

        return x, y, epsg

    def get_name(self, dict_list, selection):
        """ Returns name of selected dict_list item.
            return string
            """
        name = dict_list[selection]['nom']

        return name