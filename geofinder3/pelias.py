# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import json
import requests


class PeliasClient:
    """ Pelias servers generic client class
        Doc: https://eines.icgc.cat/geocodificador/api-docs/#/geocodificador/cercappp
             https://www.icgc.cat/es/Herramientas-y-visores/Herramientas/Geocodificador-ICGC
        """
    def __init__(self, url, default_timeout=5, \
        default_search_call="/v1/search", default_reverse_call="/v1/reverse", \
        default_autocomplete_call="/v1/autocomplete"):
        """ Configure server connection and calls """
        self.url = url + ("" if url.endswith("/") else "/")
        self.timeout = default_timeout # Segons
        self.search_call = default_search_call
        self.reverse_call = default_reverse_call
        self.autocomplete_call = default_autocomplete_call
        self.last_request = None

    def geocode(self, query_string, **extra_params_dict):
        """ Returns dict location of query string. Extra params:
            layers=v1,v2...vn
            size=n """
        params_dict = {"text": query_string}
        params_dict.update(extra_params_dict)
        json_data = self.call(self.search_call, **params_dict)
        return json_data

    def autocomplete(self, query_string, **extra_params_dict):
        """ Returns dict location of query string. Extra params:
            layers=v1,v2...vn
            size=n """
        params_dict = {"text": query_string}
        params_dict.update(extra_params_dict)
        json_data = self.call(self.autocomplete_call, **params_dict)
        return json_data

    def reverse(self, lat, lon, **extra_params_dict):
        """ Return dict with place names on coordinates.
            layers=v1,v2...vn
            size=n """
        params_dict = {"lon": lon, "lat": lat}
        params_dict.update(extra_params_dict)
        json_data = self.call(self.reverse_call, value_encode=False, **params_dict)
        return json_data

    def call(self, call_name, value_encode=True, **params_dict):
        """ Execute any Pelias's function with specified parameters """
        # Fem la petició al servidor amb tots els paràmetres indicats
        # Atenció en alguns equips dóna error de certificat al fer la consulta!!
        # ... se li pot especificar que no validi el certificat del servidor amb verify=False
        self.last_request = self.url + call_name + "?" + \
            "&".join([f"{key}={quote_plus(value) if value_encode else value}" \
            for key, value in params_dict.items() if value is not None])
        try:
            response_data = requests.get(self.last_request, verify=True, timeout=self.timeout).text
            response_json = json.loads(response_data)
        except Exception as e:
            response_json = None
            raise e
        return response_json

    # def validate_location(self, json):
    #     """ Validate existence of location data in json """
    #     try:
    #         _coordinates = json['features'][0]['geometry']['coordinates']
    #     except IndexError:
    #         json = None
    #         raise Exception('could not parse location text')
    #     return json

    def last_sent(self):
        """ Returns last query executed """
        return self.last_request
