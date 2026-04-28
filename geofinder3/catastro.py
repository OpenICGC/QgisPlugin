# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import json
import requests


class CatastroClient:
    """ Catastro client for rest services class
        Doc: https://www.catastro.hacienda.gob.es/ws/Webservices_Libres.pdf
        """
    def __init__(self, url="http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/", timeout=5):
        """ Configure server connection and calls """
        self.url = url + ("" if url.endswith("/") else "/")
        self.timeout = timeout # Segons
        self.last_request = None

    def Consulta_CPMRC(self, ref_cad, **extra_params_dict):
        """ Returns dict location of refCad.
            Extra params:
                Provincia={PROVINCIA}
                Municipio={MUNICIPIO}
                SRS={SRS}
            Raw query example:
                http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_CPMRC?RefCat=9503802DF2890D
            """
        params_dict = {"RefCat": ref_cad, "SRS": "EPSG:4326"}
        params_dict.update(extra_params_dict)
        json_data = self.call("COVCCoordenadas.svc/json/Consulta_CPMRC", **params_dict)
        return json_data["Consulta_CPMRCResult"] if json_data else json_data

    def Consulta_RCCOOR(self, x, y, **extra_params_dict):
        """ Return dict with refCad on coordinates.
            Extra params:
                SRS={SRS}
            Raw query example:
                http://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_RCCOOR?CoorX=2.155722&CoorY=41.370020&SRS=EPSG:4326
            """
        params_dict = {"CoorX": x, "CoorY": y, "SRS": "EPSG:4326"}
        params_dict.update(extra_params_dict)
        json_data = self.call("COVCCoordenadas.svc/json/Consulta_RCCOOR", value_encode=False, **params_dict)
        return json_data["Consulta_RCCOORResult"] if json_data else json_data

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

    def last_sent(self):
        """ Returns last query executed """
        return self.last_request
