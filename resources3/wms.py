# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with functions to recover data to make WMS connections to ICGC resources

                             -------------------
        begin                : 2019-03-27
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import urllib
import urllib.request
import html
import socket
import re

# Configure internal library logger (Default is dummy logger)
import logging
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())


def get_wms_capabilities(url, version="1.1.1", timeout_seconds=10, retries=3):
    """ Obté el text del capabilities d'un servei WMS
        ---
        Gets capabilities text from WMS service
        """
    capabilities_url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=%s" % (url, version)
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(capabilities_url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            log.warning("WMS resources timeout, retries: %s, URL: %s", retries, capabilities_url)
        except Exception as e:
            retries -= 1
            log.exception("WMS resources error (%s), retries: %s, URL: %s", retries, e, capabilities_url)
    if not response:
        response_data = ""
        log.error("WMS resources error, exhausted retries")      
    else:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    return response_data

def get_wms_capabilities_info(url, reg_ex_filter):
    """ Extreu informació del capabilies d'un WMS via expresions regulars
        ---
        Extract info from WMS capabilities using regular expressions
        """
    response_data = get_wms_capabilities(url)
    data_list = re.findall(reg_ex_filter, response_data)
    log.debug("WMS resources info URL: %s pattern: %s found: %s", url, reg_ex_filter, len(data_list))
    return data_list

def get_full_ortho(url="http://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms",
    reg_ex_filter=r"<Name>(.+)</Name>\s+<Title>(.+)</Title>"):
    """ Obté la URL del servidor d'ortofotos històriques de l'ICGC i la llista de capes disponibles (per rang d'anys)
        Retorna: URL, [(layer_id, layer_name, ortho_type, color_type, year_range)]
        ortho_type: "ortoxpres" | "ortofoto" | "superexpedita"    
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC historical orthophotos server and the list of available layers (by annual ranges)
        Returns: URL, [(layer_id, layer_name, ortho_type, color_type,  year)]
        ortho_type: "ortoxpres" | "ortofoto" | "superexpedita"
        olor_type: "rgb" | "ir" | "bw"
        """
    # Recuperem les capes històriques
    wms_list = get_wms_capabilities_info(url, reg_ex_filter)
    
    # Afegim escala i any com a llista
    wms_ex_list = [(
        layer_id,
        layer_name,
        #("ortofoto" if re.findall(r"ortofoto", layer_id) else "superexpedita" if re.findall(r"ortoxpres.+\d{4}", layer_id) else "ortoxpres"),
        ("ortoxpres" if re.findall(r"provisional", layer_id) else "ortofoto"),
        ("irc" if layer_id.lower().find("infraroig") >= 0 else "rgb" if layer_id.lower().find("color") >= 0 else "bw" if layer_id.lower().find("blanc_i_negre") >= 0 else None ),
        (re.findall(r"(\d{4}(?:\-\d{4})*)", layer_id) + re.findall(r"(\d{4}(?:\-\d{4})*)", layer_name) + [None])[0]
        #) for layer_id, layer_name in wms_list if re.findall("(^(ortoxpres)|^(ortofoto))_((color)|(infraroig)|(blanc_i_negre))", layer_id)]
        ) for layer_id, layer_name in wms_list if re.findall(r"^(ortofoto)_((color)|(infraroig)|(blanc_i_negre))", layer_id) and
            (re.findall(r"(\d{4}(?:\-\d{4})*)", layer_id) + re.findall(r"(\d{4}(?:\-\d{4})*)", layer_name))]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: int(p[4].split("-")[0]), reverse=False)

    return url, wms_ex_list

def get_historic_ortho(url="https://geoserveis.icgc.cat/icc_ortohistorica/wms/service",
    reg_ex_filter=r"<Name>(\w+)</Name>\s+<Title>(.+)</Title>",
    only_full_coverage=True):
    """ Obté la URL del servidor d'ortofotos històriques de l'ICGC i la llista "neta" de capes disponibles (sense dades redundants)
        Retorna: URL, [(layer_id, layer_name, color_type, scale, year)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC historical orthophotos server and the "clean" list of available layers (without redundant data)
            Returns: URL, [(layer_id, layer_name, color_type, scale, year)]
            color_type: "rgb" | "go" | "bw"
        """

    # Recuperem les capes històriques
    wms_list = get_wms_capabilities_info(url, reg_ex_filter)

    # Corregim noms de capa
    wms_list = [(layer_id, layer_name.replace("sèrie B 1:5.000", "sèrie B 1:5.000 (1956-57)"))
        for layer_id, layer_name in wms_list
        if layer_name.lower().find("no disponible") < 0]
    # Afegim escala i any com a llista
    wms_ex_list = [
        (layer_id,
        layer_name,
        [v.replace(".", "") for v in re.findall(r"1:([\d\.]+)", layer_name)],
        re.findall(r"[\s(](\d{4})", layer_name))
        for layer_id, layer_name in wms_list]
    # Afegim tipus de color i corregim tipus de dades de escala i any a enter
    wms_ex_list = [
        (layer_id,
        layer_name,
        ("irc" if layer_name.lower().find("infraroja") >= 0 else "rgb" if year_list and int(year_list[0]) >= 2000 else "bw"),
        int(scale_list[0]) if scale_list else None,
        int(year_list[0]) if year_list else None)
        for layer_id, layer_name, scale_list, year_list in wms_ex_list
        if year_list]

    ## Netegem resolucions redundants
    #wms_names_list = [layer_name for layer_id, layer_name in wms_list]
    #clean_wms_ex_list = [(layer_id, layer_name, color_type, scale, year)
    #    for layer_id, layer_name, color_type, scale, year in wms_ex_list
    #    if scale in (1000, 2500, 5000, 10000)
    #    and (scale != 5000 or layer_name.replace(":5.000", ":2.500") not in wms_names_list)
    #    ]
    if only_full_coverage:
        clean_wms_ex_list = [(layer_id, layer_name, color_type, scale, year)
            for (layer_id, layer_name, color_type, scale, year) in wms_ex_list
            if (color_type != "irc" and scale == 2500 and year >= 2009 and year not in (2010, 2011, 2012, 2013, 2014, 2015, 2016))
            or (color_type != "irc" and scale == 5000 and year in (2012, 2013, 2014, 2015, 2016))
            or (color_type != "irc" and scale == 25000 and year in (1993, 2008))
            or (year < 1960)
            or (color_type == "irc" and scale == 5000 and year >= 2008 and year not in (2010, 2011))
            ##or (color_type == "irc" and scale == 2500 and year in (2016,))
            ]
    else:
        clean_wms_ex_list = wms_ex_list

    # Ordenem per any
    clean_wms_ex_list.sort(key=lambda p: p[4], reverse=True)

    return url, clean_wms_ex_list

def get_lastest_ortoxpres(url="https://geoserveis.icgc.cat/icc_ortoxpres/wms/service",
    reg_ex_filter=r"<Name>(\w+(\d{4})\w*)</Name>\s+<Title>(.+)</Title>"):
    """ Obté la URL del servidor ortoXpres de l'ICGC i la llista capes actuals
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC ortoXpres server and the list of lastest layers
            Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
            color_type: "rgb" | "go" | "bw"
        """

    # Recuperem les capes    
    wms_list = get_wms_capabilities_info(url, reg_ex_filter)

    # Ens quedem només amb les últimes dades de Catalunya
    cat_color_list = sorted([(layer_id, layer_name, "rgb", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya 25cm") >= 0], key=lambda p: p[2], reverse=True)
    cat_infrared_list = sorted([(layer_id, layer_name, "irc", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya infraroig") >= 0], key=lambda p: p[2], reverse=True)
    cat_ndvi_list = sorted([(layer_id, layer_name, "bw", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya ndvi") >= 0], key=lambda p: p[2], reverse=True)
    clean_wms_ex_list = cat_color_list[0:1] + cat_infrared_list[0:1] + cat_ndvi_list[0:1]

    return url, clean_wms_ex_list

def get_superexpedita_ortho(url="https://geoserveis.icgc.cat/servei/catalunya/ortodarp/wms?VERSION=1.3.0",
    reg_ex_filter=r"<Name>((\d{4})_.+_ortofoto_(rgb|irc))</Name>\s*<Title>(.+)</Title>",
    force_layers=False):
    """ Obté la URL del servidor d'ortofoto superexpèdita de l'ICGC i la llista capes actuals
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC ortofoto superexpèdita server and the list of lastest layers
        Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb" | "go" | "bw"
        """
    if not force_layers:
        # Recuperem les capes    
        wms_list = get_wms_capabilities_info(url, reg_ex_filter)
    else:
        # $$$ FAKE! per fer proves i per si està la capa oculta en el servidor ortoDARP
        response_data = """<Name>2019_catalunya_ortofoto_rgb</Name><Title>Ortofoto ràpida Catalunya 2019 RGB</Title>"""
        wms_list = re.findall(reg_ex, response_data)
    
    # Reorganitzem la informació
    wms_ex_list = [(layer_id, layer_name, color_type, date_tag) for layer_id, date_tag, color_type, layer_name in wms_list]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: p[3], reverse=True)

    return url, wms_ex_list

def get_historic_satelite_ortho(url="https://geoserveis.icgc.cat/icgc_sentinel2/wms/service",
    reg_ex_filter=r"<Name>(sen2(\w+)_(\d+))</Name>\s+<Title>(.+)</Title>"):
    """ Obté la URL del servidor d'ortofotos històriques satèl·lt de l'ICGC i la llista capes disponibles
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC historical satelite orthophotos server and the "list of available layers
            Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
            color_type: "rgb" | "go" | "bw"
        """
    # Recuperem les capes històriques
    wms_list = get_wms_capabilities_info(url, reg_ex_filter)

    # Reorganitzem la informació
    wms_ex_list = [(layer_id, layer_name, color_type, date_tag) for layer_id, color_type, date_tag, layer_name in wms_list]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: p[3], reverse=True)

    return url, wms_ex_list