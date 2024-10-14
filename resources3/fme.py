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
import datetime
from importlib import reload

from . import http
reload(http)
from .http import get_historic_ortho_years, get_coastline_years, get_coastline_filenames

# Configure internal library logger (Default is dummy logger)
import logging
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())


#FME_URL = "https://qgis:qgis@sefme2022dev" # A linux no va bé el DNS, ca posar la IP (desenvolupament)
#FME_URL = "https://qgis:qgis@sefme2020prod.icgc.local" # Test
FME_URL = "https://qgis:qgis@descarregues.icgc.cat" # Servidor extern / adreça externa (producció)

FME_DOWNLOAD_EPSG = 25831
FME_MAX_POLYGON_POINTS = 100


###############################################################################
# Define list of services availables

services_list = [
    # (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_type_list, default_filename, 
    #    download_limits_id, url_pattern, <(url_ref, qml_style) | (wms_url, wms_layer, wms_style, wms_format)>),
    ("of25c", "Ortofoto color vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "of25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=0.25", \
        None),
    ("of5m", "Ortofoto color vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "of50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=0.50", \
        None),
    ("of25m", "Ortofoto color vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=2.50", \
        None),

    ("hc10cm", "Ortofoto color històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_ortho_years(True, 0.1), ["", "pol"], "of10cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
        (None, "orto-historica.qml")),
    ("hc15cm", "Ortofoto color històrica 15cm 1:1.500", 15, 4500000, None, None, 0.15, get_historic_ortho_years(True, 0.15), ["", "pol"], "of15cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.15", \
        (None, "orto-historica.qml")),
    ("hc25cm", "Ortofoto color històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, get_historic_ortho_years(True, 0.25), ["", "pol"], "of25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
        (None, "orto-historica.qml")),
    ("hc50cm", "Ortofoto color històrica 50cm 1:5.000", 50, 50000000, None, None, 0.50, get_historic_ortho_years(True, 0.50), ["", "pol", "mu"], "of50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
        (None, "orto-historica.qml")),
    ("hc1m", "Ortofoto color històrica 1m 1:10.000", 100, 200000000, None, None, 1, get_historic_ortho_years(True, 1), ["", "pol", "mu"], "of1m.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
        (None, "orto-historica.qml")),
    ("hc250cm", "Ortofoto color històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, get_historic_ortho_years(True, 2.5), ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
        (None, "orto-historica.qml")),

    ("oi25c", "Ortofoto infraroja vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "oi25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=0.25", \
        None),
    ("oi5m", "Ortofoto infraroja vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "oi50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=0.50", \
        None),
    ("oi25m", "Ortofoto infraroja vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=2.50", \
        None),

    ("hi10cm", "Ortofoto infraroja històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_ortho_years(False, 0.1), ["", "pol"], "oi10cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
        (None, "orto-historica.qml")),
    ("hi25cm", "Ortofoto infraroja històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, get_historic_ortho_years(False, 0.25), ["", "pol"], "oi25cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
        (None, "orto-historica.qml")),
    ("hi50cm", "Ortofoto infraroja històrica 50cm 1:5.000", 50, 50000000, None, None, 0.5, get_historic_ortho_years(False, 0.5), ["", "pol", "mu"], "oi50cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
        (None, "orto-historica.qml")),
    ("hi1m", "Ortofoto infraroja històrica 1m 1:10.000", 100, 200000000, None, None, 1, get_historic_ortho_years(False, 1), ["", "pol", "mu"], "oi1m.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
        (None, "orto-historica.qml")),
    ("hi250cm", "Ortofoto infraroja històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, get_historic_ortho_years(False, 2.5), ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", \
        "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
        (None, "orto-historica.qml")),

    ("of-lidar-territorial", "Lidar territorial ortofoto color 15cm 2021-2023", 100, 4500000, None, None, 0.15, ["2021-2023"], ["", "pol"], "lidar_rgb.tif", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial-ortofoto_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=lidar-territorial-ortofoto-rgb-15cm", None),
    ("oi-lidar-territorial", "Lidar territorial ortofoto infraroja 15cm 2021-2023", 100, 4500000, None, None, 0.15, ["2021-2023"], ["", "pol"], "lidar_irc.tif", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial-ortofoto_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=lidar-territorial-ortofoto-irc-15cm", None),

    ("topografia-territorial", "Referencial topogràfic territorial", 50, 50000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=bt5m&Format=GEOTIFF&Projecte=topografia-territorial&Codi=%s&piramide=True", None),

    ("mtc250m", "Mapa topogràfic 1:250.000", 2500, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc250m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc250m&Format=GEOTIFF&Projecte=mtc250m&Codi=%s&piramide=True", None),
    ("mtc1000m", "Mapa topogràfic 1:1.000.000", 10000, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "mtc1000m.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mtc1000m&Format=GEOTIFF&Projecte=mtc1000m&Codi=%s&piramide=True", None),

    ("ct1m", "Cartografia topogràfica 1:1.000", None, 2000000, None, None, None, None, ["", "pol", "mu"], "ct1m.shp-zip", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=ct1m&Codi=%s",
        ("https://datacloud.icgc.cat/datacloud/ct1m_ETRS89/json_tall/ct1m_id.json", "ct1m_disponible.qml")),

    ("divisions-administratives", "Divisions administratives", None, None, None, None, None, None, ["cat"], "divisions-administratives.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=divisions-administratives&Codi=%s", None),

    ("topografia-territorial-gpkg", "Referencial topogràfic territorial GeoPackage", 50, 100000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.gpkg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
    ("topografia-territorial-dgn", "Referencial topogràfic territorial DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt&Codi=%s", None),
    ("topografia-territorial-dwg", "Referencial topogràfic territorial DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt&Codi=%s", None),
    ("topografia-territorial-3d-gpkg", "Referencial topogràfic territorial 3D GeoPackage", 50, 100000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.gpkg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&geopackage_out=tt3&dimensio=3d&Codi=%s", None),
    ("topografia-territorial-3d-dgn", "Referencial topogràfic territorial 3D DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt3&Codi=%s", None),
    ("topografia-territorial-3d-dwg", "Referencial topogràfic territorial 3D DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt3d&Codi=%s", None),
    ("topografia-territorial-volum-dwg", "Referencial topogràfic territorial Volum DWG", 50, 12500000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-volum.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&gen_volum=si&file_name=ttvolum&Codi=%s", None),
    ("topografia-territorial-bim-ifc", "Referencial topogràfic territorial BIM", None, None, None, None, None, None, ["full"], "topografia-territorial-bim.ifc-zip", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_download_IFC.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&file_name=tt&Codi=%s", 
        ("https://datacloud.icgc.cat/datacloud/talls_ETRS89/vigent/json_unzip/tall5m.json", "tall-5k.qml")),

    ("cobertes-sol-raster", "Mapa de cobertes del sòl", 100, 200000000, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "cobertes-sol.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mcsc&Format=GEOTIFF&Projecte=cobertes-sol&Codi=%s&piramide=True", None),
    ("cobertes-sol-vector", "Mapa de cobertes del sòl", None, 400000000, None, None, None, None, ["", "pol", "mu", "co"], "cobertes-sol.gpkg", "cat_limits", "%s/fmedatastreaming/cobertes-sol/ICGC_cobertes-sol_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),

    ("met2", "MET 2m", 200, 800000000, None, None, None, None, ["", "pol", "mu", "co"], "met2.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met2&Format=GEOTIFF&Projecte=met2&Codi=%s&piramide=True", None),
    ("met5", "MET 5m", 500, 5000000000, None, None, None, None, ["", "pol", "mu", "co"], "met5.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met5m&Format=GEOTIFF&Projecte=met5&Codi=%s&piramide=True", None),

    ] + [                          
    ("mggt1", "GT I. Mapa geològic 1:25.000", None, None, None, None, None, None, ["tot"], "gt1.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt125m&Codi=%s", None),
    ("mg50m", "Mapa Geològic 1:50.000", None, None, None, None, None, None, ["tot"], "mg50m.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=mg50m&Codi=%s", None),
    ("mg250m", "Mapa geològic 1:250.000", None, 250000000000, None, None, None, None, ["", "pol", "co", "tot"], "mg250m.gpkg", "cat_limits", "%s/fmedatastreaming/geologia-territorial/ICGC_geologia-territorial-250000-geologic_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
    ("mg250m-raster", "Mapa geològic 1:250.000", 100, 125000000000, None, None, None, None, ["", "pol", "co", "cat", "tot"], "mg250m.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mg250mm&Format=GEOTIFF&Projecte=mg250m&Codi=%s&piramide=True", None),
    ("mggt6", "GT VI. Mapa per a la prevenció dels riscos geològics 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt6.shp-zip", "25k_limits", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt6&Codi=%s",
        ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_VI", "", "image/png")),
    # Pending revision of symbology
    #("gt2", "GT II. ...  1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt2.shp-zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt2&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_II", "", "image/png")),
    #("gt3", "GT III. ... 1:5.000", None, 50000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt3.shp-zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt3&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_III", "", "image/png")),
    #("gt4", "GT IV. ... 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt4.shp-zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt4&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_IV", "", "image/png")),
    #("gt5", "GT V. ... 1:25.000", None, 1250000000, None, None, None, None, ["", "mu", "co", "cat", "tot"], "gt5.shp-zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt5&Codi=%s",
    #    ("https://geoserveis.icgc.cat/icgc_geotreballs/wms/service", "geotreball_V", "", "image/png")),
    #("mah250m", "Mapa Àrees Hidrogeològiques 1:250.000", None, 50000000, None, None, None, ["cat", "tot"], "mah250m.shp-zip", "cat_simple", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=mah250m&Codi=%s", None),

    ("lidar-territorial", "Lidar Territorial 2021-2023", None, None, None, None, None, ["2021-2023"], ["full"], "lidar.laz", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&Projecte=lidar&Codi=%s", 
        ("https://datacloud.icgc.cat/datacloud/lidar-territorial/json/lidar-territorial-tall.json", "tall-5k.qml")),

    ("photo", "Fotogrames", None, None, 100, 100000000, None, None, ["", "pol", "tot"], "photo.tif", "cat_rect", "%s/fmedatastreaming/Fototeca/ICGC_fototeca_download.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&Any=%s&CodiVol=%s&NomFoto=%s&Nom=%s", None),
    ]
services_dict = dict([(id, (name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple)) for (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple) in services_list])

def get_services():
    """ Retorna una llista de tuples de productes descarregables amb els valors:
            (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, 
            download_list, default_filename, limits, url_pattern, ref_tuple, enabled)
        """
    final_services_list = []
    t0 = datetime.datetime.now()
    for id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple in services_list:        
        # Si ens passen un time_list buit (no None) desactivem la entrada
        enabled = time_list is None or len(time_list) > 0
        # Injectem el path dels arxiu .qml
        if ref_tuple and len(ref_tuple) == 2:
            ref_file, style_file = ref_tuple
            style_file = os.path.join(os.path.dirname(__file__), "symbols", style_file)
            ref_tuple = (ref_file, style_file)
        # Afegim els valors modificats a la llista
        final_services_list.append((id, name, min_side, max_query_area, min_px_side, max_px_area, \
            gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple, enabled))
    t1 = datetime.datetime.now()

    log.debug("FME resources URL: %s found: %s (%s)", FME_URL.split("/")[0] + "//" +  FME_URL.split("@")[1], len(final_services_list), t1-t0)
    return final_services_list

def get_clip_data_url(data_type, mode, xmin, ymin, xmax, ymax, points_list=[], extra_params=[], referrer=None, url_base=FME_URL):
    """ Retorna la petició URL FME per descarregar un producte """
    _name, _min_side, _max_query_area, _min_px_side, _max_px_area, _gsd, _time_list, download_list, _filename, _limits, url_pattern, _url_ref_or_wms_tuple = services_dict.get(data_type, (None, None, None, None, None, None, None, None, None, None, None, None))
    rect_list = [("%.2f" % v if v is not None else "0") for v in [xmin, ymin, xmax, ymax]]
    points_list = [",".join(["%.2f %.2f" % (x, y) for x, y in points_list])] if "pol" in download_list else [""]
    values_list = [url_base] + rect_list + points_list + [mode] + extra_params
    url = (url_pattern % tuple(values_list)) if url_pattern else None
    if url and referrer:
        url += "&referrer=%s" % referrer
    return url


###############################################################################
# Define dict data filters availables
filters_list = { # (product_code, filter_text)
    "lidar-territorial": "Classification = 0"
    }

def get_data_filters():
    """ Retorna diccionari amb els filters de dades disponibles """
    return filters_list


###############################################################################
# Define list styles availables

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

