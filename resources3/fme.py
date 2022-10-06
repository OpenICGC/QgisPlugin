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
from .http import get_http_files

# Configure internal library logger (Default is dummy logger)
import logging
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())


#FME_URL = "http://qgis:qgis@sefme2020dev" # A linux no va bé el DNS, ca posar la IP (desenvolupament)
#FME_URL = "https://qgis:qgis@sefme2020prod.icgc.local" # Test
FME_URL = "https://qgis:qgis@descarregues.icgc.cat" # Servidor extern / adreça externa (producció)

FME_DOWNLOAD_EPSG = 25831

FME_AUTO_SEARCH = "Search"

services_list = [
    # (id, name, min_side, max_query_area, min_px_side, max_px_area, download_type_list, gsd, time_list, default_filename, 
    #    download_limits_id, url_pattern, <(url_ref, qml_style) | (wms_url, wms_layer, wms_style, wms_format)>),
    # Note: time_list is tuple (rgb_not_irc:bool, gsd:float) -> It has time_list but query is required
    ("of25c", "Ortofoto color vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "of25cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=of25c&Format=GEOTIFF&Projecte=of25c&Codi=%s&piramide=True", None),
    ("of5m", "Ortofoto color vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "of50cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=of5m&Format=GEOTIFF&Projecte=of5m&Codi=%s&piramide=True", None),
    ("of25m", "Ortofoto color vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=of25m&Format=GEOTIFF&Projecte=of25m&Codi=%s&piramide=True", None),

    ("hc10cm", "Ortofoto color històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, FME_AUTO_SEARCH, ["", "pol"], "of10cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hc15cm", "Ortofoto color històrica 15cm 1:1.500", 15, 4500000, None, None, 0.15, FME_AUTO_SEARCH, ["", "pol"], "of15cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.15", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hc25cm", "Ortofoto color històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, FME_AUTO_SEARCH, ["", "pol"], "of25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hc50cm", "Ortofoto color històrica 50cm 1:5.000", 50, 50000000, None, None, 0.50, FME_AUTO_SEARCH, ["", "pol", "mu"], "of50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hc1m", "Ortofoto color històrica 1m 1:10.000", 100, 200000000, None, None, 1, FME_AUTO_SEARCH, ["", "pol", "mu"], "of1m.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hc250cm", "Ortofoto color històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, FME_AUTO_SEARCH, ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),

    ("oi25c", "Ortofoto infraroja vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "oi25cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=oi25c&Format=GEOTIFF&Projecte=oi25c&Codi=%s&piramide=True", None),
    ("oi5m", "Ortofoto infraroja vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "oi50cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=oi5m&Format=GEOTIFF&Projecte=oi5m&Codi=%s&piramide=True", None),
    ("oi25m", "Ortofoto infraroja vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=oi25m&Format=GEOTIFF&Projecte=oi25m&Codi=%s&piramide=True", None),

    ("hi10cm", "Ortofoto infraroja històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, FME_AUTO_SEARCH, ["", "pol"], "oi10cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hi25cm", "Ortofoto infraroja històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, FME_AUTO_SEARCH, ["", "pol"], "oi25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hi50cm", "Ortofoto infraroja històrica 50cm 1:5.000", 50, 50000000, None, None, 0.5, FME_AUTO_SEARCH, ["", "pol", "mu"], "oi50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hi1m", "Ortofoto infraroja històrica 1m 1:10.000", 100, 200000000, None, None, 1, FME_AUTO_SEARCH, ["", "pol", "mu"], "oi1m.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),
    ("hi250cm", "Ortofoto infraroja històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, FME_AUTO_SEARCH, ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
        (FME_AUTO_SEARCH, "orto-historica.qml")),

    #("bt5m", "Base topogràfica 1:5.000", 50, 50000000, None, None, None, ["", "pol", "mu"], "bt5m.tif", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=bt5m&Format=GEOTIFF&Projecte=bt5m&Codi=%s&piramide=True", None),
    ("topografia-territorial", "Referencial topogràfic territorial", 50, 50000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=bt5m&Format=GEOTIFF&Projecte=topografia-territorial&Codi=%s&piramide=True", None),

    ("mtc25m", "Mapa topogràfic 1:25.000", 250, 1250000000, None, None, None, None, ["", "pol", "mu", "co"], "mtc25m.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc25m&Format=GEOTIFF&Projecte=mtc25m&Codi=%s&piramide=True", None),
    ("mtc50m", "Mapa topogràfic 1:50.000", 500, 5000000000, None, None, None, None, ["", "pol", "mu", "co"], "mtc50m.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc50m&Format=GEOTIFF&Projecte=mtc50m&Codi=%s&piramide=True", None),
    ("mtc100m", "Mapa topogràfic 1:100.000", 1000, 20000000000, None, None, None, None, ["", "pol", "mu", "co"], "mtc100m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc100m&Format=GEOTIFF&Projecte=mtc100m&Codi=%s&piramide=True", None),
    ("mtc250m", "Mapa topogràfic 1:250.000", 2500, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc250m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc250m&Format=GEOTIFF&Projecte=mtc250m&Codi=%s&piramide=True", None),
    ("mtc500m", "Mapa topogràfic 1:500.000", 5000, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc500m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc500m&Format=GEOTIFF&Projecte=mtc500m&Codi=%s&piramide=True", None),
    ("mtc1000m", "Mapa topogràfic 1:1.000.000", 10000, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc1000m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc1000m&Format=GEOTIFF&Projecte=mtc1000m&Codi=%s&piramide=True", None),
    ("mtc2000m", "Mapa topogràfic 1:2.000.000", 20000, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc2000m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc2000m&Format=GEOTIFF&Projecte=mtc2000m&Codi=%s&piramide=True", None),

    ("ct1m", "Cartografia topogràfica 1:1.000", None, 2000000, None, None, None, None, ["", "pol", "mu"], "ct1m.zip", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=ct1m&Codi=%s",
        ("http://www.icc.cat/appdownloads/lib/json/ct1m_id.json", "ct1m_disponible.qml")),

    #("bm5m", "Base municipal 1:5.000", None, None, ["cat", "tot"], "bm5m.zip", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=bm5m&Codi=%s", None),
    ("divisions-administratives", "Divisions administratives", None, None, None, None, None, None, ["cat"], "divisions-administratives.zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=divisions-administratives&Codi=%s", None),

    ("topografia-territorial-gpkg", "Referencial topogràfic territorial GeoPackage", 50, 100000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.gpkg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
    ("topografia-territorial-dgn", "Referencial topogràfic territorial DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt&Codi=%s", None),
    ("topografia-territorial-dwg", "Referencial topogràfic territorial DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt&Codi=%s", None),
    ("topografia-territorial-3d-dgn", "Referencial topogràfic territorial 3D DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt3&Codi=%s", None),
    ("topografia-territorial-3d-dwg", "Referencial topogràfic territorial 3D DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt3d&Codi=%s", None),
    ("topografia-territorial-volum-dwg", "Referencial topogràfic territorial Volum DWG", 50, 12500000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-volum.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&gen_volum=si&file_name=ttvolum&Codi=%s", None),

    ("cobertes-sol-raster", "Mapa de cobertes del sòl", 100, 200000000, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "cobertes-sol.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mcsc&Format=GEOTIFF&Projecte=cobertes-sol&Codi=%s&piramide=True", None),
    ("cobertes-sol-vector", "Mapa de cobertes del sòl", None, 400000000, None, None, None, None, ["", "pol", "mu", "co"], "cobertes-sol.gpkg", "cat_limits", "%s/fmedatastreaming/cobertes-sol/ICGC_cobertes-sol_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),

    ("met2", "MET 2m", 200, 800000000, None, None, None, None, ["", "pol", "mu", "co"], "met2.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met2&Format=GEOTIFF&Projecte=met2&Codi=%s&piramide=True", None),
    ("met5", "MET 5m", 500, 5000000000, None, None, None, None, ["", "pol", "mu", "co"], "met5.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met5m&Format=GEOTIFF&Projecte=met5&Codi=%s&piramide=True", None),

    ("mggt1", "GT I. Mapa geològic 1:25.000", None, None, None, None, None, None, ["tot"], "gt1.zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt125m&Codi=%s", None),
    ("mg50m", "Mapa Geològic 1:50.000", None, None, None, None, None, None, ["tot"], "mg50m.zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=mg50m&Codi=%s", None),
    ("mg250m", "Mapa geològic 1:250.000", None, None, None, None, None, None, ["tot"], "mg250m.zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=mg250m&Codi=%s", None),
    ("mggt6", "GT VI. Mapa per a la prevenció dels riscos geològics 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt6.zip", "25k_limits", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt6&Codi=%s",
        ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_VI", "", "image/png")),
    # Pending revision of symbology
    #("gt2", "GT II. ...  1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt2.zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt2&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_II", "", "image/png")),
    #("gt3", "GT III. ... 1:5.000", None, 50000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt3.zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt3&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_III", "", "image/png")),
    #("gt4", "GT IV. ... 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt4.zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt4&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_IV", "", "image/png")),
    #("gt5", "GT V. ... 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt5.zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt5&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_V", "", "image/png")),
    #("mah250m", "Mapa Àrees Hidrogeològiques 1:250.000", None, 50000000, None, None, None, ["cat", "tot"], "mah250m.zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=mah250m&Codi=%s", None),

    ("photo", "Fototeca digital", None, None, 100, 100000000, None, None, ["", "pol"], "photo.tif", "cat_rect", "%s/fmedatastreaming/Fototeca/ICGC_fototeca_download.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&Any=%s&CodiVol=%s&NomFoto=%s&Nom=%s", None),
    ]
services_dict = dict([(id, (name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple)) for (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple) in services_list])

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


def get_historic_ortho_dict(urlbase="https://datacloud.icgc.cat/datacloud/orto-territorial/gpkg_unzip", \
        file_pattern=r"(ortofoto-(\w+)-(\d+)(c*m)-(\w+)-(\d{4})\.gpkg)"):
    """ Obté les ortofotos històriques disponibles per descàrrega """
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
        url_filename = "/vsicurl/" + urlbase + "/" + filename

        # Adds current resolution
        add_data(data_dict, color_not_irc, gsd, year, url_filename, gsd)
        # Adds default resolutions if not exist default resolution or previous source gsd is worse
        for default_gsd in default_gsd_list:
            if gsd < default_gsd:
                source_gsd = get_source_gsd(data_dict, color_not_irc, default_gsd, year)
                if not source_gsd or abs(gsd - default_gsd) < abs(source_gsd - default_gsd):
                    add_data(data_dict, color_not_irc, default_gsd, year, url_filename, gsd)
   
    return data_dict

historic_ortho_dict = {}
def get_historic_ortho_years(rgb_not_irc, gsd):
    """ Obté els anys disponibles per un tipus d'orto (RGB/IRC) i GSD """
    global historic_ortho_dict
    if not historic_ortho_dict:
        historic_ortho_dict = get_historic_ortho_dict()
    
    gsd_dict = historic_ortho_dict.get(rgb_not_irc, None)
    if not gsd_dict:
        return []
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return []
    return list(years_dict.keys())

def get_historic_ortho_file(rgb_not_irc, gsd, year):
    """ Obté el fitxer assicat a una ortofoto color/resolució/any """
    global historic_ortho_dict
    if not historic_ortho_dict:
        historic_ortho_dict = get_historic_ortho_dict()
    
    gsd_dict = historic_ortho_dict.get(rgb_not_irc, None)
    if not gsd_dict:
        return None
    years_dict = gsd_dict.get(gsd, None)
    if not years_dict:
        return None
    filename_and_source_gsd = years_dict.get(year, None) # Tuple (filename, source_gsd)
    return filename_and_source_gsd[0] if filename_and_source_gsd else None 

def get_historic_ortho_code(rgb_not_irc, gsd, year):
    """ Obté el codi de descàrrega FME associat a una ortofoto color/resolució/any """
    filename = get_historic_ortho_file(rgb_not_irc, gsd, year)
    if filename:
        filename = os.path.splitext(os.path.basename(filename))[0]
    return filename

def get_historic_ortho_ref(rgb_not_irc, gsd, year):
    """ Obté l'arxiu de referència associat a una ortofoto color/resolució/any """
    return get_historic_ortho_file(rgb_not_irc, gsd, year)

def get_services():
    """ Retorna la llista de productes descarregables """
    final_services_list = []

    for id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple in services_list:
        # Injectem anys d'ortofoto si cal
        if time_list == FME_AUTO_SEARCH:
            color_not_irc = name.lower().find("infraroja") < 0
            time_list = get_historic_ortho_years(color_not_irc, gsd)
        # Injectem el path dels arxiu .qml
        if ref_tuple and len(ref_tuple) == 2:
            ref_file, style_file = ref_tuple
            style_file = os.path.join(os.path.dirname(__file__), "symbols", style_file)
            ref_tuple = (ref_file, style_file)
        # Afegim els valors modificats a la llista
        final_services_list.append((id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple))

    log.debug("FME resources URL: %s found: %s", FME_URL.split("/")[0] + "//" +  FME_URL.split("@")[1], len(final_services_list))
    return final_services_list

def get_clip_data_url(data_type, mode, xmin, ymin, xmax, ymax, points_list=[], extra_params=[], referrer=None, url_base=FME_URL):
    """ Retorna la petició URL FME per descarregar un producte """
    _name, _min_side, _max_query_area, _min_px_side, _max_px_area, _gsd, _time_list, download_list, _filename, _limits, url_pattern, _url_ref_or_wms_tuple = services_dict.get(data_type, (None, None, None, None, None, None, None, None, None, None, None, None))
    rect_list = [("%.2f" % v if v is not None else "") for v in [xmin, ymin, xmax, ymax]]
    points_list = [",".join(["%.2f %.2f" % (x, y) for x, y in points_list])] if "pol" in download_list else [None]
    values_list = [url_base] + rect_list + points_list + [mode] + extra_params
    url = (url_pattern % tuple(values_list)) if url_pattern else None
    if url and referrer:
        url += "&referrer=%s" % referrer
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

