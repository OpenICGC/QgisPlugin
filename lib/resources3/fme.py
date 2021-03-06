# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with functions to recover data FME ICGC resources

                             -------------------
        begin                : 2019-06-27
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import urllib
import urllib.request
import socket
import re
import os


#FME_URL = "http://qgis:qgis@fmedev" # A linux no va bé el DNS, posem la IP (desenvolupament)
FME_URL = "https://qgis:qgis@descarregues.icgc.cat" # Servidor extern / adreça externa (producció)

services_list = [
    # (id, name, min_side, max_query_area, default_filename, url_pattern, <(url_ref, qml_style) | (wms_url, wms_layer, wms_style, wms_format)>),

    ("of25c", "Ortofoto 25cm 1:2.500", 25, 12500000, [""], "of25c.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=of25c&Format=GEOTIFF&Projecte=of25c&Codi=%s", None),
    ("of5m", "Ortofoto 50cm 1:5.000", 50, 50000000, ["", "mu"], "of5m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=of5m&Format=GEOTIFF&Projecte=of5m&Codi=%s", None),
    ("of25m", "Ortofoto 2.5m 1:25.000", 250, 1250000000, ["", "mu", "co"], "of25m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=of25m&Format=GEOTIFF&Projecte=of25m&Codi=%s", None),

    ("oi25c", "Ortofoto Infraroja 25cm 1:2.500", 25, 12500000, [""], "oi25c.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=oi25c&Format=GEOTIFF&Projecte=oi25c&Codi=%s", None),
    ("oi5m", "Ortofoto Infraroja 50cm 1:5.000", 50, 50000000, ["", "mu"], "oi5m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=oi5m&Format=GEOTIFF&Projecte=oi5m&Codi=%s", None),
    ("oi25m", "Ortofoto Infraroja 2.5m 1:25.000", 250, 1250000000, ["", "mu", "co"], "oi25m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=oi25m&Format=GEOTIFF&Projecte=oi25m&Codi=%s", None),

    ("bt5m", "Base Topogràfica 1:5.000", 50, 50000000, ["", "mu"], "bt5m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=bt5m&Format=GEOTIFF&Projecte=bt5m&Codi=%s", None),

    ("mtc25m", "Mapa Topogràfic 1:25.000", 250, 1250000000, ["", "mu", "co"], "mtc25m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc25m&Format=GEOTIFF&Projecte=mtc25m&Codi=%s", None),
    ("mtc50m", "Mapa Topogràfic 1:50.000", 500, 5000000000, ["", "mu", "co"], "mtc50m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc50m&Format=GEOTIFF&Projecte=mtc50m&Codi=%s", None),
    ("mtc100m", "Mapa Topogràfic 1:100.000", 1000, 20000000000, ["", "mu", "co"], "mtc100m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc100m&Format=GEOTIFF&Projecte=mtc100m&Codi=%s", None),
    ("mtc250m", "Mapa Topogràfic 1:250.000", 2500, None, ["", "mu", "co", "cat", "tot"], "mtc250m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc250m&Format=GEOTIFF&Projecte=mtc250m&Codi=%s", None),
    ("mtc500m", "Mapa Topogràfic 1:500.000", 5000, None, ["", "mu", "co", "cat", "tot"], "mtc500m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc500m&Format=GEOTIFF&Projecte=mtc500m&Codi=%s", None),
    ("mtc1000m", "Mapa Topogràfic 1:1.000.000", 10000, None, ["", "mu", "co", "cat", "tot"], "mtc1000m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc1000m&Format=GEOTIFF&Projecte=mtc1000m&Codi=%s", None),
    ("mtc2000m", "Mapa Topogràfic 1:2.000.000", 20000, None, ["", "mu", "co", "cat", "tot"], "mtc2000m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mtc2000m&Format=GEOTIFF&Projecte=mtc2000m&Codi=%s", None),

    ("ct1m", "Cartografia Topogràfica 1:1.000", None, 2000000, ["", "mu"], "ct1m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=ct1m&Codi=%s",
        ("http://www.icc.cat/appdownloads/lib/json/ct1m_id.json", "ct1m_disponible.qml")),

    ("bm5m", "Base Municipal 1:5.000", None, None, ["cat", "tot"], "bm5m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=bm5m&Codi=%s", None),

    ("topografia-territorial", "Referencial Topogràfic Territorial", None, 100000000, ["", "mu"], "topografia-territorial.gpkg", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&Codi=%s", None),

    ("cobertes-sol-raster", "Mapa de Cobertes del Sol", 100, 200000000, ["", "mu", "co", "cat", "tot"], "cobertes-sol.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=mcsc&Format=GEOTIFF&Projecte=cobertes-sol&Codi=%s", None),
    ("cobertes-sol-vector", "Mapa de Cobertes del Sol", None, 400000000, ["", "mu", "co"], "cobertes-sol.gpkg", "%s/fmedatastreaming/cobertes-sol/ICGC_cobertes-sol_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&Codi=%s", None),

    ("met2", "MET 2m", 200, 800000000, ["", "mu", "co"], "met2.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=met2&Format=GEOTIFF&Projecte=met2&Codi=%s", None),
    ("met5", "MET 5m", 500, 5000000000, ["", "mu", "co"], "met5.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&DEF_NAME=met5m&Format=GEOTIFF&Projecte=met5&Codi=%s", None),

    # Pending revision of symbology
    #("mg50m", "Mapa Geològic 1:50.000", None, None, ["cat", "tot"], "mg50m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=mg50m&Codi=%s", None),
    ("mg250m", "Mapa Geològic 1:250.000", None, None, ["cat", "tot"], "mg250m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=mg250m&Codi=%s", None),

    #("gt1", "GeoTreball 1 1:25.000", None, 1250000000, ["", "mu", "co"], "gt1.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt1&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_I", "", "image/png")),
    #("gt2", "GeoTreball 2 1:25.000", None, 1250000000, ["", "mu", "co", "cat", "tot"], "gt2.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt2&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_II", "", "image/png")),
    #("gt3", "GeoTreball 3 1:5.000", None, 50000000, ["", "mu", "co", "cat", "tot"], "gt3.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt3&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_III", "", "image/png")),
    #("gt4", "GeoTreball 4 1:25.000", None, 1250000000, ["", "mu", "co", "cat", "tot"], "gt4.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt4&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_IV", "", "image/png")),
    #("gt5", "GeoTreball 5 1:25.000", None, 1250000000, ["", "mu", "co", "cat", "tot"], "gt5.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt5&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_V", "", "image/png")),
    ("gt6", "GT VI. Mapa per a la prevenció dels riscos geològics 1:25.000", None, 1250000000, ["", "mu", "co", "cat", "tot"], "gt6.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=gt6&Codi=%s",
        ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_VI", "", "image/png")),

    #("mah250m", "Mapa Àrees Hidrogeològiques 1:250.000", None, 50000000, ["cat", "tot"], "mah250m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&Projecte=mah250m&Codi=%s", None),
    ]
services_dict = dict([(id, (name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple)) for (id, name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple) in services_list])

# Permet estilitzar i ordernar les capes dins un zip amb shapes dins
styles_list = [ # (regex_file_pattern, qml_style)
    # Global
    (r"ct1m.+axt\d", "ct1mv22_t.qml"), # ct1mv22sh0f4483707eaxt1 (Textos)
    # Altres projectes
    (r"ct1m.+n\dr\d{3}", "ct1mv22_n.qml"), # ct1mv21sh0f001844028200axn1r010
    (r"ct1m.+l\dr\d{3}", "ct1mv22_l.qml"), # ct1m_20190801_135724 ct1mv22sh0f001844078700axl1r010
    (r"ct1m.+p\dr\d{3}", "ct1mv22_p.qml"), # ct1mv21sh0f001844028200axp1r010
    (r"ct1m.+c\d_\d{2}ca", "ct1mv22_c.qml"), # ct1mv21sh0f001844028200ac1_01ca (Full 1000)
    # AMB & BCN
    (r"ct1m.+n\d_", "ct1mv22_n.qml"), # ct1mv22sh0f4483707fn1_201505_0
    (r"ct1m.+l\d_", "ct1mv22_l.qml"), # ct1mv22sh0f4483707fl1_201505_0
    (r"ct1m.+p\d_", "ct1mv22_p.qml"), # ct1mv22sh0f4483707fp1_201505_0
    (r"ct1m.+c\d_full", "ct1mv22_c.qml"), # ct1mv22sh0f4483707c1_full (Full 1000)
    ]

def get_services():
    """ Retorna la llista de productes descarregables """
    final_services_list = [
        (id, name, min_side, max_query_area, download_list, default_filename, url_pattern,
        # Injectem el path dels arxiu .qml
        (ref_tuple[0], os.path.join(os.path.dirname(__file__), "symbols", ref_tuple[1])) if ref_tuple and len(ref_tuple) == 2 else ref_tuple
        ) for id, name, min_side, max_query_area, download_list, default_filename, url_pattern, ref_tuple in services_list]
    return final_services_list

def get_clip_data_url(data_type, xmin, ymin, xmax, ymax, mode, url_base=FME_URL):
    """ Retorna la petició URL FME per descarregar un producte """
    name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple = services_dict.get(data_type, (None, None, None, None, None, None))
    url = url_pattern % (url_base, xmin, ymin, xmax, ymax, mode) if url_pattern else None
    return url

def get_regex_styles():
    """ Retorna la llista d'estils disponibles amb el path al seu QML """
    final_styles_list = [
        (style_regex,
        # Injectem el path dels arxiu .qml
        os.path.join(os.path.dirname(__file__), "symbols", style_qml) if style_qml else None
        ) for style_regex, style_qml in styles_list]
    return final_styles_list

def get_layer_style(layer_name):
    """ Retorna el fitxer QML d'esti associat a una capa de dades """
    for regex_pattern, qml_style in styles_list:
        if re.match(regex_pattern, layer_name):
            if not os.path.splitext(qml_style)[1]:
                qml_style += ".qml"
            return os.path.join(os.path.dirname(__file__), "symbols", qml_style)
    return None