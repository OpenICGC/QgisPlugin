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
import ssl
import re
import os


styles_list = [ # (regex_file_pattern, qml_style)
    (r".+-caps-municipi-.+", "divisions-administratives-caps-municipi-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    (r".+-municipis-.+", "divisions-administratives-municipis-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    (r".+-comarques-.+", "divisions-administratives-comarques-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    (r".+-vegueries-.+", "divisions-administratives-vegueries-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    (r".+-provincies-.+", "divisions-administratives-provincies-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    (r".+-catalunya-.+", "divisions-administratives-catalunya-ref.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    ]

def get_http_dir(url, timeout_seconds=0.5, retries=3):
    """ Obté el codi HTML d'una pàgina web amb fitxers
        Retorna: string
        ---
        Gets HTML code of web page with files
        Returns: string
        """
    # Codi per ignorar errors de certificats...
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    remaining_retries = retries
    while remaining_retries:
        try:
            response = None
            response = urllib.request.urlopen(url, timeout=timeout_seconds, context=context)
            remaining_retries = 0
        except socket.timeout:
            remaining_retries -= 1
            #print("retries", remaining_retries)
        except:
            remaining_retries -= 1
            #print("retries", remaining_retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""
    return response_data

def get_http_files(url, file_regex_pattern, replace_list=[]):
    """ Obté una llista de fitxer d'una pàgina web a partir d'una expressió regular
        Retorna: llista de resultats de la expressió regular
        ---
        Gets file list of web page from a regular expression
        Returns: list of regex matches
        """
    # LLegeixo les dades HTML del directori HTTP
    response_data = get_http_dir(url)
    if not response_data:
        return []
    # Reemplacem els textos indicats
    for search, replace in replace_list:
        response_data = response_data.replace(search, replace)
    # Obtinc la informació de fitxers a partri de la regex
    http_file_regex_pattern = r'<A HREF="[\/\w-]*%s">' % file_regex_pattern
    files_list = re.findall(http_file_regex_pattern, response_data)
    return files_list

def get_dtms(dtm_urlbase_list=[
    ("2m 2008-2011", "https://datacloud.icgc.cat/datacloud/met2_ETRS89/mosaic"),
    ("5m 2020", "https://datacloud.icgc.cat/datacloud/met5_ETRS89/mosaic")],
    dtm_http_file_pattern=r'(met\w+\.\w+)'):
    """ Obté les URLs dels arxius de MET disponibles de l'ICGC
        Retorna: [(dtm_name, dtm_url)]
        ---
        Gets ICGC's available DTM urls
        Returns: [(dtm_name, dtm_url)]
        """
    dtm_list = []
    for dtm_name, dtm_urlbase in dtm_urlbase_list:
        # Llegeixo la pàgina HTTP que informa dels arxius disponibles
        # Cerquem links a arxius MET i ens quedem el més recent
        files_list = get_http_files(dtm_urlbase, dtm_http_file_pattern)
        if not files_list:
            continue

        dtm_file = sorted(files_list, reverse=True)[0]
        dtm_url = "%s/%s" % (dtm_urlbase, dtm_file)
        dtm_list.append((dtm_name, dtm_url))

    return dtm_list

def get_sheets(sheets_urlbase="https://datacloud.icgc.cat/datacloud/talls_ETRS89/json_unzip", 
    sheet_http_file_pattern=r'(tall(\w+)etrs\w+\.json)'):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    # Cerquem links a arxius json
    sheets_info_list = get_http_files(sheets_urlbase, sheet_http_file_pattern)
    if not sheets_info_list:
        return []
    sheets_info_list.sort(key=lambda sheet_infoi:int(sheet_infoi[1][:-1]) if sheet_infoi[1][:-1].isdigit() and sheet_infoi[1][-1] == "m" else 9999999)

    # Ajustem els noms i generem les urls completes
    sheets_list = []
    for sheet_file, sheet_name in sheets_info_list:
        if sheet_name[:-1].isdigit() and sheet_name[-1] == 'm':
            sheet_name = sheet_name.replace("m", ".000")
        sheet_url = "%s/%s" % (sheets_urlbase, sheet_file)
        sheets_list.append((sheet_name, sheet_url))

    return sheets_list

def get_delimitations_old(delimitations_urlbase="https://datacloud.icgc.cat/datacloud/bm5m_ETRS89/json_unzip",
    delimitation_http_file_pattern=r'(bm5mv\d+js\dt[cp][cmp][\d_]+\.json)',
    delimitation_type_patterns_list=[("Caps de Municipi", "bm5mv\d+js\dtcm[\d_]+\.json"), ("Municipis", "bm5mv\d+js\dtpm[\d_]+\.json"),
        ("Comarques", "bm5mv\d+js\dtpc[\d_]+\.json"), ("Províncies", "bm5mv\d+js\dtpp[\d_]+\.json")]):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    delimitations_info_list = get_http_files(delimitations_urlbase, delimitation_http_file_pattern)
    
    # Cerquem links a arxius json
    delimitations_list = []
    for delimitation_name, delimitation_type_pattern in delimitation_type_patterns_list:
        for delimitation_file in delimitations_info_list:
            # Cerquem el fitxer que quadri amb cada plantilla de tipus
            if re.match(delimitation_type_pattern, delimitation_file):
                delimitation_url = "%s/%s" % (delimitations_urlbase, delimitation_file)
                delimitations_list.append((delimitation_name, delimitation_url))
                break

    return delimitations_list

def get_delimitations(delimitations_urlbase="https://datacloud.icgc.cat/datacloud/divisions-administratives/json_unzip",
    delimitation_http_file_pattern=r'(divisions-administratives-v\d+r\d+\-(\D+)(?:-(\d+))*-(\d{8})\.json)'):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles (canvio "caps-municipi" per parsejar-lo més fàcil...)
    delimitations_info_list = get_http_files(delimitations_urlbase, delimitation_http_file_pattern)
    delimitations_info_list.sort(key=lambda d:d[0], reverse=True)    
    # Cerquem links a arxius json (només ens quedem els de la data més nova)
    delimitations_dict = {}
    last_name = None
    last_scale = None
    for filename, name, scale, date in delimitations_info_list:
        # Ens quedem el primer (el de data més nova -> sort reverse)
        if last_name != name or last_scale != scale:
            delimitations_dict[name] = delimitations_dict.get(name, []) + [(int(scale) if scale else None, "%s/%s" % (delimitations_urlbase, filename))]
        last_name = name
        last_scale = scale
    
    # Ordenem els arxius...
    order_dict = {
        "caps-municipi": 1,
        "municipis": 2,
        "comarques": 3,
        "vegueries": 4,
        "provincies": 5,
        "catalunya": 6
        }
    #delimitations_list = sorted(list(delimitations_dict.items()), key=lambda d: order_dict.get(d[0], 0) * 1000000 + d[1][0]) # index(name) * 1000000 + scale
    delimitations_list = sorted(list(delimitations_dict.items()), key=lambda d: order_dict[d[0]])
    delimitations_list = [(name, sorted(scale_list, key=lambda s: s[0])) for name, scale_list in delimitations_list]
    return delimitations_list

def get_ndvis(urlbase="https://datacloud.icgc.cat/datacloud/ndvi/tif",
    http_file_pattern=r'(ndvi-v\d+r\d+-(\d+)\.tif)'):
    """ Obté les URLs dels arxius NDVI disponibles de l'ICGC
        Retorna: [(year, ndvi_url)]
        ---
        Gets ICGC's available NDVI file urls
        Returns: [(year, ndvi_url)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    # Cerquem links a arxius json
    info_list = get_http_files(urlbase, http_file_pattern)
    file_tuple_list = [(year, "%s/%s" % (urlbase, filename)) for filename, year in info_list]
    file_tuple_list.sort(key=lambda f : f[0]) # Ordenem per any
    return file_tuple_list

def get_topographic_5k(urlbase="https://datacloud.icgc.cat/datacloud/topografia-territorial/tif_unzip",
    http_file_pattern=r'(topografia-territorial-v\d+r\d+-(\d+)\.tif)'):
    """ Obté les URLs dels arxius de topografia 1:5.000 disponibles de l'ICGC
        Retorna: [(year, ndvi_url)]
        ---
        Gets ICGC's available topography 1:5,000 file urls
        Returns: [(year, ndvi_url)]
        """    
    info_list = get_http_files(urlbase, http_file_pattern)
    file_tuple_list = [(year, "%s/%s" % (urlbase, filename)) for filename, year in info_list]
    file_tuple_list.sort(key=lambda f : f[0]) # Ordenem per any
    return file_tuple_list

def get_regex_styles():
    """ Retorna la llista d'estils disponibles amb el path al seu QML """
    final_styles_list = [
        (style_regex,
        # Injectem el path dels arxiu .qml
        os.path.join(os.path.dirname(__file__), "symbols", style_qml) if style_qml else None
        ) for style_regex, style_qml in styles_list]
    return final_styles_list
