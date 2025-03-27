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


# Obtenim el path dels arxius d'estil
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

def get_http_files(url, file_regex_pattern, replace_list=[]):
    """ Obté una llista de fitxer d'una pàgina web a partir d'una expressió regular
        Retorna: llista de resultats de la expressió regular
        ---
        Gets file list of web page from a regular expression
        Returns: list of regex matches
        """
    # LLegeixo les dades HTML del directori HTTP
    t0 = datetime.datetime.now()
    response_data = get_http_dir(url)
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
    log.debug("HTTP resources files find URL: %s pattern: %s found: %s (%s)", url, file_regex_pattern, len(files_list), t1-t0)
    return files_list

def get_products(urlbase_list):
    """ Obté les URLs dels arxius d'un producte de l'ICGC d'una carpeta que compleixin una expresió regular
        Params: [(carpeta, regex), ...]
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
            elif len(product_info) == 2:
                product_file, product_subname = product_info
            else:
                continue
            #product_file = sorted(files_list, reverse=True)[0]
            product_url = "%s/%s" % (urlbase, product_file)
            product_list.append((product_name + product_subname, product_url))

    return product_list


# *****************************************************************************
# Products

def get_dtms(urlbase_list=[
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
    return get_products(urlbase_list)

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
    if historic_ortho_dict:
        return historic_ortho_dict

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

    data_dict = {}
    default_gsd_list = [0.25, 0.5, 2.5]
    files_list = get_http_files(urlbase, file_pattern)
    for filename, color_type, gsd_text, gsd_units, name, year_text in files_list:
        color_not_irc = color_type.lower() != "irc"
        gsd = float(gsd_text) if gsd_text.isdigit() else None
        if gsd_units.lower() == "cm":
            gsd /= 100
        year = int(year_text) if year_text.isdigit else None
        url_filename = urlbase + "/" + filename

        # Adds current resolution
        add_data(data_dict, color_not_irc, gsd, year, url_filename, gsd)
        # Adds default resolutions if not exist default resolution or previous source gsd is worse
        for default_gsd in default_gsd_list:
            if gsd < default_gsd:
                source_gsd = get_source_gsd(data_dict, color_not_irc, default_gsd, year)
                if not source_gsd or abs(gsd - default_gsd) < abs(source_gsd - default_gsd):
                    add_data(data_dict, color_not_irc, default_gsd, year, url_filename, gsd)

    return data_dict

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

def get_lidar_ortho(rgb_not_irc,
    urlbase="https://datacloud.icgc.cat/datacloud/lidar-territorial/orto-gpkg_unzip",
    http_rgb_file_pattern=r'(lidar-territorial-v\d+r\d+-ortofoto-rgb-\d+cm-([\d-]+)\.gpkg)',
    http_irc_file_pattern=r'(lidar-territorial-v\d+r\d+-ortofoto-irc-\d+cm-([\d-]+)\.gpkg)'):
    """ Obté les URLs dels arxius ortofoto LiDAR disponibles de l'ICGC
        Retorna: [(year, ortho_url)]
        ---
        Gets ICGC's available orthophoto LiDAR file urls
        Returns: [(year, ortho_url)]
        """
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    # Cerquem links a arxius json
    http_file_pattern = http_rgb_file_pattern if rgb_not_irc else http_irc_file_pattern
    info_list = get_http_files(urlbase, http_file_pattern)
    file_tuple_list = [(year, "%s/%s" % (urlbase, filename)) for filename, year in info_list]
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