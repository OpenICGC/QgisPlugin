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
import socket
import ssl
import re
import os
import datetime
from importlib import reload

# Configure internal library logger (Default is dummy logger)
import logging
reload(logging)
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())


# Gets style files path
styles_path = os.path.join(os.path.dirname(__file__), "symbols")


# *****************************************************************************
# Auxiliar functions

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
    response_data = ""
    remaining_retries = retries
    while remaining_retries:
        try:
            response = urllib.request.urlopen(url, timeout=timeout_seconds, context=context)
            if response:
                response_data = response.read()
                if response_data:
                    remaining_retries = 0
        except socket.timeout:
            remaining_retries -= 1
            log.warning("HTTP resources timeout, retries: %s, URL: %s", retries, url)
        except Exception as e:
            remaining_retries -= 1
            log.exception("HTTP resources error (%s), retries: %s, URL: %s", e, retries, url)
    if response_data:
        response_data = response_data.decode('utf-8')
    else:
        log.error("HTTP resources error, exhausted retries")
    return response_data

url_response_dict = {}
def get_http_files(url, file_regex_pattern, replace_list=[]):
    """ Obté una llista de fitxer d'una pàgina web a partir d'una expressió regular
        Retorna: llista de resultats de la expressió regular
        ---
        Gets file list of web page from a regular expression
        Returns: list of regex matches
        """
    global url_response_dict
    t0 = datetime.datetime.now()

    # Mirem si tenim la URL cachejada, si ja tenim les dades no cal fer res
    response_data = url_response_dict.get(url, None)
    if response_data:
        cached = True
    else:
        cached = False
        # LLegeixo les dades HTML del directori HTTP
        response_data = get_http_dir(url)
        if response_data:
            # Guardem el resultat a la cache
            url_response_dict[url] = response_data
    if not response_data:
        files_list = []
    else:
        # Reemplacem els textos indicats
        for search, replace in replace_list:
            response_data = response_data.replace(search, replace)
        # Obtinc la informació de fitxers a partri de la regex
        http_file_regex_pattern = r'<A HREF="[\/\w-]*%s">' % file_regex_pattern
        files_list = re.findall(http_file_regex_pattern, response_data)

    t1 = datetime.datetime.now()
    log.debug("HTTP resources files find URL: %s pattern: %s cached: %s, found: %s (%s)", url, file_regex_pattern, cached, len(files_list), t1-t0)
    return files_list

def get_products(urlbase_list, subproduct_separator="\n", subproduct_reverse=True):
    """ Obté les URLs dels arxius d'un producte de l'ICGC d'una carpeta que compleixin una expresió regular
        Params:
        - urlbase_list: [(nom_producte, carpeta, regex), ...]
        Retorna: [(product_name, product_url)]
        ---
        Gets ICGC's available product urls from a folder that match a regular expression
        Params: [(folder, regex), ...]
        Returns: [product_name, product_url)]
        """
    product_list = []
    for product_name, urlbase, http_file_pattern in urlbase_list:
        # Llegeixo la pàgina HTTP que informa dels arxius disponibles
        # Cerquem links a arxius MET i ens quedem el més recent
        files_list = get_http_files(urlbase, http_file_pattern)
        if not files_list:
            continue

        for product_info in sorted(files_list, reverse=False):
            if type(product_info) is str:
                product_file = product_info
                product_subname = ""
            elif len(product_info) > 1:
                product_file = product_info[0]
                product_subname = subproduct_separator.join(product_info[1:][::-1 if subproduct_reverse else 1])
            else:
                continue
            #product_file = sorted(files_list, reverse=True)[0]
            product_url = "%s/%s" % (urlbase, product_file)
            product_list.append((product_name + product_subname, product_url))

    return product_list


# *****************************************************************************
# Products

def get_old_dtms(urlbase_list=[
    ("2m 2008-2011", "https://datacloud.icgc.cat/datacloud/met2_ETRS89/mosaic", r'(met\w+\.\w+)'),
    ("5m 2020", "https://datacloud.icgc.cat/datacloud/met5_ETRS89/mosaic", r'(met\w+\.\w+)'),
    ]):
    """ Obté les URLs dels arxius de MET disponibles de l'ICGC
        Retorna: [(dtm_name, dtm_url)]
        ---
        Gets ICGC's available DTM urls
        Returns: [(dtm_name, dtm_url)]
        """
    # ATENCIÓ!!! El MET 2m encara que posi al fitxer 2020 és del 2008-2011 per això està fixat!
    # Donat que no es pot obtenir la data del nom de fitxer... FIXO els paths!
    # return get_products(urlbase_list)

    # ATENCIÓ! la carpeta vigent està tancada i no puc accedir!
    # return [
    #     ("2m 2008-2011", "https://datacloud.icgc.cat/datacloud/met2_ETRS89/vigent/mosaic/met2_catalunya.tif"),
    #     ("5m 2020", "https://datacloud.icgc.cat/datacloud/met5_ETRS89/vigent/mosaic/met5_catalunya.tif"),
    # ]

    return [
        ("2m 2008-2011", "https://datacloud.icgc.cat/datacloud/met2_ETRS89/mosaic/met2_catalunya_2020.tif"),
        ("5m 2020", "https://datacloud.icgc.cat/datacloud/met5_ETRS89/mosaic/met5_catalunya_2020.tif"),
    ]
dtm_list = []
def get_dtms(dtm_name="", group_by_product_not_gsd=True, urlbase_list=[
    # model-elevacions-terreny
    ("met25cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/json_unzip", r"(model-elevacions-terreny-\w+-(\w+)-25cm-(\d+-\d+)\.json)"),
    ("met50cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/json_unzip", r"(model-elevacions-terreny-\w+-(\w+)-50cm-(\d+-\d+)\.json)"),
    ("met1m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/json_unzip", r"(model-elevacions-terreny-\w+-(\w+)-1m-(\d+-\d+)\.json)"),
    ("met2m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/json_unzip", r"(model-elevacions-terreny-\w+-(\w+)-2m-(\d+-\d+)\.json)"),
    ("met5m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/json_unzip", r"(model-elevacions-terreny-\w+-(\w+)-5m-(\d+-\d+)\.json)"),
    # model-elevacions-terreny-edificis
    ("ed25cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("ed50cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("ed1m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("ed2m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("ed5m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-5m-(\d+-\d+)\.json)"),
    # model-superficies
    ("ms25cm-", "https://datacloud.icgc.cat/datacloud/model-superficies/json_unzip", r"(model-superficies-\w+-(\w+)-25cm-(\d+-\d+)\.json)"),
    ("ms50cm-", "https://datacloud.icgc.cat/datacloud/model-superficies/json_unzip", r"(model-superficies-\w+-(\w+)-50cm-(\d+-\d+)\.json)"),
    ("ms1m-", "https://datacloud.icgc.cat/datacloud/model-superficies/json_unzip", r"(model-superficies-\w+-(\w+)-1m-(\d+-\d+)\.json)"),
    ("ms2m-", "https://datacloud.icgc.cat/datacloud/model-superficies/json_unzip", r"(model-superficies-\w+-(\w+)-2m-(\d+-\d+)\.json)"),
    ("ms5m-", "https://datacloud.icgc.cat/datacloud/model-superficies/json_unzip", r"(model-superficies-\w+-(\w+)-5m-(\d+-\d+)\.json)"),
    # model-orientacions
    ("mo25cm-", "https://datacloud.icgc.cat/datacloud/model-orientacions/json_unzip", r"(model-orientacions-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("mo50cm-", "https://datacloud.icgc.cat/datacloud/model-orientacions/json_unzip", r"(model-orientacions-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("mo1m-", "https://datacloud.icgc.cat/datacloud/model-orientacions/json_unzip", r"(model-orientacions-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("mo2m-", "https://datacloud.icgc.cat/datacloud/model-orientacions/json_unzip", r"(model-orientacions-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("mo5m-", "https://datacloud.icgc.cat/datacloud/model-orientacions/json_unzip", r"(model-orientacions-\w+-\w+-5m-(\d+-\d+)\.json)"),
    # model-elevacions-terreny-litoral
    ("metl25cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-litoral/json_unzip", r"(model-elevacions-terreny-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("metl50cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-litoral/json_unzip", r"(model-elevacions-terreny-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("metl1m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-litoral/json_unzip", r"(model-elevacions-terreny-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("metl2m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-litoral/json_unzip", r"(model-elevacions-terreny-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("metl5m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-litoral/json_unzip", r"(model-elevacions-terreny-\w+-\w+-5m-(\d+-\d+)\.json)"),
    # model-elevacions-terreny-edificis-litoral
    ("edl25cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis-litoral/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("edl50cm-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis-litoral/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("edl1m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis-litoral/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("edl2m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis-litoral/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("edl5m-", "https://datacloud.icgc.cat/datacloud/model-elevacions-terreny-edificis-litoral/json_unzip", r"(model-elevacions-terreny-edificis-\w+-\w+-5m-(\d+-\d+)\.json)"),
    # model-superficies-litoral
    ("msl25cm-", "https://datacloud.icgc.cat/datacloud/model-superficies-litoral/json_unzip", r"(model-superficies-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("msl50cm-", "https://datacloud.icgc.cat/datacloud/model-superficies-litoral/json_unzip", r"(model-superficies-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("msl1m-", "https://datacloud.icgc.cat/datacloud/model-superficies-litoral/json_unzip", r"(model-superficies-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("msl2m-", "https://datacloud.icgc.cat/datacloud/model-superficies-litoral/json_unzip", r"(model-superficies-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("msl5m-", "https://datacloud.icgc.cat/datacloud/model-superficies-litoral/json_unzip", r"(model-superficies-\w+-\w+-5m-(\d+-\d+)\.json)"),
    # model-orientacions-litoral
    ("mol25cm-", "https://datacloud.icgc.cat/datacloud/model-orientacions-litoral/json_unzip", r"(model-orientacions-\w+-\w+-25cm-(\d+-\d+)\.json)"),
    ("mol50cm-", "https://datacloud.icgc.cat/datacloud/model-orientacions-litoral/json_unzip", r"(model-orientacions-\w+-\w+-50cm-(\d+-\d+)\.json)"),
    ("mol1m-", "https://datacloud.icgc.cat/datacloud/model-orientacions-litoral/json_unzip", r"(model-orientacions-\w+-\w+-1m-(\d+-\d+)\.json)"),
    ("mol2m-", "https://datacloud.icgc.cat/datacloud/model-orientacions-litoral/json_unzip", r"(model-orientacions-\w+-\w+-2m-(\d+-\d+)\.json)"),
    ("mol5m-", "https://datacloud.icgc.cat/datacloud/model-orientacions-litoral/json_unzip", r"(model-orientacions-\w+-\w+-5m-(\d+-\d+)\.json)"),
    ], json_not_tiff=True, remove_prefix=False, sort_by_key=False):
    """ Obté les URLs dels arxius de MET disponibles de l'ICGC
        Retorna: [(dtm_name, dtm_url)]
        ---
        Gets ICGC's available DTM urls
        Returns: [(dtm_name, dtm_url)]
        """
    # Detectem si tenim les dades catxejades i si no les llegim remotament segons
    # els filtres indicats
    global dtm_list
    if not dtm_list:
        dtm_list = get_products(urlbase_list)
    print("ZZZ", dtm_list)

    if group_by_product_not_gsd:
        # Si ens demanen agrupar per producte, juntem tots productes iguals de diferent GSD
        final_dtm_list = []
        for dtm_name_gsd, dtm_url in dtm_list:
            dtm_id = "".join(re.split(r"\d+c*m", dtm_name_gsd))
            final_dtm_list.append((dtm_id, dtm_url))
    else:
        final_dtm_list = dtm_list
    if dtm_name:
        final_dtm_list = [(dtm_id, dtm_url) \
            for dtm_id, dtm_url in final_dtm_list if dtm_id.split("-")[0] == dtm_name]
    if remove_prefix:
        final_dtm_list = [("-".join(dtm_id.split("-")[1:]), dtm_url) \
            for dtm_id, dtm_url in final_dtm_list]
    if not json_not_tiff:
        final_dtm_list = [(dtm_id, dtm_url.replace("json_unzip", "tif_unzip").replace(".json", ".tif")) \
            for dtm_id, dtm_url in final_dtm_list]
    return sorted(final_dtm_list) if sort_by_key else final_dtm_list

def get_dtm_time(dtm_name, group_by_product_not_gsd=False):
    """ Retorna les franjes temporals disponibles de mets
        ---
        Gets available dtm time ranges
    """
    dtm_prefix = dtm_name + "-"
    time_list = [time_code.replace(dtm_prefix, "") \
        for time_code, _url in get_dtms(dtm_name, group_by_product_not_gsd)]
    return sorted(time_list)

def get_dtm_time_layers(dtm_name, group_by_product_not_gsd=False):
    """ Retorna les franjes temporals disponibles de mets i la capa WMS associada
        ---
        Gets available dtm time ranges and associated WMS layer
    """
    dtm_prefix = dtm_name + "-"
    time_list = [
        (time_code.replace(dtm_prefix, ""), os.path.splitext(url.split("/")[-1])[0]) \
        for time_code, url in get_dtms(dtm_name, group_by_product_not_gsd)]
    return sorted(time_list)

def get_dtm_ref(dtm_name_gsd, time_code):
    """ Retorna l'arxiu de referència (URL) d'un MET
        ---
        Gets dtm refernce file (URL)
    """
    dtm_gsd_time = "%s-%s" % (dtm_name_gsd, time_code)
    ref_file = dict(get_dtms(dtm_name_gsd, group_by_product_not_gsd=False)).get(dtm_gsd_time)
    return ref_file

def get_dtm_image(dtm_name, time_code):
    """ Retorna l'arxiu imatge (URL) d'un MET
        ---
        Gets dtm image file (URL)
    """
    dtm_time = "%s-%s" % (dtm_name, time_code)
    ref_file = dict(get_dtms(dtm_name, group_by_product_not_gsd=True)).get(dtm_time)
    image_file = ref_file.replace(".json", ".tif").replace("/json_unzip", "/tif_unzip")
    return image_file

def get_dtm_filename(dtm_name, time_code):
    """ Retorna el nom l'arxiu de referència d'un MET
        ---
        Gets dtm reference file name
    """
    url = get_dtm_ref(dtm_name, time_code)
    filename = os.path.splitext(url.split("/")[-1])[0]
    return filename

coastline_list = None # Cached data
def get_coastlines(urlbase_list = [
    ("", "https://datacloud.icgc.cat/datacloud/linia-costa/gpkg_unzip/", r"(linia-costa-v\d+r\d+-(\d+-\d+(?:-\w+)*)\.gpkg)")
    ]):
    """ Obté les URLs dels arxius de linia de costa disponibles de l'ICGC
        Retorna: [(coast_name, coast_url)]
        ---
        Gets ICGC's available coast line urls
        Returns: [(coast_name, coast_url)]
        """
    global coastline_list
    if not coastline_list:
        coastlist_list = get_products(urlbase_list)
    return coastlist_list

def get_coastline_filename_dict():
    """ Retorna els arxius disponibles de linia de costa
        ---
        Returns available coast line files
        """
    return {time: os.path.splitext(url.split("/")[-1])[0] for time, url in get_coastlines()}

def get_coastline_years():
    """ Retorna els anys disponbiles de linia de costa
        ---
        Gets available coast line years
    """
    coastline_list = get_coastlines()
    return [time for time, url in coastline_list]

coast_orthophoto_list = None # Cached data
def get_coast_orthophotos(urlbase_list = [
    ("", "https://datacloud.icgc.cat/datacloud/orto-costa/gpkg_unzip/", r"(orto-costa-(?:rgb|irc)-\d+cm-(\d+-\d+(?:-\w+)*)\.gpkg)")
    ]):
    """ Obté les URLs dels arxius de linia de costa disponibles de l'ICGC
        Retorna: [(coast_name, coast_url)]
        ---
        Gets ICGC's available coast line urls
        Returns: [(coast_name, coast_url)]
        """
    global coast_orthophoto_list
    if not coast_orthophoto_list:
        coast_orthophoto_list = get_products(urlbase_list)
        coast_orthophoto_list.sort(key=lambda p: p[0])
    return coast_orthophoto_list

def get_coast_orthophoto_filename_dict():
    """ Retorna els arxius disponibles de linia de costa
        ---
        Returns available coast line files
        """
    coast_orthophoto_list = get_coast_orthophotos()
    return {time_tag: os.path.splitext(url.split("/")[-1])[0] for time_tag, url in coast_orthophoto_list}

def get_coast_orthophoto_years():
    """ Retorna els anys disponbiles de linia de costa
        ---
        Gets available coast line years
    """
    coast_orthophoto_list = get_coast_orthophotos()
    return [time_tag for time_tag, url in coast_orthophoto_list]

def get_sheets(sheets_urlbase="https://datacloud.icgc.cat/datacloud/talls_ETRS89/vigent/fgb_unzip_EPSG25831",
    scale_list=[1,2,5,10,25,50,100]):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
           Returns: [(sheet_name, sheet_url)]
        """
    # Generem una llista d'arxius a partir d'unes escales fixes i uns noms
    # d'arxius fixes a la carpeta "vigent"
    sheets_style_file = os.path.join(styles_path, "talls.qml")
    sheets_list = [
        (f"{scale}.000", sheets_urlbase + f"/tall{scale}m.fgb", sheets_style_file)
        for scale in scale_list
        ]
    return sheets_list

def get_grids(grid_urlbase="https://datacloud.icgc.cat/datacloud/quadricules-utm/vigent/fgb_unzip_EPSG25831/",
    scale_list=[1,10]):
    """ Obté les URLs dels arxius de quadricules disponibles de l'ICGC.
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available grid urls
        Returns: [(grid_name, grid_url)]
        """
    # Generem una llista d'arxius a partir d'unes escales fixes i uns noms
    # d'arxius fixes a la carpeta "vigent"
    grids_style_file = os.path.join(styles_path, "talls.qml")
    grid_list = [(f"UTM (MGRS) {scale}x{scale} km", f"{grid_urlbase}quadricules-utm-{scale}km.fgb", grids_style_file)
        for scale in scale_list]
    return grid_list

def get_delimitations(
    delimitations_urlbase="https://datacloud.icgc.cat/datacloud/divisions-administratives/vigent/fgb_unzip_EPSG25831",
    delimitation_type_list=[
        ("caps-municipi", [None]),
        ("municipis", [5000, 50000, 100000, 250000, 500000, 1000000]),
        ("comarques", [5000, 50000, 100000, 250000, 500000, 1000000]),
        ("vegueries", [5000, 50000, 100000, 250000, 500000, 1000000]),
        ("provincies", [5000, 50000, 100000, 250000, 500000, 1000000]),
        ("catalunya", [5000, 50000, 100000, 250000, 500000, 1000000]),
        ]):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    delimitations_list = [(
        name,
        [(
            scale,
            delimitations_urlbase + \
                "/divisions-administratives-%s.fgb" % "-".join([name] + ([str(scale)] if scale else [])),
            ) for scale in scale_list],
        os.path.join(
            styles_path, # Variable global
            "divisions-administratives-%s-ref.qml" % name)
        ) for name, scale_list in delimitation_type_list]
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
    file_tuple_list.sort(key=lambda f : f[0], reverse=True) # Ordenem per any
    return file_tuple_list

historic_ortho_dict = None # Result cache
def get_historic_ortho_dict(urlbase="https://datacloud.icgc.cat/datacloud/orto-territorial/gpkg_unzip", \
        file_pattern=r"(ortofoto-(\w+)-(\d+)(c*m)-(\w+)-(\d{4})\.gpkg)"):
    """ Obté un diccionari amb les ortofotos históriques disponibles per descarregar:
        Retorna dict[color_not_irc][gsd][year] = (filename, source_gsd)
        ----
        Gets historic orthophotos dictionary available to download
        Returns dict[color_not_irc][gsd][year] = (filename, source_gsd)
        """
    # If we have a cached result, we return it
    global historic_ortho_dict
    if not historic_ortho_dict:
        historic_ortho_dict = get_historic_dict(urlbase, file_pattern, [0.25, 0.5, 2.5])
    return historic_ortho_dict

def get_historic_dict(urlbase, file_pattern, default_gsd_list=[]):
    """ Obté un diccionari amb les dades históriques disponibles per descarregar:
        Retorna dict[color_not_irc][gsd][year] = (filename, source_gsd)
        ----
        Gets historical data dictionary available to download
        Returns dict[color_not_irc][gsd][year] = (filename, source_gsd)
        """
    def add_data(data_dict, color_not_irc, gsd, year, filename, source_gsd):
        if color_not_irc not in data_dict:
            data_dict[color_not_irc] = {}
        gsd_dict = data_dict[color_not_irc]
        if gsd not in gsd_dict:
            gsd_dict[gsd] = {}
        year_dict = gsd_dict[gsd]
        year_dict[year] = (filename, source_gsd) # Tuple (filename, source_gsd)
    def get_source_gsd(data_dict, color_not_irc, gsd, year):
        if not color_not_irc in data_dict or not gsd in data_dict[color_not_irc] or not year in data_dict[color_not_irc][gsd]:
            return None
        source_gsd = data_dict[color_not_irc][gsd][year][1] # Tuple (filename, source_gsd)
        return source_gsd

    historic_dict = {}
    files_list = get_http_files(urlbase, file_pattern)
    for filename, color_type, gsd_text, gsd_units, name, year_text in files_list:
        color_not_irc = color_type.lower() != "irc"
        gsd = float(gsd_text) if gsd_text.isdigit() else None
        if gsd_units.lower() == "cm":
            gsd /= 100
        year = int(year_text) if year_text.isdigit() else None
        url_filename = urlbase + "/" + filename

        # Adds current resolution
        add_data(historic_dict, color_not_irc, gsd, year, url_filename, gsd)
        # Adds default resolutions if not exist default resolution or previous source gsd is worse
        for default_gsd in default_gsd_list:
            if gsd < default_gsd:
                source_gsd = get_source_gsd(historic_dict, color_not_irc, default_gsd, year)
                if not source_gsd or abs(gsd - default_gsd) < abs(source_gsd - default_gsd):
                    add_data(historic_dict, color_not_irc, default_gsd, year, url_filename, gsd)

    return historic_dict

def get_historic_ortho_years(rgb_not_irc, gsd):
    """ Obté els anys disponibles per un tipus d'orto (RGB/IRC) i GSD
        ---
        Gets available years associated to orthophot/color/gsd
        """
    gsd_dict = get_historic_ortho_dict().get(rgb_not_irc, None)
    if not gsd_dict:
        return []
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return []
    return list(years_dict.keys())

def get_historic_ortho_file(rgb_not_irc, gsd, year):
    """ Obté el fitxer associat a una ortofoto/color/resolució/any
        ---
        Gets file associated to orthophoto/color/resolution/year

        """
    gsd_dict = get_historic_ortho_dict().get(rgb_not_irc, None)
    if not gsd_dict:
        return None
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return None
    filename_and_source_gsd = years_dict.get(year, None) # Tuple (filename, source_gsd)
    return filename_and_source_gsd[0] if filename_and_source_gsd else None

def get_historic_ortho_code(rgb_not_irc, gsd, year):
    """ Obté el codi de descàrrega FME associat a una ortofoto/color/resolució/any
        ---
        Gest FME download code associated to orthophoto/color/resolution/year
        """
    filename = get_historic_ortho_file(rgb_not_irc, gsd, year)
    if filename:
        filename = os.path.splitext(os.path.basename(filename))[0]
    return filename

def get_historic_ortho_ref(rgb_not_irc, gsd, year):
    """ Obté l'arxiu de referència associat a una ortofoto/color/resolució/any
        ---
        Gets referece file associated to orthophoto/color/resolution/year
        """
    return get_historic_ortho_file(rgb_not_irc, gsd, year)

historic_local_ortho_dict = None # Result cache
def get_historic_local_ortho_dict(urlbase="https://datacloud.icgc.cat/datacloud/orto-local/json_unzip", \
        file_pattern=r"(orto-local-(rgb|irc)-(\d+)(cm)-()(\d{4})\.json)"):
    """ Obté un diccionari amb les ortofotos históriques locals disponibles per descarregar:
        Retorna dict[color_not_irc][gsd][year] = (filename, source_gsd)
        ----
        Gets historic local orthophotos dictionary available to download
        Returns dict[color_not_irc][gsd][year] = (filename, source_gsd)
        """
    # If we have a cached result, we return it
    global historic_local_ortho_dict
    if not historic_local_ortho_dict:
        historic_local_ortho_dict = get_historic_dict(urlbase, file_pattern, [])
    return historic_local_ortho_dict

def get_historic_local_ortho_years(rgb_not_irc, gsd):
    """ Obté els anys disponibles per un tipus d'orto (RGB/IRC) i GSD
        ---
        Gets available years associated to orthophot/color/gsd
        """
    gsd_dict = get_historic_local_ortho_dict().get(rgb_not_irc)
    if not gsd_dict:
        return []
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return []
    return list(years_dict.keys())

def get_historic_local_ortho_ref(rgb_not_irc, gsd, year):
    """ Obté l'arxiu de referència associat a una ortofoto/color/resolució/any
        ---
        Gets referece file associated to orthophoto/color/resolution/year
        """
    return get_historic_local_ortho_file(rgb_not_irc, gsd, year)

def get_historic_local_ortho_file(rgb_not_irc, gsd, year):
    """ Obté el fitxer associat a una ortofoto/color/resolució/any
        ---
        Gets file associated to orthophoto/color/resolution/year

        """
    gsd_dict = get_historic_local_ortho_dict().get(rgb_not_irc, None)
    if not gsd_dict:
        return None
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return None
    filename_and_source_gsd = years_dict.get(year, None) # Tuple (filename, source_gsd)
    return filename_and_source_gsd[0] if filename_and_source_gsd else None

def get_historic_local_ortho_code(rgb_not_irc, gsd, year):
    """ Obté el codi de descàrrega FME associat a una ortofoto/color/resolució/any
        ---
        Gest FME download code associated to orthophoto/color/resolution/year
        """
    filename = get_historic_local_ortho_file(rgb_not_irc, gsd, year)
    if filename:
        filename = os.path.splitext(os.path.basename(filename))[0].replace("orto-local-", "")
    return filename

def get_lidar_ortho(urlbase="https://datacloud.icgc.cat/datacloud/lidar-territorial/orto-gpkg_unzip",
    http_file_pattern=r'(lidar-territorial-v\d+r\d+-ortofoto-(rgb|irc)-\d+cm-([\d-]+)\.gpkg)'):
    """ Obté les URLs dels arxius ortofoto LiDAR disponibles de l'ICGC
        Retorna: [(year, ortho_url, <rgb|irc>)]
        ---
        Gets ICGC's available orthophoto LiDAR file urls
        Returns: [(year, ortho_url, <rgb|irc>)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    # Cerquem links a arxius json
    info_list = get_http_files(urlbase, http_file_pattern)
    file_tuple_list = [(year, "%s/%s" % (urlbase, filename), color.lower()) for filename, color, year in info_list]
    file_tuple_list.sort(key=lambda f : f[0]) # Ordenem per any
    return file_tuple_list

def get_census_tracts(urlbase="https://datacloud.icgc.cat/datacloud/bseccen_etrs89/vigent/fgb_unzip_EPSG25831"):
    """ Obté la URL del producte vigent seccions censals
        Retorna: url, style_file
        ---
        Gets ICGC's available census tract product URL
        Returns: url, style_file
        """
    url = urlbase + "/" + "bseccen.fgb"
    style_file = os.path.join(
        styles_path, # Variable global
        "bseccen.qml")
    return url, style_file

def get_decentralized_municipal_entities(urlbase="https://datacloud.icgc.cat/datacloud/entitats-municipals-descentralitzades/vigent/gpkg_unzip"):
    """ Obté la URL del producte vigent unitats municipals descentralitzades
        Retorna: url
        ---
        Gets ICGC's available decentralized municipal entities product URL
        Returns: url
    """
    url = urlbase + "/" + "entitats-municipals-descentralitzades.gpkg|layername=entitats-municipals-descentralitzades"
    return url

def get_population_zones(urlbase="https://datacloud.icgc.cat/datacloud/arees-poblament/vigent/gpkg_unzip"):
    """ Obté la URL del producte àrees de població
        Retorna: url
        ---
        Gets ICGC's population zones product URL
        Returns: url
    """
    url = urlbase + "/" + "arees-poblament.gpkg|layername=arees-poblament"
    return url

coast_lidar_list = None # Cached data
def get_coast_lidar(urlbase_list = [
    ("", "https://datacloud.icgc.cat/datacloud/lidar-litoral/json/", r"(lidar-litoral-tall-\dkm-(\d{6}-\d{6})\.json)")
    ]):
    """ Obté les URLs dels arxius de lidar de costa disponibles de l'ICGC
        Retorna: [(coast_name, coast_url)]
        ---
        Gets ICGC's available lidar coast urls
        Returns: [(coast_name, coast_url)]
        """
    global coast_lidar_list
    if not coast_lidar_list:
        coast_lidar_list = get_products(urlbase_list)
    return coast_lidar_list

def get_coast_lidar_filename_dict():
    """ Retorna els arxius disponibles de lidar de costa
        ---
        Returns available lidar coast files
        """
    return {time: os.path.splitext(url.split("/")[-1])[0] for time, url in get_coast_lidar()}

def get_coast_lidar_ref(time_code):
    """ Retorna els arxius de referència disponibles de lidar de costa
        ---
        Returns available reference lidar coast files
        """
    return {time: url for time, url in get_coast_lidar()}[time_code]

def get_coast_lidar_time():
    """ Retorna les franjes temporals disponibles de lidar de costa
        ---
        Gets available lidar coast time ranges
    """
    coast_lidar_list = get_coast_lidar()
    return sorted([time for time, url in coast_lidar_list])
