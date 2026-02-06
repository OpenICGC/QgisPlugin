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

import re
import os
import datetime
from importlib import reload

from . import http
reload(http)
from .http import get_historic_ortho_years, get_historic_local_ortho_years, get_coast_orthophoto_years
from .http import get_coastline_years, get_coast_lidar_time, get_dtm_time

# Configure internal library logger (Default is dummy logger)
import logging
reload(logging)
log = logging.getLogger('dummy')
log.addHandler(logging.NullHandler())

# Set server URL
#FME_URL = "https://qgis:qgis@sefme2022dev" # A linux no va bé el DNS, ca posar la IP (desenvolupament)
#FME_URL = "https://qgis:qgis@sefme2022prod.icgc.local" # Test alies de descarreges.icgc.cat
FME_URL = "https://qgis:qgis@descarregues.icgc.cat" # Servidor extern / adreça externa (producció)

# Set server properties
FME_DOWNLOAD_EPSG = 25831
FME_MAX_POLYGON_POINTS = 100
FME_MAX_ASPECT_RATIO = 5

# Cache services variables
services_list = []
services_dict = {}


def get_services_list():
    """ Retorna una llista dels serveis disponibles (catxejada en variable global)
        ---
        Returns available services dictionary (cached on globar variable)
    """
    global services_list
    if not services_list:
        services_list = [
            # (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_type_list, default_filename,
            #    download_limits_id, url_pattern, <(url_ref, qml_style) | (wms_url, wms_layer, wms_style, wms_format)>),
            # ATTENTION! id field can specify a product group using "/" separator:
            #   "orto-color/of25c" -> group: orto-color product_id: of25c

            # GROUP orthophoto color
            # Current orthophoto color (gsd auto group)
            ("orto-color/of25c", "Ortofoto color vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "of25cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=0.25", None),
            ("orto-color/of5m", "Ortofoto color vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "of50cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=0.50", None),
            ("orto-color/of25m", "Ortofoto color vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_vigent&gsd=2.50", None),
            # Historic orthophoto color (gsd auto group)
            ("orto-color/hc10cm", "Ortofoto color històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_ortho_years(True, 0.1), ["", "pol"], "of10cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
                (None, "orto-historica.qml")),
            ("orto-color/hc15cm", "Ortofoto color històrica 15cm 1:1.500", 15, 4500000, None, None, 0.15, get_historic_ortho_years(True, 0.15), ["", "pol"], "of15cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.15", \
                (None, "orto-historica.qml")),
            ("orto-color/hc25cm", "Ortofoto color històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, get_historic_ortho_years(True, 0.25), ["", "pol"], "of25cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
                (None, "orto-historica.qml")),
            ("orto-color/hc50cm", "Ortofoto color històrica 50cm 1:5.000", 50, 50000000, None, None, 0.50, get_historic_ortho_years(True, 0.50), ["", "pol", "mu"], "of50cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
                (None, "orto-historica.qml")),
            ("orto-color/hc1m", "Ortofoto color històrica 1m 1:10.000", 100, 200000000, None, None, 1, get_historic_ortho_years(True, 1), ["", "pol", "mu"], "of1m.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
                (None, "orto-historica.qml")),
            ("orto-color/hc250cm", "Ortofoto color històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, get_historic_ortho_years(True, 2.5), ["", "pol", "mu", "co"], "of250cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
                (None, "orto-historica.qml")),
            # Local orthophoto color
            ("orto-color/olc10cm", "Ortofoto local color vigent 10cm 1:1.000", 10, 2000000, None, None, 0.1, None, ["", "pol"], "orto-local-color-10cm.tif", "cat_limits", \
                "%s/fmedatastreaming/orto-local/ICGC_orto-local_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=rgb_10cm_vigent", \
                ("https://datacloud.icgc.cat/datacloud/orto-local/json_unzip/orto-local-rgb-10cm-vigent.json", "tall-5k.qml")),
            ("orto-color/hlc10cm", "Ortofoto local color històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_local_ortho_years(True, 0.1), ["", "pol"], "orto-local-color-10cm.tif", "cat_limits", \
                "%s/fmedatastreaming/orto-local/ICGC_orto-local_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s", \
                (None, "tall-5k.qml")),
            # LiDAR orthophoto color
            ("orto-color/of-lidar-territorial", "Lidar territorial ortofoto color 15cm 2021-2023", 100, 4500000, None, None, 0.15, ["2021-2023"], ["", "pol"], "lidar_rgb.tif", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial-ortofoto_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=lidar-territorial-ortofoto-rgb-15cm", None),

            # GROUP orthophoto infrared
            # Current orthophoto infrared (gsd auto group)
            ("orto-irc/oi25c", "Ortofoto infraroja vigent 25cm 1:2.500", 25, 12500000, None, None, 0.25, None, ["", "pol"], "oi25cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=0.25", None),
            ("orto-irc/oi5m", "Ortofoto infraroja vigent 50cm 1:5.000", 50, 50000000, None, None, 0.5, None, ["", "pol", "mu"], "oi50cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=0.50", None),
            ("orto-irc/oi25m", "Ortofoto infraroja vigent 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, None, ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_vigent&gsd=2.50", None),
            # Historic orthophoto infrared (gsd auto group)
            ("orto-irc/hi10cm", "Ortofoto infraroja històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_ortho_years(False, 0.1), ["", "pol"], "oi10cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.1", \
                (None, "orto-historica.qml")),
            ("orto-irc/hi25cm", "Ortofoto infraroja històrica 25cm 1:2.500", 25, 12500000, None, None, 0.25, get_historic_ortho_years(False, 0.25), ["", "pol"], "oi25cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.25", \
                (None, "orto-historica.qml")),
            ("orto-irc/hi50cm", "Ortofoto infraroja històrica 50cm 1:5.000", 50, 50000000, None, None, 0.5, get_historic_ortho_years(False, 0.5), ["", "pol", "mu"], "oi50cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=0.5", \
                (None, "orto-historica.qml")),
            ("orto-irc/hi1m", "Ortofoto infraroja històrica 1m 1:10.000", 100, 200000000, None, None, 1, get_historic_ortho_years(False, 1), ["", "pol", "mu"], "oi1m.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=1", \
                (None, "orto-historica.qml")),
            ("orto-irc/hi250cm", "Ortofoto infraroja històrica 2.5m 1:25.000", 250, 1250000000, None, None, 2.5, get_historic_ortho_years(False, 2.5), ["", "pol", "mu", "co"], "oi250cm.tif", "5k_limits", \
                "%s/fmedatastreaming/orto-territorial/ICGC_orto-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&gsd=2.5", \
                (None, "orto-historica.qml")),
            # Local orthophoto infrared
            ("orto-irc/oli10cm", "Ortofoto local infraroja vigent 10cm 1:1.000", 10, 2000000, None, None, 0.1, None, ["", "pol"], "orto-local-irc-10cm.tif", "cat_limits", \
                "%s/fmedatastreaming/orto-local/ICGC_orto-local_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=irc_10cm_vigent", \
                ("https://datacloud.icgc.cat/datacloud/orto-local/json_unzip/orto-local-irc-10cm-vigent.json", "tall-5k.qml")),
            ("orto-irc/hli10cm", "Ortofoto local infraroja històrica 10cm 1:1.000", 10, 2000000, None, None, 0.1, get_historic_local_ortho_years(False, 0.1), ["", "pol"], "orto-local-color-10cm.tif", "cat_limits", \
                "%s/fmedatastreaming/orto-local/ICGC_orto-local_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s", \
                (None, "tall-5k.qml")),
            # LiDAR orthopho infrared
            ("orto-irc/oi-lidar-territorial", "Lidar territorial ortofoto infraroja 15cm 2021-2023", 100, 4500000, None, None, 0.15, ["2021-2023"], ["", "pol"], "lidar_irc.tif", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial-ortofoto_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=lidar-territorial-ortofoto-irc-15cm", None),

            # GROUP administrative divisions
            # Administrative divisions (prefix_id auto group)
            ("divisions-administratives/divisions-administratives-shp", "Divisions administratives ShapeFile", None, None, None, None, None, None, ["cat"], "divisions-administratives.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=divisions-administratives&Codi=%s", None),
            ("divisions-administratives/divisions-administratives-gpkg", "Divisions administratives GeoPackage", None, None, None, None, None, None, ["cat"], "divisions-administratives.gpkg", None, "%s/fmedatastreaming/divisions-administratives/ICGC_divisions-administratives_download.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=divisions-administratives&Codi=%s&format=gpkg", None),
            ("divisions-administratives/divisions-administratives-dwg", "Divisions administratives DWG", None, None, None, None, None, None, ["cat"], "divisions-administratives.dwg", None, "%s/fmedatastreaming/divisions-administratives/ICGC_divisions-administratives_download.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=divisions-administratives&Codi=%s&format=dwg", None),
            # Orther administrative divisions
            ("divisions-administratives/entitats-municipals-descentralitzades", "Decentraliced municipal entities", None, None, None, None, None, None, ["cat"], "entitats-municipals-descentralitzades.gpkg", None, "%s/fmedatastreaming/Descarrega_basica/ICGC_descarrega_producte.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&producte=entitats-municipals-descentralitzades&format=gpkg", None),
            ("divisions-administratives/bsenccen", "Seccions censals", None, None, None, None, None, None, ["cat"], "seccions-censals.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&Projecte=bseccen", None),
            ("divisions-administratives/arees-poblament", "Population zones", None, None, None, None, None, None, ["cat"], "arees-poblament.gpkg", None, "%s/fmedatastreaming/Descarrega_basica/ICGC_descarrega_producte.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&producte=arees-poblament&format=gpkg", None),

            # Topographic maps raster (prefix_id auto group)
            ("topografia-territorial", "Referencial topogràfic territorial", 50, 50000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=bt5m&Format=GEOTIFF&Projecte=topografia-territorial&Codi=%s&piramide=True", None),
            ("topografia-250000", "Mapa topogràfic 1:250.000", 2500, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "topografia-250000.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=topografia-250000&Format=GEOTIFF&Projecte=topografia-250000&Codi=%s&piramide=True", None),
            ("topografia-1000000", "Mapa topogràfic 1:1.000.000", 10000, None, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "topografia-1000000.tif", "cat_rect", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=topografia-1000000&Format=GEOTIFF&Projecte=topografia-1000000&Codi=%s&piramide=True", None),
            # GROUP topographic maps
            # Territorial topography vectorial (prefix_id auto group)
            ("mapa-topo/topografia-territorial-gpkg", "Referencial topogràfic territorial GeoPackage", 50, 100000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.gpkg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
            ("mapa-topo/topografia-territorial-dgn", "Referencial topogràfic territorial DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt&Codi=%s", None),
            ("mapa-topo/topografia-territorial-dwg", "Referencial topogràfic territorial DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt&Codi=%s", None),
            ("mapa-topo/topografia-territorial-dwg-object-data", "Referencial topogràfic territorial DWG object-data", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-od.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt&Codi=%s&format_od=Si", None),
            ("mapa-topo/topografia-territorial-3d-gpkg", "Referencial topogràfic territorial 3D GeoPackage", 50, 100000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.gpkg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&geopackage_out=tt3&dimensio=3d&Codi=%s", None),
            ("mapa-topo/topografia-territorial-3d-dgn", "Referencial topogràfic territorial 3D DGN", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dgn", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DGN&file_name=tt3&Codi=%s", None),
            ("mapa-topo/topografia-territorial-3d-dwg", "Referencial topogràfic territorial 3D DWG", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt3d&Codi=%s", None),
            ("mapa-topo/topografia-territorial-3d-dwg-object-data", "Referencial topogràfic territorial 3D DWG object-data", 50, 25000000, None, None, None, None, ["", "pol", "mu"], "topografia-territorial-3d-od.dwg", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_clip_to_CAD3D.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&format_cad=DWG&file_name=tt3d&Codi=%s&format_od=Si", None),
            ("mapa-topo/topografia-territorial-bim-ifc", "Referencial topogràfic territorial BIM", None, None, None, None, None, None, ["full"], "topografia-territorial-bim.ifc-zip", "5k_limits", "%s/fmedatastreaming/topografia-territorial/ICGC_topografia-territorial_download_IFC.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&file_name=tt&Codi=%s",
                ("https://datacloud.icgc.cat/datacloud/talls_ETRS89/vigent/json_unzip/tall5m.json", "tall-5k.qml")),
            # Local territorial topography vectorial (prefix_id auto group)
            ("mapa-topo/referencial-topografic-local-gpkg", "Referencial topogràfic local GeoPackage", None, None, None, None, None, None, ["full"], "topografia-local.gpkg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=gpkg&dimension=2d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-dgn", "Referencial topogràfic local DGN", None, None, None, None, None, None, ["full"], "topografia-local.dgn", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dgn&dimension=2d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-dwg", "Referencial topogràfic local DWG", None, None, None, None, None, None, ["full"], "topografia-local.dwg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dwg&dimension=2d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-dwg-object-data", "Referencial topogràfic local DWG object-data", None, None, None, None, None, None, ["full"], "topografia-local-od.dwg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dwg&format_od=Si&dimension=2d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            # Pending revision of symbology
            #("mapa-topo/referencial-topografic-local-gdb", "Referencial topogràfic local GDB", None, None, None, None, None, None, ["full"], "topografia-local.gdb-zip", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=gdb&dimension=2d",
            #    ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-3d-gpkg", "Referencial topogràfic local 3D GeoPackage", None, None, None, None, None, None, ["full"], "topografia-local-3d.gpkg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=gpkg&dimensio=3d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-3d-dgn", "Referencial topogràfic local 3D DGN", None, None, None, None, None, None, ["full"], "topografia-local-3d.dgn", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dgn&dimensio=3d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-3d-dwg", "Referencial topogràfic local 3D DWG", None, None, None, None, None, None, ["full"], "topografia-local-3d.dwg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dwg&dimension=3d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-3d-dwg-object-data", "Referencial topogràfic local 3D DWG object-data", None, None, None, None, None, None, ["full"], "topografia-local-3d-od.dwg", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=dwg&format_od=Si&dimension=3d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            ("mapa-topo/referencial-topografic-local-bim-ifc", "Referencial topogràfic local BIM", None, None, None, None, None, None, ["full"], "topografia-local-bim.ifc-zip", "cat_limits", "%s/fmedatastreaming/topografia-local/ICGC_topografia-local_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&format=ifc&dimension=2d",
                ("http://datacloud.icgc.cat/datacloud/topografia-local/json/topografia-local-tall.json", "tall-5k.qml")),
            # Topographics maps vectorial
            ("mapa-topo/ct1m", "Cartografia topogràfica 1:1.000", None, 2000000, None, None, None, None, ["", "pol", "mu"], "ct1m.shp-zip", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=ct1m&Codi=%s",
                ("https://datacloud.icgc.cat/datacloud/ct1m_ETRS89/json_tall/ct1m_id.json", "ct1m_disponible.qml")),

            # Ground maps
            ("cobertes-sol-raster", "Mapa de cobertes del sòl", 100, 200000000, None, None, None, None, ["", "pol", "mu", "co", "cat", "tot"], "cobertes-sol.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mcsc&Format=GEOTIFF&Projecte=cobertes-sol&Codi=%s&piramide=True", None),
            ("cobertes-sol-vector", "Mapa de cobertes del sòl", None, 400000000, None, None, None, None, ["", "pol", "mu", "co"], "cobertes-sol.gpkg", "cat_limits", "%s/fmedatastreaming/cobertes-sol/ICGC_cobertes-sol_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),

            # DTMs (prefix_id auto group)
            #("met2", "MET 2m", 200, 800000000, None, None, None, None, ["", "pol", "mu", "co"], "met2.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met2&Format=GEOTIFF&Projecte=met2&Codi=%s&piramide=True", None),
            #("met5", "MET 5m", 500, 5000000000, None, None, None, None, ["", "pol", "mu", "co"], "met5.tif", "5k_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=met5m&Format=GEOTIFF&Projecte=met5&Codi=%s&piramide=True", None),
            # model-elevacions-terreny
            ("elevacions/met25cm", "MET 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("met25cm"), ["", "pol"], "met25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny&nom=met-x",
                (None, "tall-5k.qml")),
            ("elevacions/met50cm", "MET 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("met50cm"), ["", "pol", "mu"], "met50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny&nom=met-x",
                (None, "tall-5k.qml")),
            ("elevacions/met1m", "MET 1m", 100, 200000000, None, None, 1, get_dtm_time("met1m"), ["", "pol", "mu"], "met1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny&nom=met-x",
                (None, "tall-5k.qml")),
            ("elevacions/met2m", "MET 2m", 200, 800000000, None, None, 2, get_dtm_time("met2m"), ["", "pol", "mu"], "met2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny&nom=met-x",
                (None, "tall-5k.qml")),
            ("elevacions/met5m", "MET 5m", 500, 5000000000, None, None, 5, get_dtm_time("met5m"), ["", "pol", "mu", "co"], "met5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny&nom=met-x",
                (None, "tall-5k.qml")),
            # # model-elevacions-terreny-edificis
            # ("elevacions/ed25cm", "MET Ed 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("ed25cm"), ["", "pol"], "mete25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis&nom=met-ed-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/ed50cm", "MET Ed 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("ed50cm"), ["", "pol", "mu"], "mete50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis&nom=met-ed-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/ede1m", "MET Ed 1m", 100, 200000000, None, None, 1, get_dtm_time("ed1m"), ["", "pol", "mu"], "mete1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis&nom=met-ed-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/ed2m", "MET Ed 2m", 200, 800000000, None, None, 2, get_dtm_time("ed2m"), ["", "pol", "mu"], "mete2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis&nom=met-ed-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/ed5m", "MET Ed 5m", 500, 5000000000, None, None, 5, get_dtm_time("ed5m"), ["", "pol", "mu", "co"], "mete5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis&nom=met-ed-x",
            #     (None, "tall-5k.qml")),
            # model-superficies
            ("elevacions/ms25cm", "MS 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("ms25cm"), ["", "pol"], "ms25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies&nom=ms-x",
                (None, "tall-5k.qml")),
            ("elevacions/ms50cm", "MS 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("ms50cm"), ["", "pol", "mu"], "ms50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies&nom=ms-x",
                (None, "tall-5k.qml")),
            ("elevacions/ms1m", "MS 1m", 100, 200000000, None, None, 1, get_dtm_time("ms1m"), ["", "pol", "mu"], "ms1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies&nom=ms-x",
                (None, "tall-5k.qml")),
            ("elevacions/ms2m", "MS 2m", 200, 800000000, None, None, 2, get_dtm_time("ms2m"), ["", "pol", "mu"], "ms2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies&nom=ms-x",
                (None, "tall-5k.qml")),
            ("elevacions/ms5m", "MS 5m", 500, 5000000000, None, None, 5, get_dtm_time("ms5m"), ["", "pol", "mu", "co"], "ms5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies&nom=ms-x",
                (None, "tall-5k.qml")),
            # # model-orientacions
            # ("elevacions/mo25cm", "MO 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("mo25cm"), ["", "pol"], "mo25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions&nom=mo-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/mo50cm", "MO 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("mo50cm"), ["", "pol", "mu"], "mo50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions&nom=mo-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/mo1m", "MO 1m", 100, 200000000, None, None, 1, get_dtm_time("mo1m"), ["", "pol", "mu"], "mo1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions&nom=mo-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/mo2m", "MO 2m", 200, 800000000, None, None, 2, get_dtm_time("mo2m"), ["", "pol", "mu"], "mo2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions&nom=mo-x",
            #     (None, "tall-5k.qml")),
            # ("elevacions/mo5m", "MO 5m", 500, 5000000000, None, None, 5, get_dtm_time("mo5m"), ["", "pol", "mu", "co"], "mo5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions&nom=mo-x",
            #     (None, "tall-5k.qml")),
            # model-elevacions-terreny-litoral
            ("elevacions-lito/metl25cm", "MET Lito 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("metl25cm"), ["", "pol"], "metl25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-litoral&nom=met-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/metl50cm", "MET Lito 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("metl50cm"), ["", "pol", "mu"], "metl50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-litoral&nom=met-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/metl1m", "MET Lito 1m", 100, 200000000, None, None, 1, get_dtm_time("metl1m"), ["", "pol", "mu"], "metl1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-litoral&nom=met-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/metl2m", "MET Lito 2m", 200, 800000000, None, None, 2, get_dtm_time("metl2m"), ["", "pol", "mu"], "metl2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-litoral&nom=met-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/metl5m", "MET Lito 5m", 500, 5000000000, None, None, 5, get_dtm_time("metl5m"), ["", "pol", "mu", "co"], "metl5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-litoral&nom=met-lito.x",
                (None, "tall-5k.qml")),
            # model-elevacions-terreny-edificis-litoral
            ("elevacions-lito/edl25cm", "MET Ed Lito 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("edl25cm"), ["", "pol"], "metel25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis-litoral&nom=met-ed-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/edl50cm", "MET Ed Lito 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("edl50cm"), ["", "pol", "mu"], "metel50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis-litoral&nom=met-ed-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/edl1m", "MET Ed Lito 1m", 100, 200000000, None, None, 1, get_dtm_time("edl1m"), ["", "pol", "mu"], "metel1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis-litoral&nom=met-ed-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/edl2m", "MET Ed Lito 2m", 200, 800000000, None, None, 2, get_dtm_time("edl2m"), ["", "pol", "mu"], "metel2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis-litoral&nom=met-ed-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/edl5m", "MET Ed Lito 5m", 500, 5000000000, None, None, 5, get_dtm_time("edl5m"), ["", "pol", "mu", "co"], "metel5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-elevacions-terreny-edificis-litoral&nom=met-ed-lito-x",
                (None, "tall-5k.qml")),
            # model-superficies-litoral
            ("elevacions-lito/msl25cm", "MS Lito 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("msl25cm"), ["", "pol"], "msl25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies-litoral&nom=ms-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/msl50cm", "MS Lito 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("msl50cm"), ["", "pol", "mu"], "msl50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies-litoral&nom=ms-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/msl1m", "MS Lito 1m", 100, 200000000, None, None, 1, get_dtm_time("msl1m"), ["", "pol", "mu"], "msl1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies-litoral&nom=ms-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/msl2m", "MS Lito 2m", 200, 800000000, None, None, 2, get_dtm_time("msl2m"), ["", "pol", "mu"], "msl2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies-litoral&nom=ms-lito-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/msl5m", "MS Lito 5m", 500, 5000000000, None, None, 5, get_dtm_time("msl5m"), ["", "pol", "mu", "co"], "msl5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-superficies-litoral&nom=ms-lito-x",
                (None, "tall-5k.qml")),
            # model-orientacions-litoral
            ("elevacions-lito/mol25cm", "MO Lito 25cm", 25, 12500000, None, None, 0.25, get_dtm_time("mol25cm"), ["", "pol"], "mol25cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions-litoral&nom=mol-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/mol50cm", "MO Lito 50cm", 50, 50000000, None, None, 0.5, get_dtm_time("mol50cm"), ["", "pol", "mu"], "mol50cm.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions-litoral&nom=mol-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/mol1m", "MO Lito 1m", 100, 200000000, None, None, 1, get_dtm_time("mol1m"), ["", "pol", "mu"], "mol1m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions-litoral&nom=mol-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/mol2m", "MO Lito 2m", 200, 800000000, None, None, 2, get_dtm_time("mol2m"), ["", "pol", "mu"], "mol2m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions-litoral&nom=mol-x",
                (None, "tall-5k.qml")),
            ("elevacions-lito/mol5m", "MO Lito 5m", 500, 5000000000, None, None, 5, get_dtm_time("mol5m"), ["", "pol", "mu", "co"], "mol5m.tif", "5k_limits", "%s/fmedatastreaming/elevacions/ICGC_elevacions_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s&producte=model-orientacions-litoral&nom=mol-x",
                (None, "tall-5k.qml")),

            # GROUP coast
            # Coast data
            ("costa/elevacions-franja-litoral", "Model d’elevacions topobatimètric de la franja litoral", None, 200000000, None, None, None, None, ["", "pol"], "elevacions_costa.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=peticio&Format=GEOTIFF&Projecte=elevacions-franja-litoral&Codi=%s&piramide=True",
                ("https://geoserveis.icgc.cat/servei/catalunya/batimetria/wms", "elevacions_franja_litoral", "default", "image/png", "batimetria.qml")),
            ("costa/batimetria", "Mapa d’isòbates", None, 200000000 , None, None, None, None, ["", "pol", "tot"], "batimetria.gpkg", "cat_limits", "%s/fmedatastreaming/batimetries/ICGC_batimetria_gpkg_clip.fmw?geopackage_out=peticio&xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s",
                ("https://geoserveis.icgc.cat/servei/catalunya/batimetria/wms", "elevacions_franja_litoral", "default", "image/png", "batimetria.qml")),
            ("costa/lcosta", "Línia de costa", None, 200000000 , None, None, None, get_coastline_years(), ["tot"], "linia-costa.gpkg", "cat_limits", "%s/fmedatastreaming/batimetries/ICGC_linia-costa_download.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s&geopackage_in=%s", None),
            ("costa/ocosta", "Ortofoto costa", None, 2000000 , None, None, None, get_coast_orthophoto_years(), ["", "pol"], "orto-costa.tif", "cat_limits", "%s/fmedatastreaming/orto-costa/ICGC_orto-costa_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&codi=%s&projecte=%s",
                ("https://geoserveis.icgc.cat/servei/catalunya/orto-costa/wms", None, "default", "image/png", "orto-costa.qml")),

            # Geològical maps (prefix_id auto group)
            ("mggt1", "GT I. Mapa geològic 1:25.000", None, None, None, None, None, None, ["tot"], "gt1.shp-zip", None, "%s/fmedatastreaming/Descarrega_basica/descarrega_shape_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Projecte=gt125m&Codi=%s", None),
            ("mg50m", "Mapa Geològic 1:50.000", None, 10000000000, None, None, None, None, ["", "pol", "co"], "mg50m.gpkg", "cat_limits", "%s/fmedatastreaming/geologia-territorial/ICGC_geologia-territorial-50000-geologic_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
            ("mg50m-raster", "Mapa Geològic 1:50.000", 5000, 5000000000 , None, None, None, None, ["", "pol", "co", "tot"], "mg50m.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mg250m&Format=GEOTIFF&Projecte=mg50m&Codi=%s&piramide=True", None),
            ("mg250m", "Mapa geològic 1:250.000", None, 250000000000, None, None, None, None, ["", "pol", "co", "tot"], "mg250m.gpkg", "cat_limits", "%s/fmedatastreaming/geologia-territorial/ICGC_geologia-territorial-250000-geologic_gpkg_clip.fmw?xMin=%s&yMin=%s&xMax=%s&yMax=%s&poligon=%s&Codi=%s", None),
            ("mg250m-raster", "Mapa geològic 1:250.000", 2500, 125000000000, None, None, None, None, ["", "pol", "co", "cat", "tot"], "mg250m.tif", "cat_limits", "%s/fmedatastreaming/Descarrega_basica/geotiff2format_clip_coor.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&DEF_NAME=mg250m&Format=GEOTIFF&Projecte=mg250m&Codi=%s&piramide=True", None),
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

            # LiDAR data
            ("lidar-territorial", "Lidar Territorial 2021-2023", 10, 200000, None, None, None, ["2021-2023"], ["","full"], "lidar.laz", "lidar1k_limits", "%s/fmedatastreaming/lidar-territorial/ICGC_lidar-territorial_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&Projecte=lidar&Codi=%s",
                ("https://datacloud.icgc.cat/datacloud/lidar-territorial/json/lidar-territorial-tall.json", "tall-5k.qml")),
            ("lidar-litoral", "Lidar Litoral", 10, 200000, None, None, None, get_coast_lidar_time(), ["","full"], "lidar-litoral.laz", "lidar1k_limits", "%s/fmedatastreaming/lidar-litoral/ICGC_lidar-litoral_download.fmw?x_min=%s&y_min=%s&x_max=%s&y_max=%s&poligon=%s&Projecte=lidar-litoral&Codi=%s&tall=%s",
                (None, "tall-5k.qml")),

            # Photo library
            ("photo", "Fotogrames", None, None, 100, 100000000, None, None, ["", "pol", "tot"], "photo.tif", "cat_rect", "%s/fmedatastreaming/Fototeca/ICGC_fototeca_download.fmw?SW_X=%s&SW_Y=%s&NE_X=%s&NE_Y=%s&poligon=%s&Codi=%s&Any=%s&CodiVol=%s&NomFoto=%s&Nom=%s", None),
        ]
    return services_list

def get_services_dict():
    """ Retorna un diccionari dels serveis disponibles  (catxejat en variable global)
        ---
        Returns available services dictionary (cached on global variable)
    """
    global services_dict
    if not services_dict:
        services_dict = dict([
            (id.split("/")[-1], (name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple)) for (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, filename, limits, url_pattern, url_ref_or_wms_tuple)
            in get_services_list()])
    return services_dict

def get_services():
    """ Retorna una llista de tuples de productes descarregables amb els valors:
            (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list,
            download_list, default_filename, limits, url_pattern, ref_tuple, enabled)
        ---
        Returns a tuple list with dowloadable products with values:
            (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list,
            download_list, default_filename, limits, url_pattern, ref_tuple, enabled)
        """
    final_services_list = []
    t0 = datetime.datetime.now()
    for id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple in get_services_list():
        # Si ens passen un time_list buit (no None) desactivem la entrada
        enabled = time_list is None or len(time_list) > 0
        # Injectem el path dels arxiu .qml
        if ref_tuple and len(ref_tuple) == 2:
            ref_file, style_file = ref_tuple
            style_file = os.path.join(os.path.dirname(__file__), "symbols", style_file)
            ref_tuple = (ref_file, style_file)
        elif ref_tuple and len(ref_tuple) == 5:
            ref_url, ref_layer, ref_style, ref_format, style_file = ref_tuple
            style_file = os.path.join(os.path.dirname(__file__), "symbols", style_file)
            ref_tuple = (ref_url, ref_layer, ref_style, ref_format, style_file)
        # Afegim els valors modificats a la llista
        final_services_list.append((id, name, min_side, max_query_area, min_px_side, max_px_area, \
            gsd, time_list, download_list, default_filename, limits, url_pattern, ref_tuple, enabled))
    t1 = datetime.datetime.now()

    log.debug("FME resources URL: %s found: %s (%s)", FME_URL.split("/")[0] + "//" +  FME_URL.split("@")[1], len(final_services_list), t1-t0)
    return final_services_list

def get_clip_data_url(data_type, mode, xmin, ymin, xmax, ymax, points_list=[], extra_params=[], referrer=None, url_base=FME_URL):
    """ Retorna la petició URL FME per descarregar un producte
        ---
        Returns FME URL request to download a product
        """
    _name, _min_side, _max_query_area, _min_px_side, _max_px_area, _gsd, _time_list, download_list, _filename, _limits, url_pattern, _url_ref_or_wms_tuple \
        = get_services_dict().get(data_type, (None, None, None, None, None, None, None, None, None, None, None, None))
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
    """ Retorna la llista d'estils disponibles amb el path al seu QML
        ---
        Returns available style list with path to QML
        """
    final_styles_list = [
        (style_regex,
        # Injectem el path dels arxiu .qml
        os.path.join(os.path.dirname(__file__), "symbols", style_qml) if style_qml else None
        ) for style_regex, style_qml in styles_list]
    return final_styles_list

def get_layer_style(layer_name):
    """ Retorna el fitxer QML d'estil associat a una capa de dades
        ---
        Returns QMS style file associated to a data layer
        """
    for regex_pattern, qml_style in styles_list:
        if re.match(regex_pattern, layer_name):
            if not os.path.splitext(qml_style)[1]:
                qml_style += ".qml"
            return os.path.join(os.path.dirname(__file__), "symbols", qml_style)
    return None
