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

# Add a additional library folder to pythonpath (for external libraries)
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Import base libraries
import re
import datetime
import zipfile
import io
import locale
locale.setlocale(locale.LC_ALL, '')
from urllib.request import urlopen, Request
from urllib.parse import urljoin
from importlib import reload

# Import QGIS libraries
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsPointXY, QgsRectangle, QgsGeometry, QgsMultiPolygon
from qgis.core import Qgis, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsProject, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand
# Import the PyQt and QGIS libraries
from PyQt5.QtCore import QSize, Qt, QPoint, QDateTime
from PyQt5.QtGui import QIcon, QCursor, QColor, QPolygon
from PyQt5.QtWidgets import QApplication, QComboBox, QMessageBox, QStyle, QInputDialog, QLineEdit

# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Detect import relative mode (for release) or global import mode (for debug)
is_import_relative = os.path.exists(os.path.join(os.path.dirname(__file__), "qlib3"))
if is_import_relative:
	# Import basic plugin functionalities
	from .qlib3.base.loginfodialog import LogInfoDialog
	from .qlib3.base.pluginbase import PluginBase, WaitCursor
	# Import geofinder dialog and class
	from .geofinder3.geofinder import GeoFinder
	from .qlib3.geofinderdialog.geofinderdialog import GeoFinderDialog
	# Import photosearch dialog
	from .qlib3.photosearchselectiondialog.photosearchselectiondialog import PhotoSearchSelectionDialog
	# Import wms resources access functions
	from .resources3.wms import get_historic_ortho, get_lastest_ortoxpres, get_superexpedita_ortho, get_full_ortho
	from .resources3.fme import get_clip_data_url, get_services, get_regex_styles as get_fme_regex_styles
	from .resources3.http import get_dtms, get_sheets, get_delimitations, get_ndvis, get_topographic_5k, get_regex_styles as get_http_regex_styles
else:
    # Import basic plugin functionalities
    import qlib3.base.pluginbase
    reload(qlib3.base.pluginbase)
    from qlib3.base.pluginbase import PluginBase, WaitCursor
    import qlib3.base.loginfodialog
    reload(qlib3.base.loginfodialog)
    from qlib3.base.loginfodialog import LogInfoDialog
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
    from qlib3.photosearchselectiondialog.photosearchselectiondialog import PhotoSearchSelectionDialog
    # Import wms resources access functions
    import resources3.wms
    reload(resources3.wms)
    from resources3.wms import get_historic_ortho, get_lastest_ortoxpres, get_superexpedita_ortho, get_full_ortho
    import resources3.fme
    reload(resources3.fme)
    from resources3.fme import get_clip_data_url, get_services, get_regex_styles as get_fme_regex_styles
    import resources3.http
    reload(resources3.http)
    from resources3.http import get_dtms, get_sheets, get_delimitations, get_ndvis, get_topographic_5k, get_regex_styles as get_http_regex_styles


# Global function to set HTML tags to apply fontsize to QInputDialog text
set_html_font_size = lambda text, size=9: ('<html style="font-size:%spt;">%s</html>' % (size, text.replace("\n", "<br/>").replace(" ", "&nbsp;")))

# Constants
PHOTOLIB_WFS_MAX_FEATURES = 1000
PHOTOLIB_WFS = "https://fototeca-connector.icgc.cat/" 
#PHOTOLIB_WFS = "http://sedockersec01.icgc.local/"
#PHOTOLIB_WFS = "http://seuatdlinux01.icgc.local/" 
#PHOTOLIB_WFS = "http://localhost:5000/"
PHOTOLIB_WMS = PHOTOLIB_WFS


class QgsMapToolSubScene(QgsMapTool):
    """ Tool class to manage rectangular selections """

    def __init__(self, map_canvas, callback=None, \
        min_side=None, max_download_area=None, min_px_side=None, max_px_download_area=None, gsd=None, \
        mode_area_not_point=None, download_type=None, color=QColor(0,150,0,255), error_color=QColor(255,0,0,255), line_width=3):
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
        self.download_type = download_type
        # Initialize paint object
        self.rubberBand = QgsRubberBand(map_canvas, True)

    def set_callback(self, callback):
        self.callback = callback

    def set_min_max(self, min_side, max_download_area, min_px_side, max_px_download_area):
        self.min_side = min_side
        self.max_download_area = max_download_area
        self.min_px_side = min_px_side
        self.max_px_download_area = max_px_download_area

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
        color = self.error_color if area_too_big or area_too_little else self.color

        self.rubberBand.reset(True)

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

    def subscene(self, x=0, y=0):
        # Gets selection geometry
        area = None
        if self.mode_area_not_point:
            # If area is required takes rubberBans geometry
            geo = self.rubberBand.asGeometry()
            if geo:
                area = geo.boundingBox()
        if not area:
            # If not area then we takes a point
            point = self.toMapCoordinates(QPoint(x, y))
            area = QgsRectangle(point.x(), point.y(), point.x(), point.y())

        # Hide selection area
        self.rubberBand.reset(True)
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
        "ct":":/lib/qlib3/base/images/cat_topo5k.png",
        "bm":":/lib/qlib3/base/images/cat_topo5k.png",
        #"bt":":/lib/qlib3/base/images/cat_topo5k.png",
        "di":":/lib/qlib3/base/images/cat_topo5k.png", # divisions-administratives
        "to":":/lib/qlib3/base/images/cat_topo5k.png", # topografia-territorial
        "of":":/lib/qlib3/base/images/cat_ortho5k.png",
        "oi":":/lib/qlib3/base/images/cat_ortho5ki.png",
        "mt":":/lib/qlib3/base/images/cat_topo5k.png",
        "co":":/lib/qlib3/base/images/cat_landcover.png",
        "me":":/lib/qlib3/base/images/cat_dtm.png",
        #"gt":":/lib/qlib3/base/images/cat_geo250k.png",
        "mg":":/lib/qlib3/base/images/cat_geo250k.png",
        "ma":":/lib/qlib3/base/images/cat_geo250k.png",
        "ph":":/lib/qlib3/photosearchselectiondialog/images/photo_preview.png", # fototeca
        }

    CAT_WKT = "POLYGON((304457.290340574458241 4758033.341267678886652, 300160.834704967564903 4683919.481553458608687, 283512.069116991071496 4639880.811288491822779, 266863.303529014694504 4608731.507930342108011, 251825.708804390684236 4504542.458766875788569, 295327.322114910115488 4476078.440180979669094, 339903.049334330891725 4505079.515721328556538, 322717.226791903492995 4527635.907808261923492, 445166.212406698206905 4567378.122437627054751, 452147.952814559219405 4582952.774116697721183, 527335.926437678863294 4628065.558290572836995, 534317.666845540050417 4704864.702777042984962, 469333.775356986618135 4713994.671002711169422, 443555.041543345665559 4707012.930594847537577, 388238.175234907655977 4722050.525319471955299, 368367.067920226138085 4741384.575679702684283, 304457.290340574458241 4758033.341267678886652))"

    download_action = None
    time_series_action = None
    photo_search_action = None
    photo_search_2_action = None
    photo_download_action = None
    geopackage_style_action = None

    debug_mode = False

    ###########################################################################
    # Plugin initialization

    def __init__(self, iface):
        """ Plugin variables initialization """
        # Save reference to the QGIS interface
        super().__init__(iface, __file__)

        # Detection of developer enviroment
        self.lite = os.environ.get("openicgc_lite", "").lower() in ["true", "1", "enabled"]
        if self.lite:
            print("Open ICGC Lite")
        self.extra_countries = self.lite
        self.debug_mode = __file__.find("pyrepo") >= 0

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

        # Initialize references names (with translation)
        self.HTTP_NAMES_DICT = {
            "caps-municipi": self.tr("Municipal capitals"),
            "municipis": self.tr("Municipalities"),
            "comarques": self.tr("Counties"),
            "vegueries": self.tr("Vegueries"),
            "provincies": self.tr("Provinces"),
            "catalunya": self.tr("Catalonia"),
            }
        # Get download services regex styles
        self.http_regex_styles_list = get_http_regex_styles()

        # Initialize download names (with translation)
        self.FME_NAMES_DICT = {
            "of25c": self.tr("Color orthophoto 25cm 1:2,500"),
            "of5m": self.tr("Color orthophoto 50cm 1:5,000"),
            "of25m": self.tr("Color orthophoto 2.5m 1:25,000"),
            "oi25c": self.tr("Infrared orthophoto 25cm 1:2,500"),
            "oi5m": self.tr("Infrared orthophoto 50cm 1:5,000"),
            "oi25m": self.tr("Infrared orthophoto 2.5m 1:25,000"),
            #"bt5m": self.tr("Topographic base 1:5,000"),
            "topografia-territorial": self.tr("Territorial topographic referential"),
            "mtc25m": self.tr("Topographic map 1:25,000"),
            "mtc50m": self.tr("Topographic map 1:50,000"),
            "mtc100m": self.tr("Topographic map 1:100,000"),
            "mtc250m": self.tr("Topographic map 1:250,000"),
            "mtc500m": self.tr("Topographic map 1:500,000"),
            "mtc1000m": self.tr("Topographic map 1:1,000,000"),
            "mtc2000m": self.tr("Topographic map 1:2,000,000"),
            "ct1m": self.tr("Topographic cartography 1:1,000"),
            #"bm5m": self.tr("Municipal base 1:5,000"),
            "divisions-administratives": self.tr("Administrative divisions"),
            "topografia-territorial-gpkg": self.tr("Territorial topographic referential"),
            "topografia-territorial-dgn": self.tr("Territorial topographic referential"),
            "topografia-territorial-3d-dgn": self.tr("Territorial topographic referential 3D"),
            "topografia-territorial-dwg": self.tr("Territorial topographic referential"),
            "topografia-territorial-3d-dwg": self.tr("Territorial topographic referential 3D"),
            "topografia-territorial-volum-dwg": self.tr("Territorial topographic referential volume"),
            "cobertes-sol-raster": self.tr("Land cover map"),
            "cobertes-sol-vector": self.tr("Land cover map"),
            "met2": self.tr("Digital terrain model 2m"),
            "met5": self.tr("Digital terrain model 5m"),
            "mggt1": self.tr("Geological map 1:25,000 (GT I)"),
            "mg50m": self.tr("Geological map 1:50,000"),
            "mg250m": self.tr("Geological map 1:250,000"),
            "mggt6": self.tr("Geological map for the prevention of geological hazards 1:25,000 (GT VI)"),
            # Pending revision of symbology
            #"gt2": self.tr("GT II. Geoanthropic map 1:25,000"),
            #"gt3": self.tr("GT III. Geological map of urban areas 1:5,000"),
            #"gt4": self.tr("GT IV. Soil map 1:25,000"),
            #"gt5": self.tr("GT V. Hydrogeological map 1:25,000"),
            #"mah250m": self.tr("Map of hydrogeological Areas 1:250,000"),
            "photo": self.tr("Photo library"),
            }
        # Initialize download type descriptions (with translation)
        self.FME_DOWNLOADTYPE_LIST = [
            ("dt_area", self.tr("Area"), ""),
            ("dt_coord", self.tr("Area coordinates"), ""),
            ("dt_layer_polygon", self.tr("Selected layer polygons"), "pol"),
            ("dt_municipalities", self.tr("Municipality"), "mu"),
            ("dt_counties", self.tr("County"), "co"),
            ("dt_cat", self.tr("Catalonia"), "cat"),
            ("dt_all", self.tr("Available data"), "tot")]
        ## Inicitialize default download type
        self.download_type = "dt_area"
        self.cat_geo = QgsGeometry.fromWkt(self.CAT_WKT)
        # Get download services regex styles
        self.fme_regex_styles_list = get_fme_regex_styles()
        # Initialize download group
        self.download_group_name = self.tr("Download")

        # We created a GeoFinder object that will allow us to perform spatial searches
        self.geofinder = GeoFinder()
        self.geofinder_dialog = GeoFinderDialog(self.geofinder, title=self.tr("Spatial search"),
            columns_list=[self.tr("Name"), self.tr("Type"), self.tr("Municipality"), self.tr("Region")],
            keep_scale_text=self.tr("Keep scale"))

        # Initialize reference to PhotoSearchSelectionDialog
        self.photo_search_dialog = None
        # Initialize photo search group names
        self.photos_group_name = self.tr("Photograms")
        # Initialize photo search label
        self.photo_label = self.tr("Photo: %s")
        self.photo_layer_id = self.photo_label.replace(" ", "_").replace(":", "_") % ""
        self.photo_search_label = self.tr("Photo query: %s")
        self.photo_search_layer_id = self.photo_search_label.replace(" ", "_").replace(":", "_") % ""

        # Map change current layer event
        self.iface.layerTreeView().currentLayerChanged.connect(self.on_change_current_layer)
        self.iface.layerTreeView().clicked.connect(self.on_click_legend)

    def unload(self):
        """ Release of resources """
        # Unmap signals
        self.iface.layerTreeView().currentLayerChanged.disconnect(self.on_change_current_layer)
        self.iface.layerTreeView().clicked.disconnect(self.on_click_legend)
        self.combobox.activated.disconnect()
        # Remove photo dialog
        if self.photo_search_dialog:
            self.photo_search_dialog.reset()
            self.iface.removeDockWidget(self.photo_search_dialog)
        self.photo_search_dialog = None
        # Remove photo search groups
        self.legend.remove_group_by_name(self.photos_group_name)
        self.legend.remove_group_by_name(self.download_group_name)
        # Parent PluginBase class release all GUI resources created with their functions
        super().unload()

    def format_scale(self, scale):
        """ Format scale number with locale separator """
        text = locale.format("%d", scale, grouping=True)
        if self.translation.get_qgis_language() in ['ca', 'es']:
            text = text.replace(',', '.')
        return text

    def initGui(self, check_qgis_updates=True, check_icgc_updates=False):
        """ GUI initializacion """
        # Plugin registration in the plugin manager
        self.gui.configure_plugin()

        # Add combobox to search
        self.combobox = QComboBox()
        self.combobox.setFixedSize(QSize(250,24))
        self.combobox.setEditable(True)
        self.combobox.setToolTip(self.TOOLTIP_HELP)
        self.combobox.addItems(self.get_setting_value("last_searches", []))
        self.combobox.setCurrentText("")
        self.combobox.setMaxVisibleItems(20)
        self.combobox.activated.connect(self.run) # Press intro and select combo value

        # Gets available Topo5k files to simulate WMS-T service
        topo5k_time_series_list = [(time_year, "/vsicurl/%s" % url) for time_year, url in get_topographic_5k()]

        # Get Available delimitations
        delimitations_list = get_delimitations()

        # Gets available Sheets
        sheets_list = get_sheets()

        # Gets available DTMs
        dtm_list = [(name, "/vsicurl/%s" % url) for name, url in get_dtms()]
        height_highlighting_url = dtm_list[0][1] if dtm_list else None

        # Gets available NDVI files to simulate WMS-T service
        ndvi_time_series_list = [(time_year, "/vsicurl/%s" % url) for time_year, url in get_ndvis()]
        ndvi_current_time = ndvi_time_series_list[-1][0] if ndvi_time_series_list else None

        # Gets all ortho data (except satellite)
        ortho_wms_url, historic_ortho_list = get_full_ortho()
        ortho_color_time_series_list = [(str(year), layer_id) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortofoto" and color != "irc"]
        ortho_color_current_time = ortho_color_time_series_list[-1][1] if ortho_color_time_series_list else None
        ortho_infrared_time_series_list = [(str(year), layer_id) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortofoto" and color == "irc"]
        ortho_infrared_current_time = ortho_infrared_time_series_list[-1][1] if ortho_infrared_time_series_list else None
        ortosuperexp_color_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "superexpedita" and color != "irc"]
        ortosuperexp_color_year, ortosuperexp_color_layer_id, ortosuperexp_color_layer_name = ortosuperexp_color_list[-1] if ortosuperexp_color_list else (None, None, None)
        ortosuperexp_infrared_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "superexpedita" and color == "irc"]
        ortosuperexp_infrared_year, ortosuperexp_infrared_layer_id, ortosuperexp_infrared_layer_name = ortosuperexp_infrared_list[-1] if ortosuperexp_infrared_list else (None, None, None)
        ortoxpres_color_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortoxpres" and color != "irc"]
        ortoxpres_color_year, ortoxpres_color_layer_id, ortoxpres_color_layer_name = ortoxpres_color_list[-1] if ortoxpres_color_list else (None, None, None)
        ortoxpres_infrared_list = [(str(year), layer_id, layer_name) for layer_id, layer_name, ortho_type, color, year in historic_ortho_list if ortho_type == "ortoxpres" and color == "irc"]
        ortoxpres_infrared_year, ortoxpres_infrared_layer_id, ortoxpres_infrared_layer_name = ortoxpres_infrared_list[-1] if ortoxpres_infrared_list else (None, None, None)        
        
        # Gets anaglyph fotograms. Last year can not have full photograms coverage, we select previous year as default
        photolib_wms_url = PHOTOLIB_WMS
        photolib_time_series_list, photolib_current_time = self.layers.get_wms_t_time_series(photolib_wms_url, "anaglif_central")
        photolib_current_time = str(int(photolib_current_time) - 1) if photolib_current_time else photolib_current_time

        # Gets available download source data
        fme_services_list = get_services()
        download_raster_submenu = self.get_download_menu(fme_services_list, True)
        download_vector_submenu = self.get_download_menu(fme_services_list, False)

        # Check plugin update
        new_icgc_plugin_version = self.check_plugin_update() if check_icgc_updates else None
        new_qgis_plugin_version = self.metadata.get_qgis_new_version_available() if check_qgis_updates and not self.lite else None

        # Check QGIS version problems
        enable_http_files = self.check_qgis_version(31004)
        qgis_version_ok = self.check_qgis_version(31004)

        # Add new toolbar with plugin options (using pluginbase functions)
        style = self.iface.mainWindow().style()
        self.toolbar = self.gui.configure_toolbar(self.tr("Open ICGC Toolbar") + (" lite" if self.lite else ""), [
            self.tr("Find"), # Label text
            self.combobox, # Editable combobox
            (self.tr("Find place names and adresses"), self.run, QIcon(":/lib/qlib3/geofinderdialog/images/geofinder.png")), # Action button
            "---",
            (self.tr("Background maps"),
                lambda _checked:self.layers.add_wms_layer(self.tr("Topographic map (topographical pyramid)"), "https://geoserveis.icgc.cat/icc_mapesmultibase/utm/wms/service", ["topo"], ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                QIcon(":/lib/qlib3/base/images/wms.png"), True, False, "background_maps", [
                (self.tr("Topographic map (topographical pyramid)"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Topographic map (topographical pyramid)"), "https://geoserveis.icgc.cat/icc_mapesmultibase/utm/wms/service", ["topo"], ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo250k.png")),
                (self.tr("Territorial topographic referential"), None, QIcon(":/lib/qlib3/base/images/cat_topo5k.png"), enable_http_files, [
                    (self.tr("Territorial topographic referential %s (temporal serie)") % topo5k_year,
                        lambda _checked, topo5k_year=topo5k_year:self.add_wms_t_layer(self.tr("[TS] Territorial topographic referential"), None, topo5k_year, None, "default", "image/jpeg", topo5k_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, resampling_bilinear=True, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_topo5k.png"))
                    for topo5k_year, _url in topo5k_time_series_list]),
                (self.tr("Topographic map 1:50,000"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Topographic map 1:50,000"), "https://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc50m"], ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo50k.png")),
                (self.tr("Topographic map 1:250,000"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Topographic map 1:250,000"), "https://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc250m"], ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo250k.png")),
                "---",
                (self.tr("Administrative divisions"), None, QIcon(":/lib/qlib3/base/images/cat_vector.png"), enable_http_files, [
                    (self.tr("Administrative divisions (raster pyramid)"),
                        lambda _checked:self.layers.add_wms_layer(self.tr("Administrative divisions (raster pyramid)"), "https://geoserveis.icgc.cat/servei/catalunya/divisions-administratives/wms",
                            ['divisions_administratives_comarques_1000000', 'divisions_administratives_comarques_500000', 'divisions_administratives_comarques_250000', 'divisions_administratives_comarques_100000', 'divisions_administratives_comarques_50000', 'divisions_administratives_comarques_5000', 'divisions_administratives_municipis_250000', 'divisions_administratives_municipis_100000', 'divisions_administratives_municipis_50000', 'divisions_administratives_municipis_5000', 'divisions_administratives_capsdemunicipi_capmunicipi', 'divisions_administratives_capsdemunicipi_capcomarca'],
                            ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_vector.png")),
                    "---",
                    ] + [
                    (self.HTTP_NAMES_DICT.get(name, name),
                        (lambda _checked, name=name, scale_list=scale_list:self.layers.add_vector_layer(self.HTTP_NAMES_DICT.get(name, name), scale_list[0][1], group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, regex_styles_list=self.http_regex_styles_list) if len(scale_list) == 1 else None),
                        QIcon(":/lib/qlib3/base/images/cat_vector.png"), ([
                            ("%s 1:%s" % (self.HTTP_NAMES_DICT.get(name, name), self.format_scale(scale)),
                                lambda _checked, name=name, scale=scale, url=url:self.layers.add_vector_layer("%s 1:%s" % (self.HTTP_NAMES_DICT.get(name, name), self.format_scale(scale)), url, group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, regex_styles_list=self.http_regex_styles_list),
                                QIcon(":/lib/qlib3/base/images/cat_vector.png"))
                            for scale, url in scale_list] if len(scale_list) > 1 else True))
                        for name, scale_list in delimitations_list
                        ]),
                (self.tr("Cartographic series"), None, QIcon(":/lib/qlib3/base/images/sheets.png"), enable_http_files, [
                    (self.tr("%s serie") % sheet_name,
                        lambda _checked, sheet_name=sheet_name, sheet_url=sheet_url:self.layers.add_vector_layer(self.tr("%s serie") % sheet_name, sheet_url, group_name=self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True, style_file="talls.qml"),
                        QIcon(":/lib/qlib3/base/images/sheets.png"), enable_http_files
                        ) for sheet_name, sheet_url in sheets_list
                    ]),
                "---",
                (self.tr("Geological map 1:250,000"),
                    lambda _checked:self.layers.add_wms_layer(self.tr("Geological map 1:250,000"), "https://geoserveis.icgc.cat/mgc250mv2(raster)/wms/service", ["0"], ["default"], "image/png", 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_geo250k.png")),
                (self.tr("Land cover map (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] Land cover map"), "https://geoserveis.icgc.cat/servei/catalunya/cobertes-sol/wms", "serie_temporal", None, "default", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_landcover.png")),
                "---",
                ] + [(self.tr("Digital Terrain Model %s") % dtm_name,
                    # Force EPSG:25831 by problems with QGIS 3.10 version
                    lambda _checked, dtm_name=dtm_name, dtm_url=dtm_url:self.layers.add_raster_layer(self.tr("Digital Terrain Model %s") % dtm_name, dtm_url, group_name=self.backgroup_map_group_name, group_pos=0, epsg=25831, only_one_map_on_group=False, set_current=True, color_default_expansion=True),
                    QIcon(":/lib/qlib3/base/images/cat_dtm.png"), enable_http_files
                    ) for dtm_name, dtm_url in dtm_list] + [
                "---",
                (self.tr("NDVI color (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] NDVI color"), "https://geoserveis.icgc.cat/servei/catalunya/ndvi/wms", "ndvi_serie_anual_color", None, "default", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_landcover.png")),
                (self.tr("NDVI (temporal serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[TS] NDVI"), None, ndvi_current_time, None, "default", "image/jpeg", ndvi_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png"), enable_http_files),
                "---",
                (self.tr("Color orthophoto"), None, QIcon(":/lib/qlib3/base/images/cat_ortho5k.png"), [
                    ] + ([(self.tr("Color orthophoto %s (provisional)") % ortoxpres_color_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Color orthophoto %s (provisional)") % ortoxpres_color_year, ortho_wms_url, [ortoxpres_color_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0xFFFFFF", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5k.png"))
                        ] if ortoxpres_color_list else []) + [
                    ] + ([(self.tr("Color orthophoto %s (rectification without corrections)") % ortosuperexp_color_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Color orthophoto %s (rectification without corrections)") % ortosuperexp_color_year, ortho_wms_url, [ortosuperexp_color_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5k.png"))
                        ] if ortosuperexp_color_list else []) + [
                    "---",
                    ] + [
                    (self.tr("Color orthophoto %s (temporal serie)") % ortho_year,
                        lambda _checked,layer_id=layer_id:self.add_wms_t_layer(self.tr("[TS] Color orthophoto"), ortho_wms_url, layer_id, None, "default", "image/jpeg", ortho_color_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5k.png")) for ortho_year, layer_id in reversed(ortho_color_time_series_list)
                    ] + [
                    "---",
                    (self.tr("Color orthophoto (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Color orthophoto"), "https://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms", "ortofoto_color_serie_anual", None, "", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                    ]),
                (self.tr("Satellite color orthophoto (monthly serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[MS] Satellite color orthophoto"), "https://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2rgb", None, "", "image/jpeg", None, 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                "---",
                (self.tr("Infrared orthophoto"), None, QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png"), [
                    ] + ([(self.tr("Infrared orthophoto %s (provisional)") % ortoxpres_infrared_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Infrared orthophoto %s (provisional)") % ortoxpres_infrared_year, ortho_wms_url, [ortoxpres_infrared_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0xFFFFFF", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png"))
                        ] if ortoxpres_infrared_list else []) + [
                    ] + ([(self.tr("Infrared orthophoto %s (rectification without corrections)") % ortosuperexp_infrared_year,
                        lambda _checked:self.layers.add_wms_layer(self.tr("Infrared orthophoto %s (rectification without corrections)") % ortosuperexp_infrared_year, ortho_wms_url, [ortosuperexp_infrared_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png"))
                        ] if ortosuperexp_infrared_list else []) + [
                    "---"
                    ] + [
                    (self.tr("Infrared orthophoto %s (temporal serie)") % ortho_year,
                        lambda _checked,layer_id=layer_id:self.add_wms_t_layer(self.tr("[TS] Infrared orthophoto"), ortho_wms_url, layer_id, None, "default", "image/jpeg", ortho_infrared_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5k.png")) for ortho_year, layer_id in reversed(ortho_infrared_time_series_list)
                    ] + [
                    "---",
                    (self.tr("Infrared orthophoto (annual serie)"),
                        lambda _checked:self.add_wms_t_layer(self.tr("[AS] Infrared orthophoto"), "https://geoserveis.icgc.cat/servei/catalunya/orto-territorial/wms", "ortofoto_infraroig_serie_anual", None, "", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                    ]),
                (self.tr("Satellite infrared orthophoto (monthly serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[MS] Satellite infared orthophoto"), "https://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2irc", None, "default", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png")),
                "---",
                (self.tr("Centered anaglyph photogram"), None, QIcon(":/lib/qlib3/photosearchselectiondialog/images/stereo_preview.png"), [
                    (self.tr("Centered anaglyph photogram %s (annual serie)") % anaglyph_year,
                    lambda _checked,anaglyph_year=anaglyph_year,anaglyph_layer=anaglyph_layer:self.add_wms_t_layer(self.tr("[AS] Centered anaglyph phootogram"), photolib_wms_url, anaglyph_layer, str(anaglyph_year), "central,100,false", "image/png", None, 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False), 
                    QIcon(":/lib/qlib3/photosearchselectiondialog/images/stereo_preview.png")) for anaglyph_year, anaglyph_layer in reversed(photolib_time_series_list)
                    ])
                ] + ([
                (self.tr("Centered rectified photogram (annual serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[AS] Centered rectified photogram"), photolib_wms_url, "ortoxpres_central", photolib_current_time, "central", "image/png", None, 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False), 
                    QIcon(":/lib/qlib3/photosearchselectiondialog/images/rectified_preview.png")),
                (self.tr("Centered photogram (annual serie)"),
                    lambda _checked:self.add_wms_t_layer(self.tr("[AS] Centered photogram"), photolib_wms_url, "foto_central", photolib_current_time, "central", "image/png", None, 25831, "referer=ICGC", self.backgroup_map_group_name, only_one_map_on_group=False, set_current=False), 
                    QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_preview.png")),
                ] if self.debug_mode else []) + [
                "---"
                ] + ([
                    (self.tr("Instamaps pyramid"),
                        lambda:self.layers.add_wms_layer(self.tr("Instamaps pyramid"), "https://tilemaps.icgc.cat/mapfactory/service", ["osm_suau"], ["default"], "image/png", 25831, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                        QIcon(":/lib/qlib3/base/images/cat_topo5k.png")),
                    "---",
                    (self.tr("Spain"), None, QIcon(":/lib/qlib3/base/images/spain_topo.png"), [
                        (self.tr("IGN topographic"),
                            lambda:self.layers.add_wms_layer(self.tr("IGN topographic"), "http://www.ign.es/wms-inspire/mapa-raster", ["mtn_rasterizado"], ["default"], "image/png", 25830, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/spain_topo.png")),
                        "---",
                        (self.tr("PNOA orthophoto"),
                            lambda:self.layers.add_wms_layer(self.tr("PNOA orthophoto"), "http://www.ign.es/wms-inspire/pnoa-ma", ["OI.OrthoimageCoverage"], ["default"], "image/png", 25830, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/spain_orto.png")),
                        "---",
                        (self.tr("Cadastral registry"),
                            lambda:self.layers.add_wms_layer(self.tr("Cadastral registry"), "http://ovc.catastro.meh.es/Cartografia/WMS/ServidorWMS.aspx", ["Catastro"], ["default"], "image/png", 25831, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/spain_cadastral.png")),
                        ]),
                    (self.tr('Andorra'), None, QIcon(":/lib/qlib3/base/images/andorra_topo50k.png"), [
                        (self.tr("Andorra topographic 1:25,000 1989"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra topographic 1:25,000 1989"), "http://www.ideandorra.ad/Serveis/wmscarto25kraster_1989/wms", ["carto_25k_1989"], [], "image/png",  27573, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/andorra_topo25k.png")),
                        (self.tr("Andorra topographic 1:50,000 1987"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra topographic 1:50,000 1987"), "http://www.ideandorra.ad/Serveis/wmscarto50kraster_1987/wms", ["carto_50k_1987"], [], "image/png",  27573, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/andorra_topo50k.png")),
                        "---",
                        (self.tr("Andorra orthophoto 1:5,000 2003"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra orthophoto 1:5,000 2003"), "http://www.ideandorra.ad/Serveis/wmsorto2003/wms", ["Orto5000_2003"], [], "image/jpeg",  27573, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/andorra_orto2003.png")),
                        (self.tr("Andorra Infrared orthophoto 1:5,000 2003"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra Infrared orthophoto 1:5,000 2003"), "http://www.ideandorra.ad/Serveis/wmsortoIRC/wms", ["mosaic_IRC"], [], "image/jpeg",  27573, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/andorra_orto2003i.png")),
                        (self.tr("Andorra orthophoto 1:500-1,000 20cm 2008"),
                            lambda:self.layers.add_wms_layer(self.tr("Andorra orthophoto 1:500-1,000 20cm 2008"), "http://www.ideandorra.ad/Serveis/wmsorto2008/wms", ["orto2008"], [], "image/jpeg",  27573, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                            QIcon(":/lib/qlib3/base/images/andorra_orto2008.png")),
                        ]),
                    (self.tr("World"), None, QIcon(":/lib/qlib3/base/images/world.png"), [
                         (self.tr("NASA blue marble"),
                             lambda:self.layers.add_wms_layer(self.tr("NASA blue marble"), "http://geoserver.webservice-energy.org/geoserver/ows", ["gn:bluemarble-2048"], [], "image/png", 4326, '', self.backgroup_map_group_name, only_one_map_on_group=False, set_current=True),
                             QIcon(":/lib/qlib3/base/images/world.png")),
                         ]),
                    "---",
                ] if self.extra_countries or self.debug_mode else []) + [
                (self.tr("Delete background maps"), lambda _checked:self.legend.empty_group_by_name(self.backgroup_map_group_name),
                    QIcon(":/lib/qlib3/base/images/wms_remove.png"), True, False, "delete_background")
                ]),
            (self.tr("Time series"),
                lambda _checked:self.tools.toggle_time_series_dialog(self.iface.mapCanvas().currentLayer(), self.tr("Time series"), self.tr("Selected: ")) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                QIcon(":/lib/qlib3/base/images/time.png"),
                False, True, "time_series"),
            ] + ([
                (self.tr("Search photograms"), (self.enable_search_photos, self.pair_photo_search_checks), QIcon(":/plugins/openicgc/images/search.png"), True, True, "photo_search", [
                    (self.tr("Search photograms interactively"), (self.enable_search_photos, self.pair_photo_search_checks), QIcon(":/plugins/openicgc/images/search.png"), True, True, "photo_search_2"),
                    (self.tr("Search photograms by coordinates"), lambda _checked:self.search_photos_by_point(), QIcon(":/plugins/openicgc/images/search_coord.png"), True, False),
                    (self.tr("Search photograms by name"), lambda _checked:self.search_photos_by_name(), QIcon(":/plugins/openicgc/images/search_name.png"), True, False),
                    ]),
                (self.tr("Download tool"), self.disable_download_global_check, QIcon(":/plugins/openicgc/images/download_area.png"), True, True, "download",
                    download_vector_submenu + ["---"] + download_raster_submenu + [
                    "---",
                    (self.tr("Select download folder"), self.set_download_folder, QIcon(":/lib/qlib3/base/images/download_folder.png"), True, False, "select_download_folder"),
                    (self.tr("Open download folder"), self.open_download_folder, style.standardIcon(QStyle.SP_DirIcon), True, False, "open_download_folder"),
                    ])
            ] if not self.lite else []) + [
            (self.tr("Paint styles for selected layers"), None, QIcon(":/lib/qlib3/base/images/style.png"), [
                (self.tr("Transparence"),
                    lambda _checked:self.tools.show_transparency_dialog(self.tr("Transparence"), self.iface.mapCanvas().currentLayer()) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                    QIcon(":/lib/qlib3/base/images/transparency.png")),
                (self.tr("Desaturate raster layer"),
                    lambda _checked:self.layers.set_saturation(self.iface.mapCanvas().currentLayer(), -100, True) if type(self.iface.mapCanvas().currentLayer()) is QgsRasterLayer else None,
                    QIcon(":/lib/qlib3/base/images/desaturate.png")),
                (self.tr("Anaglyph"),
                    lambda _checked:self.tools.show_anaglyph_dialog(self.iface.mapCanvas().currentLayer(), self.tr("Anaglyph"), self.tr("Anaglyph"), self.tr("Inverted stereo")),
                    QIcon(":/lib/qlib3/photosearchselectiondialog/images/stereo_preview.png")),
                (self.tr("Shading DTM layer"),
                    self.shading_dtm,
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png")),
                "---",
                (self.tr("Add height highlighting"),
                    lambda _checked, dtm_url=height_highlighting_url:self.add_height_highlighting_layer(self.tr("Height highlighting"), dtm_url, style_file="ressaltat_alçades.qml", group_name=self.backgroup_map_group_name),
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png"), enable_http_files and height_highlighting_url),
                "---",
                (self.tr("Change DB/geoPackage style"),
                    lambda _checked:self.tools.show_db_styles_dialog(self.tr("Change DB/geoPackage style")),
                    QIcon(":/lib/qlib3/base/images/style.png"),
                    False, False, "geopackage_style"),
            ]),
            ] + ([] if self.lite else [
            "---",
            (self.tr("Help"), self.show_help, QIcon(":/lib/qlib3/base/images/help.png"), [
                (self.tr("About Open ICGC"), self.show_about, QIcon(":/plugins/openicgc/icon.png")),
                (self.tr("What's new"), self.show_changelog, QIcon(":/lib/qlib3/base/images/new.png")),
                (self.tr("Help"), self.show_help, QIcon(":/lib/qlib3/base/images/help.png")),
                "---",
                (self.tr("Available products list"), self.show_available_products, style.standardIcon(QStyle.SP_FileDialogDetailedView)),
                "---",
                (self.tr("Cartographic and Geological Institute of Catalonia web"), lambda _checked:self.show_help_file("icgc"), QIcon(":/lib/qlib3/base/images/icgc.png")),
                (self.tr("QGIS plugin repository"), lambda _checked:self.show_help_file("plugin_qgis"), QIcon(":/lib/qlib3/base/images/plugin.png")),
                (self.tr("Software Repository"), lambda _checked:self.show_help_file("plugin_github"), QIcon(":/lib/qlib3/base/images/git.png")),
                (self.tr("Report an issue"), lambda _checked:self.show_help_file("plugin_issues"), QIcon(":/lib/qlib3/base/images/bug.png")),
                (self.tr("Send us an email"), lambda _checked:self.tools.send_email("qgis.openicgc@icgc.cat", "OpenICGC QGIS plugin"), QIcon(":/lib/qlib3/base/images/send_email.png")),
                ]),
            ]) + ([] if not new_qgis_plugin_version or self.lite else [
                self.tr("Update\n available: v%s") % new_qgis_plugin_version,
                (self.tr("Download plugin"), lambda _checked,v=new_qgis_plugin_version:self.download_plugin_update(v, UpdateType.plugin_manager), QIcon(":/lib/qlib3/base/images/new.png")), #style.standardIcon(QStyle.SP_BrowserReload)),
            ]) + ([] if not new_icgc_plugin_version or self.lite else [
                self.tr("Update\n available: v%s") % new_icgc_plugin_version,
                (self.tr("Download plugin"), lambda _checked,v=new_icgc_plugin_version:self.download_plugin_update(v, UpdateType.icgc_web), QIcon(":/lib/qlib3/base/images/new_icgc.png")), #style.standardIcon(QStyle.SP_BrowserReload)),
            ]) + ([] if qgis_version_ok or self.lite else [
                self.tr("Warning:"),
                (self.tr("QGIS version warnings"), self.show_qgis_version_warnings, style.standardIcon(QStyle.SP_MessageBoxWarning)),
            ]))

        # Add plugin reload button (debug purpose)
        if self.debug_mode and not self.lite:
            self.gui.add_to_toolbar(self.toolbar, [
                "---",
                (self.tr("Reload Open ICGC"), self.reload_plugin, QIcon(":/lib/qlib3/base/images/python.png")),
                ])

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

    def get_download_menu(self, fme_services_list, raster_not_vector=None, nested_download_submenu=True):
        """ Create download submenu structure list """
        # Filter data type if required
        if raster_not_vector is not None:
            fme_services_list = [(id, name, min_side, max_query_area, min_px_side, max_px_area, download_list, filename, url_pattern, url_ref_or_wms_tuple) for id, name, min_side, max_query_area, min_px_side, max_px_area, download_list, filename, url_pattern, url_ref_or_wms_tuple in fme_services_list if self.is_raster_file(filename) == raster_not_vector]

        # Define text labels
        common_label = "%s"
        vector_label = self.tr("%s vectorial data")
        vector_file_label = vector_label + " (%s)"
        raster_label = self.tr("%s raster data")
        raster_file_label = raster_label + " (%s)"

        # Prepare nested download submenu
        if nested_download_submenu:
            # Add a end null entry
            fme_extra_services_list = fme_services_list + [(None, None, None, None, None, None, None, None, None, None)]
            download_submenu = []
            product_submenu = []
            # Create menu with a submenu for every product prefix
            for i, (id, _name, min_side, max_query_area, min_px_side, max_px_area, download_list, filename, url_pattern, url_ref_or_wms_tuple) in enumerate(fme_extra_services_list):
                prefix_id = id[:2] if id else None
                previous_prefix_id = fme_extra_services_list[i-1][0][:2] if i > 0 else id[:2]
                if previous_prefix_id != prefix_id:
                    if len(product_submenu) == 1:
                        # Add single menu entry
                        download_submenu.append(product_submenu[0])
                    else:
                        # Find group product common prefix
                        previous_name1 = self.FME_NAMES_DICT.get(fme_extra_services_list[i-1][0], fme_extra_services_list[i-1][1])
                        previous_name2 = self.FME_NAMES_DICT.get(fme_extra_services_list[i-2][0], fme_extra_services_list[i-2][1])
                        diff_list = [pos for pos in range(min(len(previous_name1), len(previous_name2))) if previous_name1[pos] != previous_name2[pos]]
                        pos = diff_list[0] if diff_list else min(len(previous_name1), len(previous_name2))
                        previous_name = previous_name1[:pos].replace("1:", "").strip()
                        # Add submenu entry
                        download_submenu.append(
                            ((common_label if raster_not_vector is None else raster_label if raster_not_vector else vector_label) % previous_name,
                            None,
                            QIcon(self.FME_ICON_DICT.get(previous_prefix_id, None)),
                            product_submenu))
                    product_submenu = []
                if id:
                    # Add entry to temporal product submenu
                    vectorial_not_raster = not self.is_raster_file(filename)
                    product_submenu.append((
                        (vector_file_label if vectorial_not_raster else raster_file_label) % (self.FME_NAMES_DICT.get(id, id), os.path.splitext(filename)[1][1:]),
                        (lambda _dummy, id=id, name=self.FME_NAMES_DICT.get(id, id), min_side=min_side, max_query_area=max_query_area, min_px_side=min_px_side, max_px_area=max_px_area, download_list=download_list, filename=filename, url_ref_or_wms_tuple=url_ref_or_wms_tuple : self.enable_download_subscene(id, name, min_side, max_query_area, min_px_side, max_px_area, download_list, filename, url_ref_or_wms_tuple), self.pair_download_checks),
                        QIcon(self.FME_ICON_DICT.get(prefix_id, None)),
                        True, True, id # Indiquem: actiu, checkable i un id d'acció
                        ))

        # Prepare "all in one" download submenu
        else:
            fme_extra_services_list = []
            # Add separators on change product prefix
            for i, (id, name, min_side, max_query_area, min_px_side, max_px_area, filename, url_pattern, url_ref_or_wms_tuple) in enumerate(fme_services_list): # 7 params
                if id[:2] != fme_services_list[max(0, i-1)][0][:2]: # If change 2 first characters the inject a separator
                    fme_extra_services_list.append((None, None, None, None, None, None, None, None, None, None)) # 7 + 1 (vectorial_not_raster)
                vectorial_not_raster = not self.is_raster_file(filename)
                fme_extra_services_list.append((id, name, min_side, max_query_area, min_px_side, max_px_side, filename, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple)) # 8 params
            # Create download menu
            download_submenu = [
                ((vector_file_label if vectorial_not_raster else raster_file_label) % (name, os.path.splitext(filename)[1][1:]),
                    (lambda _dummy, id=id, name=name, min_side=min_side, max_query_area=max_query_area, min_px_side=min_px_side, max_px_area=max_px_area, download_list=download_list, filename=filename, url_ref_or_wms_tuple=url_ref_or_wms_tuple : self.enable_download_subscene(id, name, min_side, max_query_area, min_px_side, max_px_area, download_list, filename, url_ref_or_wms_tuple), self.pair_download_checks),
                    QIcon(self.FME_ICON_DICT.get(id[:2], None)),
                    True, True, id # Indiquem: actiu, checkable i un id d'acció
                ) if id else "---" for id, name, min_side, max_query_area, min_px_side, max_px_area, filename, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple in fme_extra_services_list
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
                self.photo_search_dialog.select_photo(photo_id, flight_year)
            if self.tool_subscene:
                self.tool_subscene.set_gsd(gsd)

    def pair_download_checks(self, status):
        """ Synchronize the check of the button associated with Download button """
        if self.download_action:
            self.download_action.setChecked(status)

    def disable_download_global_check(self):
        """ Undo the change on button state we make when clicking on the Download button """
        if self.download_action:
            self.download_action.setChecked(not self.download_action.isChecked())

        # If not download action checked
        if not self.download_action.isChecked():
            if self.tool_subscene.download_type in ["dt_area", "dt_counties", "dt_municipalities"]:
                self.download_action.setChecked(True)
                self.gui.enable_tool(self.tool_subscene)
            else:
                self.tool_subscene.subscene()
            #self.enable_download_subscene(data_type, name, min_side, max_download_area, min_px_side, max_px_area, download_list, filename, url_ref_or_wms_tuple)

    def pair_photo_search_checks(self, status):
        """ Synchronize the check of the button associated with Download button """
        if self.photo_search_2_action:
            self.photo_search_2_action.setChecked(status)
        if self.photo_search_action:
            self.photo_search_action.setChecked(status)


    ###########################################################################
    # Functionalities

    def run(self, checked): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Basic plugin call, which reads the text of the combobox and the search for the different web services available """
        self.find(self.combobox.currentText())
        # Save last searches in persistent app settings
        searches_list = [self.combobox.itemText(i) for i in range(self.combobox.count())][-self.combobox.maxVisibleItems():]
        self.set_setting_value("last_searches", searches_list)

    def add_wms_t_layer(self, layer_name, url, layer_id, time, style, image_format, time_series_list=None, epsg=None, extra_tags="", group_name="", group_pos=None, only_one_map_on_group=False, collapsed=True, visible=True, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False):
        """ Add WMS-T layer and enable timeseries dialog """
        # Add WMS-T
        layer = self.layers.add_wms_t_layer(layer_name, url, layer_id, time, style, image_format, time_series_list, epsg, extra_tags, group_name, group_pos, only_one_map_on_group, collapsed, visible, transparency, saturation, resampling_bilinear, resampling_cubic, set_current)
        if layer:
            if type(layer) in [QgsRasterLayer, QgsVectorLayer]:
                # Show timeseries dialog
                self.tools.show_time_series_dialog(layer, self.tr("Time series"), self.tr("Selected: "))
                # Enable / check timeseries button
                if self.time_series_action:
                    self.time_series_action.setEnabled(True)
                    self.time_series_action.setChecked(self.tools.time_series_dialog is not None and self.tools.time_series_dialog.isVisible())
            # Show stereo anaglyph options
            if layer_id.lower().startswith("anaglif"):
                self.tools.show_anaglyph_dialog(layer, self.tr("Anaglyph"), self.tr("Anaglyph"), self.tr("Inverted stereo"))        
            # Show "on the fly" central photogram rendering layers warning
            if layer_id.lower().endswith("_central"):
                message = self.tr("This layer renders only the most centered photogram in the map view, you can zoom in for continuous navigation. Please note that current year may not have full photogram coverage")
                self.iface.messageBar().pushMessage(layer_name, message, level=Qgis.Info, duration=10)
        
        return layer

    def find(self, user_text):
        """ Performs a geo-spatial query and shows the results to the user so he can choose the one he wants to visualize """
        if not user_text:
            QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"), self.tr("You must write any text"))
            return

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
                print("Error, no coordinates found")
                QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"),
                    self.tr("Error, location without coordinates"))
                return
            scale = self.geofinder_dialog.get_scale()
            # We resituate the map (implemented in parent PluginBase)
            self.set_map_point(x, y, epsg, scale)
        
        if self.debug_mode:
            print("")

    def is_unsupported_file(self, pathname):
        return self.is_file_type(pathname, ["dgn", "dwg"])
    def is_unsupported_extension(self, ext):
        return self.is_extension(ext, ["dgn", "dwg"])

    def is_compressed_file(self, pathname):
        return self.is_file_type(pathname, ["zip"])
    def is_compressed_extension(self, ext):
        return self.is_extension(ext, ["zip"])

    def is_raster_file(self, pathname):
        return self.is_file_type(pathname, ["tif", "jpeg", "jpg", "png"])
    def is_raster_extension(self, ext):
        return self.is_extension(ext, ["tif", "jpeg", "jpg", "png"])

    def is_file_type(self, pathname, ext_list):
        _filename, ext = os.path.splitext(pathname)
        return self.is_extension(ext, ext_list)
    def is_extension(self, ext, ext_list):
        return ext[1:].lower() in ext_list

    def enable_download_subscene(self, data_type, name, min_side, max_download_area, min_px_side, max_px_area, download_list, filename, url_ref_or_wms_tuple):
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

        # Check photo search warning
        gsd = None
        is_photo = (data_type == "photo")
        if is_photo:
            # If we want download a photogram, we need have select it one
            photo_id, _flight_year, _flight_code, _filename, _photo_name, gsd, _epsg = self.get_selected_photo_info()
            if not photo_id:
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

        # Download type selection
        download_descriptions_list = [description for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST]
        available_download_descriptions_list = [description for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST if operation_code in download_list]
        download_description, ok_pressed = QInputDialog.getItem(self.iface.mainWindow(), title,
            set_html_font_size(self.tr("Select the type of download and then use the download tool\nto mark a point or area of interest, enter a rectangle coordinates\nor select a polygons layer\n\nDownload type:") +
                " (%s)" % data_type),
            available_download_descriptions_list, 0, editable=False)
        if not ok_pressed:
            return
        download_index = download_descriptions_list.index(download_description)
        self.download_type, download_description, download_operation_code = self.FME_DOWNLOADTYPE_LIST[download_index]
        # Show selection info
        if self.download_type == 'dt_area':
            message = self.tr("Select an area")
        elif self.download_type == 'dt_municipalities':
            message = self.tr("Select municipality")
        elif self.download_type == 'dt_counties':
            message = self.tr("Select county")
        else:
            message = None
        if message:
            self.iface.messageBar().pushMessage(title, message, level=Qgis.Info, duration=5)

        # Changes icon and tooltip of download button
        self.gui.set_item_icon("download",
            QIcon(":/plugins/openicgc/images/download_%s.png" % self.download_type.replace("dt_", "")),
            "%s: %s / %s" % (self.tr("Download tool"), download_description, name))

        # Disable all reference layers
        self.disable_ref_layers()
        # Load reference map layer
        if url_ref_or_wms_tuple:
            self.load_ref_layer(url_ref_or_wms_tuple, name)

        # Configure new option to download
        self.tool_subscene.set_callback(lambda geo, data_type=data_type,
            min_side=min_side, max_download_area=max_download_area, min_px_side=min_px_side, max_px_area=max_px_area,
            download_operation_code=download_operation_code, filename=filename:
            self.download_map_area(geo, data_type, min_side, max_download_area, min_px_side, max_px_area, download_operation_code, filename))
        self.tool_subscene.set_min_max(min_side, max_download_area, min_px_side, max_px_area)
        self.tool_subscene.set_gsd(gsd)
        self.tool_subscene.set_mode(self.download_type in ['dt_area', 'dt_coord', 'dt_layer_polygon'])
        # Configure new download action (for auto manage check/uncheck action button)
        self.tool_subscene.setAction(action)

        if self.download_type in ['dt_cat', 'dt_all', 'dt_coord', 'dt_layer_polygon']:
            # No interactive geometry required, call download process
            self.tool_subscene.subscene()
        else:
            # Interactive point or rect is required, enable tool
            action.setChecked(True)
            self.gui.enable_tool(self.tool_subscene)

    def download_map_area(self, geo, data_type, min_side, max_download_area, min_px_side, max_px_area, download_operation_code, local_filename, default_point_buffer=50):
        """ Download a FME server data area (limited to max_download_area) """
        title = self.tr("Download tool")

        if self.download_type == 'dt_coord':
            # Ask coordinates to user
            msg_text = self.tr('Enter west, north, east, south values in the project coordinates system or add the corresponding EPSG code in the following format:\n   "429393.19 4580194.65 429493.19 4580294.65" or\n   "429393.19 4580194.65 429493.19 4580294.65 EPSG:25831" or\n   "EPSG:25831 429393.19 4580194.65 429493.19 4580294.65"')
            coord_text, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), self.tr("Download tool"),
                set_html_font_size(msg_text), QLineEdit.Normal, "")
            if not ok_pressed:
                return
            # Use GeoFinder static function to parse coordinate text
            west, north, east, south, epsg = GeoFinder.get_rectangle_coordinate(coord_text)
            if not west or not north:
                QMessageBox.warning(self.iface.mainWindow(), title, self.tr("Incorrect coordinates format"))
                return
            # Transform point coordinates to EPSG 4326
            if not epsg:
                epsg = int(self.project.get_epsg())
            rect = QgsRectangle(west, north, east, south)
            if epsg != self.project.get_epsg():
                transformation = QgsCoordinateTransform(
                    QgsCoordinateReferenceSystem("EPSG:%s" % epsg),
                    QgsCoordinateReferenceSystem("EPSG:%s" % self.project.get_epsg()),
                    QgsProject.instance())
                point = transformation.transform(rect)
            # Force download by rect
            geo = rect

        elif self.download_type == 'dt_layer_polygon':
            # Gets polygons from selected layer (vectorial)
            multipolygon, epsg = None, None
            layer = self.iface.mapCanvas().currentLayer()
            if layer and type(layer) == QgsVectorLayer:
                # Prepare transformation polygon coordinates to project EPSG
                epsg = self.layers.get_epsg(layer)
                transformation = None
                if epsg != self.project.get_epsg():
                    transformation = QgsCoordinateTransform(
                        QgsCoordinateReferenceSystem("EPSG:%s" % epsg),
                        QgsCoordinateReferenceSystem("EPSG:%s" % self.project.get_epsg()),
                        QgsProject.instance())
                # Add only selected polygons
                polygons_list = []
                for feature in layer.selectedFeatures():
                    geom = feature.geometry()
                    if geom.wkbType() in [QgsWkbTypes.Polygon, QgsWkbTypes.MultiPolygon]:
                        if transformation:
                            geom.transform(transformation)
                        polygons_list.append(geom)
                if polygons_list:
                    multipolygon = QgsGeometry.collectGeometry(polygons_list)
            if not multipolygon:
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("You must activate a vector layer with one or more selected polygons"))
                return
            max_polygons_points = 100
            polygons_points_count = sum(1 for _v in multipolygon.vertices())
            if polygons_points_count > max_polygons_points:
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Your polygons have too many points: %d maximum %d" % (polygons_points_count, max_polygons_points)))
                return
            # Force download by polygon
            geo = multipolygon

        # Check selection type
        is_polygon = (type(geo) == QgsGeometry)
        is_point = (type(geo) == QgsRectangle and geo.isEmpty())
        is_area = (type(geo) == QgsRectangle and not geo.isEmpty())

        title = self.tr("Download map area") if is_area or is_polygon else self.tr("Download point")

        # Check download file type
        filename, ext = os.path.splitext(local_filename)
        is_unsupported_format = self.is_unsupported_extension(ext)
        is_compressed = self.is_compressed_extension(ext)
        is_raster = self.is_raster_extension(ext)
        is_photo = (data_type == "photo")

        epsg = 25831
        gsd = None
        rect = None

        # Validate download path
        download_folder = self.get_download_folder()
        if not download_folder:
            return

        # If is photo download, change default out filename and add extra params to download
        if is_photo:
            _photo_id, flight_year, flight_code, filename, name, gsd, epsg = self.get_selected_photo_info()
            extra_params = [flight_year, flight_code, filename, name + ext]
            filename = os.path.splitext(filename)[0]
        else:
            extra_params = []

        # Check CS and transform
        if self.project.get_epsg() != str(epsg):
            transformation = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(self.project.get_epsg(True)),
                QgsCoordinateReferenceSystem("EPSG:%s" % epsg),
                QgsProject.instance())
            if self.debug_mode:
                print("Transformation geometry from %s to 25831\n%s" % (self.project.get_epsg(), geo))
            geo = transformation.transformBoundingBox(geo)
            if self.debug_mode:
                print("Geometry %s" % (geo))

        # Check area limit
        if is_area or is_polygon:
            rect = geo.boundingBox() if is_polygon else geo
            if min_side and (rect.width() < min_side or rect.height() < min_side):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Minimum download rect side not reached (%d m)") % (min_side))
                return
            if max_download_area and (geo.area() > max_download_area):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum download area reached (%s m%s)") % (self.format_scale(max_download_area), self.SQUARE_CHAR))
                return
            if min_px_side and gsd and ((rect.width() / gsd) < min_px_side or (rect.height() / gsd) < min_px_side):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Minimum download rect side not reached (%d px)") % (min_px_side))
                return
            if max_px_area and ((geo.area() / gsd / gsd) > max_px_area):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum download area reached (%s px%s)") % (self.format_scale(max_px_area), self.SQUARE_CHAR))
                return

        # If area is point, maybe we need transform into a rectangle
        if is_point:
            if self.download_type in ["dt_area", "dt_coord", "dt_layer_polygon"]:
                # If download type is area ensure that selection is area
                geo = geo.buffered(min_side if min_side else default_point_buffer)
            elif self.download_type in ["dt_municipalities", "dt_counties"]:
                # If download type is point, make a rectangle to can intersect with Catalonia edge
                geo = geo.buffered(1)
            rect = geo

        # If coordinates are out of Catalonia, error
        out_of_cat = False
        found_dict_list = None
        if self.download_type in ["dt_area", "dt_coord"]:
            out_of_cat = not self.cat_geo.intersects(geo)
        elif self.download_type in ["dt_layer_polygon"]:
            # With selfintersection multipolygon intersects fails, we can fix it using boundingbox
            out_of_cat = not self.cat_geo.intersects(geo if geo.isGeosValid() else geo.boundingBox())
        elif self.download_type in ["dt_municipalities", "dt_counties"]:
            # Find point on GeoFinder
            center = geo.center()
            found_dict_list = self.find_point_secure(center.x(), center.y(), 25831)
            out_of_cat = not found_dict_list
        if out_of_cat:
            QMessageBox.warning(self.iface.mainWindow(), title, self.tr("The selected area is outside Catalonia"))
            return

        # Show information about download
        type_info = (self.tr("raster") if is_raster else self.tr("vector"))
        if self.download_type in ["dt_area", "dt_coord"]:
            confirmation_text = self.tr("Data type:\n   %s (%s)\nRectangle:\n   %.2f, %.2f %.2f, %.2f\nArea:\n   %d m%s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, type_info, rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum(), rect.area(), self.SQUARE_CHAR, download_folder, ext[1:])
        elif self.download_type == "dt_layer_polygon":
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPolygon area:\n   %d m%s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, type_info, geo.area(), self.SQUARE_CHAR, download_folder, ext[1:])
        elif self.download_type == "dt_municipalities":
            municipality = found_dict_list[0]['nomMunicipi'] if found_dict_list else ""
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f\nMunicipality:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, type_info, rect.center().x(), rect.center().y(), municipality, download_folder, ext[1:])
        elif self.download_type == "dt_counties":
            county = found_dict_list[0]['nomComarca'] if found_dict_list else ""
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f\nCounty:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, type_info, rect.center().x(), rect.center().y(), county, download_folder, ext[1:])
        else:
            zone = self.tr("Catalonia") if self.download_type == "dt_cat" else self.tr("Available data")
            confirmation_text = self.tr("Data type:\n   %s (%s)\nZone:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, type_info, zone, download_folder, ext[1:])

        # User confirmation
        filename, ok_pressed = QInputDialog.getText(self.iface.mainWindow(), title,
            set_html_font_size(confirmation_text), QLineEdit.Normal, filename)
        if not ok_pressed or not local_filename:
            return
        local_filename = "%s_%s%s" % (filename, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), ext)

        # Get URL with FME action
        west, south, east, north = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()) if rect else (None, None, None, None)
        points_list = [(vertex.x(), vertex.y()) for vertex in geo.vertices()] if is_polygon else []
        referrer = "%s_v%s" % (self.metadata.get_name().replace(" ", ""), self.metadata.get_version())
        url = get_clip_data_url(data_type, download_operation_code, west, south, east, north, points_list, extra_params, referrer=referrer)
        if self.debug_mode:
            print("Download URL: %s" % url)
        if not url:
            print(self.tr("Error, can't find product %s as available to download") % data_type)
            return

        # Load layer
        current_layer = self.layers.get_current_layer()
        download_layer = None
        try:
            if is_unsupported_format:
                # With an unsupported format we only download file
                self.layers.download_remote_file(url, local_filename, download_folder=None)
            elif is_compressed:
                # We suppose that compressed file contains a QLR file
                download_layer = self.layers.add_remote_layer_definition_file(url, local_filename, group_name=self.download_group_name, group_pos=0)
                if not download_layer:
                    # If can't load QLR, we suppose that compressed file contains Shapefiles
                    download_layer = self.layers.add_vector_files([os.path.join(download_folder, local_filename)], group_name=self.download_group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.fme_regex_styles_list)
            elif is_raster:
                # Force EPSG:25831 or photo EPSG by problems with QGIS 3.10 version in auto detection EPSG
                download_layer = self.layers.add_remote_raster_file(url, local_filename, group_name=self.download_group_name, group_pos=0, epsg=epsg, only_one_visible_map_on_group=False, color_default_expansion=data_type.lower().startswith("met"), resampling_bilinear=True)
            else:
                download_layer = self.layers.add_remote_vector_file(url, local_filename, group_name=self.download_group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.fme_regex_styles_list)
        except Exception as e:
            error = str(e)
            # If server don't return error message (replied empty), we return a generic error
            if error.endswith("replied: "):
                error = self.tr("Error downloading file or selection is out of reference area")
            QMessageBox.warning(self.iface.mainWindow(), title, error)
            return
        if current_layer:
            self.layers.set_current_layer(current_layer)

        # Hide photo preview
        if is_photo and download_layer:
            self.layers.set_visible_by_id(self.photo_layer_id, False)

        # With unsupported format we try open file with external app
        if is_unsupported_format:
            if QMessageBox.question(self.iface.mainWindow(), title,
                self.tr("File type %s is unsupported by QGIS\nDo you want try open downloaded file in a external viewer?") % ext,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
                return
            try:
                self.layers.open_download_path(filename=local_filename)
            except:
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("The download file could not be opened"))

        # Disable tool
        action = self.tool_subscene.action()
        if action:
            action.setChecked(False)
        self.gui.enable_tool(None)

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

    def disable_ref_layers(self):
        """ Disable all reference layers """
        ref_pattern = self.tr("Reference %s")

        group = self.legend.get_group_by_name(self.backgroup_map_group_name)
        if group:
            for layer_tree in group.children():
                if layer_tree.name().startswith(ref_pattern % ""):
                    self.layers.set_visible(layer_tree.layer(), False)

    def load_ref_layer(self, url_ref_or_wfs_or_wms_tuple, name):
        """ Load a reference layer in WMS, WFS or HTTP file format """
        # Load reference layer
        ref_pattern = self.tr("Reference %s")
        layer_name = ref_pattern % name
        layer = self.layers.get_by_id(layer_name.replace(" ", "_"))
        if layer:
            # If exist reference layer, only set visible
            self.layers.set_visible(layer)
        else:
            # If don't exist reference layer in project, we load it
            if len(url_ref_or_wfs_or_wms_tuple) == 4: # Load WMS layer
                wms_url, wms_layer, wms_style, wms_format = url_ref_or_wfs_or_wms_tuple
                # Load WMS layer from URL
                layer = self.layers.add_wms_layer(layer_name, wms_url, [wms_layer], [wms_style] if wms_style else None, wms_format,
                    None, "referer=ICGC&bgcolor=0x000000", self.backgroup_map_group_name, 0, only_one_visible_map_on_group=False)
            elif len(url_ref_or_wfs_or_wms_tuple) == 3: # Load WFS
                wfs_url, wfs_layer, style_file = url_ref_or_wfs_or_wms_tuple
                # Load WFS layer from URL
                layer = self.layers.add_wfs_layer(layer_name, wfs_url, [wfs_layer],
                    extra_tags="referer=ICGC", group_name=self.backgroup_map_group_name, group_pos=0, style_file=style_file, only_one_visible_map_on_group=False)
            elif len(url_ref_or_wfs_or_wms_tuple) == 2: # Load HTTP
                url_ref, style_file = url_ref_or_wfs_or_wms_tuple
                is_raster = self.is_raster_file(url_ref)
                if is_raster:
                    # Load raster layer from URL
                    layer = self.layers.add_raster_layer(layer_name, url_ref, self.backgroup_map_group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
                else:
                    # Load vector layer from URL
                    layer = self.layers.add_vector_layer(layer_name, url_ref, self.backgroup_map_group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
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
        self.geofinder.get_icgc_geoencoder_client().set_options(timeout=timeout)
        try:
            found_dict_list = self.geofinder.find_point_coordinate(x, y, epsg)
        except:
            error = self.tr("Unknow, service unavailable")
            found_dict_list = [{'nomMunicipi': error, 'nomComarca': error}]
        self.geofinder.get_icgc_geoencoder_client().set_options(timeout=None)
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
        download_list = self.get_menu_names("download", ["open_download_folder", "select_download_folder"])
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
                if subaction.text() and subaction.objectName() not in exclude_list:
                    names_list.append(subaction.text())
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
            found = re.search('http-equiv="last-modified"\s+content="([\d-]+)"', local_data)
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
            if self.debug_mode:
                print("Help checked", remote_url)
            found = re.search('http-equiv="last-modified"\s+content="([\d-]+)"', remote_data)
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
                if self.debug_mode:
                    print("Help updated:", remote_url)

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
            if self.debug_mode:
                print("Help updated:", remote_image_url)

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
        found = re.search('version=(.+)\s', local_online_data)
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
                return False
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

        if self.debug_mode:
            print("Search photo: %s" % photolib_wfs)

        with WaitCursor():
            photo_layer = None

            # Search by coordinates
            if x and y:    
                if not epsg:
                    epsg = int(self.project.get_epsg())

                # Get municipality information of coordinate
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
                photo_layer = self.layers.add_wfs_layer(layer_name, photolib_wfs,
                    ["icgc:fotogrames"], 4326,
                    filter="SELECT * FROM fotogrames WHERE ST_Intersects(msGeometry, ST_GeometryFromText('POINT(%f %f)'))" % (x, y),
                    extra_tags="referer=ICGC",
                    group_name=self.photos_group_name, group_pos=group_pos, only_one_map_on_group=False, only_one_visible_map_on_group=True,
                    collapsed=False, visible=True, transparency=None, set_current=True)

            # Search by name
            if name and len(name) > 7: # at least flight code...
                layer_name = self.photo_search_label % name
                photo_layer = self.layers.add_wfs_layer(layer_name, photolib_wfs,
                    ["icgc:fotogrames"], 4326,
                    filter="SELECT * FROM fotogrames WHERE name LIKE '%s'" % (name),
                    extra_tags="referer=ICGC",
                    group_name=self.photos_group_name, group_pos=group_pos, only_one_map_on_group=False, only_one_visible_map_on_group=True,
                    collapsed=False, visible=True, transparency=None, set_current=True)

            if not photo_layer:
                return
            # Translate field names
            self.layers.set_fields_alias(photo_layer, {
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
            self.search_photos_year_list = sorted(list(set([(f[date_field].date().year() if type(f[date_field]) == QDateTime \
                else int(f[date_field].split("-")[0])) for f in photo_layer.getFeatures()])), reverse=True)
            # Set layer colored by year style
            self.layers.classify(photo_layer, 'to_int(left("flight_date", 4))', values_list=self.search_photos_year_list,
                color_list=[QColor(0, 127, 255, 25), QColor(100, 100, 100, 25)], # Fill with transparence
                border_color_list=[QColor(0, 127, 255), QColor(100, 100, 100)],  # Border without transparence
                interpolate_colors=True)
            self.layers.set_categories_visible(photo_layer, self.search_photos_year_list[1:], False)
            self.layers.enable_feature_count(photo_layer)
            self.layers.zoom_to_full_extent(photo_layer)
            self.layers.set_visible(photo_layer, False)

            # Show photo search dialog
            self.search_photos_year_list.reverse()
            self.show_photo_search_dialog(photo_layer, self.search_photos_year_list, self.search_photos_year_list[-1] if self.search_photos_year_list else None)

            # Map change selection feature event
            photo_layer.selectionChanged.connect(self.on_change_photo_selection)
            if self.photo_search_dialog:
                photo_layer.willBeDeleted.connect(self.photo_search_dialog.reset)

        # Disable search tool
        self.gui.enable_tool(None)

        ## Show warning if max results
        #if photo_layer and photo_layer.featureCount() == PHOTOLIB_WFS_MAX_FEATURES:
        #    QMessageBox.warning(self.iface.mainWindow(), title, 
        #        self.tr("The maximum number of results (%d) has been reached.\nThe query may have more results than are displayed.") % PHOTOLIB_WFS_MAX_FEATURES)

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
        if self.debug_mode:
            print("Show photo: %s %s" % (photolib_wms, photo_style))
        photo_label = self.photo_label % photo_name
        if photo_layer:
            # Update current photo_layer
            self.layers.update_wms_layer(photo_layer, wms_layer=layer_name, wms_style=photo_style)
            photo_layer.setName(photo_label)
            self.layers.set_visible(photo_layer)
            self.legend.set_group_visible_by_name(self.photos_group_name)
        else:
            # Load new preview layer at top (using WMS or UNC path to file)
            photo_layer = self.layers.add_wms_layer(photo_label, photolib_wms,
                [layer_name], [photo_style], "image/png", self.project.get_epsg(), extra_tags="referer=ICGC&bgcolor=0x000000",
                group_name=self.photos_group_name, group_pos=0, only_one_map_on_group=False, only_one_visible_map_on_group=False,
                collapsed=False, visible=True, transparency=None, set_current=False)
        # Restore previous selected layer
        if current_layer:
            self.layers.set_current_layer(current_layer)

        return photo_layer

    def show_photo_search_dialog(self, layer, years_list, current_year=None, title=None, current_prefix="", show=True):
        """ Show photo search dialog to filter photo results """
        # Show or hide dialog
        if show:
            if not current_year and years_list:
                current_year = years_list[0]

            # If not exist dialog we create it else we configure and show it
            update_photo_time_callback = lambda current_year, range_year: self.update_photo_search_layer_year(layer, current_year, range_year)
            update_photo_selection_callback = lambda photo_id: self.layers.set_selection(layer, [photo_id] if photo_id else [])
            show_info_callback = lambda photo_id: self.iface.openFeatureForm(layer, layer.getFeature(photo_id))
            preview_callback = lambda photo_id: self.photo_preview(layer.getFeature(photo_id)['name'])
            rectified_preview_callback = lambda photo_id: self.photo_preview(layer.getFeature(photo_id)['name'], rectified=True)
            stereo_preview_callback = lambda photo_id: self.photo_preview(layer.getFeature(photo_id)['name'], stereo=True)
            download_callback = lambda photo_id: self.photo_download_action.trigger()
            request_certificate_callback = None #lambda photo_id: self.tools.send_email("qgis.openicgc@icgc.cat",
                #"OpenICGC QGIS plugin. certificate %s" % layer.getFeature(photo_id)['name'],
                #self.tr("Certificate request for photogram: %s") % layer.getFeature(photo_id)['name'])
            request_scan_callback = None #lambda photo_id: self.tools.send_email("qgis.openicgc@icgc.cat",
                #"OpenICGC QGIS plugin. scan %s" % layer.getFeature(photo_id)['name'],
                #self.tr("Scan request for photogram: %s") % layer.getFeature(photo_id)['name'])
            report_photo_bug_callback = lambda photo_id: self.report_photo_bug(layer.getFeature(photo_id)['name'], layer.getFeature(photo_id)['flight_code'], layer.getFeature(photo_id)['flight_date'], layer.getFeature(photo_id)['gsd'] )
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
            self.layers.set_categories_visible(photo_layer, set(self.search_photos_year_list) - set(year_range), False)
            self.layers.set_categories_visible(photo_layer, year_range, True)
            self.layers.set_current_layer(photo_layer) # click in categories of layer can unselect layer... we fix it
            self.layers.set_visible(photo_layer) # force visibility of photo layer
            self.legend.set_group_visible_by_name(self.photos_group_name) # force visibility of photo group

    def report_photo_bug(self, photo_name, flight_code="", photo_date="", photo_resolution=0):
        """ Report a photo bug """
        # description, ok_pressed = QInputDialog.getMultiLineText(self.iface.mainWindow(), self.tr("Report photo bug"),
        #     set_html_font_size(self.tr("Looks like you found an error in photogram:\n%s\n\nWe will register the problem and try to fix it. Could you describe it briefly?") % photo_name))
        # if not ok_pressed:
        #     return
        title=self.tr("Report photo bug")
        if QMessageBox.question(self.iface.mainWindow(), title,
            self.tr("Before reporting an error, bear in mind that the position of photograms is an approximation i will never completely fit the underlying cartography, since no terrain model has been used to project the imatge against. Furthermore, changes in instrumenation over time (wheter GPS is used or not, scanning and photogrammetric workflow) account for a very limited precision in positioning.\n\nOnly large displacements in position (for example, an element that should appear near the center does not appear) or if there is an error in rotation (eg. the sea appears in the northern part of a photo).\n\nDo you want continue?"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) != QMessageBox.Yes:
            return
        self.tools.send_email("qgis.openicgc@icgc.cat",
                "Error en el fotograma %s" % photo_name, # Static text no translated
                self.tr("Photo: %s\nFlight code: %s\nDate: %s\nResolution: %.2fm\n\nProblem description: ") % (photo_name, flight_code, photo_date, photo_resolution or 0))
        QMessageBox.information(self.iface.mainWindow(), title,
            self.tr("Thanks for reporting an error in photogram:\n%s\n\nWe try to fix it as soon as possible") % photo_name)
