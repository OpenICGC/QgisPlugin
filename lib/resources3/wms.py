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


def get_full_ortho(timeout_seconds=5, retries=3):
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
    # Consultem el Capabilities del servidor WMS d'ortofotos històriques
    url_base = "http://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms"
    url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1" % url_base
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            #print("retries", retries)
        except:
            retries -= 1
            #print("retries", retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""

    # Recuperem les capes històriques
    reg_ex = "<Name>(.+)</Name>\s+<Title>(.+)</Title>"
    wms_list = re.findall(reg_ex, response_data)
    # Afegim escala i any com a llista
    wms_ex_list = [(
        layer_id,
        layer_name,
        ("ortofoto" if re.findall("ortofoto", layer_id) else "superexpedita" if re.findall("ortoxpres.+\d{4}", layer_id) else "ortoxpres"),
        ("irc" if layer_id.lower().find("infraroig") >= 0 else "rgb" if layer_id.lower().find("color") >= 0 else "bw" if layer_id.lower().find("blanc_i_negre") >= 0 else None ),
        (re.findall("(\d{4}(?:\-\d{4})*)", layer_id) + re.findall("(\d{4}(?:\-\d{4})*)", layer_name) + [None])[0]
        ) for layer_id, layer_name in wms_list if re.findall("(^(ortoxpres)|^(ortofoto))_((color)|(infraroig)|(blanc_i_negre))", layer_id)]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: int(p[4].split("-")[0]), reverse=False)

    return url_base, wms_ex_list

def get_historic_ortho(only_full_coverage=True, timeout_seconds=5, retries=3):
    """ Obté la URL del servidor d'ortofotos històriques de l'ICGC i la llista "neta" de capes disponibles (sense dades redundants)
        Retorna: URL, [(layer_id, layer_name, color_type, scale, year)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC historical orthophotos server and the "clean" list of available layers (without redundant data)
            Returns: URL, [(layer_id, layer_name, color_type, scale, year)]
            color_type: "rgb" | "go" | "bw"
        """
    # Consultem el Capabilities del servidor WMS d'ortofotos històriques
    url_base = "https://geoserveis.icgc.cat/icc_ortohistorica/wms/service"
    url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1" % url_base
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            #print("retries", retries)
        except:
            retries -= 1
            #print("retries", retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""

    # Recuperem les capes històriques
    reg_ex = "<Name>(\w+)</Name>\s+<Title>(.+)</Title>"
    wms_list = re.findall(reg_ex, response_data)

    # Corregim noms de capa
    wms_list = [(layer_id, layer_name.replace("sèrie B 1:5.000", "sèrie B 1:5.000 (1956-57)"))
        for layer_id, layer_name in wms_list
        if layer_name.lower().find("no disponible") < 0]
    # Afegim escala i any com a llista
    wms_ex_list = [
        (layer_id,
        layer_name,
        [v.replace(".", "") for v in re.findall("1:([\d\.]+)", layer_name)],
        re.findall("[\s(](\d{4})", layer_name))
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

    return url_base, clean_wms_ex_list

def get_lastest_ortoxpres(timeout_seconds=5, retries=3):
    """ Obté la URL del servidor ortoXpres de l'ICGC i la llista capes actuals
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC ortoXpres server and the list of lastest layers
            Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
            color_type: "rgb" | "go" | "bw"
        """
    # Consultem el Capabilities del servidor WMS d'ortofotos satèl·lit històriques
    url_base = "https://geoserveis.icgc.cat/icc_ortoxpres/wms/service"
    url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1" % url_base
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            #print("retries", retries)
        except:
            retries -= 1
            #print("retries", retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('latin1')
    else:
        response_data = ""

    # Recuperem les capes
    reg_ex = "<Name>(\w+(\d{4})\w*)</Name>\s+<Title>(.+)</Title>"
    wms_list = re.findall(reg_ex, response_data)

    # Ens quedem només amb les últimes dades de Catalunya
    cat_color_list = sorted([(layer_id, layer_name, "rgb", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya 25cm") >= 0], key=lambda p: p[2], reverse=True)
    cat_infrared_list = sorted([(layer_id, layer_name, "irc", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya infraroig") >= 0], key=lambda p: p[2], reverse=True)
    cat_ndvi_list = sorted([(layer_id, layer_name, "bw", year) for layer_id, year, layer_name in wms_list if layer_name.lower().find("catalunya ndvi") >= 0], key=lambda p: p[2], reverse=True)
    clean_wms_ex_list = cat_color_list[0:1] + cat_infrared_list[0:1] + cat_ndvi_list[0:1]

    return url_base, clean_wms_ex_list

def get_superexpedita_ortho(timeout_seconds=5, retries=3, force_layers=False):
    """ Obté la URL del servidor d'ortofoto superexpèdita de l'ICGC i la llista capes actuals
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC ortofoto superexpèdita server and the list of lastest layers
        Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb" | "go" | "bw"
        """
    # Consultem el Capabilities del servidor WMS d'ortofotos satèl·lit històriques
    url_base = "https://geoserveis.icgc.cat/servei/catalunya/ortodarp/wms?VERSION=1.3.0"
    #url_base = "http://localhost:5000/fcgi-bin/fortodarp.py?VERSION=1.3.0"
    #url_base = "http://localhost:5000/cgi-bin/ortodarp.py?VERSION=1.3.0"
    if not force_layers:
        url = "%s?REQUEST=GetCapabilities&SERVICE=WMS" % url_base.split("?")[0]
        while retries:
            try:
                response = None
                response = urllib.request.urlopen(url, timeout=timeout_seconds)
                retries = 0
            except socket.timeout:
                retries -= 1
                #print("retries", retries)
            except:
                retries -= 1
                #print("retries", retries)
        if response:
            response_data = response.read()
            response_data = html.unescape(response_data.decode())
        else:
            response_data = ""
    else:
        # $$$ FAKE! per fer proves i per si està la capa oculta en el servidor ortoDARP
        response_data = """<Name>2019_catalunya_ortofoto_rgb</Name><Title>Ortofoto ràpida Catalunya 2019 RGB</Title>"""

    # Recuperem les capes tipus: se_2019_catalunya_rgb
    reg_ex = "<Name>((\d{4})_.+_ortofoto_(rgb|irc))</Name>\s*<Title>(.+)</Title>"
    wms_list = re.findall(reg_ex, response_data)

    # Reorganitzem la informació
    wms_ex_list = [(layer_id, layer_name, color_type, date_tag) for layer_id, date_tag, color_type, layer_name in wms_list]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: p[3], reverse=True)

    return url_base, wms_ex_list

def get_historic_satelite_ortho(timeout_seconds=5, retries=3):
    """ Obté la URL del servidor d'ortofotos històriques satèl·lt de l'ICGC i la llista capes disponibles
        Retorna: URL, [(layer_id, layer_name, color_type, date_tag)]
        color_type: "rgb"|"ir"|"bw"
        ---
        Gets the URL of the ICGC historical satelite orthophotos server and the "list of available layers
            Returns: URL, [(layer_id, layer_name, color_type, date_tag)]
            color_type: "rgb" | "go" | "bw"
        """
    # Consultem el Capabilities del servidor WMS d'ortofotos satèl·lit històriques
    url_base = "https://geoserveis.icgc.cat/icgc_sentinel2/wms/service"
    url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1" % url_base
    while retries:
        try:
            response = None
            response = urllib.request.urlopen(url, timeout=timeout_seconds)
            retries = 0
        except socket.timeout:
            retries -= 1
            #print("retries", retries)
        except:
            retries -= 1
            #print("retries", retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""

    # Recuperem les capes històriques
    reg_ex = "<Name>(sen2(\w+)_(\d+))</Name>\s+<Title>(.+)</Title>"
    wms_list = re.findall(reg_ex, response_data)

    # Reorganitzem la informació
    wms_ex_list = [(layer_id, layer_name, color_type, date_tag) for layer_id, color_type, date_tag, layer_name in wms_list]

    # Ordenem per any
    wms_ex_list.sort(key=lambda p: p[3], reverse=True)

    return url_base, wms_ex_list