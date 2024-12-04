# -*- coding: utf-8 -*-
"""
*******************************************************************************
OpenICGC
                                 A QGIS plugin

Plugin for accessing open data published by the Cartographic and Geological
Institute of Catalonia (Catalan mapping agency).
Includes spatial toponymic searches, streets, roads, coordinates in different
reference systems and load of WMS base layers of Catalonia.

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat

*******************************************************************************
"""

import os
import sys
import platform

# Import base libraries
import re
import datetime
import zipfile
import io
import logging
import json
from urllib.request import urlopen, Request
from urllib.parse import urljoin, quote
from importlib import reload

# Import QGIS libraries
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsPointXY, QgsRectangle, QgsGeometry
from qgis.core import Qgis, QgsProject, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand
# Import the PyQt and QGIS libraries
from PyQt5.QtCore import QSize, Qt, QPoint, QDateTime
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QComboBox, QMessageBox, QStyle, QInputDialog
from PyQt5.QtWidgets import QLineEdit, QFileDialog, QWidgetAction

# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Detect import relative mode (for release) or global import mode (for debug)
is_import_relative = os.path.exists(os.path.join(os.path.dirname(__file__), "qlib3"))
if is_import_relative:
    # Add a additional library folder to pythonpath (for external libraries)
    sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
    # Import basic plugin functionalities
    from .qlib3.base.loginfodialog import LogInfoDialog
    from .qlib3.base.pluginbase import PluginBase, WaitCursor
    from .qlib3.base.progressdialog import WorkingDialog
    # Import geofinder dialog and class
    from .geofinder3.geofinder import GeoFinder
    from .qlib3.geofinderdialog.geofinderdialog import GeoFinderDialog
    # Import photosearch dialog
    from .qlib3.photosearchselectiondialog.photosearchselectiondialog import PhotoSearchSelectionDialog, photo_search_selection_dialog_ok
    # Import download dialog
    from .qlib3.downloaddialog.downloaddialog import DownloadDialog
    # Import wms resources access functions
    from .resources3.wms import get_full_ortho
    #from .resources3.wfs import get_delimitations as get_wfs_delimitations
    from .resources3.fme import get_clip_data_url, get_services, get_data_filters, FME_MAX_ASPECT_RATIO
    from .resources3.fme import get_regex_styles as get_fme_regex_styles, FME_DOWNLOAD_EPSG, FME_MAX_POLYGON_POINTS
    from .resources3.http import get_historic_ortho_code, get_historic_ortho_ref, get_lidar_ortho
    from .resources3.http import get_dtms, get_coast_dtms,  get_bathimetrics, get_coastlines, get_sheets, get_grids
    from .resources3.http import get_delimitations, get_ndvis, get_topographic_5k
    from .resources3 import http as http_resources, wms as wms_resources, fme as fme_resources
else:
    # Import basic plugin functionalities
    import qlib3.base.pluginbase
    reload(qlib3.base.pluginbase)
    from qlib3.base.pluginbase import PluginBase, WaitCursor
    import qlib3.base.loginfodialog
    reload(qlib3.base.loginfodialog)
    from qlib3.base.loginfodialog import LogInfoDialog
    import qlib3.base.progressdialog
    reload(qlib3.base.progressdialog)
    from qlib3.base.progressdialog import WorkingDialog
    # Import geofinder dialog and class
    import qlib3.geofinderdialog.geofinderdialog
    reload(qlib3.geofinderdialog.geofinderdialog)
    from qlib3.geofinderdialog.geofinderdialog import GeoFinderDialog
    import geofinder3.geofinder
    reload(geofinder3.geofinder)
    from geofinder3.geofinder import GeoFinder
    # Import photosearch dialog
    import qlib3.photosearchselectiondialog.photosearchselectiondialog
    reload(qlib3.photosearchselectiondialog.photosearchselectiondialog)
    from qlib3.photosearchselectiondialog.photosearchselectiondialog import PhotoSearchSelectionDialog, photo_search_selection_dialog_ok
    # Import download dialog
    import qlib3.downloaddialog.downloaddialog
    reload(qlib3.downloaddialog.downloaddialog)
    from qlib3.downloaddialog.downloaddialog import DownloadDialog
    # Import wms resources access functions
    import resources3.wms
    reload(resources3.wms)
    from resources3.wms import get_full_ortho
    import resources3.fme
    reload(resources3.fme)
    from resources3.fme import get_clip_data_url, get_services, get_data_filters, FME_MAX_ASPECT_RATIO
    from resources3.fme import get_regex_styles as get_fme_regex_styles, FME_DOWNLOAD_EPSG, FME_MAX_POLYGON_POINTS
    import resources3.http
    reload(resources3.http)
    from resources3.http import get_historic_ortho_code, get_historic_ortho_ref, get_lidar_ortho
    from resources3.http import get_dtms, get_coast_dtms, get_bathimetrics, get_coastlines, get_sheets, get_grids
    from resources3.http import get_delimitations, get_ndvis, get_topographic_5k
    from resources3 import http as http_resources, wms as wms_resources, fme as fme_resources

# Global function to set HTML tags to apply fontsize to QInputDialog text
set_html_font_size = lambda text, size=9: ('<html style="font-size:%spt;">%s</html>' % (size, text.replace("\n", "<br/>").replace(" ", "&nbsp;")))

# Constants
PHOTOLIB_WFS_MAX_FEATURES = 1000
PHOTOLIB_WFS = "https://fototeca-connector.icgc.cat/"
PHOTOLIB_WMS = PHOTOLIB_WFS


class QgsMapToolSubScene(QgsMapTool):
    """ Tool class to manage rectangular selections """

    def __init__(self, map_canvas, callback=None, \
        min_side=None, max_download_area=None, min_px_side=None, max_px_download_area=None, gsd=None, gsd_dict={}, \
        mode_area_not_point=None, color=QColor(0,150,0,255), error_color=QColor(255,0,0,255), line_width=3):
        # Initialize parent
        QgsMapTool.__init__(self, map_canvas)
        # Initialize local variables
        self.callback = callback
        self.pressed = False
        self.color = color
        self.error_color = error_color
        self.line_width = line_width
        self.min_side = min_side
        self.max_download_area = max_download_area
        self.min_px_side = min_px_side
        self.max_px_download_area = max_px_download_area
        self.gsd = gsd
        self.mode_area_not_point = mode_area_not_point
        # Initialize paint object
        self.rubberBand = QgsRubberBand(map_canvas)

    def set_callback(self, callback):
        self.callback = callback

    def set_min_max(self, min_side, max_download_area, min_px_side, max_px_download_area, max_aspect_ratio):
        self.min_side = min_side
        self.max_download_area = max_download_area
        self.min_px_side = min_px_side
        self.max_px_download_area = max_px_download_area
        self.max_aspect_ratio = max_aspect_ratio

    def set_gsd(self, gsd):
        self.gsd = gsd

    def set_mode(self, area_not_point):
        self.mode_area_not_point = area_not_point

    def canvasPressEvent(self, event):
        #click
        if event.button() == Qt.LeftButton:
            self.pressed = True
            self.top_left = self.toMapCoordinates(QPoint(event.pos().x(), event.pos().y()))

    def canvasMoveEvent(self, event):
        # If don't have drag then exit
        if not self.pressed:
            return
        if not self.mode_area_not_point:
            return

        # Show selection rectangle
        cpos = self.toMapCoordinates(QPoint(event.pos().x(), event.pos().y()))

        width = abs(cpos.x() - self.top_left.x())
        height = abs(cpos.y() - self.top_left.y())
        area =  width * height
        area_too_big = self.max_download_area and (area > self.max_download_area) or \
            self.max_px_download_area and self.gsd and ((area / self.gsd / self.gsd) > self.max_px_download_area)
        area_too_little = self.min_side and (width < self.min_side or height < self.min_side) or \
            self.min_px_side and self.gsd and ((width / self.gsd) < self.min_px_side or (height / self.gsd) < self.min_px_side)
        aspect_ratio = width / max(height, 1)
        invalid_aspect_ratio = aspect_ratio < (1/self.max_aspect_ratio) or aspect_ratio > self.max_aspect_ratio
        color = self.error_color if area_too_big or area_too_little or invalid_aspect_ratio else self.color

        self.rubberBand.reset()

        self.rubberBand.setLineStyle(Qt.DashLine)
        self.rubberBand.setColor(color)
        self.rubberBand.setWidth(self.line_width)

        self.rubberBand.addPoint(self.top_left, False)
        self.rubberBand.addPoint(QgsPointXY(cpos.x(), self.top_left.y()), False)
        self.rubberBand.addPoint(cpos, False)
        self.rubberBand.addPoint(QgsPointXY(self.top_left.x(), cpos.y()), False)
        self.rubberBand.addPoint(self.top_left, True)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.subscene(event.pos().x(), event.pos().y())

    def subscene(self, x=None, y=None):
        # Gets selection geometry
        area = None
        if self.mode_area_not_point:
            # If area is required takes rubberBans geometry
            geo = self.rubberBand.asGeometry()
            if geo:
                area = geo.boundingBox()
        if not area and x is not None and y is not None:
            # If not area then we takes a point
            point = self.toMapCoordinates(QPoint(x, y))
            area = QgsRectangle(point.x(), point.y(), point.x(), point.y())

        # Hide selection area
        self.rubberBand.reset()
        self.pressed = False

        # Execute callback with selected area as parameter
        if self.callback:
            self.callback(area)


class QgsMapToolPhotoSearch(QgsMapTool):
    """ Enable to return coordinates from clic in a layer.
    """
    def __init__(self, map_canvas, callback=None, action=None):
        """ Constructor.
        """
        QgsMapTool.__init__(self, map_canvas)
        self.map_canvas = map_canvas
        self.callback = callback
        # Action to check / uncheck tools
        self.setAction(action)
        # Assign tool cursor
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        cpos = self.toMapCoordinates(QPoint(event.pos().x(), event.pos().y()))
        if self.callback:
            self.callback(cpos.x(), cpos.y())


class HelpType:
    """ Definition of differents types of show pluggin help """
    local = 0
    online = 1
    online_cached = 2


class UpdateType:
    """ Definition of diferents types of plugin updates """
    plugin_manager = 0
    qgis_web = 1
    icgc_web = 2


class OpenICGC(PluginBase):
    """ Plugin for accessing open data published by ICGC """

    TOOLTIP_HELP = "" # Filled on __init__ (translation required)
    SQUARE_CHAR = "\u00B2"

    FME_DOWNLOADTYPE_LIST = [] # Filled on __init__ (translation required)
    FME_NAMES_DICT = {} # Filled on __init__ (translation required)
    FME_ICON_DICT = {
        "ct": "cat_topo5k.png",
        "bm": "cat_topo5k.png",
        #"bt" :"cat_topo5k.png",
        "di": "cat_topo5k.png", # divisions-administratives
        "to": "cat_topo5k.png", # topografia-territorial
        "of": "cat_ortho5k.png",
        "hc": "cat_ortho5k.png",
        "oi": "cat_ortho5ki.png",
        "hi": "cat_ortho5ki.png",
        "mt": "cat_topo5k.png",
        "co": "cat_landcover.png",
        "me": "cat_dtm.png",
        #"gt": "cat_geo250k.png",
        "mg": "cat_geo250k.png",
        "ma": "cat_geo250k.png",
        "li": "cat_coast.png",
        "ba": "cat_coast.png",
        "el": "cat_coast.png",
        "li": "cat_lidar.png",
        "ph": "photo.png", # fototeca
        }
    FME_METADATA_DICT = {
        "of": "Current color orthophoto",
        "hc": "Color orthophoto (temporal serie)",
        "oi": "Current infrared orthophoto",
        "hi": "Infrared orthophoto (temporal serie)",
        #"bt5m": "Topographic base 1:5,000",
        "topografia-territorial": "Territorial topographic referential",
        "mtc250m": "Topographic map 1:250,000",
        "mtc500m": "Topographic map 1:500,000",
        "mtc1000m": "Topographic map 1:1,000,000",
        "ct1m": "Topographic cartography 1:1,000",
        #"bm5m": "Municipal base 1:5,000",
        "divisions-administratives": "Administrative divisions",
        "topografia-territorial-gpkg": "Territorial topographic referential",
        "topografia-territorial-dgn": "Territorial topographic referential",
        "topografia-territorial-dwg": "Territorial topographic referential",
        "topografia-territorial-bim-ifc": "Territorial topographic referential",
        "topografia-territorial-3d-gpkg": "Territorial topographic referential",
        "topografia-territorial-3d-dgn": "Territorial topographic referential",
        "topografia-territorial-3d-dwg": "Territorial topographic referential",
        "topografia-territorial-volum-dwg": "Territorial topographic referential",
        "cobertes-sol-raster": "Land cover map",
        "cobertes-sol-vector": "Land cover map",
        "met2": "Digital Terrain Model 2m 2008-2011",
        "met5": "Digital Terrain Model 5m 2020",
        "elevacions-franja-litoral": "Topobathymetric elevation model (-50m) 1m 2022-2024",
        "batimetria": "Bathymetric chart (-50m) 2022-2024",
        "linia-costa": "Coastline",
        "mg50m": "Geological map 1:50,000",
        "mg250m": "Geological map 1:250,000",
        "mg250m-raster": "Geological map 1:250,000",
        "mggt6": "Geological map for the prevention of geological hazards 1:25,000 (GT VI)",
        "mggt1": "Geological map 1:25,000 (GT I)",
        # Pending revision of symbology
        #"gt2": "GT II. Geoanthropic map 1:25,000",
        #"gt3": "GT III. Geological map of urban areas 1:5,000",
        #"gt4": "GT IV. Soil map 1:25,000",
        #"gt5": "GT V. Hydrogeological map 1:25,000",
        #"mah250m": "Map of hydrogeological Areas 1:250,000",
        "lidar-territorial": "Territorial Lidar",
        "of-lidar-territorial": "Territorial Lidar Color Orthophoto",
        "oi-lidar-territorial": "Territorial Lidar Infrared Orthophoto",
        # No metadata
        #"photo": "Photo library",
        }

    PRODUCT_METADATA_FILE = os.path.join(os.path.dirname(__file__), "data", "product_metadata.json")

    CAT_EXTENSION = QgsRectangle(215300, 4478100, 577600, 4758400)

    download_action = None
    time_series_action = None
    photo_search_action = None
    photo_search_2_action = None
    photo_download_action = None
    geopackage_style_action = None

    debug_mode = False
    test_available = False

    ###########################################################################
    # Plugin initialization

    def __init__(self, iface, debug_mode=False):
        """ Plugin variables initialization """
        # Save reference to the QGIS interface
        super().__init__(iface, __file__)

        # Detection of developer enviroment
        self.debug_mode = debug_mode or __file__.find("pyrepo") >= 0
        if self.debug_mode:
            self.enable_debug_log()
        # Dectection of plugin mode (lite or full)
        self.lite = os.environ.get("openicgc_lite", "").lower() in ["true", "1", "enabled"]
        self.log.info("Initializing %s%s", self.metadata.get_name(), " Lite" if self.lite else "")
        self.extra_countries = self.lite
        # Detection of test environment
        self.test_available = self.debug.is_test_available()
        # Configure library loggers
        http_resources.log = self.log
        wms_resources.log = self.log
        fme_resources.log = self.log

        # Load extra fonts (Fira Sans)
        t0 = datetime.datetime.now()
        fonts_status, self.font_id_list = self.load_fonts(copy_to_temporal_folder=True)
        t1 = datetime.datetime.now()
        self.log.info("Load fonts folder %s: %s (%s)" % (self.get_fonts_temporal_folder(), fonts_status, t1-t0))
        if not fonts_status:
            self.log.warning("Error loading extra fonts")

        # Translated long tooltip text
        self.TOOLTIP_HELP = self.tr("""Find:
            Address: municipality, street number or vice versa
                Barcelona, Aribau 86
                Aribau 86, Barcelona
                Barcelona, C/ Aribau 86

            Crossing: municipality, street, street
                Barcelona, Mallorca, Aribau

            Road: road, km
                C32 km 10
                C32, 10

            Toponym: free text
                Barcelona
                Collserola
                Institut Cartografic

            Coordinate: x and EPSG: code (by default coordinate system of the project)
                429394.751 4580170.875
                429394,751 4580170,875
                429394.751 4580170.875 EPSG:25831
                EPSG:4326 1.9767050 41.3297270

            Rectangle: west north east south EPSG: code (by default system coordinates of the project)
                427708.277 4582385.829 429808.277 4580285.829
                427708,277 4582385,829 429808,277 4580285,829
                427708.277 4582385.829 429808.277 4580285.829 EPSG:25831
                EPSG:25831 427708.277 4582385.829 429808.277 4580285.829

            Cadastral reference: ref (also works with the first 14 digits)
                9872023 VH5797S 0001 WX
                13 077 A 018 00039 0000 FP
                13077A018000390000FP""")

        # Set group name for background maps
        self.backgroup_map_group_name = self.tr("Background maps")

        # Initialize base maps (with translation)
        self.base_map_dict = {
            "topografic": (self.tr("Topographic base map"), "cat_topo.png"),
            "topografic-gris": (self.tr("Gray topographic base map"), "cat_topogray.png"),
            "simplificat": (self.tr("Simplified base map"), "cat_simplified.png"),
            "administratiu": (self.tr("Administrative base map"), "cat_administrative.png"),
            "estandard": (self.tr("Standard base map"), "cat_standard.png"),
            "orto": (self.tr("Orthophoto base map"), "cat_ortho.png"),
            "orto-gris": (self.tr("Gray orthophoto base map"), "cat_orthogray.png"),
            "orto-hibrida": (self.tr("Hybrid orthophoto base map"), "cat_orthohybrid.png"),
            }
        self.base_maps_info_url = "https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/mapa-base-wms"

        # Initialize references names (with translation)
        self.HTTP_NAMES_DICT = {
            "caps-municipi": self.tr("Municipal capitals"), # Available HTTP
            "capmunicipi": self.tr("Municipal capitals"), # Available WFS
            "capcomarca": self.tr("County capitals"), #  # Available WFS
            "municipis": self.tr("Municipalities"),
            "comarques": self.tr("Counties"),
            "vegueries": self.tr("Vegueries"), # Available HTTP
            "provincies": self.tr("Provinces"),
            "catalunya": self.tr("Catalonia"), #Available HTTP
            }

        # Initialize download names (with translation)
        self.FME_NAMES_DICT = {
            "of25c": self.tr("Current color orthophoto 25cm 1:2,500"),
            "of5m": self.tr("Current color orthophoto 50cm 1:5,000"),
            "of25m": self.tr("Current color orthophoto 2.5m 1:25,000"),
            "hc10cm": self.tr("Historic color orthophoto 10cm 1:1,000"),
            "hc15cm": self.tr("Historic color orthophoto 15cm 1:1,500"),
            "hc25cm": self.tr("Historic color orthophoto 25cm 1:2,500"),
            "hc50cm": self.tr("Historic color orthophoto 50cm 1:5,000"),
            "hc1m": self.tr("Historic color orthophoto 1m 1:10,000"),
            "hc250cm": self.tr("Historic color orthophoto 2.5m 1:25,000"),
            "oi25c": self.tr("Current infrared orthophoto 25cm 1:2,500"),
            "oi5m": self.tr("Current infrared orthophoto 50cm 1:5,000"),
            "oi25m": self.tr("Current infrared orthophoto 2.5m 1:25,000"),
            "hi10cm": self.tr("Historic infrared orthophoto 10cm 1:1,000"),
            "hi25cm": self.tr("Historic infrared orthophoto 25cm 1:2,500"),
            "hi50cm": self.tr("Historic infrared orthophoto 50cm 1:5,000"),
            "hi1m": self.tr("Historic infrared orthophoto 1m 1:10,000"),
            "hi250cm": self.tr("Historic infrared orthophoto 2.5m 1:25,000"),
            #"bt5m": self.tr("Topographic base 1:5,000"),
            "topografia-territorial": self.tr("Territorial topographic referential"),
            "mtc250m": self.tr("Topographic map 1:250,000"),
            "mtc500m": self.tr("Topographic map 1:500,000"),
            "mtc1000m": self.tr("Topographic map 1:1,000,000"),
            "ct1m": self.tr("Topographic cartography 1:1,000"),
            #"bm5m": self.tr("Municipal base 1:5,000"),
            "divisions-administratives": self.tr("Administrative divisions"),
            "topografia-territorial-gpkg": self.tr("Territorial topographic referential"),
            "topografia-territorial-dgn": self.tr("Territorial topographic referential"),
            "topografia-territorial-dwg": self.tr("Territorial topographic referential"),
            "topografia-territorial-bim-ifc": self.tr("Territorial topographic referential BIM"),
            "topografia-territorial-3d-gpkg": self.tr("Territorial topographic referential 3D"),
            "topografia-territorial-3d-dgn": self.tr("Territorial topographic referential 3D"),
            "topografia-territorial-3d-dwg": self.tr("Territorial topographic referential 3D"),
            "topografia-territorial-volum-dwg": self.tr("Territorial topographic referential volume"),
            "cobertes-sol-raster": self.tr("Land cover map"),
            "cobertes-sol-vector": self.tr("Land cover map"),
            "met2": self.tr("Digital terrain model 2m 2008-2011"),
            "met5": self.tr("Digital terrain model 5m 2020"),
            "elevacions-franja-litoral": self.tr("Topobathymetric elevation model"),
            "batimetria": self.tr("Bathymetric chart"),
            "linia-costa": self.tr("Coastline"),
            "mggt1": self.tr("Geological map 1:25,000 (GT I)"),
            "mg50m": self.tr("Geological map 1:50,000"),
            "mg250m": self.tr("Geological map 1:250,000"),
            "mg250m-raster": self.tr("Geological map 1:250,000"),
            "mggt6": self.tr("Geological map for the prevention of geological hazards 1:25,000 (GT VI)"),
            # Pending revision of symbology
            #"gt2": self.tr("GT II. Geoanthropic map 1:25,000"),
            #"gt3": self.tr("GT III. Geological map of urban areas 1:5,000"),
            #"gt4": self.tr("GT IV. Soil map 1:25,000"),
            #"gt5": self.tr("GT V. Hydrogeological map 1:25,000"),
            #"mah250m": self.tr("Map of hydrogeological Areas 1:250,000"),
            "lidar-territorial": self.tr("Territorial Lidar"),
            "of-lidar-territorial": self.tr("Territorial Lidar Color Orthophoto"),
            "oi-lidar-territorial": self.tr("Territorial Lidar Infrared Orthophoto"),
            "photo": self.tr("Photograms"),
            }
        # Initialize download type descriptions (with translation)
        self.FME_DOWNLOADTYPE_LIST = [
            ("dt_area", self.tr("Area"), ""),
            ("dt_coord", self.tr("Area coordinates"), ""),
            ("dt_layer_polygon", self.tr("Selected layer polygons"), "pol"),
            ("dt_layer_polygon_bb", self.tr("Selected layer polygons bounding box"), "pol"),
            ("dt_sheet", self.tr("Sheet"), "full"),
            ("dt_municipalities", self.tr("Municipality"), "mu"),
            ("dt_counties", self.tr("County"), "co"),
            ("dt_cat", self.tr("Catalonia"), "cat"),
            ("dt_all", self.tr("Available data"), "tot")]
        ## Inicitialize default download variables
        self.download_type = "dt_area"
        self.download_group_name = self.tr("Download")
        self.download_ref_pattern = self.tr("Reference %s")
        self.cat_limits_dict = { # key: (geometry, epsg)
            "cat_rect": self.get_catalonia_limits("cat_rect_limits", buffer=0),
            "cat_simple": self.get_catalonia_limits("cat_simple_limits", buffer=0),
            "cat_limits": self.get_catalonia_limits("cat_limits", buffer=250),
            "lidar1k_limits": self.get_catalonia_limits("cat_lidar1k_limits", buffer=0),
            "5k_limits": self.get_catalonia_limits("cat_tall5k_limits", buffer=0),
            "25k_limits": self.get_catalonia_limits("cat_tall25k_limits", buffer=0),
            }
        # Lambda function with last download reference layer used
        self.load_last_ref_layer = lambda: None
        # Get download services regex styles and filters
        self.fme_regex_styles_list = get_fme_regex_styles()
        self.fme_data_filters_dict = get_data_filters()
        # Initialize reference to DownloadDialog
        self.download_dialog = None

        # We created a GeoFinder object that will allow us to perform spatial searches
        # and we configure it with our plugin logger
        self.geofinder = GeoFinder(logger=self.log)
        self.geofinder_dialog = GeoFinderDialog(self.geofinder, title=self.tr("Spatial search"),
            columns_list=[self.tr("Name"), self.tr("Type"), self.tr("Municipality"), self.tr("Region")],
            keep_scale_text=self.tr("Keep scale"))

        # Initialize product metatata dictionary with metadata urls
        product_dict_list = []
        if os.path.exists(self.PRODUCT_METADATA_FILE):
            with open(self.PRODUCT_METADATA_FILE, 'r') as json_file:
                product_dict_list = json.load(json_file)
        self.product_metadata_dict = { product_dict['Carpeta']: product_dict['Metadades'] \
            for product_dict in product_dict_list }

        # Initialize reference to PhotoSearchSelectionDialog
        self.photo_search_dialog = None
        # Initialize photo search group names
        self.photos_group_name = self.tr("Photograms")
        # Initialize photo search label
        self.photo_label = self.tr("Photo: %s")
        self.photo_layer_id = ""
        self.photo_search_label = self.tr("Photo query: %s")
        self.photo_search_layer_id = ""

        # Configure referrer string to use on url requests
        self.request_referrer = "%s_v%s" % (self.metadata.get_name().replace(" ", ""), self.metadata.get_version())
        self.request_referrer_param = "referrer=%s" % self.request_referrer

        # Check QGIS version problems
        self.enable_http_files = self.check_qgis_version(31004)
        self.qgis_version_ok = self.check_qgis_version(31004)
        self.can_show_point_cloud_files = self.check_qgis_version(31800)
        self.can_filter_point_cloud = self.check_qgis_version(32600)

        # Map change current layer event
        self.iface.layerTreeView().currentLayerChanged.connect(self.on_change_current_layer)
        self.iface.layerTreeView().clicked.connect(self.on_click_legend)

    def unload(self):
        """ Release of resources """
        # Unmap signals
        self.iface.layerTreeView().currentLayerChanged.disconnect(self.on_change_current_layer)
        self.iface.layerTreeView().clicked.disconnect(self.on_click_legend)
        self.combobox.activated.disconnect()
        photo_search_layer = self.layers.get_by_id(self.photo_search_layer_id)
        if photo_search_layer:
            photo_search_layer.selectionChanged.disconnect(self.on_change_photo_selection)
            if self.photo_search_dialog:
                photo_search_layer.willBeDeleted.disconnect(self.photo_search_dialog.reset)
        self.log.debug("Disconnected signals")
        # Remove photo dialog
        if self.photo_search_dialog:
            self.photo_search_dialog.visibilityChanged.disconnect()
            self.photo_search_dialog.reset()
            self.iface.removeDockWidget(self.photo_search_dialog)
        self.photo_search_dialog = None
        # Remove photo search groups
        self.legend.remove_group_by_name(self.photos_group_name)
        self.legend.remove_group_by_name(self.download_group_name)
        self.log.debug("Removed groups")
        # Remove GeoFinder dialog
        self.geofinder_dialog = None
        # Remove Download dialog
        self.download_dialog = None
        self.log.debug("Removed dialogs")
        # Unload fonts
        self.log.debug("Removed fonts: %s" % self.unload_fonts(self.font_id_list))
        # Log plugin unloaded
        self.log.info("Unload %s%s", self.metadata.get_name(), " Lite" if self.lite else "")
        # Parent PluginBase class release all GUI resources created with their functions
        super().unload()

    def get_catalonia_limits(self, filename, buffer=0, segments=10):
        """ Gets Catalonia limits from geojson resource file
            Apply 250m of buffer to fix possible errors on CAT envolope scale 1:1,000,000 """
        t0 = datetime.datetime.now()
        pathname = os.path.join(self.plugin_path, "data", "%s.geojson" % filename)
        if not os.path.exists(pathname):
            self.log.warning("Geometry limits %s file not found %s", filename, pathname)
            return None, None
        tmp_layer = QgsVectorLayer(pathname, "cat_limits", "ogr")
        if tmp_layer.featureCount() < 1:
            self.log.warning("Load geometry limits %s error: %s\nFeatures: %s",
                filename, pathname, tmp_layer.featureCount())
        geom = list(tmp_layer.getFeatures())[0].geometry().buffer(buffer, segments)
        if not geom or geom.isEmpty():
            self.log.warning("Load geometry limits %s empty: %s\nFeatures: %s",
                filename, pathname, tmp_layer.featureCount())
        epsg = tmp_layer.crs().authid()
        t1 = datetime.datetime.now()
        self.log.info("Load geometry limits: %s (features: %s, empty: %s, buffer: %s, segments: %s, EPSG:%s) (%s)",
            pathname, tmp_layer.featureCount(), geom.isEmpty(), buffer, segments, epsg, t1-t0)
        return geom, epsg

    def format_scale(self, scale):
        """ Format scale number with locale separator """
        text = format(scale, ",d")
        if self.translation.get_qgis_language() in ['ca', 'es']:
            text = text.replace(',', '.')
        return text

    def initGui(self, check_qgis_updates=True, check_icgc_updates=False):
        """ GUI initializacion """
        # Log plugin started
        t0 = datetime.datetime.now()
        self.log.info("Initializing GUI")

        # Plugin registration in the plugin manager
        self.gui.configure_plugin()

        # Add combobox to search
        self.combobox = QComboBox()
        self.combobox.setFixedSize(QSize(250,24))
        self.combobox.setEditable(True)
        self.combobox.setInsertPolicy(QComboBox.InsertAtTop)
        self.combobox.setToolTip(self.TOOLTIP_HELP)
        self.combobox.addItems(self.get_setting_value("last_searches", []))
        self.combobox.setCurrentText("")
        self.combobox.setMaxVisibleItems(20)
        self.combobox.activated.connect(self.run) # Press intro and select combo value

        # Gets available Topo5k files to simulate WMS-T service
        topo5k_time_series_list = [(time_year, "/vsicurl/%s" % url) for time_year, url in get_topographic_5k()]

        # Get Available delimitations
        delimitations_list = get_delimitations()
        #self.cat_1M_name, cat_scale_list, self.cat_1M_style_file = delimitations_list[-1] # Last is Catalonia
        #self.cat_1M_scale, self.cat_1M_url = cat_scale_list[-1] # Last is 1M scale

        # Gets available Sheets and Grids
        sheets_list = get_sheets()
        grids_list = get_grids()

        # Gets available DTMs i costa
        dtm_list = [(name, "/vsicurl/%s" % url) for name, url in get_dtms()]
        height_highlighting_url = dtm_list[0][1] if dtm_list else None
        coast_dtm_list = [(name, "/vsicurl/%s" % url) for name, url in get_coast_dtms()]
        bathimetric_list = [(name, "/vsicurl/%s" % url) for name, url in get_bathimetrics()]
        coastline_list = [(name, "/vsicurl/%s" % url) for name, url in get_coastlines()]

        # Gets available NDVI files to simulate WMS-T service
        ndvi_time_series_list = [(time_year, "/vsicurl/%s" % url) for time_year, url in get_ndvis()]
        ndvi_current_time = ndvi_time_series_list[-1][0] if ndvi_time_series_list else None

        # Gets all ortho data (except satellite)
        ortho_wms_url, historic_ortho_list = get_full_ortho()
        ortho_color_time_series_list = [(str(year), layer_id) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortofoto" and color != "irc"]
        ortho_color_year = ortho_color_time_series_list[-1][0] if ortho_color_time_series_list else None
        ortho_infrared_time_series_list = [(str(year), layer_id) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortofoto" and color == "irc"]
        ortho_infrared_year = ortho_infrared_time_series_list[-1][0] if ortho_infrared_time_series_list else None
        ortosuperexp_color_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "superexpedita" and color != "irc"]
        ortosuperexp_color_year, ortosuperexp_color_layer_id, ortosuperexp_color_layer_name = ortosuperexp_color_list[-1] if ortosuperexp_color_list else (None, None, None)
        ortosuperexp_infrared_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "superexpedita" and color == "irc"]
        ortosuperexp_infrared_year, ortosuperexp_infrared_layer_id, ortosuperexp_infrared_layer_name = ortosuperexp_infrared_list[-1] if ortosuperexp_infrared_list else (None, None, None)
        ortoxpres_color_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortoxpres" and color != "irc"]
        ortoxpres_color_year, ortoxpres_color_layer_id, ortoxpres_color_layer_name = ortoxpres_color_list[-1] if ortoxpres_color_list else (None, None, None)
        ortoxpres_infrared_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortoxpres" and color == "irc"]
        ortoxpres_infrared_year, ortoxpres_infrared_layer_id, ortoxpres_infrared_layer_name = ortoxpres_infrared_list[-1] if ortoxpres_infrared_list else (None, None, None)
        lidar_ortho_color_time_series_list = get_lidar_ortho(rgb_not_irc=True)
        lidar_ortho_color_year = lidar_ortho_color_time_series_list[-1][0] if lidar_ortho_color_time_series_list else None
        lidar_ortho_infrared_time_series_list = get_lidar_ortho(rgb_not_irc=False)
        lidar_ortho_infrared_year = lidar_ortho_infrared_time_series_list[0][0] if lidar_ortho_infrared_time_series_list else None

        # Gets anaglyph fotograms. Last year can not have full photograms coverage, we select previous year as default
        photolib_wms_url = PHOTOLIB_WMS
        _photolib_time_series_list, photolib_current_time = self.layers.get_wms_t_time_series(photolib_wms_url, "photo_central")
        photolib_current_time = str(int(photolib_current_time) - 1) if photolib_current_time else photolib_current_time

        # Gets available download source data
        fme_services_list = get_services()
        download_raster_submenu = self.get_download_menu(fme_services_list, raster_not_vector=True)
        download_vector_submenu = self.get_download_menu(fme_services_list, raster_not_vector=False)

        # Check plugin update
        new_icgc_plugin_version = self.check_plugin_update() if check_icgc_updates else None
        new_qgis_plugin_version = self.metadata.get_qgis_new_version_available() if check_qgis_updates and not self.lite else None
        new_plugin_version = new_qgis_plugin_version or new_icgc_plugin_version

        # Add new toolbar with plugin options (using pluginbase functions)
        style = self.iface.mainWindow().style()
        base_map_callback = lambda layer_name: self.zoom_to_cat_when_empty(self.layers.add_wms_layer( \
            self.base_map_dict[layer_name][0], \
            "https://geoserveis.icgc.cat/servei/catalunya/mapa-base/wms", \
            [layer_name], None, "image/png", 25831, self.request_referrer_param, \
            self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True))
        self.default_map_callback = lambda _checked=False: base_map_callback("topografic") # Used on find call and  layer button
        self.toolbar = self.gui.configure_toolbar(self.tr("Open ICGC Toolbar") + (" lite" if self.lite else ""), [
            self.tr("Find"), # Label text
            self.combobox, # Editable combobox
            (self.tr("Find place names and adresses"),
                self.run, # GeoFinder
                "map.png"), # Action button
            "---",
            (self.tr("Background maps"),
                # Default background map
                self.default_map_callback,
                "wms.png", True, False, "background_maps", [
                # Background map list
                (self.tr("Base maps (world-wide)"), None, "world.png", [
                    (product_name,
                        lambda _checked=False, layer_name=layer_name: base_map_callback(layer_name),
                        icon_file,
                        self.manage_metadata_button(product_metadata_url=self.base_maps_info_url), True) \
                    for layer_name, (product_name, icon_file) in self.base_map_dict.items()]),
                "---",
                (self.tr("Territorial topographic referential"), None, "cat_topo5k.png", \
                    self.enable_http_files and len(topo5k_time_series_list) > 0, [
                    (self.tr("Territorial topographic referential %s (temporal serie)") % topo5k_year,
                        lambda _checked, topo5k_year=topo5k_year:self.add_wms_t_layer(self.tr("[TS] Territorial topographic referential"), None, topo5k_year, None, "default", "image/png", topo5k_time_series_list[::-1], None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, resampling_bilinear=True, set_current=True),
                        "cat_topo5k.png",
                        self.manage_metadata_button("Territorial topographic referential %s (temporal serie)" % topo5k_year), True)
                    for topo5k_year, _url in topo5k_time_series_list]),
                (self.tr("Topographic map 1:250,000"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Topographic map 1:250,000"), "https://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc250m"], ["default"], "image/png", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_topo250k.png",
                    self.manage_metadata_button("Topographic map 1:250,000"), True),
                "---",
                (self.tr("Administrative divisions"), None, "cat_vector.png", self.enable_http_files, [
                    (self.tr("Administrative divisions (raster pyramid)"),
                        lambda _checked:self.layers.add_wms_layer(self.tr("Administrative divisions (raster pyramid)"), "https://geoserveis.icgc.cat/servei/catalunya/divisions-administratives/wms",
                            ['divisions_administratives_comarques_1000000', 'divisions_administratives_comarques_500000', 'divisions_administratives_comarques_250000', 'divisions_administratives_comarques_100000', 'divisions_administratives_comarques_50000', 'divisions_administratives_comarques_5000', 'divisions_administratives_municipis_250000', 'divisions_administratives_municipis_100000', 'divisions_administratives_municipis_50000', 'divisions_administratives_municipis_5000', 'divisions_administratives_capsdemunicipi_capmunicipi', 'divisions_administratives_capsdemunicipi_capcomarca'],
                            ["default"], "image/png", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_vector.png",
                        self.manage_metadata_button("Administrative divisions"), True),
                    "---",
                    ] + [
                        (self.HTTP_NAMES_DICT.get(name, name),
                        (lambda _checked, name=name, scale_list=scale_list, style_file=style_file:self.layers.add_vector_layer(self.HTTP_NAMES_DICT.get(name, name), scale_list[0][1], group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, style_file=style_file) if len(scale_list) == 1 else None),
                        "cat_vector.png", ([
                            ("%s 1:%s" % (self.HTTP_NAMES_DICT.get(name, name), self.format_scale(scale)),
                                lambda _checked, name=name, scale=scale, url=url, style_file=style_file:self.layers.add_vector_layer("%s 1:%s" % (self.HTTP_NAMES_DICT.get(name, name), self.format_scale(scale)), url, group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, style_file=style_file),
                                "cat_vector.png",
                                self.manage_metadata_button("Administrative divisions"), True)
                            for scale, url in scale_list] if len(scale_list) > 1 \
                            else self.manage_metadata_button("Administrative divisions")),
                            len(scale_list) == 1)
                        for name, scale_list, style_file in delimitations_list
                        ]),
                (self.tr("Cartographic series"), None, "sheets.png", self.enable_http_files, [
                    (self.tr("%s serie") % sheet_name,
                        lambda _checked, sheet_name=sheet_name, sheet_url=sheet_url:self.layers.add_vector_layer(self.tr("%s serie") % sheet_name, sheet_url, group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, style_file="talls.qml"),
                        "sheets.png", self.enable_http_files,
                        self.manage_metadata_button("Cartographic series"), True
                        ) for sheet_name, sheet_url in sheets_list
                    ] + [
                    "---"
                    ] + [
                    (self.tr("%s grid") % grid_name,
                        lambda _checked, grid_name=grid_name, grid_url=grid_url:self.layers.add_vector_layer(self.tr("%s grid") % grid_name, grid_url, group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, style_file="talls.qml"),
                        "sheets.png", self.enable_http_files,
                        self.manage_metadata_button("UTM (MGRS) grids"), True
                        ) for grid_name, grid_url in grids_list
                    ]),
                "---",
                (self.tr("Geological map 1:250,000"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Geological map 1:250,000"), "https://geoserveis.icgc.cat/servei/catalunya/geologia-territorial/wms", ["geologia-territorial-250000-geologic"], ["default"], "image/png", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, resampling_bilinear=True),
                    "cat_geo250k.png",
                    self.manage_metadata_button("Geological map 1:250,000"), True),
                (self.tr("Land cover map (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] Land cover map"), "https://geoserveis.icgc.cat/servei/catalunya/cobertes-sol/wms", None, None, "default", "image/png", None, r"cobertes_(.+)", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_landcover.png",
                    self.manage_metadata_button("Land cover map (temporal serie)"), True),
                "---",
                ] + [(self.tr("Digital Terrain Model %s") % dtm_name,
                    # Force EPSG:25831 by problems with QGIS 3.10 version
                    lambda _checked, dtm_name=dtm_name, dtm_url=dtm_url:self.layers.add_raster_layer(self.tr("Digital Terrain Model %s") % dtm_name, dtm_url, group_name=self.backgroup_map_group_name, group_pos=0, epsg=25831, only_one_map_on_group=False, set_current=True, color_default_expansion=True, resampling_bilinear=True),
                    "cat_dtm.png", self.enable_http_files,
                    self.manage_metadata_button("Digital Terrain Model %s" % dtm_name), True
                    ) for dtm_name, dtm_url in dtm_list] + [
                "---",
                ] + ([
                (self.tr("Coast"), None, "cat_coast.png", [
                    ("%s %s" % (self.tr("Topobathymetric elevation model"), dtm_name),
                        # Force EPSG:25831 by problems with QGIS 3.10 version
                        lambda _checked, dtm_name=dtm_name, dtm_url=dtm_url:self.layers.add_raster_layer("%s %s" % (self.tr("Topobathymetric elevation model"), dtm_name), dtm_url, group_name=self.backgroup_map_group_name, group_pos=0, epsg=25831, only_one_map_on_group=False, set_current=True, color_default_expansion=True, resampling_bilinear=True),
                        "cat_coast.png", self.enable_http_files,
                        self.manage_metadata_button("Topobathymetric elevation model %s" % dtm_name), True
                    ) for dtm_name, dtm_url in coast_dtm_list] + [
                    "---"
                    ] + [
                    ("%s %s" % (self.tr("Bathymetric chart"), bathymetric_name),
                        # Force EPSG:25831 by problems with QGIS 3.10 version
                        lambda _checked, bathymetric_name=bathymetric_name, bathymetri_url=bathymetri_url:self.layers.add_vector_layer("%s %s" % (self.tr("Bathymetric chart"), bathymetric_name), bathymetri_url, group_name=self.backgroup_map_group_name, group_pos=0, only_one_map_on_group=False, set_current=True),
                        "cat_coast.png", self.enable_http_files,
                        self.manage_metadata_button("Bathymetric chart %s" % bathymetric_name), True
                    ) for bathymetric_name, bathymetri_url in bathimetric_list] + [
                    "---"
                    ] + [
                    ("%s %s" % (self.tr("Coastline"), coastline_name),
                        # Force EPSG:25831 by problems with QGIS 3.10 version
                        lambda _checked, coastline_name=coastline_name, coastline_url=coastline_url:self.layers.add_vector_layer("%s %s" % (self.tr("Coastline"), coastline_name), coastline_url, group_name=self.backgroup_map_group_name, group_pos=0, only_one_map_on_group=False, set_current=True),
                        "cat_coast.png", self.enable_http_files,
                        self.manage_metadata_button("Coastline %s" % coastline_name), True
                    ) for coastline_name, coastline_url in coastline_list]
                ),
                "---",
                ] if coast_dtm_list or bathimetric_list or coastline_list else []) + [
                (self.tr("NDVI color (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] NDVI color"), "https://geoserveis.icgc.cat/servei/catalunya/ndvi/wms", "ndvi_serie_anual_color", None, "default", "image/png", None, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_landcover.png",
                    self.manage_metadata_button("NDVI (temporal serie)"), True),
                (self.tr("NDVI (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] NDVI"), None, ndvi_current_time, None, "default", "image/png", ndvi_time_series_list, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_shadows.png", self.enable_http_files and len(ndvi_time_series_list) > 0,
                    self.manage_metadata_button("NDVI (temporal serie)"), True),
                "---",
                (self.tr("Current color orthophoto") + " (%s)" % ortho_color_year,
                    lambda _checked:self.layers.add_wms_layer(self.tr("Current color orthophoto"), ortho_wms_url, ["ortofoto_color_vigent"], ["default"], "image/png", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5k.png",
                    self.manage_metadata_button("Color orthophoto (temporal serie)"), True),
                (self.tr("Color orthophoto"), None, "cat_ortho5k.png", [
                    ] + ([(self.tr("Color orthophoto %s (provisional)") % ortoxpres_color_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Color orthophoto %s (provisional)") % ortoxpres_color_year, ortho_wms_url, [ortoxpres_color_layer_id], [""], "image/png", 25831, self.request_referrer_param + "&bgcolor=0xFFFFFF", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5k.png",
                        self.manage_metadata_button("Color orthophoto %s (provisional)" % ortoxpres_color_year), True
                        )] if ortoxpres_color_list else []) + [
                    ] + ([(self.tr("Color orthophoto %s (rectification without corrections)") % ortosuperexp_color_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Color orthophoto %s (rectification without corrections)") % ortosuperexp_color_year, ortho_wms_url, [ortosuperexp_color_layer_id], [""], "image/png", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5k.png",
                        self.manage_metadata_button("Color orthophoto %s (rectification without corrections)" % ortosuperexp_color_year), True
                        )] if ortosuperexp_color_list else []) + [
                    "---",
                    ] + [
                    (self.tr("Color orthophoto %s (temporal serie)") % ortho_year,
                        lambda _checked,layer_id=layer_id:self.add_wms_t_layer(self.tr("[TS] Color orthophoto"), ortho_wms_url, layer_id, None, "default", "image/png", ortho_color_time_series_list, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5k.png",
                        self.manage_metadata_button("Color orthophoto (temporal serie)"), True
                        ) for ortho_year, layer_id in reversed(ortho_color_time_series_list)
                    ] + [
                    "---",
                    (self.tr("Color orthophoto (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Color orthophoto"), "https://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms", "ortofoto_color_serie_anual", None, "", "image/png", None, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5k.png",
                        self.manage_metadata_button("Color orthophoto (temporal serie)"), True),
                    ]),
                (self.tr("Satellite color orthophoto (monthly serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[MS] Satellite color orthophoto"), "https://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2rgb", None, "", "image/png", None, None, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5k.png",
                    self.manage_metadata_button("Satellite color orthophoto (monthly serie)"), True),
                (self.tr("LiDAR color orthophoto (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] LiDAR color orthophoto"), None, None, None, "", "image/png", lidar_ortho_color_time_series_list, lidar_ortho_color_year, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5k.png",
                    self.manage_metadata_button("Territorial Lidar Color Orthophoto"), True),
                "---",
                (self.tr("Current infrared orthophoto") + " (%s)" % ortho_infrared_year,
                    lambda _checked:self.layers.add_wms_layer(self.tr("Current infrared orthophoto"), ortho_wms_url, ["ortofoto_infraroig_vigent"], ["default"], "image/png", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5ki.png",
                    self.manage_metadata_button("Infrared orthophoto (temporal serie)"), True),
                (self.tr("Infrared orthophoto"), None, "cat_ortho5ki.png", [
                    ] + ([(self.tr("Infrared orthophoto %s (provisional)") % ortoxpres_infrared_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Infrared orthophoto %s (provisional)") % ortoxpres_infrared_year, ortho_wms_url, [ortoxpres_infrared_layer_id], [""], "image/png", 25831, self.request_referrer_param + "&bgcolor=0xFFFFFF", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5ki.png",
                        self.manage_metadata_button("Infrared orthophoto %s (provisional)" % ortoxpres_infrared_year), True)
                        ] if ortoxpres_infrared_list else []) + [
                    ] + ([(self.tr("Infrared orthophoto %s (rectification without corrections)") % ortosuperexp_infrared_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Infrared orthophoto %s (rectification without corrections)") % ortosuperexp_infrared_year, ortho_wms_url, [ortosuperexp_infrared_layer_id], [""], "image/png", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5ki.png",
                        self.manage_metadata_button("Infrared orthophoto %s (rectification without corrections)" % ortosuperexp_infrared_year), True)
                        ] if ortosuperexp_infrared_list else []) + [
                    "---",
                    ] + [
                    (self.tr("Infrared orthophoto %s (temporal serie)") % ortho_year,
                        lambda _checked,layer_id=layer_id:self.add_wms_t_layer(self.tr("[TS] Infrared orthophoto"), ortho_wms_url, layer_id, None, "default", "image/png", ortho_infrared_time_series_list, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5ki.png",
                        self.manage_metadata_button("Infrared orthophoto (temporal serie)"), True
                        ) for ortho_year, layer_id in reversed(ortho_infrared_time_series_list)
                    ] + [
                    "---",
                    (self.tr("Infrared orthophoto (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Infrared orthophoto"), "https://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms", "ortofoto_infraroig_serie_anual", None, "", "image/png", None, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        "cat_ortho5ki.png",
                        self.manage_metadata_button("Infrared orthophoto (temporal serie)"), True),
                    ]),
                (self.tr("Satellite infrared orthophoto (monthly serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[MS] Satellite infared orthophoto"), "https://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2irc", None, "default", "image/png", None, None, 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5ki.png",
                    self.manage_metadata_button("Satellite infrared orthophoto (monthly serie)"), True),
                (self.tr("LiDAR infrared orthophoto (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] LiDAR infrared orthophoto"), None, None, None, "", "image/png", lidar_ortho_infrared_time_series_list, lidar_ortho_infrared_year, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5ki.png",
                    self.manage_metadata_button("Territorial Lidar Infrared Orthophoto"), True),
                "---",
                (self.tr("Current gray orthophoto") + " (%s)" % ortho_color_year,
                    lambda _checked:self.layers.add_wms_layer(self.tr("Current gray orthophoto"), ortho_wms_url, ["ortofoto_gris_vigent"], ["default"], "image/png", 25831, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    "cat_ortho5kbw.png",
                    self.manage_metadata_button("Gray orthophoto (temporal serie)"), True),
                "---",
                (self.tr("Centered photogram"), None, "photo.png", [
                    (self.tr("Centered photogram (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Centered photogram"), photolib_wms_url, "foto_central", photolib_current_time, "central", "image/png", None, None, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False),
                        "photo.png"),
                    (self.tr("Centered rectified photogram (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Centered rectified photogram"), photolib_wms_url, "ortoxpres_central", photolib_current_time, "central", "image/png", None, None, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False),
                        "rectified.png"),
                    (self.tr("Centered anaglyph photogram (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Centered anaglyph phootogram"), photolib_wms_url, "anaglif_central", photolib_current_time, "central,100,false", "image/png", None, None, 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False),
                        "stereo.png"),
                        #) for anaglyph_year, anaglyph_layer in reversed(photolib_time_series_list)]),
                    ]),
                "---",
                ] + ([
                    (self.tr("Others"), None, "cat_cmstandard.png", [
                        (self.tr("ContextMaps standard map"),
                            lambda _checked:self.layers.add_wms_layer(self.tr("ContextMaps standard map"), "https://geoserveis.icgc.cat/servei/catalunya/contextmaps/wms", ["contextmaps-mapa-estandard"], [""], "image/jpeg", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "cat_cmstandard.png",
                            self.manage_metadata_button("ContextMaps standard map"), True),
                        (self.tr("ContextMaps gray map"),
                            lambda _checked:self.layers.add_wms_layer(self.tr("ContextMaps gray map"), "https://geoserveis.icgc.cat/servei/catalunya/contextmaps/wms", ["contextmaps-mapa-base-gris"], [""], "image/jpeg", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "cat_cmgray.png",
                            self.manage_metadata_button("ContextMaps gray map"), True),
                        (self.tr("ContextMaps simplified gray map"),
                            lambda _checked:self.layers.add_wms_layer(self.tr("ContextMaps simplified gray map"), "https://geoserveis.icgc.cat/servei/catalunya/contextmaps/wms", ["contextmaps-mapa-base-gris-simplificat"], [""], "image/jpeg", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "cat_cmgray.png",
                            self.manage_metadata_button("ContextMaps simplified gray map"), True),
                        (self.tr("ContextMaps hybrid orthophoto"),
                            lambda _checked:self.layers.add_wms_layer(self.tr("ContextMaps hybrid orthophoto"), "https://geoserveis.icgc.cat/servei/catalunya/contextmaps/wms", ["contextmaps-orto-hibrida"], [""], "image/jpeg", 25831, self.request_referrer_param, self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "cat_cmortho.png",
                            self.manage_metadata_button("ContextMaps hybrid orthophoto"), True),
                        "---",
                        (self.tr("Instamaps pyramid"),
                            lambda:self.layers.add_wms_layer(self.tr("Instamaps pyramid"), "https://tilemaps.icgc.cat/mapfactory/service", ["osm_suau"], ["default"], "image/png", 25831, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "cat_topo5k.png"),
                        ]),
                    "---",
                    (self.tr("Spain"), None, "spain_topo.png", [
                        (self.tr("IGN topographic"),
                            lambda:self.layers.add_wms_layer(self.tr("IGN topographic"), "http://www.ign.es/wms-inspire/mapa-raster", ["mtn_rasterizado"], ["default"], "image/png", 25830, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "spain_topo.png"),
                        "---",
                        (self.tr("PNOA orthophoto"),
                            lambda:self.layers.add_wms_layer(self.tr("PNOA orthophoto"), "http://www.ign.es/wms-inspire/pnoa-ma", ["OI.OrthoimageCoverage"], ["default"], "image/png", 25830, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "spain_orto.png"),
                        "---",
                        (self.tr("Cadastral registry"),
                            lambda:self.layers.add_wms_layer(self.tr("Cadastral registry"), "http://ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx", ["Catastro"], ["default"], "image/png", 25831, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "spain_cadastral.png"),
                        ]),
                    (self.tr('Andorra'), None, "andorra_topo50k.png", [
                        (self.tr("Andorra topographic 1:50,000 2020"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra topographic 1:50,000 2020"), "https://www.ideandorra.ad/Serveis/wmscarto50kraster_2020/wms", ["mta50m2020geotif"], [], "image/png",  27563, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "andorra_topo50k.png"),
                        "---",
                        (self.tr("Andorra orthophoto 1:5,000 2012"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra orthophoto 1:5,000 2012"), "https://www.ideandorra.ad/Serveis/wmsorto2012/wms", ["orto2012"], [], "image/png",  27563, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "andorra_orto2003.png"),
                        ]),
                    (self.tr("France"), None, "france_topo.png", [
                        (self.tr("France topographic"),
                            lambda:self.layers.add_wms_layer(self.tr("France topographic"), "http://mapsref.brgm.fr/wxs/refcom-brgm/refign", ["FONDS_SCAN"], [], "image/png", 23031, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "france_topo.png"),
                        "---",
                        (self.tr("France orthophoto 20cm"),
                            lambda:self.layers.add_wms_layer(self.tr("France orthophoto 20cm"), "https://data.geopf.fr/annexes/ressources/wms-r/ortho.xml", ["HR.ORTHOIMAGERY.ORTHOPHOTOS"], ["normal"], "image/png", 23031, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, ignore_get_map_url=False),
                            "france_ortho.png"),
                        ]),
                    (self.tr("World"), None, "world.png", [
                        (self.tr("OpenStreetMap"),
                            lambda:self.layers.add_wms_layer(self.tr("OpenStreetMap"), "http://ows.terrestris.de/osm/service", ["OSM-WMS"], [], "image/png", 4326, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "world.png"),
                        (self.tr("NASA blue marble"),
                         lambda:self.layers.add_wms_layer(self.tr("NASA blue marble"), "http://geoserver.webservice-energy.org/geoserver/ows", ["gn:bluemarble-2048"], [], "image/png", 4326, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            "world.png"),
                         ]),
                    "---",
                ] if self.extra_countries or self.debug_mode else []) + [
                (self.tr("Delete background maps"), lambda _checked:self.legend.empty_group_by_name(self.backgroup_map_group_name),
                    "wms_remove.png", True, False, "delete_background")
                ]),
            (self.tr("Time series"),
                lambda _checked:self.tools.toggle_time_series_dialog(self.iface.mapCanvas().currentLayer(), self.tr("Time series"), self.tr("Selected: ")) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                "time.png",
                False, True, "time_series"),
            ] + ([
                (self.tr("Search photograms"), (self.enable_search_photos, self.pair_photo_search_checks),
                    "search.png", photo_search_selection_dialog_ok, True, "photo_search", [
                    (self.tr("Search photograms interactively"), (self.enable_search_photos, self.pair_photo_search_checks),
                        "search.png", True, True, "photo_search_2"),
                    (self.tr("Search photograms by coordinates"), lambda _checked:self.search_photos_by_point(),
                        "search_coord.png", True, False),
                    (self.tr("Search photograms by name"), lambda _checked:self.search_photos_by_name(),
                        "search_name.png", True, False),
                    ]),
                (self.tr("Download tool"), self.enable_last_download,
                    "download_area.png", True, True, "download", [
                    (self.tr("Select download folder"), self.set_download_folder,
                        "download_folder.png", True, False, "select_download_folder"),
                    (self.tr("Open download folder"), self.open_download_folder,
                        style.standardIcon(QStyle.SP_DirIcon), True, False, "open_download_folder"),
                    "---",
                    ] + download_vector_submenu + [
                    "---"
                    ] + download_raster_submenu + [
                    "---",
                    (self.tr("Save map as PDF"), lambda:self.save_map("A4H", "", self.tr("Save map as PDF")),
                        "pdf.png", True, False, "save_pdf"),
                    (self.tr("Save location map as PDF"), lambda:self.save_map("A4V", self.tr(" (location)"), self.tr("Save location map as PDF")),
                        "pdf.png", True, False, "save_location_pdf"),
                    ])
            ] if not self.lite else []) + [
            (self.tr("Paint styles for selected layers"), None,
                "style.png", [
                (self.tr("Transparence"),
                    lambda _checked:self.tools.show_transparency_dialog(self.tr("Transparence"), self.iface.mapCanvas().currentLayer()) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                    "transparency.png"),
                (self.tr("Desaturate raster layer"),
                    lambda _checked:self.layers.set_saturation(self.iface.mapCanvas().currentLayer(), -100, True) if type(self.iface.mapCanvas().currentLayer()) is QgsRasterLayer else None,
                    "desaturate.png"),
                (self.tr("Height highlighting"),
                    lambda _checked, dtm_url=height_highlighting_url:self.add_height_highlighting_layer(self.tr("Height highlighting"), dtm_url, style_file="ressaltat_alçades.qml", group_name=self.backgroup_map_group_name),
                    "cat_shadows.png", self.enable_http_files and height_highlighting_url),
                (self.tr("Shading DTM layer"),
                    self.shading_dtm,
                    "cat_shadows.png"),
                "---",
                (self.tr("Anaglyph options"),
                    lambda _checked:self.tools.show_anaglyph_dialog(self.iface.mapCanvas().currentLayer(), self.tr("Anaglyph"), self.tr("Anaglyph"), self.tr("Inverted stereo")),
                    "stereo.png"),
                (self.tr("Change DB/geoPackage style"),
                    lambda _checked:self.tools.show_db_styles_dialog(self.tr("Change DB/geoPackage style")),
                    "style.png",
                    False, False, "geopackage_style"),
            ]),
            ] + ([] if self.lite else [
            "---",
            (self.tr("Help"), self.show_help, "help.png", [
                (self.tr("About Open ICGC"), self.show_about, "icon.png"),
                (self.tr("What's new"), self.show_changelog, "new.png"),
                (self.tr("Help"), self.show_help, "help.png"),
                "---",
                (self.tr("Available products list"), self.show_available_products,
                    style.standardIcon(QStyle.SP_FileDialogDetailedView)),
                (self.tr("Deprecated products list"),
                    lambda _checked:self.show_url("https://www.icgc.cat/ca/Geoinformacio-i-mapes/Obsolescencia-daplicacions-productes-i-serveis"),
                    style.standardIcon(QStyle.SP_FileDialogDetailedView)),
                "---",
                (self.tr("Cartographic and Geological Institute of Catalonia web"),
                    lambda _checked:self.show_help_file("icgc"), "icgc.png"),
                (self.tr("QGIS plugin repository"),
                    lambda _checked:self.show_help_file("plugin_qgis"),
                    "plugin.png"),
                (self.tr("Software Repository"),
                    lambda _checked:self.show_help_file("plugin_github"),
                    "git.png"),
                (self.tr("Send us an email"),
                    lambda _checked, new_plugin_version=new_plugin_version:self.send_email(new_plugin_version=new_plugin_version),
                    "send_email.png"),
                "---",
                (self.tr("Report an issue"),
                    lambda _checked, new_plugin_version=new_plugin_version:self.report_issue(new_plugin_version=new_plugin_version),
                    "bug.png"),
                (self.tr("Debug"), None, "bug_target.png", [
                    (self.tr("Enable debug log info"),
                        self.enable_debug_log,
                        "bug_target.png", True, True, "enable_debug_log"),
                    (self.tr("Open debug log file"),
                        lambda _checked:self.gui.open_file_folder(self.log.getLogFilename()),
                        style.standardIcon(QStyle.SP_FileIcon), self.log.getLogFilename() is not None),
                    (self.tr("Open plugin installation folder"),
                        lambda _checked:self.gui.open_file_folder(self.plugin_path),
                        style.standardIcon(QStyle.SP_DirIcon)),
                    (self.tr("Send us an email with debug information"),
                        lambda _checked, new_plugin_version=new_plugin_version:self.send_email(debug=True, new_plugin_version=new_plugin_version),
                        "send_email_red.png"),
                    ]),
                ]),
            ]) + ([] if not new_qgis_plugin_version or self.lite else [
                self.tr("Update\n available: v%s") % new_qgis_plugin_version,
                (self.tr("Download plugin"),
                    lambda _checked,v=new_qgis_plugin_version:self.download_plugin_update(v, UpdateType.plugin_manager),
                    "new.png"),
            ]) + ([] if not new_icgc_plugin_version or self.lite else [
                self.tr("Update\n available: v%s") % new_icgc_plugin_version,
                (self.tr("Download plugin"),
                    lambda _checked,v=new_icgc_plugin_version:self.download_plugin_update(v, UpdateType.icgc_web),
                    "new_icgc.png"),
            ]) + ([] if self.qgis_version_ok or self.lite else [
                self.tr("Warning:"),
                (self.tr("QGIS version warnings"),
                    self.show_qgis_version_warnings,
                    style.standardIcon(QStyle.SP_MessageBoxWarning)),
            ]))

        # Add plugin reload and test buttons (debug purpose)
        if not self.lite:
            if self.debug_mode or self.test_available:
                self.gui.add_to_toolbar(self.toolbar, ["---"])
            if self.debug_mode:
                self.gui.add_to_toolbar(self.toolbar, [
                    (self.tr("Reload Open ICGC"), lambda _checked:self.reload_plugin(),
                        "python.png"),
                    ])
            if self.test_available:
                self.gui.add_to_toolbar(self.toolbar, [
                    (self.tr("Unit tests"),
                        lambda _checked:self.debug.show_test_plugin(self.tr("Unit tests")),
                        "flask.png", [
                            (test_name,
                                lambda _checked, test_name=test_name:self.debug.show_test_plugin(self.tr("Unit tests"), test_name),
                                "flask.png")
                            for test_name in self.debug.get_test_names()
                        ]),
                    ])

        # Check debug button if debug_mode
        if self.debug_mode:
            self.gui.set_check_item("enable_debug_log")

        # Get a reference to any actions
        self.download_action = self.gui.find_action("download").defaultWidget().defaultAction() if self.gui.find_action("download") else None  # it is a toolbar menu, it has a subaction...
        self.time_series_action = self.gui.find_action("time_series")
        self.geopackage_style_action = self.gui.find_action("geopackage_style")
        self.photo_search_action = self.gui.find_action("photo_search").defaultWidget().defaultAction() if self.gui.find_action("photo_search") else None
        self.photo_search_2_action = self.gui.find_action("photo_search_2")
        self.photo_download_action = self.gui.find_action("photo")

        # Add a tool to download map areas
        self.tool_subscene = QgsMapToolSubScene(self.iface.mapCanvas())

        # Add a tool to search photograms in photo library (set action to manage check/uncheck tools)
        self.tool_photo_search = QgsMapToolPhotoSearch(self.iface.mapCanvas(), self.search_photos, self.photo_search_action)

        # Log plugin started
        t1 = datetime.datetime.now()
        self.log.info("Initialization complete (%s)" % (t1-t0))

    def manage_metadata_button(self, product_access=None, product_metadata_url=None):
        """ Returns buttons list for product metadata """
        style = self.iface.mainWindow().style()
        if not product_metadata_url:
            product_metadata_url = self.product_metadata_dict.get(product_access, None)
        return [(self.tr("Product metadatas"), \
            lambda: self.show_url(product_metadata_url), \
            style.standardIcon(QStyle.SP_MessageBoxInformation), \
            )] if product_metadata_url else []

    def get_download_menu(self, fme_services_list, raster_not_vector=None, nested_download_submenu=True):
        """ Create download submenu structure list """
        # Filter data type if required
        if raster_not_vector is not None:
            fme_services_list = [(id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, \
                filename, limits, url_pattern, url_ref_or_wms_tuple, enabled) \
                for id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, \
                filename, limits, url_pattern, url_ref_or_wms_tuple, enabled \
                in fme_services_list if self.is_raster_file(filename) == raster_not_vector]

        # Define text labels
        vector_label = self.tr(" vectorial data")
        raster_label = self.tr(" raster data")
        product_label_pattern = "%s" + ("" if raster_not_vector is None else raster_label if raster_not_vector else vector_label)
        product_file_label_pattern = "%s%s (%s)"

        # Prepare nested download submenu
        if nested_download_submenu:
            # Add a end null entry
            fme_extra_services_list = fme_services_list + [ \
                (None, None, None, None, None, None, None, None, None, None, None, None, None, None)]
            download_submenu = []
            product_submenu = []
            gsd_info_dict = {}
            # Create menu with a submenu for every product prefix
            for i, (id, _name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, \
                filename, limits, url_pattern, url_ref_or_wms_tuple, enabled) in enumerate(fme_extra_services_list):
                prefix_id = id[:2] if id else None
                previous_id = fme_extra_services_list[i-1][0] if i > 0 else id
                previous_prefix_id = previous_id[:2]
                previous_name = fme_extra_services_list[i-1][1]

                # If break group prefix, create a grouped menu entry
                if previous_prefix_id != prefix_id:
                    # Find group product common prefix
                    if len(gsd_info_dict) == 1:
                        common_name = self.FME_NAMES_DICT.get(previous_id, previous_name)
                    elif len(product_submenu) == 1:
                        common_name = None
                    else:
                        previous_name1 = self.FME_NAMES_DICT.get(previous_id, previous_name)
                        previous_name2 = self.FME_NAMES_DICT.get(fme_extra_services_list[i-2][0], fme_extra_services_list[i-2][1])
                        diff_list = [pos for pos in range(min(len(previous_name1), len(previous_name2))) \
                            if previous_name1[pos] != previous_name2[pos]]
                        pos = diff_list[0] if diff_list else min(len(previous_name1), len(previous_name2))
                        common_name = previous_name1[:pos].replace("1:", "").strip()
                    # Create submenu
                    if gsd_info_dict:
                        # Add single ménu entry with GDS info dict
                        previous_time_list = list(gsd_info_dict.values())[0][6]
                        previous_enabled = any([info[-1] for info in gsd_info_dict.values()])
                        download_submenu.append((
                            product_file_label_pattern % (common_name,
                                raster_label if self.is_raster_file(filename) else vector_label if self.is_vector_file(filename) else "",
                                os.path.splitext(filename)[1][1:]),
                            (lambda _dummy, id=previous_prefix_id, name=common_name, time_list=previous_time_list, gsd_info_dict=gsd_info_dict: \
                                self.enable_download_subscene(id, name, None, None, None, None, time_list, None, None, None, None, gsd_info_dict), self.pair_download_checks),
                            self.FME_ICON_DICT.get(previous_prefix_id, None),
                            previous_enabled, True, previous_prefix_id,
                            self.manage_metadata_button(self.FME_METADATA_DICT.get(previous_id, None) \
                                or self.FME_METADATA_DICT.get(previous_prefix_id, None)),
                            True
                            ))
                        gsd_info_dict = {}
                    elif product_submenu:
                        if len(product_submenu) == 1:
                            # Add single menu entry with one product
                            download_submenu.append(product_submenu[0])
                        else:
                            # Add submenu entry
                            download_submenu.append(
                                (product_label_pattern % common_name,
                                None,
                                self.FME_ICON_DICT.get(previous_prefix_id, None),
                                product_submenu))
                        product_submenu = []

                # Store info in group (submenu or gsd group)
                if id:
                    first_part_id = id.split()[0]
                    last_part_id = id.split()[-1]
                    product_name = self.FME_NAMES_DICT.get(id, None) \
                        or ((self.FME_NAMES_DICT[first_part_id] + " " + last_part_id) \
                            if self.FME_NAMES_DICT.get(first_part_id, None) else id)
                    file_label = product_file_label_pattern % (product_name, \
                        raster_label if self.is_raster_file(filename) else vector_label if self.is_vector_file(filename) else "", \
                        os.path.splitext(filename)[1][1:])
                    if gsd:
                        # Store product info in GSD dict
                        gsd_info_dict[gsd] = (id, file_label, min_side, max_query_area, min_px_side, max_px_area, \
                            time_list, download_list, filename, limits, url_ref_or_wms_tuple, enabled)
                    else:
                        # Add entry to temporal product submenu
                        first_part_id = id.split()[0]
                        last_part_id = id.split()[-1]
                        product_submenu.append((
                            file_label,
                            (lambda _dummy, id=id, name=product_name, min_side=min_side, max_query_area=max_query_area, min_px_side=min_px_side, max_px_area=max_px_area, time_list=time_list, download_list=download_list, filename=filename, limits=limits, url_ref_or_wms_tuple=url_ref_or_wms_tuple : \
                                self.enable_download_subscene(id, name, min_side, max_query_area, min_px_side, max_px_area, time_list, download_list, filename, limits, url_ref_or_wms_tuple), self.pair_download_checks),
                            self.FME_ICON_DICT.get(prefix_id, None),
                            enabled, True, id, # Indiquem: actiu, checkable i un id d'acció
                            self.manage_metadata_button(self.FME_METADATA_DICT.get(id, None) \
                                or self.FME_METADATA_DICT.get(prefix_id, None) \
                                or (self.FME_METADATA_DICT[first_part_id] + " " + last_part_id \
                                    if self.FME_METADATA_DICT.get(first_part_id, None) else None)
                                ),
                            True
                            ))

        # Prepare "all in one" download submenu
        else:
            fme_extra_services_list = []
            # Add separators on change product prefix
            for i, (id, name, min_side, max_query_area, min_px_side, max_px_area, gsd, time_list, download_list, \
                filename, limits, url_pattern, url_ref_or_wms_tuple, enabled) in enumerate(fme_services_list):
                prefix_id = id[:2] if id else None
                previous_id = fme_extra_services_list[i-1][0] if i > 0 else id
                previous_prefix_id = previous_id[:2] if previous_id else None
                first_part_id = id.split()[0]
                last_part_id = id.split()[-1]

                # If change 2 first characters the inject a separator
                if prefix_id != previous_prefix_id:
                    fme_extra_services_list.append((None, None, None, None, None, None, None, None, \
                        None, None, None, None)) # 11 + 1 (vectorial_not_raster)
                vectorial_not_raster = not self.is_raster_file(filename)
                fme_extra_services_list.append((id, name, min_side, max_query_area, min_px_side, max_px_area, filename, \
                    limits, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple, enabled)) # 12 params
            # Create download menu
            first_part_id = id.split()[0]
            last_part_id = id.split()[-1]
            download_submenu = [
                (product_file_label_pattern % (name,
                    raster_label if self.is_raster_file(filename) else vector_label if self.is_vector_file(filename) else "",
                    os.path.splitext(filename)[1][1:]),
                    (lambda _dummy, id=id, name=name, min_side=min_side, max_query_area=max_query_area, min_px_side=min_px_side, max_px_area=max_px_area, time_list=time_list, download_list=download_list, filename=filename, limits=limits, url_ref_or_wms_tuple=url_ref_or_wms_tuple : \
                        self.enable_download_subscene(id, name, min_side, max_query_area, min_px_side, max_px_area, time_list, download_list, filename, limits, url_ref_or_wms_tuple), self.pair_download_checks),
                    self.FME_ICON_DICT.get(id[:2], None),
                    enabled, True, id,  # Indiquem: actiu, checkable i un id d'acció
                    self.manage_metadata_button(self.FME_METADATA_DICT.get(id, None) \
                        or self.FME_METADATA_DICT.get(prefix_id, None) \
                        or (self.FME_METADATA_DICT[first_part_id] + " " + last_part_id \
                            if self.FME_METADATA_DICT.get(first_part_id, None) else None)
                        ),
                    True
                ) if id else "---" for id, name, min_side, max_query_area, min_px_side, max_px_area, filename, \
                    limits, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple, enabled in fme_extra_services_list
                ]

        return download_submenu


    ###########################################################################
    # Signals

    def on_change_current_layer(self, layer):
        """ Enable disable time series options according to the selected layer """
        is_wms_t = layer is not None and self.layers.is_wms_t_layer(layer)
        if self.time_series_action:
            self.time_series_action.setEnabled(is_wms_t)
            self.time_series_action.setChecked(self.tools.time_series_dialog is not None and self.tools.time_series_dialog.isVisible())

    def on_click_legend(self, _index):
        """ Enable disable geopackage style options according to the selected layer """
        is_geopackage_layer = self.tools.is_current_group_db_styled_layers()
        if self.geopackage_style_action:
            self.geopackage_style_action.setEnabled(is_geopackage_layer)

    def on_change_photo_selection(self):
        """ Select photogram in photosearch dialog if change selection on photosearch layer """
        if self.photo_search_dialog and self.photo_search_dialog.isVisible():
            photo_id, flight_year, _flight_code, _filename, _photo_name, gsd, _epsg = self.get_selected_photo_info(show_errors=False)
            if self.photo_search_dialog:
                self.photo_search_dialog.select_photo(photo_id, flight_year, update_map=False)
            if self.tool_subscene:
                self.tool_subscene.set_gsd(gsd)

    def pair_download_checks(self, status):
        """ Synchronize the check of the button associated with Download button """
        if self.download_action:
            self.download_action.setChecked(status)

    def enable_last_download(self):
        """ Undo the change on button state we make when clicking on the Download button """
        # Undo last check change and if previous download action is enabled, exit
        if self.download_action:
            self.download_action.setChecked(not self.download_action.isChecked())
        if self.download_action.isChecked():
            return
        # Show last download reference layer
        ref_layer = self.load_last_ref_layer()
        # Enable or execute current download tool
        self.enable_download_tool(with_ref_layer=(ref_layer is not None))

    def pair_photo_search_checks(self, status):
        """ Synchronize the check of the button associated with Download button """
        if self.photo_search_2_action:
            self.photo_search_2_action.setChecked(status)
        if self.photo_search_action:
            self.photo_search_action.setChecked(status)


    ###########################################################################
    # Functionalities

    def run(self, _checked=False): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Basic plugin call, which reads the text of the combobox and the search for the different web services available """
        search_text = self.combobox.currentText()
        self.find(search_text)
        # Set search text on top of combobox
        pos = self.combobox.findText(search_text)
        if pos != 0:
            self.combobox.removeItem(pos)
            self.combobox.insertItem(0, search_text)
            self.combobox.setCurrentIndex(0)
        # Save last searches in persistent app settings
        searches_list = [self.combobox.itemText(i) for i in range(self.combobox.count())][:self.combobox.maxVisibleItems()]
        self.set_setting_value("last_searches", searches_list)

    def add_wms_t_layer(self, layer_name, url, layer_id, time, style, image_format, time_series_list=None, time_series_regex=None, epsg=None, extra_tags="", group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False):
        """ Add WMS-T layer and enable timeseries dialog """
        # Add WMS-T
        layer = self.layers.add_wms_t_layer(layer_name, url, layer_id, time, style, image_format, time_series_list, time_series_regex, epsg, extra_tags, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, saturation, resampling_bilinear, resampling_cubic, set_current)
        if layer:
            if type(layer) in [QgsRasterLayer, QgsVectorLayer]:
                # Show timeseries dialog
                self.tools.show_time_series_dialog(layer, self.tr("Time series"), self.tr("Selected: "))
                # Enable / check timeseries button
                if self.time_series_action:
                    self.time_series_action.setEnabled(True)
                    self.time_series_action.setChecked(self.tools.time_series_dialog is not None and self.tools.time_series_dialog.isVisible())
            # Show stereo anaglyph options
            if layer_id and layer_id.lower().startswith("anaglif"):
                self.tools.show_anaglyph_dialog(layer, self.tr("Anaglyph"), self.tr("Anaglyph"), self.tr("Inverted stereo"))
            # Show "on the fly" central photogram rendering layers warning
            if layer_id and layer_id.lower().endswith("_central"):
                message = self.tr("This layer renders only the most centered photogram in the map view, you can zoom in for continuous navigation. Please note that current year may not have full photogram coverage")
                self.iface.messageBar().pushMessage(layer_name, message, level=Qgis.Info, duration=10)

        return layer

    def find(self, user_text):
        """ Performs a geo-spatial query and shows the results to the user so he can choose the one he wants to visualize """
        # Check user text
        if not user_text:
            QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"), self.tr("You must write any text"))
            return

        # Check loaded map. If we have not maps, we load default map and rerun search
        if not self.iface.mapCanvas().layers():
            self.default_map_callback()
            return self.find(user_text)

        # Find user text
        try:
            if not self.geofinder_dialog.find(user_text, self.project.get_epsg()):
                return
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"), str(e))
            return

        # If we have a rectangle, we do not have to do anything, we get the coordinates and access
        if self.geofinder_dialog.is_rectangle():
            # Get rectangle coordinates
            west, north, east, south, epsg = self.geofinder_dialog.get_rectangle()
            # We resituate the map (implemented in parent PluginBase)
            self.set_map_rectangle(west, north, east, south, epsg)
        else:
            # We get point coordinates
            x, y, epsg = self.geofinder_dialog.get_point()
            if not x or not y:
                self.log.warning("Error, no coordinates found")
                QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"),
                    self.tr("Error, location without coordinates"))
                return
            scale = self.geofinder_dialog.get_scale()
            # We resituate the map (implemented in parent PluginBase)
            self.set_map_point(x, y, epsg, scale)

    def is_unsupported_file(self, pathname):
        return self.is_file_type(pathname, ["dgn", "dwg", "ifc"])
    def is_unsupported_extension(self, ext):
        return self.is_extension(ext, ["dgn", "dwg", "ifc"])

    def is_compressed_file(self, pathname):
        return self.is_file_type(pathname, ["zip"])
    def is_compressed_extension(self, ext):
        return self.is_extension(ext, ["zip"])

    def is_raster_file(self, pathname):
        return self.is_file_type(pathname, ["tif", "jpeg", "jpg", "png"])
    def is_raster_extension(self, ext):
        return self.is_extension(ext, ["tif", "jpeg", "jpg", "png"])

    def is_vector_file(self, pathname):
        return self.is_file_type(pathname, ["shp", "dgn", "dwg", "gpkg", "shp-zip"])
    def is_vector_extension(self, ext):
        return self.is_extension(ext, ["shp", "dgn", "dwg", "gpkg", "shp-zip"])

    def is_points_file(self, pathname):
        return self.is_file_type(pathname, ["laz", "las"])
    def is_points_extension(self, ext):
        return self.is_extension(ext, ["laz", "las"])

    def is_slow_file(self, pathname):
        return self.is_file_type(pathname, ["laz", "las"])
    def is_slow_extension(self, ext):
        return self.is_extension(ext, ["laz", "las"])

    def is_file_type(self, pathname, ext_list):
        _filename, ext = os.path.splitext(pathname)
        return self.is_extension(ext, ext_list)
    def is_extension(self, ext, ext_list):
        return ext[1:].lower() in ext_list

    def enable_download_subscene(self, data_type, name, min_side, max_download_area, min_px_side, max_px_area, time_list, download_list, filename, limits, url_ref_or_wms_tuple, gsd_dict={}):
        """ Enable subscene tool """
        title = self.tr("Download tool")

        # Uncheck previous associated action
        old_action = self.tool_subscene.action()
        if old_action:
            old_action.setChecked(False)
        # Get action associated to data_type
        action = self.gui.find_action(data_type)

        # Initialy disables any tool
        if action:
            action.setChecked(False)
        self.gui.enable_tool(None)

        is_photo = (data_type == "photo")
        is_historic_ortho = (data_type.startswith("hc") or data_type.startswith("hi"))

        # Check photo search warning
        gsd = None
        if is_photo:
            # If we want download a photogram, we need have select it one
            photo_id, _flight_year, _flight_code, _filename, _photo_name, gsd, _epsg = self.get_selected_photo_info()
            if photo_id is None:
                action.setChecked(False)
                self.gui.enable_tool(None)
                return
            # If we have a selected photo, we show it
            # we force keep the layer active, when we add a layer to a group sometimes the active layer changes
            self.photo_search_dialog.preview()

        # Check EPSG warning
        if self.project.get_epsg() != "25831":
            if QMessageBox.warning(self.iface.mainWindow(), title, \
                self.tr("ICGC products are generated in EPSG 25831, loading them into a project with EPSG %s could cause display problems, download problems, or increased load time.\n\nDo you want change the project coordinate system to EPSG 25831?") % self.project.get_epsg(), \
                #"Els productes ICGC estan generats en EPSG 25831, carregar-los en un projecte amb EPSG %s podria provocar problemes de visualització, descàrrega o augment del temps de càrrega.\n\nVols canviar el sistema de coordenades del projecte a EPSG 25831?"
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.project.set_epsg(25831)

        if gsd_dict:
            # With GSD dictionari, integrates all GSD years
            time_list_list = [time_list or [] for _data_type, _name, _min_side, _max_download_area, _min_px_side, _max_px_area, time_list, _download_list, _filename, _limits, _url_ref_or_wms_tuple, _enabled in gsd_dict.values()]
            time_list = sorted(list(set([item for sublist in time_list_list for item in sublist])))
            if not time_list:
                time_list = [None]
            data_dict = {year: {gsd: {description: id \
                for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST \
                if operation_code in download_list} \
                for (gsd, (_data_type, _name, _min_side, _max_download_area, _min_px_side, _max_px_area, _time_list, download_list, _filename, _limits, _url_ref_or_wms_tuple, _enabled)) in gsd_dict.items() \
                if not year or year in gsd_dict[gsd][6]} \
                for year in time_list}
        else:
            # Without GSD dictionari
            download_type_dict = {description: id \
                for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST \
                if operation_code in download_list}
            if not time_list:
                time_list = [None]
            data_dict = {year: {None: download_type_dict} for year in time_list}
        # Open dialog
        if not self.download_dialog:
            self.download_dialog = DownloadDialog(data_dict)
        else:
            self.download_dialog.set_data(data_dict)
        ok_pressed = self.download_dialog.do_modal()
        if not ok_pressed:
            return
        # Gets download parameters for selected product
        self.download_type = self.download_dialog.get_download_type()
        fme_download_type_dict = {id: (description, op_code) for id, description, op_code in self.FME_DOWNLOADTYPE_LIST}
        download_description, download_operation_code = fme_download_type_dict[self.download_type]
        time_code = self.download_dialog.get_year()
        gsd = self.download_dialog.get_gsd()
        if gsd_dict and gsd:
            data_type, name, min_side, max_download_area, min_px_side, max_px_area, time_list, download_list, filename, limits, url_ref_or_wms_tuple, enabled = gsd_dict[gsd]

        # Changes icon and tooltip of download button
        self.gui.set_item_icon("download",
            "download_%s.png" % self.download_type.replace("dt_", ""),
            "%s: %s / %s%s" % (self.tr("Download tool"), download_description, name, (" / %s" % time_code if time_code else "")))

        # Load reference map layer
        self.load_last_ref_layer = lambda:None
        if url_ref_or_wms_tuple:
            # If it is historic ortho we need gets reference file dynamically
            if is_historic_ortho:
                ref_file, symbol_file = url_ref_or_wms_tuple
                color_not_irc = data_type.startswith("hc")
                ref_file = get_historic_ortho_ref(color_not_irc, gsd, time_code)
                url_ref_or_wms_tuple = (ref_file, symbol_file) if ref_file else None
                name += " %d" % time_code
            self.load_last_ref_layer = lambda:self.load_ref_layer(url_ref_or_wms_tuple, name)
            self.load_last_ref_layer()

        # Configure new option to download
        self.tool_subscene.set_callback(lambda geo, data_type=data_type,
            min_side=min_side, max_download_area=max_download_area, min_px_side=min_px_side, max_px_area=max_px_area,
            time_code=time_code, download_operation_code=download_operation_code, filename=filename, limits=limits:
            self.download_map_area(geo, data_type, min_side, max_download_area, min_px_side, max_px_area, gsd, time_code, download_operation_code, filename, limits))
        self.tool_subscene.set_min_max(min_side, max_download_area, min_px_side, max_px_area, FME_MAX_ASPECT_RATIO)
        self.tool_subscene.set_gsd(gsd)
        self.tool_subscene.set_mode(self.download_type in ['dt_area', 'dt_coord', 'dt_layer_polygon', 'dt_layer_polygon_bb'])
        # Configure new download action (for auto manage check/uncheck action button)
        self.tool_subscene.setAction(action)
        # Enable or execute current download tool
        self.enable_download_tool(with_ref_layer=(url_ref_or_wms_tuple is not None))

    def enable_download_tool(self, with_ref_layer=False):
        """ Enable or execute current download tool """
        if not self.tool_subscene.callback:
            return
        if self.download_type in ["dt_area", "dt_counties", "dt_municipalities", "dt_sheet"]:
            # Show download type info
            title = self.tr("Download tool")
            message = None
            if self.download_type == 'dt_area':
                message = self.tr("Select an area")
            elif self.download_type == 'dt_municipalities':
                message = self.tr("Select municipality")
            elif self.download_type == 'dt_counties':
                message = self.tr("Select county")
            elif self.download_type == 'dt_sheet':
                message = self.tr("Select sheet")
            # Show reference layer info
            if with_ref_layer:
                if not message:
                    message = self.tr("Select a zone")
                message += self.tr(" with available information")
            if message:
                self.iface.messageBar().pushMessage(title, message, level=Qgis.Info, duration=5)
            # Interactive point or rect is required, enable tool
            self.gui.enable_tool(self.tool_subscene)
            self.download_action.setChecked(True)
        else:
            # No interactive geometry required, call download process
            self.tool_subscene.subscene()

    def download_map_area(self, geo, data_type, min_side, max_download_area, min_px_side, max_px_area, gsd, time_code, download_operation_code, local_filename, limits="cat_simple"):
        """ Download a FME server data area (limited to max_download_area) """

        # Check download file type
        filename, ext = os.path.splitext(local_filename)
        download_ext = ("" if len(ext.split("-")) <= 1 else ".") + ext.split("-")[-1]
        ext = ext.split("-")[0]
        is_unsupported_format = self.is_unsupported_extension(ext)
        is_slow_format = self.is_slow_extension(ext)
        is_compressed = self.is_compressed_extension(download_ext)
        is_raster = self.is_raster_extension(ext)
        is_points = self.is_points_extension(ext)
        is_photo = (data_type == "photo")
        is_historic_ortho = (data_type.startswith("hc") or data_type.startswith("hi"))
        is_sheet = self.download_type == "dt_sheet"
        data_name = self.FME_NAMES_DICT.get(data_type, data_type)
        download_epsg = FME_DOWNLOAD_EPSG
        extra_params = []
        if is_photo:
            # If is photo download, change default out filename and add extra params to download
            _photo_id, flight_year, flight_code, filename, name, gsd, download_epsg = self.get_selected_photo_info()
            extra_params = [flight_year, flight_code, filename, name + ext]
            filename = os.path.splitext(filename)[0]
        elif is_historic_ortho:
            # If is historic ortho download, add extra param in_filename to download
            rgb_not_irc = data_type.startswith("hc")
            ortho_code = get_historic_ortho_code(rgb_not_irc, gsd, time_code)
            extra_params = [ortho_code]
            filename = "%s_%s" % (os.path.splitext(filename)[0], time_code)
        elif is_sheet:
            # If download a sheet, gets sheet name from reference layer if exists
            ref_layer = self.load_last_ref_layer()
            if ref_layer:
                area = geo.buffered(1)
                field_list = ["IDABS", "ID1K"]
                for field_name in field_list:
                    sheet_name_list = self.layers.get_attribute_by_area(ref_layer, field_name, area)
                    if sheet_name_list and sheet_name_list[0]:
                        filename += "-" + sheet_name_list[0]

        # Get download geometry
        if self.download_type not in ["dt_cat", "dt_all"]:
            geo = self.download_get_geometry(geo, download_epsg, min_side, max_download_area, min_px_side, max_px_area, gsd, limits)
            if not geo:
                return
        is_polygon = (type(geo) == QgsGeometry)
        is_area = (type(geo) == QgsRectangle and not geo.isEmpty())
        title = self.tr("Download map area") if is_area or is_polygon else self.tr("Download point")

        # Validate download path
        download_folder = self.get_download_folder()
        if not download_folder:
            return

        # Show information about download
        type_info = (self.tr("raster") if is_raster else self.tr("vector"))
        if self.download_type in ["dt_area", "dt_coord"]:
            confirmation_text = self.tr("Data type:\n   %s (%s)\nRectangle:\n   %.2f, %.2f %.2f, %.2f (EPSG:%s)\nArea:\n   %d m%s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_name, type_info, geo.xMinimum(), geo.yMinimum(), geo.xMaximum(), geo.yMaximum(), download_epsg, geo.area(), self.SQUARE_CHAR, download_folder, download_ext[1:])
        elif self.download_type in ["dt_layer_polygon", "dt_layer_polygon_bb"]:
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPolygon area:\n   %d m%s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_name, type_info, geo.area(), self.SQUARE_CHAR, download_folder, download_ext[1:])
        elif self.download_type in ["dt_municipalities", "dt_counties", "dt_sheet"]:
            # Find point on GeoFinder
            center = geo.center()
            found_dict_list = self.find_point_secure(center.x(), center.y(), download_epsg)
            # Set download information
            if self.download_type in ["dt_municipalities", "dt_sheet"]:
                municipality = found_dict_list[0]['nomMunicipi'] if found_dict_list else ""
                confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f (EPSG:%s)\nMunicipality:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_name, type_info, geo.center().x(), geo.center().y(), download_epsg, municipality, download_folder, download_ext[1:])
            elif self.download_type == "dt_counties":
                county = found_dict_list[0]['nomComarca'] if found_dict_list else ""
                confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f (EPSG:%s)\nCounty:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_name, type_info, geo.center().x(), geo.center().y(), download_epsg, county, download_folder, download_ext[1:])
        else:
            zone = self.tr("Catalonia") if self.download_type == "dt_cat" \
                else (self.tr("Full photogram") + " " * 50) if is_photo \
                else self.tr("Available data")
            confirmation_text = self.tr("Data type:\n   %s (%s)\nZone:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_name, type_info, zone, download_folder, download_ext[1:])
        # User confirmation
        filename, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), title,
            set_html_font_size(confirmation_text), QLineEdit.Normal, filename)
        if not ok_pressed or not local_filename:
            self.log.debug("User filename input cancelled")
            return
        local_filename = "%s_%s%s" % (filename, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), download_ext)
        self.log.debug("Download filename: %s", local_filename)

        # Get URL with FME action
        west, south, east, north = (geo.xMinimum(), geo.yMinimum(), geo.xMaximum(), geo.yMaximum()) if geo and not is_polygon else (None, None, None, None)
        points_list = [(vertex.x(), vertex.y()) for vertex in geo.vertices()] if is_polygon else []
        url = get_clip_data_url(data_type, download_operation_code, west, south, east, north, points_list, extra_params, referrer=self.request_referrer)
        if not url:
            self.log.error("Error, can't find product %s as available to download", data_type)
            return
        self.log.debug("Download URL: %s", url)

        # Request user confirmation to load slow formats
        if is_slow_format:
            if is_points and not self.can_show_point_cloud_files:
                if QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("File type %s is not supported by the current version of QGIS.\nIt will be downloaded but not displayed") % ext,
                    QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok) != QMessageBox.Ok:
                    return
            else:
                if QMessageBox.question(self.iface.mainWindow(), title,
                    self.tr("File type %s can take quite a while to open in QGIS\nDo you want to open it after downloading?") % ext,
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
                    is_slow_format = False

        # Load layer
        current_layer = self.layers.get_current_layer()
        download_layer = None
        geometry_ok = True
        data_filter = self.fme_data_filters_dict.get(data_type, None)
        try:
            if is_compressed:
                if is_unsupported_format:
                    # Download and uncopmress file
                    uncompressed_folder = self.layers.download_remote_file(url, local_filename, download_folder, unzip=True, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
                    # If compressed file contains unsupported format, search first file
                    local_filename_list = [os.path.join(uncompressed_folder, f) for f in \
                        os.listdir(uncompressed_folder) \
                        if os.path.splitext(f)[1] == ext]
                    local_filename = local_filename_list[0] if local_filename_list else None
                else:
                    # We suppose that compressed file contains a QLR file, this process uncompress downloaded file
                    download_layer = self.layers.add_remote_layer_definition_file(url, local_filename, group_name=self.download_group_name, group_pos=0, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
                    if not download_layer:
                        # If can't load QLR, we suppose that compressed file contains Shapefiles
                        download_layer = self.layers.add_vector_files([os.path.join(download_folder, local_filename)], group_name=self.download_group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.fme_regex_styles_list)
            elif is_unsupported_format or is_slow_format:
                # With an unsupported format we only download file
                local_filename = self.layers.download_remote_file(url, local_filename, download_folder=None, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
            elif is_raster:
                # With full photograms need download additional georeference file
                if is_photo and download_operation_code == "tot":
                    world_ext = ext[0:2] + ext[3] + "w"
                    image_filename = extra_params[2]
                    world_filename = os.path.splitext(image_filename)[0] + world_ext
                    world_file_url = url.replace(image_filename, world_filename)
                    world_pathname = os.path.splitext(local_filename)[0] + world_ext
                    geometry_ok = self.layers.download_remote_file(world_file_url, world_pathname, download_folder, unzip=True, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s")) is not None
                # Force EPSG:25831 or photo EPSG by problems with QGIS 3.10 version in auto detection EPSG
                if geometry_ok:
                    download_layer = self.layers.add_remote_raster_file(url, local_filename, group_name=self.download_group_name, group_pos=0, epsg=download_epsg, only_one_visible_map_on_group=False, color_default_expansion=data_type.lower().startswith("met"), resampling_bilinear=True, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
            elif is_points:
                download_layer = self.layers.add_remote_point_cloud_file(url, local_filename, group_name=self.download_group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.fme_regex_styles_list, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
                # We cannot set a data filter until layer finish point indexing
                if download_layer and data_filter:
                    if self.can_filter_point_cloud: # Checks QGIS version
                        # Signal statisticsCalculationState has a bug and cannot be used! https://github.com/qgis/QGIS/issues/58312
                        # download_layer.statisticsCalculationStateChanged.connect(lambda state:self.layers.set_filter_by_id(download_layer.id(), data_filter))
                        # We make an active wait (supported on QGIS > 3.26)
                        if download_layer.statisticsCalculationState() != 2:
                            with WorkingDialog(os.path.basename(local_filename), self.tr("Indexing points and applying data filters ..."), self.tr("Cancel")) as progress:
                                while download_layer.statisticsCalculationState() != 2 and not progress.was_canceled():
                                    progress.step_it()
                # Force expanded group (group not responding??)
                self.legend.expand_group_by_name(self.download_group_name, False)
                self.legend.expand_group_by_name(self.download_group_name, True)
            else:
                download_layer = self.layers.add_remote_vector_file(url, local_filename, group_name=self.download_group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.fme_regex_styles_list, title=self.tr("Downloading ..."), cancel_button_text=self.tr("Cancel"), time_info=self.tr("Elapsed %s"))
        except Exception as e:
            error = str(e)
            # If server don't return error message (replied empty), we return a generic error
            if error.endswith("replied: "):
                error = self.tr("Error downloading file or selection is out of reference area")
            self.log.exception(error)
            QMessageBox.warning(self.iface.mainWindow(), title, error)
            return

        # Apply data filter if required
        if download_layer and data_filter and (not is_points or self.can_filter_point_cloud):
            status_ok = self.layers.set_filter(download_layer, data_filter)

        # Restore previous current layer
        if current_layer:
            self.layers.set_current_layer(current_layer)

        # Hide photo preview
        if is_photo and download_layer:
            self.layers.set_visible_by_id(self.photo_layer_id, False)

        # Disable all reference layers
        self.disable_ref_layers(hide_not_remove=True)

        # Disable tool
        action = self.tool_subscene.action()
        if action:
            action.setChecked(False)
        self.gui.enable_tool(None)

        # Checks download is ok
        if not local_filename:
            self.log.error("Error downloading file: %s", local_filename)
            QMessageBox.warning(self.iface.mainWindow(), title,
                self.tr("Error downloading file\n%s") % local_filename)
            return
        if not geometry_ok:
            self.log.error("Error downloading geometry file: %s", world_filename)
            QMessageBox.warning(self.iface.mainWindow(), title,
                self.tr("Error downloading geometry file\n%s") % world_file)
            return
        # With slow formats we show end download message
        if is_slow_format:
            QMessageBox.information(self.iface.mainWindow(), title,
                self.tr("File downloaded:\n%s") % local_filename)
        else:
            # With unsupported point cloud indexing status show message
            if not self.can_filter_point_cloud and is_points and download_layer and data_filter:
                QMessageBox.warning(None, title,
                    self.tr("The current version of QGIS does not allow filtering data from point cloud files, " \
                        "so data may be displayed incorrectly."))
        # With unsupported format we try open file with external app
        if is_unsupported_format:
            if QMessageBox.question(self.iface.mainWindow(), title,
                self.tr("File type %s is unsupported by QGIS\nDo you want try open downloaded file in a external viewer?") % ext,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
                self.log.debug("Open donwloaded file with external viewer cancelled")
                return
            try:
                self.layers.open_download_path(filename=local_filename)
                self.log.debug("Open donwloaded file with external viewer")
            except:
                self.log.exception("The downloaded file could not be opened with external viewer")
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("The download file could not be opened"))

    def download_get_geometry(self, geo, download_epsg, min_side, max_download_area, min_px_side, max_px_area, gsd, limits, default_point_buffer=50, max_aspect_ratio=FME_MAX_ASPECT_RATIO):
        """ Gets geometry to download """
        title = self.tr("Download tool")
        epsg = None

        if self.download_type == 'dt_coord':
            # Ask coordinates to user
            self.log.debug("Download tool coordinates (%s)", self.download_type)
            msg_text = self.tr('Enter west, north, east, south values in the project coordinates system or add the corresponding EPSG code in the following format:\n   "429393.19 4580194.65 429493.19 4580294.65" or\n   "429393.19 4580194.65 429493.19 4580294.65 EPSG:25831" or\n   "EPSG:25831 429393.19 4580194.65 429493.19 4580294.65"')
            coord_text, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), self.tr("Download tool"),
                set_html_font_size(msg_text), QLineEdit.Normal, "")
            if not ok_pressed:
                self.log.debug("User coordinates input cancelled")
                return None
            # Use GeoFinder static function to parse coordinate text
            west, north, east, south, epsg = GeoFinder.get_rectangle_coordinate(coord_text)
            if not west or not north:
                self.log.warning("Incorrect coordinates format")
                QMessageBox.warning(self.iface.mainWindow(), title, self.tr("Incorrect coordinates format"))
                return None
            epsg = int(epsg) if epsg else None
            geo = QgsRectangle(west, north, east, south)
            self.log.debug("User coordinates %s (EPSG %s)", geo, epsg)

        elif self.download_type in ['dt_layer_polygon', 'dt_layer_polygon_bb']:
            # Gets polygons from selected layer (vectorial)
            self.log.debug("Download tool polygon (%s)", self.download_type)
            multipolygon = None
            layer = self.iface.mapCanvas().currentLayer()
            if layer and type(layer) == QgsVectorLayer:
                # Prepare transformation polygon coordinates to project EPSG
                epsg = self.layers.get_epsg(layer)
                epsg = int(epsg) if epsg else None
                self.log.debug("Selected polygons layer %s (EPSG %s)", layer.name(), epsg)
                # Add only selected polygons
                polygons_list = []
                for feature in layer.selectedFeatures():
                    geom = feature.geometry()
                    if geom.wkbType() in [QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon]:
                        polygons_list.append(geom)
                if polygons_list:
                    multipolygon = QgsGeometry.collectGeometry(polygons_list)
            if not multipolygon:
                self.log.warning("Download type polygon without selected layer / polygon")
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("You must activate a vector layer with one or more selected polygons"))
                return None
            if self.download_type == 'dt_layer_polygon':
                # Check geometry max number of points
                polygons_points_count = sum(1 for _v in multipolygon.vertices())
                if polygons_points_count > FME_MAX_POLYGON_POINTS:
                    self.log.warning("Download type polygon with too many points %d / %d", polygons_points_count, FME_MAX_POLYGON_POINTS)
                    QMessageBox.warning(self.iface.mainWindow(), title,
                        self.tr("Your polygons have too many points: %d maximum %d" % (polygons_points_count, FME_MAX_POLYGON_POINTS)))
                    return None
                # Force download by polygon
                geo = multipolygon
            else: # if self.download_type == 'dt_layer_polygon_bb':
                geo = QgsGeometry.fromRect(multipolygon.boundingBox())

        else:
            self.log.debug("Download tool user selection (%s)", self.download_type)

        # Check selection type
        is_polygon = (type(geo) == QgsGeometry)
        is_point = (type(geo) == QgsRectangle and geo.isEmpty())
        is_area = (type(geo) == QgsRectangle and not geo.isEmpty())

        # If not EPSG then gets project epsg
        if not epsg:
            epsg = int(self.project.get_epsg())
            self.log.debug("Use project EPSG for geometry: %s", epsg)
        # Check CS and transform
        if geo:
            if epsg == download_epsg:
                self.log.debug("Download geometry %s (EPSG:%s)", geo.asWkt() if is_polygon else geo.asWktCoordinates(), download_epsg)
            else:
                self.log.debug("User geometry %s (EPSG:%s)", geo.asWkt() if is_polygon else geo.asWktCoordinates(), epsg)
                geo = self.crs.transform(geo, epsg, download_epsg)
                self.log.debug("Download (transformed) geometry %s (EPSG:%s)", geo.asWkt() if is_polygon else geo.asWktCoordinates(), download_epsg)

        title = self.tr("Download map area") if is_area or is_polygon else self.tr("Download point")

        # Check area limit
        if is_area or is_polygon:
            rect = geo.boundingBox() if is_polygon else geo
            if min_side and (rect.width() < min_side or rect.height() < min_side):
                self.log.warning("Minimum download rect side not reached (%d m)", min_side)
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Minimum download rect side not reached (%d m)") % (min_side))
                return None
            if max_download_area and (geo.area() > max_download_area):
                self.log.warning("Maximum download area exceeded (%s m2)", max_download_area)
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum download area exceeded (%s m%s)") % (self.format_scale(max_download_area), self.SQUARE_CHAR))
                return None
            if min_px_side and gsd and ((rect.width() / gsd) < min_px_side or (rect.height() / gsd) < min_px_side):
                self.log.warning("Minimum download rect side not reached (%d px)", min_px_side)
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Minimum download rect side not reached (%d px)") % (min_px_side))
                return None
            if max_px_area and gsd and ((geo.area() / gsd / gsd) > max_px_area):
                self.log.warning("Maximum download area exceeded (%s px2)", max_px_area)
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum download area exceeded (%s px%s)") % (self.format_scale(max_px_area), self.SQUARE_CHAR))
                return None
            # Check proportion between sides
            aspect_ratio = rect.width() / max(rect.height(), 1)
            if aspect_ratio < (1/max_aspect_ratio) or aspect_ratio > max_aspect_ratio:
                self.log.warning("Maximum aspect ratio exceeded (1:%d)", max_aspect_ratio)
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum aspect ration exceeded (1:%d)") % (max_aspect_ratio))
                return None

        # If area is point, maybe we need transform into a rectangle
        if is_point:
            if self.download_type in ["dt_area", "dt_coord", "dt_layer_polygon", "dt_layer_polygon_bb"]:
                # If download type is area ensure that selection is area
                geo = geo.buffered(min_side if min_side else default_point_buffer)
                self.log.debug("Geometry (point) buffered %s", min_side if min_side else default_point_buffer)
            elif self.download_type in ["dt_municipalities", "dt_counties", "dt_sheet"]:
                # If download type is point, make a rectangle to can intersect with Catalonia edge
                geo = geo.buffered(1)
                self.log.debug("Geometry (point) buffered %s", 1)

        # If coordinates are out of Catalonia, error
        geo_limits = None
        geo_limits_epsg = None
        if self.download_type in ["dt_area", "dt_coord", "dt_sheet"]:
            geo_limits, geo_limits_epsg = self.cat_limits_dict[limits]
        elif self.download_type == "dt_layer_polygon":
            geo_limits, geo_limits_epsg = self.cat_limits_dict[limits]
            # With selfintersection multipolygon intersects fails, we can fix it using boundingbox
            if not geo.isGeosValid():
                geo = geo.makeValid()
                if not geo.isGeosValid():
                    geo = geo.boundingBox()
        elif self.download_type in ["dt_municipalities", "dt_counties"]:
            limits = "cat_limits"
            geo_limits, geo_limits_epsg = self.cat_limits_dict[limits]
        if not geo_limits or geo_limits.isEmpty():
            self.log.warning("Catalonia limits %s are empty %s (EPSG: %s)", limits, geo_limits, geo_limits_epsg)
            out_of_cat = False
        else:
            self.log.debug("Check geometry limits %s" % limits)
            out_of_cat = not geo_limits.intersects(geo)
        if out_of_cat:
            self.log.warning("The selected area is outside Catalonia %s", limits)
            self.log.debug("Limits geometry: %s (EPSG: %s)", geo_limits, geo_limits_epsg)
            QMessageBox.warning(self.iface.mainWindow(), title, self.tr("The selected area is outside Catalonia"))
            return None

        return geo

    def get_selected_photo_info(self, show_errors=True):
        """ Return selected photo attributes: flight_year, flight_code, filename, name, gsd, epsg """
        photo_layer = self.layers.get_by_id(self.photo_search_layer_id)
        selected_photos_list = list(photo_layer.getSelectedFeatures()) if photo_layer else None
        photo_id = selected_photos_list[0].id() if selected_photos_list else None
        if show_errors:
            photo_info_list = self.layers.get_attributes_selection_by_id(self.photo_search_layer_id, ['flight_year', 'flight_code', 'image_filename', 'name', 'gsd', 'epsg'], lambda p: len(p) != 1, self.tr("You must select one photogram"))
        else:
            photo_info_list = self.layers.get_attributes_selection_by_id(self.photo_search_layer_id, ['flight_year', 'flight_code', 'image_filename', 'name', 'gsd', 'epsg'], lambda p: len(p) != 1)
        photo_id, flight_year, flight_code, filename, name, gsd, epsg = (([photo_id] + list(photo_info_list[0])) if photo_info_list else (None, None, None, None, None, None, None))
        return photo_id, flight_year, flight_code, filename, name, gsd, epsg

    def disable_ref_layers(self, hide_not_remove=False):
        """ Disable all reference layers """
        group = self.legend.get_group_by_name(self.backgroup_map_group_name)
        if group:
            disable_layers_list = [layer_tree.layer() for layer_tree in group.children() if layer_tree.name().startswith(self.download_ref_pattern % "")]
            for layer in disable_layers_list:
                if hide_not_remove:
                    self.layers.set_visible(layer, False)
                else:
                    self.layers.remove_layer(layer)
        self.iface.mapCanvas().refresh()

    def load_ref_layer(self, url_ref_or_wfs_or_wms_tuple, name):
        """ Load a reference layer in WMS, WFS or HTTP file format """
        current_layer = self.layers.get_current_layer()
        current_layer_id = current_layer.id() if current_layer else None
        # Load reference layer
        layer_name = self.download_ref_pattern % name
        #layer = self.layers.get_by_id(layer_name.replace(" ", "_"))
        layer = self.layers.get_by_name(layer_name)
        if layer:
            # If exist reference layer, only set visible
            self.layers.set_visible(layer)
        else:
            with WaitCursor():
                # Disable all reference layers
                self.disable_ref_layers()

                # If don't exist reference layer in project, we load it
                if len(url_ref_or_wfs_or_wms_tuple) == 4: # Load WMS layer
                    wms_url, wms_layer, wms_style, wms_format = url_ref_or_wfs_or_wms_tuple
                    # Load WMS layer from URL
                    layer = self.layers.add_wms_layer(layer_name, wms_url, [wms_layer], [wms_style] if wms_style else None, wms_format,
                        None, self.request_referrer_param + "&bgcolor=0x000000", self.backgroup_map_group_name, 0, only_one_visible_map_on_group=False)
                elif len(url_ref_or_wfs_or_wms_tuple) == 3: # Load WFS
                    wfs_url, wfs_layer, style_file = url_ref_or_wfs_or_wms_tuple
                    # Load WFS layer from URL
                    layer = self.layers.add_wfs_layer(layer_name, wfs_url, [wfs_layer],
                        extra_tags=self.request_referrer_param, group_name=self.backgroup_map_group_name, group_pos=0, style_file=style_file, only_one_visible_map_on_group=False)
                elif len(url_ref_or_wfs_or_wms_tuple) == 2: # Load HTTP
                    url_ref, style_file = url_ref_or_wfs_or_wms_tuple
                    url_ref = "/vsicurl/" + url_ref
                    is_raster = self.is_raster_file(url_ref) or url_ref.lower().find("orto") >= 0
                    if is_raster:
                        # Load raster layer from URL
                        layer = self.layers.add_raster_layer(layer_name, url_ref, self.backgroup_map_group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
                    else:
                        # Load vector layer from URL
                        layer = self.layers.add_vector_layer(layer_name, url_ref, self.backgroup_map_group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
                # Zoom to reference layer content if not visible
                visible_ref_layer_element_count = len(list(self.layers.get_features_by_area( \
                    layer, self.iface.mapCanvas().extent(), self.project.get_epsg())))
                if not visible_ref_layer_element_count:
                    self.layers.zoom_to_full_extent(layer)
        # Restore current layer
        if current_layer_id:
            self.layers.set_current_layer_by_id(current_layer_id)
        return layer

    def get_download_folder(self):
        """ Get download folder and asks for it if not exists """
        return self.layers.get_download_path(self.tr("Select download folder"))

    def set_download_folder(self):
        """ Set download folder """
        return self.layers.set_download_path(self.tr("Select download folder"))

    def open_download_folder(self):
        """ Open download folder and asks for it if not exists """
        self.layers.open_download_path(self.tr("Select download folder"))

    def find_point_secure(self, x, y, epsg, timeout=5):
        """ Protected find_point function """
        try:
            self.geofinder.get_icgc_geoencoder_client().set_options(timeout=timeout)
            found_dict_list = self.geofinder.find_point_coordinate(x, y, epsg)
            self.geofinder.get_icgc_geoencoder_client().set_options(timeout=None)
        except:
            error = self.tr("Unknow, service unavailable")
            found_dict_list = [{'nomMunicipi': error, 'nomComarca': error}]
        return found_dict_list

    def add_height_highlighting_layer(self, layer_name, dtm_url, style_file, group_name):
        """ Load shadow DTM layer to overlap to current background map in the first position of background map group"""
        # Selects first group layer if group exists
        group = self.legend.get_group_by_name(group_name)
        if group:
            legend_layers_list = group.findLayers()
            if legend_layers_list:
                self.layers.set_current_layer(legend_layers_list[0].layer())
        # Load DTM layer with shadow style
        layer = self.layers.add_raster_layer(layer_name, dtm_url, style_file=style_file, group_name=group_name, only_one_visible_map_on_group=False),
        # Show colors warning
        QMessageBox.information(self.iface.mainWindow(), self.tr("Height highlighting"),
            self.tr('You can modify the brightness of the "Height hightlghting" layer to adjust the display to your background layer'))
        return layer

    def show_available_products(self):
        """ Show a dialog with a list of all donwloads and linkable products """
        # Read download menu an delete prefix
        download_list = self.get_menu_names("download", ["open_download_folder", "select_download_folder", "save_pdf", "save_location_pdf"])
        # Read background maps menu
        link_list = self.get_menu_names("background_maps", ["delete_background"])
        # Generates a product info text
        available_products_text = self.tr("Linkable products:\n- %s\n\nDownloadable products:\n- %s") % ("\n- ".join(link_list), "\n- ".join(download_list))
        LogInfoDialog(available_products_text, self.tr("Available products list"), LogInfoDialog.mode_info, width=600)

    def get_menu_names(self, action_name, exclude_list):
        """ Recover name of submenus options from a menu """
        names_list = []
        actions_list = self.gui.find_action(action_name).defaultWidget().menu().actions() if self.gui.find_action(action_name) else []
        for action in actions_list:
            subactions_list = action.menu().actions() if action.menu() else [action]
            for subaction in subactions_list:
                text = subaction.defaultWidget().text() if type(subaction) is QWidgetAction else subaction.text()
                object_name = subaction.defaultWidget().objectName() if type(subaction) is QWidgetAction else subaction.objectName()
                if text and object_name not in exclude_list:
                    names_list.append(text)
        return names_list

    def show_qgis_version_warnings(self):
        """ Show QGIS old versions warnigs """
        LogInfoDialog(
            self.tr("""Your QGIS version is %s.

In versions of QGIS lower than 3.10.4 http files may not load correctly. Affected products will be disabled.
In versions of QGIS lower than 3.4.0 geopackage files may not load correctly.

Update your version of qgis if possible.""") % Qgis.QGIS_VERSION,
            self.tr("QGIS version warnings"), LogInfoDialog.mode_warning, width=800, height=250)

    def show_help_file(self, basename):
        """ Show local HTML help file """
        super().show_help(path="docs", basename=basename)

    def show_help(self, checked=None, help_type=HelpType.online): # I add checked param, because the mapping of the signal triggered passes a parameter)
        """ Show HTML help local or remote """
        if help_type == HelpType.local:
            self.show_help_file("index")
        elif help_type == HelpType.online:
            self.show_help_file("online")
        elif help_type == HelpType.online_cached:
            self.sync_help("docs", "online", "index")
            self.show_help_file("index")


    ###########################################################################
    # Update help & plugin

    def sync_help(self, path, online_basename, local_basename, timeout=0.5, filename_patterns_list=["%s.html", "%s-ca.html", "%s-es.html"]):
        """ Update local help files from online (GitHub) help files """
        if not os.path.isabs(path):
            path = os.path.join(self.plugin_path, path)

        # Read remote help files date
        sync_images_dict = {}
        for filename_pattern in filename_patterns_list:
            # Read local help file metadata tag "last-modified"
            local_pathname = os.path.join(path, filename_pattern % local_basename)
            with open(local_pathname) as fin:
                local_data = fin.read()
            found = re.search(r'http-equiv="last-modified"\s+content="([\d-]+)"', local_data)
            local_date = datetime.datetime.strptime(found.group(1), '%Y-%m-%d') if found else None

            # Read local redirect online help files to gets real online help files
            local_online_pathname = os.path.join(path, filename_pattern % online_basename)
            with open(local_online_pathname) as fin:
                local_online_data = fin.read()
            found = re.search('URL=(.+)"', local_online_data)
            if not found:
                continue
            remote_url = found.group(1)
            # Read remote help file metadata tag "last-modified"
            try:
                fin = urlopen(remote_url, timeout=timeout)
                remote_data = fin.read().decode()
            except:
                fin = None
            if not fin:
                continue
            self.log.debug("Help checked", remote_url)
            found = re.search(r'http-equiv="last-modified"\s+content="([\d-]+)"', remote_data)
            if not found:
                continue
            remote_date = datetime.datetime.strptime(found.group(1), '%Y-%m-%d')

            # If remote file the newest the copy to local
            if not local_date or remote_date > local_date:
                # Search remote images on help files
                images_list = re.findall('src="([^"]+)"', remote_data)
                for image in images_list:
                    local_image_pathname = os.path.join(os.path.dirname(local_pathname), image)
                    remote_image_url = urljoin(remote_url, image) # Remove last level and cocat with /
                    sync_images_dict[local_image_pathname] = remote_image_url # Dict remove repetitions
                # Copy help file
                with open(local_pathname, "w", encoding="utf-8") as fout:
                    fout.write(remote_data)
                self.log.debug("Help updated:", remote_url)

        # Copy image files of all help files (witout repetitions)
        for local_image_pathname, remote_image_url in sync_images_dict.items():
            try:
                fin = urlopen(remote_image_url, timeout=timeout)
                remote_image_data = fin.read()
            except:
                fin = None
            if not fin:
                continue
            with open(local_image_pathname, "wb") as fout:
                fout.write(remote_image_data)
            self.log.debug("Help updated:", remote_image_url)

    def check_plugin_update(self, timeout=5):
        """ Check plugin new version
            Dont' work on SharePoint links
            To do, try: https://pypi.org/project/Office365-REST-Python-Client/
                 https://stackoverflow.com/questions/53671547/python-download-files-from-sharepoint-site
            """
        # Gets download plugin URL
        local_download_plugin_path = os.path.join(self.plugin_path, "docs", "plugin_icgc.html")
        with open(local_download_plugin_path) as fin:
            local_online_data = fin.read()
        found = re.search('URL=(.+)"', local_online_data)
        if not found:
            return None
        remote_url = found.group(1)

        # Check sharepoint download
        if remote_url.lower().find("sharepoint.com") >= 0:
            # Unsupported
            remote_data = None
        else:
            # Download plugin to gets version
            try:
                hdr = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)' }
                req = Request(remote_url, headers=hdr)
                response = urlopen(req, timeout=timeout)
                remote_data = response.read().decode()
            except Exception as e:
                remote_data = None
        if not remote_data:
            return None

        # Reads metadata file in zip to check version
        try:
            zip = zipfile.ZipFile(io.BytesIO(remote_data))
            metadata_data = zip.read('metadata.txt')
        except Exception as e:
            metadata_data = None
        if not metadata_data:
            return None

        # Get plugin version
        found = re.search(r'version=(.+)\s', local_online_data)
        if not found:
            return None
        remote_plugin_version = found.group(1)
        return remote_plugin_version

    def download_plugin_update(self, new_version, update_type):
        """ Download last plugin version """
        if update_type == UpdateType.icgc_web:
            self.show_help_file("plugin_icgc") # from ICGC
        elif update_type == UpdateType.qgis_web:
            self.show_help_file("plugin_qgis") # from QGIS plugins repository
        else:
            self.iface.actionManagePlugins().trigger()


    ###########################################################################
    # Shading DTM


    ###########################################################################
    # Shading DTM

    def shading_dtm(self, checked=False):
        """ Change current layer style """
        title=self.tr("Shading DTM layer")
        # Load style file in current layer
        layer = self.iface.mapCanvas().currentLayer()
        if type(layer) != QgsRasterLayer or layer.bandCount() > 1:
            QMessageBox.information(self.iface.mainWindow(), title,
                self.tr('You must select a DTM layer'))
            return
        self.layers.load_style(layer, "ombrejat")
        # Show shading info
        QMessageBox.information(self.iface.mainWindow(), title,
            self.tr('You can modify the angle of the sun in the layer simbology'))
        return layer


    ###########################################################################
    # Photo library search

    def enable_search_photos(self, checked=False):
        """ Enables search photos interactive tool """
        self.gui.enable_tool(self.tool_photo_search)
        self.iface.messageBar().pushMessage(self.tr("Photograms search tool"), self.tr("Select a point"), level=Qgis.Info, duration=5)

    def search_photos_by_point(self):
        """ Search photos in photo library by text point coordinates """
        # Ask coordinates
        title = self.tr("Search photograms")
        msg_text = self.tr('Enter an x y value in the project coordinate system or add the corresponding EPSG code in the following format:\n   "429393.19 4580194.65" or "429393.19 4580194.65 EPSG:25831" or "EPSG:25831 429393.19 4580194.65"')
        coord_text, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), title,
            set_html_font_size(msg_text), QLineEdit.Normal, "")
        if not ok_pressed:
            return
        # Use GeoFinder static function to parse coordinate text
        x, y, epsg = GeoFinder.get_point_coordinate(coord_text)
        if not x or not y:
            QMessageBox.warning(self.iface.mainWindow(), title, "Incorrect coordinate format")
            return
        # Search photo coordinates
        self.search_photos(x, y)

    def search_photos_by_name(self):
        """ Search photos in photo library by photo name """
        # Ask photo name
        title = self.tr("Search photograms")
        msg_text = self.tr('Photogram name:') + " " * 50
        photo_name, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), title,
            set_html_font_size(msg_text), QLineEdit.Normal, "")
        if not ok_pressed or not photo_name:
            return
        # Search photo name
        self.search_photos(name=photo_name.strip())

    def search_photos(self, x=None, y=None, name=None, photolib_wfs=PHOTOLIB_WFS, date_field="flight_date"):
        """ Search photos in photo library by selected point or photo name """
        title = self.photo_search_label.replace(": %s", "")
        epsg = None

        # Check existence of old photo search
        group_pos = 0
        group = self.legend.get_group_by_name(self.photos_group_name)
        if group and len(self.layers.get_group_layers(group)) > 0:
            if QMessageBox.question(self.iface.mainWindow(), title,
                self.tr('It exists a previous photo search. Do you want close it?'), QMessageBox.Yes, QMessageBox.No) == QMessageBox.No:
                # Walkthrough to show photo search dialog with current search
                if self.photo_search_dialog:
                    self.photo_search_dialog.show()
                return False
            # Remove previous photo search, before disables reset dialog when delete layer event
            photo_search_layer = self.layers.get_by_id(self.photo_search_layer_id)
            if photo_search_layer:
                photo_search_layer.selectionChanged.disconnect(self.on_change_photo_selection)
                if self.photo_search_dialog:
                    photo_search_layer.willBeDeleted.disconnect(self.photo_search_dialog.reset)
            self.legend.empty_group(group)
        # If photo search group not exist, we ensure that it is created before download group
        if not group:
            # If not exists download group return -1
            group_pos = self.legend.get_group_position_by_name(self.download_group_name) + 1

        # Fix event problems betwen photo layer and photo dialog for QGIS versions < 3.10
        # Needs create photo dialog previous to photo layer...
        if not self.photo_search_dialog and not self.check_qgis_version(310000):
            self.show_photo_search_dialog(None, [])
            self.photo_search_dialog.hide()
        self.log.debug("Search photo: %s" % photolib_wfs)

        photo_search_layer = None
        layer_name = None
        layer_filter = None
        with WaitCursor():
            # Search by coordinates
            if x and y:
                # Get municipality information of coordinate
                if not epsg:
                    epsg = int(self.project.get_epsg())
                found_dict_list = self.find_point_secure(x, y, epsg)
                municipality = found_dict_list[0]['nomMunicipi'] if found_dict_list else ""
                if municipality:
                    layer_name = self.photo_search_label % municipality
                else:
                    if x >= 100 and y >= 100:
                        layer_name = self.photo_search_label % self.tr("Coord %s %s") % ("%.2f" % x,"%.2f" % y)
                    else:
                        layer_name = self.photo_search_label % self.tr("Coord %s %s") % (x, y)
                # Search point in photo library (EPSG 4326)
                x, y = self.crs.transform_point(x, y, epsg, 4326)
                #layer_filter = "SELECT * FROM fotogrames WHERE ST_Intersects(msGeometry, ST_GeometryFromText('POINT(%f %f)'))" % (x, y)
                layer_filter ='<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:gml="http://www.opengis.net/gml/3.2">' \
                    '<fes:Intersects>' \
                        '<fes:ValueReference>msGeometry</fes:ValueReference>' \
                        '<gml:Point srsName="urn:ogc:def:crs:EPSG::4326" gml:id="qgis_id_geom_1">' \
                        '<gml:pos srsDimension="2">%f %f</gml:pos>' \
                        '</gml:Point>' \
                     '</fes:Intersects>' \
                    '</fes:Filter>' % (y, x)

            # Search by name
            if name and len(name) > 7: # at least flight code and wildcard ...
                layer_name = self.photo_search_label % name
                #layer_filter = "SELECT * FROM fotogrames WHERE name LIKE '%s'" % (name)
                layer_filter = '<Filter><Or>' \
                    '<PropertyIsEqualTo matchCase=false>' \
                        '<ValueReference>name</ValueReference>' \
                        '<Literal>%s</Literal>' \
                    '</PropertyIsEqualTo>' \
                    '<PropertyIsLike wildCard="*" singleChar="." escapeChar="\\">' \
                        '<ValueReference>name</ValueReference>' \
                        '<Literal>%s</Literal>' \
                    '</PropertyIsLike>' \
                    '</Or></Filter>' % (name, name)

            # Load photo layer
            if layer_name and layer_filter:
                #photo_search_layer = self.layers.add_wfs_layer(layer_name, photolib_wfs,
                #    ["icgc:fotogrames"], 4326, filter=layer_filter, extra_tags=self.request_referrer_param + "&outputformat=geojson",
                #    group_name=self.photos_group_name, group_pos=group_pos, only_one_map_on_group=False, only_one_visible_map_on_group=True,
                #    collapsed=False, visible=True, transparency=None, set_current=True)
                fake_file = '%s/?SERVICE=WFS&VERSION=%s&REQUEST=GetFeature&TYPENAMES=%s&FILTER=%s&outputformat=geojson&%s&SORTBY=flight_date,flight_code,name' % (
                    photolib_wfs, "2.0.0", "icgc:fotogrames", quote(layer_filter), self.request_referrer_param)
                begin_time = datetime.datetime.now()
                photo_search_layer = self.layers.add_vector_layer(layer_name, fake_file,
                    group_name=self.photos_group_name, group_pos=group_pos, only_one_map_on_group=False, only_one_visible_map_on_group=True,
                    expanded=True, visible=True, transparency=None, set_current=True)
                end_time = datetime.datetime.now()
                self.log.debug("Photo search time: %s" % (end_time - begin_time))

            if not photo_search_layer or type(photo_search_layer) is not QgsVectorLayer:
                return

            self.photo_search_layer_id = photo_search_layer.id() if photo_search_layer else ""

            # Translate field names
            self.layers.set_fields_alias(photo_search_layer, {
               "name": self.tr("Name"),
               "flight_code": self.tr("Flight code"),
               "flight_date": self.tr("Flight date"),
               "flight_year": self.tr("Flight year"),
               "image_filename": self.tr("Image filename"),
               "image_width": self.tr("Image width"),
               "image_height": self.tr("Image height"),
               "image_channels": self.tr("Image channels"),
               "image_bits_ppc": self.tr("Image bits PPC"),
               "color_type": self.tr("Color type"),
               "strip": self.tr("Strip"),
               "strip_photo": self.tr("Photo in strip"),
               "camera": self.tr("Camera"),
               "focal_length": self.tr("Focal Length"),
               "gsd": self.tr("Ground sampling distance"),
               "scale": self.tr("Scale"),
               "flying_height": self.tr("Flying height"),
               "mean_ground_height": self.tr("Mean ground height"),
               "view_type": self.tr("View type"),
               "northing": self.tr("Northing"),
               "easting": self.tr("Easting"),
               "epsg": self.tr("EPSG code"),
               "omega": self.tr("Omega"),
               "phi": self.tr("Phi"),
               "kappa": self.tr("Kappa"),
               "analog": self.tr("Analog"),
               })

            # Get years of found photograms
            search_photos_year_list = sorted(list(set([(f[date_field].date().year() if type(f[date_field]) == QDateTime \
                else int(f[date_field].split("-")[0])) for f in photo_search_layer.getFeatures()])), reverse=True)

            # Set layer colored by year style
            self.layers.classify(photo_search_layer, 'to_int(left("flight_date", 4))', values_list=search_photos_year_list,
                color_list=[QColor(0, 127, 255, 25), QColor(100, 100, 100, 25)], # Fill with transparence
                border_color_list=[QColor(0, 127, 255), QColor(100, 100, 100)],  # Border without transparence
                interpolate_colors=True)
            self.layers.set_categories_visible(photo_search_layer, search_photos_year_list[1:], False)
            self.layers.enable_feature_count(photo_search_layer)
            self.layers.zoom_to_full_extent(photo_search_layer)
            self.layers.set_visible(photo_search_layer, False)

            # Show photo search dialog
            search_photos_year_list.reverse()
            self.show_photo_search_dialog(photo_search_layer, search_photos_year_list)

            # Map change selection feature event
            photo_search_layer.selectionChanged.connect(self.on_change_photo_selection)
            # Map remove layer event to hide photo search dialog
            if self.photo_search_dialog:
                photo_search_layer.willBeDeleted.connect(self.photo_search_dialog.reset)

        # Disable search tool
        self.gui.enable_tool(None)

        ## Show warning if max results
        photo_count = photo_search_layer.featureCount() if photo_search_layer else 0
        if photo_count >= PHOTOLIB_WFS_MAX_FEATURES:
            QMessageBox.warning(self.iface.mainWindow(), title, self.tr( \
                "The maximum number of results (%d) has been reached.\n" \
                "The query may have more results than are displayed." \
                ) % PHOTOLIB_WFS_MAX_FEATURES)

    def photo_preview(self, photo_name, rectified=False, stereo=False, only_one=True, photolib_wms=PHOTOLIB_WMS):
        """ Load photogram raster layer """
        if only_one:
            # Get previous photo_layer to update or create it
            photo_layer = self.layers.get_by_id(self.photo_layer_id)
        else:
            photo_layer = None
            # Disable previous preview layers
            self.legend.set_group_items_visible_by_name(self.photos_group_name, False)
            self.layers.set_visible_by_id(self.photo_search_layer_id, True)

        # Determine WMS layer to load
        layer_name = "anaglif" if stereo else "ortoxpres" if rectified else "fotos"
        if stereo:
            photo_style = ",".join([photo_name, \
                str(self.photo_search_dialog.get_parallax()), \
                ("true" if self.photo_search_dialog.is_inverted_stereo() else "false") \
                ])
        else:
            photo_style = photo_name

        # We don't want change current selected layer
        current_layer = self.layers.get_current_layer()
        # Show debug info
        self.log.debug("Show photo: %s %s" % (photolib_wms, photo_style))
        photo_label = self.photo_label % photo_name
        if photo_layer:
            # Update current photo_layer
            begin_time = datetime.datetime.now()
            self.layers.update_wms_layer(photo_layer, wms_layer=layer_name, wms_style=photo_style)
            end_time = datetime.datetime.now()
            self.log.debug("Update photo raster time: %s" % (end_time - begin_time))
            photo_layer.setName(photo_label)
            self.layers.set_visible(photo_layer)
            self.legend.set_group_visible_by_name(self.photos_group_name)
        else:
            # Load new preview layer at top (using WMS or UNC path to file)
            begin_time = datetime.datetime.now()
            photo_layer = self.layers.add_wms_layer(photo_label, photolib_wms,
                [layer_name], [photo_style], "image/png", self.project.get_epsg(), extra_tags=self.request_referrer_param + "&bgcolor=0x000000",
                group_name=self.photos_group_name, group_pos=0, only_one_map_on_group=False, only_one_visible_map_on_group=False,
                collapsed=False, visible=True, transparency=None, set_current=False)
            end_time = datetime.datetime.now()
            self.log.debug("Load photo raster time: %s" % (end_time - begin_time))
            self.photo_layer_id = photo_layer.id() if photo_layer else ""
        # Restore previous selected layer
        if current_layer:
            self.layers.set_current_layer(current_layer)

        return photo_layer

    def show_photo_search_dialog(self, layer, years_list, current_year=None, title=None, current_prefix="", show=True):
        """ Show photo search dialog to filter photo results """
        # Show or hide dialog
        if show:
            if not current_year and years_list:
                current_year = years_list[-1]

            # If not exist dialog we create it else we configure and show it
            update_photo_time_callback = lambda current_year, range_year, layer=layer: self.update_photo_search_layer_year(layer, current_year, range_year)
            update_photo_selection_callback = lambda photo_id, layer=layer: self.layers.set_selection(layer, [photo_id] if photo_id is not None else [])
            show_info_callback = lambda photo_id, layer=layer: self.iface.openFeatureForm(layer, layer.getFeature(photo_id))
            preview_callback = lambda photo_id, layer=layer: self.photo_preview(layer.getFeature(photo_id)['name'])
            rectified_preview_callback = lambda photo_id, layer=layer: self.photo_preview(layer.getFeature(photo_id)['name'], rectified=True)
            stereo_preview_callback = lambda photo_id, layer=layer: self.photo_preview(layer.getFeature(photo_id)['name'], stereo=True)
            download_callback = lambda photo_id, layer=layer: self.photo_download_action.trigger()
            request_certificate_callback = None #lambda photo_id, layer=layer: self.send_email(
                #"OpenICGC QGIS plugin. certificate %s" % layer.getFeature(photo_id)['name'],
                #self.tr("Certificate request for photogram: %s") % layer.getFeature(photo_id)['name'])
            request_scan_callback = None #lambda photo_id, layer=layer: self.send_email(
                #"OpenICGC QGIS plugin. scan %s" % layer.getFeature(photo_id)['name'],
                #self.tr("Scan request for photogram: %s") % layer.getFeature(photo_id)['name'])
            report_photo_bug_callback = lambda photo_id, layer=layer: self.report_photo_bug(layer.getFeature(photo_id)['name'], \
                layer.getFeature(photo_id)['flight_code'], \
                layer.getFeature(photo_id)['flight_date'], \
                layer.getFeature(photo_id)['gsd'])
            if not self.photo_search_dialog:
                self.photo_search_dialog = PhotoSearchSelectionDialog(layer,
                    years_list, current_year,
                    update_photo_time_callback, update_photo_selection_callback, show_info_callback,
                    preview_callback, rectified_preview_callback, stereo_preview_callback,
                    None, download_callback, request_certificate_callback, request_scan_callback, report_photo_bug_callback,
                    autoshow=True, parent=self.iface.mainWindow())
                # Align dialog to right
                self.photo_search_dialog.hide()
                self.iface.addDockWidget(Qt.RightDockWidgetArea, self.photo_search_dialog)
                # Map visibility event to refresh any control if necessary. This is implemented in
                # change layer event that's why i send a change layer signal
                self.photo_search_dialog.visibilityChanged.connect(lambda dummy:self.iface.layerTreeView().currentLayerChanged.emit(self.iface.mapCanvas().currentLayer()))
            else:
                # Configure search result information
                self.photo_search_dialog.set_info(layer,
                    years_list, current_year,
                    update_photo_time_callback, update_photo_selection_callback, show_info_callback,
                    preview_callback, rectified_preview_callback, stereo_preview_callback, None,
                    download_callback, request_certificate_callback, request_scan_callback, report_photo_bug_callback)
                # Mostrem el diàleg
                self.photo_search_dialog.show()
        else:
            # Reset data and hide dialog
            if self.photo_search_dialog:
                self.photo_search_dialog.reset()

    def update_photo_search_layer_year(self, photo_layer, current_year, range_year):
        """ Update visibility of  photo categories from years range """
        year_range = range(current_year, range_year + 1) if range_year else [current_year]
        if photo_layer:
            categories_list = self.layers.get_categories(photo_layer)
            self.layers.set_categories_visible(photo_layer, set(categories_list) - set(year_range), False)
            self.layers.set_categories_visible(photo_layer, year_range, True)
            #self.layers.set_current_layer(photo_layer) # click in categories of layer can unselect layer... we fix it
            self.layers.set_visible(photo_layer) # force visibility of photo layer
            self.legend.set_group_visible_by_name(self.photos_group_name) # force visibility of photo group

    def report_photo_bug(self, photo_name, flight_code="", photo_date="", photo_resolution=0):
        """ Report a photo bug """
        title=self.tr("Report photo bug")
        photo_date_text = photo_date.toString(self.tr("yyyy/MM/dd HH:mm:ss")) if type(photo_date) is QDateTime else str(photo_date)
        if QMessageBox.question(self.iface.mainWindow(), title,
            self.tr("Before reporting an error, bear in mind that the position of photograms is an approximation i will never completely fit the underlying cartography, since no terrain model has been used to project the imatge against. Furthermore, changes in instrumenation over time (wheter GPS is used or not, scanning and photogrammetric workflow) account for a very limited precision in positioning.\n\nOnly large displacements in position (for example, an element that should appear near the center does not appear) or if there is an error in rotation (eg. the sea appears in the northern part of a photo).\n\nDo you want continue?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
            return
        self.send_email(self.tr("Photo: %s\nFlight code: %s\nDate: %s\nResolution: %.2fm\n\n" \
            "Problem description: ") % (photo_name, flight_code, photo_date_text, photo_resolution or 0), \
            title = "Error en el fotograma %s" % photo_name) # Static text no translated

        QMessageBox.information(self.iface.mainWindow(), title,
            self.tr("Thanks for reporting an error in photogram:\n%s\n\nWe try to fix it as soon as possible") % photo_name)

    def save_map(self, report_template, file_suffix="", title="Save map as PDF"):
        """ Save current map as PDF applying a template <report_template> """
        # Prepare a default filename
        download_path = self.get_download_folder()
        if not download_path:
            return False
        municipality = self.get_current_municipality()
        default_filename = ("%s%s.pdf" % (municipality, file_suffix)) if municipality else ""
        default_pathname = os.path.join(download_path, default_filename)
        # Ask pdf filename
        pathname, _filter = QFileDialog.getSaveFileName(
            self.iface.mainWindow(), title, default_pathname, self.tr("PDF file (*.pdf)"))
        if not pathname:
            return False

        with WaitCursor():
            # Load report template
            composition = self.composer.get_composition(report_template, zoom_to_view=True, zoom_to_view_map_id_list=["map"], open_composer=False)

            # Any report requires a loaded topographic layer
            location_map_item = self.composer.get_composer_item_by_id(composition, "location_map")
            topo_map_item = self.composer.get_composer_item_by_id(composition, "topo_map")
            if location_map_item or topo_map_item:
                topo_uri = self.layers.generate_wms_layer_uri(
                    "https://geoserveis.icgc.cat/servei/catalunya/mapa-base/wms",
                    ["topografic"], None, "image/png", 25831, self.request_referrer_param)
                topo_layer = QgsRasterLayer(topo_uri, "topo_temp", "wms")
                if location_map_item:
                    location_map_item.setLayers([topo_layer])
                if topo_map_item:
                    topo_map_item.setLayers([topo_layer])

            # Set report title as filename
            report_title_item = self.composer.get_composer_item_by_id(composition, "title")
            if report_title_item:
                report_title = os.path.splitext(os.path.basename(pathname))[0]
                report_title_item.setText(report_title)
            # Translate report item
            info_item = self.composer.get_composer_item_by_id(composition, "info")
            if info_item:
                date_format = "%d/%m/%Y" if self.translation.get_qgis_language() in ["ca", "es"] else "%Y/%m/%d"
                info_item.setText(self.tr("Coord. Sys.: %s\nGeneration date: %s") % ("[% @project_crs %]", datetime.date.today().strftime(date_format)))
            note_item = self.composer.get_composer_item_by_id(composition, "note")
            if note_item:
                note_item.setText(self.tr("This PDF shows all the data visible in the QGIS project at the time of its generation"))
            location_label_item = self.composer.get_composer_item_by_id(composition, "location_label")
            if location_label_item:
                location_label_item.setText(self.tr("Location map:"))
            topographic_label_item = self.composer.get_composer_item_by_id(composition, "topographic_label")
            if topographic_label_item:
                topographic_label_item.setText(self.tr("Topographic map:"))
            map_label_item = self.composer.get_composer_item_by_id(composition, "map_label")
            if map_label_item:
                map_label_item.setText(self.tr("Map:"))
            # Save PDF
            status_ok = self.composer.export_composition(composition, pathname)

        # Open PDF if Ok
        if status_ok and os.path.exists(pathname):
            self.gui.open_file_folder(pathname)
        else:
            QMessageBox.warning(self.iface.mainWindow(), title, self.tr("Error saving PDF file"))
        return status_ok

    def get_current_municipality(self):
        """ Return center of map municipality """
        map_center = self.iface.mapCanvas().center()
        found_dict_list = self.find_point_secure(map_center.x(), map_center.y(), self.project.get_epsg())
        municipality = found_dict_list[0]['nomMunicipi'] if found_dict_list else ""
        return municipality

    def enable_debug_log(self, enable=True):
        """ Enable or disable log level debug """
        if not enable:
            self.log.info("Debug log disabled")
        self.log.setLevel(logging.DEBUG if enable else logging.WARNING)
        if enable:
            self.log.info("Debug log enabled: %s", self.log.log_filename)
            self.log.info("OS: %s %s v%s (%s)", platform.system(), platform.release(), platform.version(), sys.platform)
            self.log.info("QGIS version: %s", Qgis.QGIS_VERSION)
            self.log.info("Python version: %s", sys.version)
            self.log.info("%s version: %s", self.metadata.get_name(), self.metadata.get_version())

    def send_email(self, mail_text="", title="OpenICGC QGIS plugin", debug=False, new_plugin_version=None, last_log_lines=100, email_to="qgis.openicgc@icgc.cat"):
        """ Sends Open ICGC email with optional debug information """
        if new_plugin_version:
            # Cannot report issues with obsolete version of plugin, "report_issue" show warning message
            self.report_issue(new_plugin_version=new_plugin_version)
            return

        if not mail_text:
            # Add default mail body
            mail_text = "\n\n%s v%s / QGIS v%s\n" % (
                self.metadata.get_name(), self.metadata.get_version(), Qgis.QGIS_VERSION)
            mail_text += "OS: %s %s v%s (%s)\n" % (
                platform.system(), platform.release(), platform.version(), sys.platform)
            # Adds log information from log_file
            if debug:
                title += " debug"
                log_pathname = self.log.getLogFilename()
                if log_pathname and os.path.exists(log_pathname):
                    with open(log_pathname, "r") as file_in:
                        log_text = file_in.read()
                    log_info = "Log: " + "\n".join(list(reversed(log_text.split("\n")))[:last_log_lines])
                else:
                    log_info = ""
                mail_text += "Project EPSG: %s\n" \
                    "%s" % (self.project.get_epsg(), log_info)
        # Send email
        self.tools.send_email(email_to, title, mail_text)

    def report_issue(self, new_plugin_version=None):
        """ Open web navigator with GitHub issues page (if not new version of plugin available) """
        if new_plugin_version:
            # Cannot report issues with obsolete version of plugin
            self.log.debug("Obsolete plugin version detected. Send email cancelled")
            QMessageBox.warning(self.iface.mainWindow(), self.tr("Report an issue"), \
                self.tr("Please, update %s to version %s before report an issue") % (self.metadata.get_name(), new_plugin_version))
            return False
        # Show GitHub issues page
        self.show_help_file("plugin_issues")
        return True

    # def add_cat_ref_to_layer(self, layer=None):
    #     """ Load a reference layer of Catalonia to be able to zoom in world-wide layers """
    #     # Load Catalonia administrative limits 1M layer
    #     cat_1M_layer = self.layers.add_vector_layer("%s 1:%s" % (
    #         self.HTTP_NAMES_DICT.get(self.cat_1M_name, self.cat_1M_name), self.format_scale(self.cat_1M_scale)),
    #         self.cat_1M_url,
    #         group_name=self.backgroup_map_group_name, only_one_map_on_group=False, only_one_visible_map_on_group=False,
    #         set_current=False, style_file=self.cat_1M_style_file)
    #     # Force zoom to Catalonia
    #     self.layers.zoom_to_full_extent(cat_1M_layer, 5000)

    #     # Set original layer as current layer
    #     self.layers.set_current_layer(layer)
    #     return layer

    def zoom_to_cat_when_empty(self, layer):
        """ Zoom to Catalonia if empty project """
        # Wait pending events
        QApplication.processEvents()
        # Only zoom with empty project (only 1 new layer)
        layer_count = len(QgsProject.instance().mapLayers())
        if layer_count > 1:
            return False
        return self.layers.zoom_to_cat(layer)
