# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with functions to recover data to make WMS connections to ICGC resources

                             -------------------
        begin                : 2023-05-24
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import urllib
import urllib.request
import html
import socket
import re
import os

# Configure internal library logger (Default is dummy logger)
import logging
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())


styles_path = os.path.join(os.path.dirname(__file__), "symbols")
style_dict = {
    "capmunicipi": os.path.join(styles_path, "divisions-administratives-caps-municipi-ref.qml"), 
    "capcomarca": os.path.join(styles_path, "divisions-administratives-caps-municipi-ref.qml"), 
    "municipis": os.path.join(styles_path, "divisions-administratives-municipis-ref.qml"), 
    "comarques": os.path.join(styles_path, "divisions-administratives-comarques-ref.qml"), 
    "vegueries": os.path.join(styles_path, "divisions-administratives-vegueries-ref.qml"), 
    "provincies": os.path.join(styles_path, "divisions-administratives-provincies-ref.qml"), 
    "catalunya": os.path.join(styles_path, "divisions-administratives-catalunya-ref.qml"), 
    }
order_dict = {
    "capmunicipi": 1,
    "capcomarca": 2,
    "municipis": 3,
    "comarques": 4,
    "vegueries": 5,
    "provincies": 6,
    "catalunya": 7
    }

def get_wfs_capabilities(url, version="2.0.0", timeout_seconds=10, retries=3):
    """ Obté el text del capabilities d'un servei WFS
        ---
        Gets capabilities text from WFS service
        """
    capabilities_url = "%s?REQUEST=GetCapabilities&SERVICE=WFS&VERSION=%s" % (url, version)
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(capabilities_url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            log.warning("WFS resources timeout, retries: %s, URL: %s", retries, capabilities_url)
        except Exception as e:
            retries -= 1
            log.exception("WFS resources error (%s), retries: %s, URL: %s", retries, e, capabilities_url)
    if not response:
        response_data = ""
        log.error("WFS resources error, exhausted retries")      
    else:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    return response_data

def get_wfs_capabilities_info(url, reg_ex_filter):
    """ Extreu informació del capabilies d'un WFS via expresions regulars
        ---
        Extract info from WFS capabilities using regular expressions
        """
    response_data = get_wfs_capabilities(url)
    data_list = re.findall(reg_ex_filter, response_data)
    log.debug("WFS resources info URL: %s pattern: %s found: %s", url, reg_ex_filter, len(data_list))
    return data_list

def get_delimitations(url="https://geoserveis.icgc.cat/servei/catalunya/divisions-administratives/wfs",
        reg_ex_filter=r"<wfs:Name>(.+)</wfs:Name>"):
    """ Obté la URL del servidor de delimitacions de l'ICGC i la llista de capes disponibles
        Retorna: URL, [(product_name, [(scale, layer_id), style_file])]
        ---
        Gets the URL of the ICGC delimitations server and the list of available layers
        Returns: URL, [(product_name, [(scale, layer_id)], style_file)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles (canvio "caps-municipi" per parsejar-lo més fàcil...)
    delimitations_id_list = get_wfs_capabilities_info(url, reg_ex_filter)
    # Obtenim un nom de producte simplificat i separem la informació de la escala
    delimitations_info_list = [(
        layer_id.split("_")[-2 if layer_id.split("_")[-1].isdigit() else -1], \
        int(layer_id.split("_")[-1]) if layer_id.split("_")[-1].isdigit() else None,
        layer_id \
        ) \
        for layer_id in delimitations_id_list]           
    # Agrupem les escales de cada producte
    delimitations_dict = {}
    for product_name, scale, layer_id in delimitations_info_list:
        delimitations_dict[product_name] = delimitations_dict.get(product_name, []) + [(scale, layer_id)]
    # Ordenem els productes
    delimitations_list = sorted(list(delimitations_dict.items()), key=lambda d:order_dict.get(d[0], 10))
    # Ordenem les escales dins de cada producte i afegim arxiu d'estil
    delimitations_list = [(product_name, sorted(scale_list, key=lambda s:s[0]), style_dict.get(product_name, None)) \
        for product_name, scale_list in delimitations_list]
    # retornem les dades
    return url, delimitations_list
