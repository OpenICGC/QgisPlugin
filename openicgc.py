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

# Add a additional library folder to pythonpath
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Import base libraries
import re
import datetime
import zipfile
import io
from urllib.request import urlopen, Request
from urllib.parse import urljoin

# Import QGIS libraries
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsPointXY, QgsRectangle, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsProject
from qgis.core import Qgis
from qgis.gui import QgsMapTool, QgsRubberBand
# Import the PyQt and QGIS libraries
from PyQt5.QtCore import QSize, Qt, QPoint
from PyQt5.QtGui import QIcon, QCursor, QColor
from PyQt5.QtWidgets import QApplication, QComboBox, QMessageBox, QStyle, QInputDialog, QLineEdit
# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Import basic plugin functionalities
from importlib import reload
import qlib3.base.pluginbase
reload(qlib3.base.pluginbase)
from qlib3.base.pluginbase import PluginBase
import qlib3.base.loginfodialog
reload(qlib3.base.loginfodialog)
from qlib3.base.loginfodialog import LogInfoDialog

# Import geofinder dialog
import qlib3.geofinderdialog.geofinderdialog
reload(qlib3.geofinderdialog.geofinderdialog)
from qlib3.geofinderdialog.geofinderdialog import GeoFinderDialog

# Import wms resources access functions
import resources3.wms
reload(resources3.wms)
from resources3.wms import get_historic_ortho, get_lastest_ortoxpres, get_superexpedita_ortho
import resources3.fme
reload(resources3.fme)
from resources3.fme import get_clip_data_url, get_services, get_regex_styles
import resources3.http
reload(resources3.http)
from resources3.http import get_dtms, get_sheets, get_delimitations


class QgsMapToolSubScene(QgsMapTool):
    """ Tool class to manage rectangular selections """

    def __init__(self, map_canvas, callback=None, min_side=None, max_download_area=None, mode_area_not_point=None, color=QColor(0,150,0,255), error_color=QColor(255,0,0,255), line_width=3):
        QgsMapTool.__init__(self, map_canvas)
        # Initialize local variables
        self.callback = callback
        self.pressed = False
        self.color = color
        self.error_color = error_color
        self.line_width = line_width
        self.min_side = None
        self.max_download_area = max_download_area
        self.mode_area_not_point = mode_area_not_point
        # Initialize paint object
        self.rubberBand = QgsRubberBand(map_canvas, True)

    def set_callback(self, callback):
        self.callback = callback

    def set_min_side(self, min_side):
        self.min_side = min_side

    def set_max_download_area(self, max_download_area):
        self.max_download_area = max_download_area

    def set_mode(self, area_not_point):
        self.mode_area_not_point = area_not_point

    def canvasPressEvent(self, event):
        #click
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
        area_too_big = self.max_download_area and (area > self.max_download_area)
        area_too_little = self.min_side and (width < self.min_side or height < self.min_side)
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
        self.subscene(event.pos().x(), event.pos().y())

    def subscene(self, x=0, y=0):
        # Gets selection geometry
        geo = self.rubberBand.asGeometry() if self.mode_area_not_point else None

        # Hide selection area
        self.rubberBand.reset(True)
        self.pressed = False

        if not geo:
            # If not geo then we takes a point
            point = self.toMapCoordinates(QPoint(x, y))
            area = QgsRectangle(point.x(), point.y(), point.x(), point.y())
        else:
            area = geo.boundingBox()

        # Execute callback with selected area as parameter
        if self.callback:
            self.callback(area)

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
    FME_ICON_DICT = {
            "ct":"cat_topo5k.png",
            "bm":"cat_topo5k.png",
            "bt":"cat_topo5k.png",
            "to":"cat_topo5k.png", # topografia-territorial
            "of":"cat_ortho5k.png",
            "oi":"cat_ortho5ki.png",
            "mt":"cat_topo5k.png",
            "co":"cat_landcover.png",
            "me":"cat_dtm.png",
            "gt":"cat_geo250k.png",
            "mg":"cat_geo250k.png",
            "ma":"cat_geo250k.png",
            }

    download_action = None
    time_series_action = None
    geopackage_style = None

    ###########################################################################
    # Plugin initialization

    def __init__(self, iface):
        """ Plugin variables initialization """
        # Save reference to the QGIS interface
        super().__init__(iface, __file__)

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

        # Initialize download type descriptions (with translation)
        self.FME_DOWNLOADTYPE_LIST = [
            ("dt_area", self.tr("Area"), ""),
            ("dt_municipalities", self.tr("Municipality"), "mu"),
            ("dt_counties", self.tr("County"), "co"),
            ("dt_cat", self.tr("Catalonia"), "cat"),
            ("dt_all", self.tr("Available data"), "tot")]
        ## Inicitialize default download type
        self.download_type = "dt_area"

        # Get download services regex styles
        self.regex_styles_list = get_regex_styles()

        # We created a GeoFinder object that will allow us to perform spatial searches
        self.geofinder_dialog = GeoFinderDialog(title=self.tr("Spatial search"),
            columns_list=[self.tr("Name"), self.tr("Type"), self.tr("Municipality"), self.tr("Region")])
        self.geofinder = self.geofinder_dialog.geofinder

        # Map change current layer event
        self.iface.layerTreeView().currentLayerChanged.connect(self.on_change_current_layer)

    def unload(self):
        """ Release of resources """
        # Unmap signals
        self.iface.layerTreeView().currentLayerChanged.disconnect(self.on_change_current_layer)
        self.combobox.activated.disconnect()

        # Parent PluginBase class release all GUI resources created with their functions
        super().unload()

    def initGui(self, check_qgis_updates=True, check_icgc_updates=False, debug=False):
        """ GUI initializacion """
        # Plugin registration in the plugin manager
        self.gui.configure_plugin()

        # Add combobox to search
        self.combobox = QComboBox()
        self.combobox.setFixedSize(QSize(250,24))
        self.combobox.setEditable(True)
        self.combobox.setToolTip(self.TOOLTIP_HELP)
        self.combobox.activated.connect(self.run) # Press intro and select combo value

        # Add a tool to download map areas
        self.tool_subscene = QgsMapToolSubScene(self.iface.mapCanvas())

        # Set group name for background maps
        group_name = self.tr("Background maps")

        # Gets historic orthophoto layers list to simulate WMS-T service
        historic_ortho_wms_url, historic_ortho_list = get_historic_ortho()
        historic_ortho_list.sort(key=lambda ho : ho[4]) # Ordenem per any
        ortho_color_time_series_list = [(str(year), layer_id) for layer_id, layer_name, color, scale, year in historic_ortho_list if color != "irc"]
        ortho_color_current_time = ortho_color_time_series_list[-1][1]
        ortho_infrared_time_series_list = [(str(year), layer_id) for layer_id, layer_name, color, scale, year in historic_ortho_list if color == "irc"]
        ortho_infrared_current_time = ortho_infrared_time_series_list[-1][1]

        # Gests lastest version of ortoXpres data
        ortoxpres_url, ortoxpres_list = get_lastest_ortoxpres()
        ortoxpres_color_list = [(layer_id, layer_name, year) for layer_id, layer_name, color, year in ortoxpres_list if color == "rgb"][0:1]
        ortoxpres_color_layer_id, ortoxpres_color_layer_name, ortoxpres_color_year = ortoxpres_color_list[0] if ortoxpres_color_list else (None, None, None)
        ortoxpres_infrared_list = [(layer_id, layer_name, year) for layer_id, layer_name, color, year in ortoxpres_list if color == "irc"][0:1]
        ortoxpres_infrared_layer_id, ortoxpres_infrared_layer_name, ortoxpres_infrared_year = ortoxpres_infrared_list[0] if ortoxpres_infrared_list else (None, None, None)
        ortoxpres_ndvi_list = [(layer_id, layer_name, year) for layer_id, layer_name, color, year in ortoxpres_list if color == "bw"][0:1]
        ortoxpres_ndvi_layer_id, ortoxpres_ndvi_layer_name, ortoxpres_ndvi_year = ortoxpres_ndvi_list[0] if ortoxpres_ndvi_list else (None, None, None)

        # Gets lastest version of ortofoto superexpèdita data
        ortosuperexp_url, ortosuperexp_list = get_superexpedita_ortho()
        ortosuperexp_color_list = [(layer_id, layer_name, year) for layer_id, layer_name, color, year in ortosuperexp_list if color == "rgb"][0:1]
        ortosuperexp_color_layer_id, ortosuperexp_color_layer_name, ortosuperexp_color_year = ortosuperexp_color_list[0] if ortosuperexp_color_list else (None, None, None)
        ortosuperexp_infrared_list = [(layer_id, layer_name, year) for layer_id, layer_name, color, year in ortosuperexp_list if color == "irc"][0:1]
        ortosuperexp_infrared_layer_id, ortosuperexp_infrared_layer_name, ortosuperexp_infrared_year = ortosuperexp_infrared_list[0] if ortosuperexp_infrared_list else (None, None, None)

        # Get Available delimitations
        delimitations_dict = dict(get_delimitations())

        # Gets available Sheets
        sheets_list = get_sheets()

        # Gets available DTMs
        dtm_list = get_dtms() # [(dtm_name, dtm_url), ]
        height_highlighting_url = dtm_list[0][1] if dtm_list else None

        # Gets available download source data
        fme_services_list = get_services()
        download_raster_submenu = self.get_download_menu(fme_services_list, True)
        download_vector_submenu = self.get_download_menu(fme_services_list, False)

        # Check plugin update
        new_icgc_plugin_version = self.check_plugin_update() if check_icgc_updates else None
        new_qgis_plugin_version = self.metadata.get_qgis_new_version_available() if check_qgis_updates else None

        # Check QGIS version problems
        enable_http_files = self.check_qgis_version(31004)
        qgis_version_ok = self.check_qgis_version(31004)

        # Add new toolbar with plugin options (using pluginbase functions)
        style = self.iface.mainWindow().style()
        self.toolbar = self.gui.configure_toolbar(self.tr("Open ICGC Toolbar"), [
            self.tr("Find"), # Label text
            self.combobox, # Editable combobox
            (self.tr("Find place names and adresses"), self.run, QIcon(":/lib/qlib3/geofinderdialog/images/geofinder.png")), # Action button
            "---",
            (self.tr("Background maps"), None, QIcon(":/lib/qlib3/base/images/wms.png"), True, False, "background_maps", [
                (self.tr("Municipal capital"),
                    lambda:self.layers.add_vector_layer(self.tr("Municipal capital"), delimitations_dict["Caps de Municipi"], group_name=group_name, only_one_map_on_group=False, set_current=True, style_file="caps_municipi.qml"),
                    QIcon(":/lib/qlib3/base/images/cat_vector.png"), enable_http_files and "Caps de Municipi" in delimitations_dict),
                (self.tr("Municipalities"),
                    lambda:self.layers.add_vector_layer(self.tr("Municipalities"), delimitations_dict["Municipis"], group_name=group_name, only_one_map_on_group=False, set_current=True, style_file="municipis.qml"),
                    QIcon(":/lib/qlib3/base/images/cat_vector.png"), enable_http_files and "Municipis" in delimitations_dict),
                (self.tr("Counties"),
                    lambda:self.layers.add_vector_layer(self.tr("Counties"), delimitations_dict["Comarques"], group_name=group_name, only_one_map_on_group=False, set_current=True, style_file="comarques.qml"),
                    QIcon(":/lib/qlib3/base/images/cat_vector.png"), enable_http_files and "Comarques" in delimitations_dict),
                (self.tr("Provinces"),
                    lambda:self.layers.add_vector_layer(self.tr("Provinces"), delimitations_dict["Províncies"], group_name=group_name, only_one_map_on_group=False, set_current=True, style_file="provincies.qml"),
                    QIcon(":/lib/qlib3/base/images/cat_vector.png"), enable_http_files and "Províncies" in delimitations_dict),
                (self.tr("Cartographic series"), None, QIcon(":/lib/qlib3/base/images/sheets.png"), enable_http_files, [
                    (self.tr("%s serie") % sheet_name,
                        lambda _dummy, sheet_name=sheet_name, sheet_url=sheet_url:self.layers.add_vector_layer(self.tr("%s serie") % sheet_name, sheet_url, group_name=group_name, only_one_map_on_group=False, set_current=True, style_file="talls.qml"),
                        QIcon(":/lib/qlib3/base/images/sheets.png"), enable_http_files
                        ) for sheet_name, sheet_url in sheets_list
                    ]),
                "---",
                (self.tr("Topographic (topographical pyramid)"),
                    lambda:self.layers.add_wms_layer(self.tr("Topographic (topographical pyramid)"), "http://geoserveis.icc.cat/icc_mapesmultibase/utm/wms/service", ["topo"], ["default"], "image/png", 25831, "referer=ICGC", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo250k.png")),
                (self.tr("Topographic 1:5,000"),
                    lambda:self.layers.add_wms_layer(self.tr("Topographic 1:5,000"), "http://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc5m"], ["default"], "image/png", 25831, "referer=ICGC", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo5k.png")),
                (self.tr("Topographic 1:50,000"),
                    lambda:self.layers.add_wms_layer(self.tr("Topographic 1:50,000"), "http://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc50m"], ["default"], "image/png", 25831, "referer=ICGC", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo50k.png")),
                (self.tr("Topographic 1:250,000"),
                    lambda:self.layers.add_wms_layer(self.tr("Topographic 1:250,000"), "http://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["mtc250m"], ["default"], "image/png", 25831, "referer=ICGC", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_topo250k.png")),
                "---",
                (self.tr("Geological 1:250,000"),
                    lambda:self.layers.add_wms_layer(self.tr("Geological 1:250,000"), "http://siurana.icgc.cat/arcgis/services/Base/MGC_MapaBase/MapServer/WMSServer", ["1"], ["default"], "image/png", 25831, "referer=ICGC", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_geo250k.png")),
                (self.tr("Land cover (temporal serie)"),
                    lambda:self.layers.add_wms_t_layer(self.tr("[TS] Land cover"), "http://geoserveis.icgc.cat/servei/catalunya/cobertes-sol/wms", "serie_temporal", "default", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_landcover.png")),
                "---",
                ] + [(self.tr("DTM %s") % dtm_name,
                    lambda _dummy, dtm_name=dtm_name, dtm_url=dtm_url:self.layers.add_raster_layer(self.tr("DTM %s") % dtm_name, "/vsicurl/%s" % dtm_url, group_name, only_one_map_on_group=False, set_current=True, color_default_expansion=True),
                    QIcon(":/lib/qlib3/base/images/cat_dtm.png"), enable_http_files
                    ) for dtm_name, dtm_url in dtm_list] + [
                (self.tr("DTM in grayscale"),
                    lambda:self.layers.add_wms_layer(self.tr("DTM in grayscale"), "http://geoserveis.icgc.cat/icgc_mdt2m/wms/service", ["MET2m"], ["default"], "image/jpeg", 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_dtm.png")),
                (self.tr("Shaded"),
                    lambda:self.layers.add_wms_layer(self.tr("Shaded"), "http://geoserveis.icgc.cat/icgc_mdt2m/wms/service", ["OMB2m"], ["default"], "image/jpeg", 25831, "referer=ICGC&bgcolor=0xFFFFFF", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png")),
                "---"
                ] + ([(self.tr("NDVI ortoXpres %s (rectification on the fly)") % ortoxpres_ndvi_year,
                    lambda:self.layers.add_wms_layer(self.tr("ortoXpres: %s") % ortoxpres_ndvi_layer_name, ortoxpres_url, [ortoxpres_ndvi_layer_id], [""], "image/jpeg", 25831, "referer=ICGC&bgcolor=0xFFFFFF", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png")),
                    "---"] if ortoxpres_ndvi_list else []) + [
                ] + ([(self.tr("Color ortoXpres %s (rectification on the fly)") % ortoxpres_color_year,
                    lambda:self.layers.add_wms_layer(self.tr("ortoXpres: %s") % ortoxpres_color_layer_name, ortoxpres_url, [ortoxpres_color_layer_id], [""], "image/jpeg", 25831, "referer=ICGC&bgcolor=0xFFFFFF", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5k.png"))
                    ] if ortoxpres_color_list else []) + [
                ] + ([(self.tr("Color superexpedited orthophoto %s (rectification without corrections)") % ortosuperexp_color_year,
                    lambda:self.layers.add_wms_layer(self.tr("orthoSuperExpedited: %s") % ortosuperexp_color_layer_name, ortosuperexp_url, [ortosuperexp_color_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5k.png"))
                    ] if ortosuperexp_color_list else []) + [
                (self.tr("Color orthophoto"),
                    lambda:self.layers.add_wms_layer(self.tr("Color orthophoto"), "http://geoserveis.icc.cat/icc_mapesmultibase/utm/wms/service", ["orto"], ["default"], "image/jpeg", 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5k.png")),
                (self.tr("Color orthophoto (temporal serie)"),
                    lambda:self.layers.add_wms_t_layer(self.tr("[TS] Color orthophoto"), historic_ortho_wms_url, ortho_color_current_time, "default", "image/jpeg", ortho_color_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                (self.tr("Satellite color orthophoto (temporal serie)"),
                    lambda:self.layers.add_wms_t_layer(self.tr("[TS] Satellite color orthophoto"), "http://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2rgb", "", "image/jpeg", None, 25831, "", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                "---",
                ] + ([(self.tr("Infrared ortoXpres %s (rectification on the fly)") % ortoxpres_infrared_year,
                    lambda:self.layers.add_wms_layer(self.tr("ortoXpres: %s") % ortoxpres_infrared_layer_name, ortoxpres_url, [ortoxpres_infrared_layer_id], [""], "image/jpeg", 25831, "referer=ICGC&bgcolor=0xFFFFFF", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png"))
                    ] if ortoxpres_infrared_list else []) + [
                ] + ([(self.tr("Infrared superexpedited orthophoto %s (rectification without corrections)") % ortosuperexp_infrared_year,
                    lambda:self.layers.add_wms_layer(self.tr("orthoSuperExpedited: %s") % ortosuperexp_infrared_layer_name, ortosuperexp_url, [ortosuperexp_infrared_layer_id], [""], "image/png", 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png"))
                    ] if ortosuperexp_infrared_list else []) + [
                (self.tr("Infrared orthophoto"),
                    lambda:self.layers.add_wms_layer(self.tr("Infrared orthophoto"), "http://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["ortoi5m"], ["default"], "image/jpeg", 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png")),
                (self.tr("Infrared orthophoto (temporal serie)"),
                    lambda:self.layers.add_wms_t_layer(self.tr("[TS] Infrared orthophoto"), historic_ortho_wms_url, ortho_infrared_current_time, "default", "image/jpeg", ortho_infrared_time_series_list, 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png")),
                (self.tr("Satellite infrared orthophoto (temporal serie)"),
                    lambda:self.layers.add_wms_t_layer(self.tr("[TS] Satellite infared orthophoto"), "http://geoserveis.icgc.cat/icgc_sentinel2/wms/service", "sen2irc", "default", "image/jpeg", None, 25831, "referer=ICGC&bgcolor=0x000000", group_name, only_one_map_on_group=False, set_current=True),
                    QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png")),
                "---",
                (self.tr("Delete background maps"),
                    lambda:self.legend.empty_group_by_name(group_name),
                    QIcon(":/lib/qlib3/base/images/wms_remove.png"),
                    True, False, "delete_background")
                ]),
            (self.tr("Time series"),
                lambda:self.tools.toggle_time_series_dialog(self.iface.mapCanvas().currentLayer(), self.tr("Time series"), self.tr("Selected: ")) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                QIcon(":/lib/qlib3/base/images/time.png"),
                False, True, "time_series"),
            (self.tr("Download tool"), self.disable_download_global_check, QIcon(":/plugins/openicgc/images/download_area.png"), True, True, "download",
                download_vector_submenu + ["---"] + download_raster_submenu + [
                "---",
                (self.tr("Select download folder"), self.set_download_folder, QIcon(":/lib/qlib3/base/images/download_folder.png"), True, False, "select_download_folder"),
                (self.tr("Open download folder"), self.open_download_folder, style.standardIcon(QStyle.SP_DirIcon), True, False, "open_download_folder"),
                ]),
            (self.tr("Paint styles for selected layers"), None, QIcon(":/lib/qlib3/base/images/style.png"), [
                (self.tr("Transparence"),
                    lambda:self.tools.show_transparency_dialog(self.tr("Transparence"), self.iface.mapCanvas().currentLayer()) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None,
                    QIcon(":/lib/qlib3/base/images/transparency.png")),
                (self.tr("Desaturate raster layer"),
                    lambda:self.layers.set_saturation(self.iface.mapCanvas().currentLayer(), -100, True) if type(self.iface.mapCanvas().currentLayer()) is QgsRasterLayer else None,
                    QIcon(":/lib/qlib3/base/images/desaturate.png")),
                (self.tr("Add height highlighting"),
                    lambda _dummy, dtm_url=height_highlighting_url:self.add_height_highlighting_layer(self.tr("Height highlighting"), dtm_url, style_file="ressaltat_alçades.qml", group_name=group_name),
                    QIcon(":/lib/qlib3/base/images/cat_shadows.png"), height_highlighting_url),
                "---",
                (self.tr("Change DB/geoPackage style"),
                    lambda:self.tools.show_db_styles_dialog(self.tr("Change DB/geoPackage style")),
                    QIcon(":/lib/qlib3/base/images/style.png"),
                    True, False, "geopackage_style"),
            ]),
            "---",
            (self.tr("Help"), self.show_help, QIcon(":/lib/qlib3/base/images/help.png"), [
                (self.tr("About Open ICGC"), self.show_about, QIcon(":/plugins/openicgc/icon.png")),
                (self.tr("What's new"), self.show_changelog, QIcon(":/lib/qlib3/base/images/new.png")),
                (self.tr("Help"), self.show_help, QIcon(":/lib/qlib3/base/images/help.png")),
                "---",
                (self.tr("Available products list"), self.show_available_products, style.standardIcon(QStyle.SP_FileDialogDetailedView)),
                "---",
                (self.tr("QGIS plugin repository"), lambda checked:self.show_help_file("plugin_qgis"), QIcon(":/lib/qlib3/base/images/plugin.png")),
                (self.tr("Software Repository"), lambda checked:self.show_help_file("plugin_github"), QIcon(":/lib/qlib3/base/images/git.png")),
                (self.tr("Report an issue"), lambda checked:self.show_help_file("plugin_issues"), QIcon(":/lib/qlib3/base/images/bug.png")),
                (self.tr("Send us an email"), lambda checked:self.show_help_file("send_email"), QIcon(":/lib/qlib3/base/images/send_email.png")),
                ]),
            ] + ([] if not new_qgis_plugin_version else [
                self.tr("Update\n available: v%s") % new_qgis_plugin_version,
                (self.tr("Download plugin"), lambda _dummy,v=new_qgis_plugin_version:self.download_plugin_update(v, UpdateType.plugin_manager), QIcon(":/lib/qlib3/base/images/new.png")), #style.standardIcon(QStyle.SP_BrowserReload)),
            ]) + ([] if not new_icgc_plugin_version else [
                self.tr("Update\n available: v%s") % new_icgc_plugin_version,
                (self.tr("Download plugin"), lambda _dummy,v=new_icgc_plugin_version:self.download_plugin_update(v, UpdateType.icgc_web), QIcon(":/lib/qlib3/base/images/new_icgc.png")), #style.standardIcon(QStyle.SP_BrowserReload)),
            ]) + ([] if qgis_version_ok else [
                self.tr("Warning:"),
                (self.tr("QGIS version warnings"), self.show_qgis_version_warnings, style.standardIcon(QStyle.SP_MessageBoxWarning)),
            ]))

        # Add plugin reload button (debug purpose)
        if debug:
            self.gui.add_to_toolbar(self.toolbar, [
                "---",
                (self.tr("Reload Open ICGC"), self.reload_plugin, QIcon(":/lib/qlib3/base/images/python.png")),
                ])

        # Get a reference to any actions
        self.download_action = self.gui.find_action("download")
        self.time_series_action = self.gui.find_action("time_series")
        self.geopackage_style = self.gui.find_action("geopackage_style")

    def get_download_menu(self, fme_services_list, raster_not_vector=None, nested_download_submenu=True):
        """ Create download submenu structure list """
        # Filter data type if required
        if raster_not_vector is not None:
            fme_services_list = [(id, name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple) for id, name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple in fme_services_list if self.is_raster_file(filename) == raster_not_vector]

        # Define text labels
        common_label = self.tr("Download %s")
        vector_label = self.tr("Download %s vectorial data")
        vector_file_label = vector_label + " (%s)"
        raster_label = self.tr("Download %s raster data")
        raster_file_label = raster_label + " (%s)"

        # Prepare nested download submenu
        if nested_download_submenu:
            # Add a end null entry
            fme_extra_services_list = fme_services_list + [(None, None, None, None, None, None, None, None)]
            download_submenu = []
            product_submenu = []
            # Create menu with a submenu for every product prefix
            for i, (id, name, min_side, max_query_area, download_list, filename, url_pattern, url_ref_or_wms_tuple) in enumerate(fme_extra_services_list):
                prefix_id = id[:2] if id else None
                previous_prefix_id = fme_extra_services_list[i-1][0][:2] if i > 0 else id[:2]
                if previous_prefix_id != prefix_id:
                    if len(product_submenu) == 1:
                        # Add single menu entry
                        download_submenu.append(product_submenu[0])
                    else:
                        # Find group product common prefix
                        previous_name1 = fme_extra_services_list[i-1][1]
                        previous_name2 = fme_extra_services_list[i-2][1]
                        diff_list = [pos for pos in range(min(len(previous_name1), len(previous_name2))) if previous_name1[pos] != previous_name2[pos]]
                        pos = diff_list[0]
                        previous_name = previous_name1[:pos].replace("1:", "").strip()
                        # Add submenu entry
                        download_submenu.append(
                            ((common_label if raster_not_vector is None else raster_label if raster_not_vector else vector_label) % previous_name,
                            None,
                            QIcon(":/lib/qlib3/base/images/%s" % self.FME_ICON_DICT.get(previous_prefix_id, None)),
                            product_submenu))
                    product_submenu = []
                if id:
                    # Add entry to temporal product submenu
                    vectorial_not_raster = not self.is_raster_file(filename)
                    product_submenu.append((
                        (vector_file_label if vectorial_not_raster else raster_file_label) % (name, os.path.splitext(filename)[1][1:]),
                        (lambda _dummy, id=id, name=name, min_side=min_side, max_query_area=max_query_area, download_list=download_list, filename=filename, url_ref_or_wms_tuple=url_ref_or_wms_tuple : self.enable_download_subscene(id, name, min_side, max_query_area, download_list, filename, url_ref_or_wms_tuple), self.pair_download_checks),
                        QIcon(":/lib/qlib3/base/images/%s" % self.FME_ICON_DICT.get(prefix_id, None)),
                        True, True, id # Indiquem: actiu, checkable i un id d'acció
                        ))

        # Prepare "all in one" download submenu
        else:
            fme_extra_services_list = []
            # Add separators on change product prefix
            for i, (id, name, min_side, max_query_area, filename, url_pattern, url_ref_or_wms_tuple) in enumerate(fme_services_list): # 7 params
                if id[:2] != fme_services_list[max(0, i-1)][0][:2]: # If change 2 first characters the inject a separator
                    fme_extra_services_list.append((None, None, None, None, None, None, None, None)) # 7 + 1 (vectorial_not_raster)
                vectorial_not_raster = not self.is_raster_file(filename)
                fme_extra_services_list.append((id, name, min_side, max_query_area, filename, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple)) # 8 params
            # Create download menu
            download_submenu = [
                ((vector_file_label if vectorial_not_raster else raster_file_layer) % (name, os.path.splitext(filename)[1][1:]),
                    (lambda _dummy, id=id, name=name, min_side=min_side, max_query_area=max_query_area, download_list=download_list, filename=filename, url_ref_or_wms_tuple=url_ref_or_wms_tuple : self.enable_download_subscene(id, name, min_side, max_query_area, download_list, filename, url_ref_or_wms_tuple), self.pair_download_checks),
                    QIcon(":/lib/qlib3/base/images/%s" % self.FME_ICON_DICT.get(id[:2], None)),
                    True, True, id # Indiquem: actiu, checkable i un id d'acció
                ) if id else "---" for id, name, min_side, max_query_area, filename, vectorial_not_raster, url_pattern, url_ref_or_wms_tuple in fme_extra_services_list
                ]

        return download_submenu


    ###########################################################################
    # Signals

    def on_change_current_layer(self, layer):
        """ Enable disable time series & geopackage style options according to the selected layer """
        is_wms_t = layer is not None and self.layers.is_wms_t_layer(layer)
        if self.time_series_action:
            self.time_series_action.setEnabled(is_wms_t)
            self.time_series_action.setChecked(self.tools.time_series_dialog is not None and self.tools.time_series_dialog.isVisible())

    def pair_download_checks(self, status):
        """ Synchronize the check of the button associated with Download button """
        if self.download_action:
            self.download_action.setChecked(status)

    def disable_download_global_check(self):
        """ Undo the change on button state we make when clicking on the Download button """
        if self.download_action:
            self.download_action.setChecked(not self.download_action.isChecked())


    ###########################################################################
    # Functionalities

    def run(self, checked): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Basic plugin call, which reads the text of the combobox and the search for the different web services available """
        self.find(self.combobox.currentText())

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
            print("")
        else:
            # We get point coordinates
            x, y, epsg = self.geofinder_dialog.get_point()
            if not x or not y:
                print("Error, no coordinates found")
                QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"),
                    self.tr("Error, location without coordinates"))
                return
            # We resituate the map (implemented in parent PluginBase)
            self.set_map_point(x, y, epsg)
            print("")

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

    def enable_download_subscene(self, data_type, name, min_side, max_download_area, download_list, filename, url_ref_or_wms_tuple):
        """ Enable subscene tool """
        #print("Enable tool", data_type, min_side, max_download_area, filename, url_ref_or_wms_tuple)

        # Uncheck previous associated action
        old_action = self.tool_subscene.action()
        if old_action:
            old_action.setChecked(False)
        # Get action associated to data_type
        action = self.gui.find_action(data_type)

        # Check EPSG warning
        if self.project.get_epsg() != "25831":
            if QMessageBox.warning(self.iface.mainWindow(), self.tr("EPSG warning"), \
                self.tr("ICGC products are generated in EPSG 25831, loading them into a project with EPSG %s could cause display problems, download problems, or increased load time.\n\nDo you want change the project coordinate system to EPSG 25831?") % self.project.get_epsg(), \
                #"Els productes ICGC estan generats en EPSG 25831, carregar-los en un projecte amb EPSG %s podria provocar problemes de visualització, descàrrega o augment del temps de càrrega.\n\nVols canviar el sistema de coordenades del projecte a EPSG 25831?"
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self.project.set_epsg(25831)

        # Download type selection
        download_descriptions_list = [description for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST]
        available_download_descriptions_list = [description for id, description, operation_code in self.FME_DOWNLOADTYPE_LIST if operation_code in download_list]
        download_description, ok_pressed = QInputDialog.getItem(None, self.tr("Download tool"),
            self.tr("Select the type of download and then use the download tool\nto mark a point or area of interest\n\nDownload type:") +
                    " (%s)" % data_type,
            available_download_descriptions_list, 0, editable=False)
        if not ok_pressed:
            action.setChecked(False)
            self.gui.enable_tool(None)
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
            self.iface.messageBar().pushMessage(self.tr("Download tool"), message, level=Qgis.Info, duration=5)

        # Changes icon and tooltip of download button
        self.gui.set_item_icon("download",
            QIcon(":/plugins/openicgc/images/download_%s.png" % self.download_type.replace("dt_", "")),
            "%s %s (%s)" % (self.tr("Download tool"), download_description, name))

        # Disable all reference layers
        self.disable_ref_layers()
        # Load reference map layer
        if url_ref_or_wms_tuple:
            self.load_ref_layer(url_ref_or_wms_tuple, name)

        # Configure new option to download
        self.tool_subscene.set_callback(lambda rect, data_type=data_type, min_side=min_side, max_download_area=max_download_area, download_operation_code=download_operation_code, filename=filename: self.download_map_area(rect, data_type, min_side, max_download_area, download_operation_code, filename))
        self.tool_subscene.set_max_download_area(max_download_area)
        self.tool_subscene.set_min_side(min_side)
        self.tool_subscene.set_mode(self.download_type == 'dt_area')
        # Configure new download action (for auto manage check/uncheck action button)
        self.tool_subscene.setAction(action)

        if self.download_type in ['dt_cat', 'dt_all']:
            # Force download on download types "cat" and "all"
            self.tool_subscene.subscene()
            # Disable tool
            action.setChecked(False)
            self.gui.enable_tool(None)
        else:
            # Enable tool
            self.gui.enable_tool(self.tool_subscene)

    def disable_ref_layers(self):
        """ Disable all reference layers """
        group_name = self.tr("Background maps")
        ref_pattern = self.tr("Reference %s")

        group = self.legend.get_group_by_name(group_name)
        if group:
            for layer_tree in group.children():
                if layer_tree.name().startswith(ref_pattern % ""):
                    self.layers.set_visible(layer_tree.layer(), False)

    def load_ref_layer(self, url_ref_or_wfs_or_wms_tuple, name):
        """ Load a reference layer in WMS, WFS or HTTP file format """
        # Load reference layer
        group_name = self.tr("Background maps")
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
                layer = self.layers.add_wms_layer(layer_name, wms_url, [wms_layer], wms_style, wms_format,
                    None, "referer=ICGC&bgcolor=0x000000", group_name, 0, only_one_visible_map_on_group=False)
            elif len(url_ref_or_wfs_or_wms_tuple) == 3: # Load WFS
                wfs_url, wfs_layer, style_file = url_ref_or_wfs_or_wms_tuple
                # Load WFS layer from URL
                layer = self.layers.add_wfs_layer(layer_name, wfs_url, [wfs_layer],
                    extra_tags="referer=ICGC", group_name=group_name, group_pos=0, style_file=style_file, only_one_visible_map_on_group=False)
            elif len(url_ref_or_wfs_or_wms_tuple) == 2: # Load HTTP
                url_ref, style_file = url_ref_or_wfs_or_wms_tuple
                is_raster = self.is_raster_file(url_ref)
                if is_raster:
                    # Load raster layer from URL
                    layer = self.layers.add_raster_layer(layer_name, url_ref, group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
                else:
                    # Load vector layer from URL
                    layer = self.layers.add_vector_layer(layer_name, url_ref, group_name, 0, transparency=70, style_file=style_file, only_one_visible_map_on_group=False)
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

    def download_map_area(self, rect, data_type, min_side, max_download_area, download_operation_code, local_filename):
        """ Download a FME server data area (limited to max_download_area) """

        # Check selection type
        is_point = rect.isEmpty()
        is_area = not is_point
        title = self.tr("Download map area") if is_area else self.tr("Download point")

        # Check download file type
        filename, ext = os.path.splitext(local_filename)
        is_compressed = self.is_compressed_extension(ext)
        is_raster = self.is_raster_extension(ext)

        # Validate download path
        download_folder = self.get_download_folder()
        if not download_folder:
            return

        # Check CS and transform
        if self.project.get_epsg() != '25831':
            transformation = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(self.project.get_epsg(True)),
                QgsCoordinateReferenceSystem("EPSG:25831"),
                QgsProject.instance())
            ##print("Transformation rectangle from %s to 25831\n%s" % (self.project.get_epsg(), rect))
            rect = transformation.transformBoundingBox(rect)
            ##print("Rectangle %s" % (rect))

        # Check area limit
        if is_area:
            if min_side and (rect.width() < min_side or rect.height() < min_side):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Minimum download rect side not reached (%d m)") % (min_side))
                return
            if max_download_area and (rect.area() > max_download_area):
                QMessageBox.warning(self.iface.mainWindow(), title,
                    self.tr("Maximum download area reached (%d m%s)") % (max_download_area, self.SQUARE_CHAR))
                return

        # If download type is area ensure that selection is area
        if self.download_type == "dt_area" and is_point:
            rect = rect.buffered(50)

        # Show information about download
        if self.download_type == "dt_area":
            confirmation_text = self.tr("Data type:\n   %s (%s)\nRectangle:\n   %.2f, %.2f %.2f, %.2f\nArea:\n   %d m%s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, ("raster" if is_raster else "vector"), rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum(), rect.area(), self.SQUARE_CHAR, download_folder, ext[1:])
        elif self.download_type == "dt_municipalities":
            # Find municipality on GeoFinder
            found_dict_list = self.find_point_secure(rect.xMinimum(), rect.yMaximum(), 25831)
            municipality = found_dict_list[0]['nomMunicipi'] if found_dict_list else ""
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f\nMunicipality:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, ("raster" if is_raster else "vector"), rect.xMinimum(), rect.yMaximum(), municipality, download_folder, ext[1:])
        elif self.download_type == "dt_counties":
            # Find county on GeoFinder
            found_dict_list = self.find_point_secure(rect.xMinimum(), rect.yMaximum(), 25831)
            county = found_dict_list[0]['nomComarca'] if found_dict_list else ""
            confirmation_text = self.tr("Data type:\n   %s (%s)\nPoint:\n   %.2f, %.2f\nCounty:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, ("raster" if is_raster else "vector"), rect.xMinimum(), rect.yMaximum(), county, download_folder, ext[1:])
        else:
            zone = self.tr("Catalonia") if self.download_type == "dt_cat" else self.tr("Available data")
            confirmation_text = self.tr("Data type:\n   %s (%s)\nZone:\n   %s\n\nDownload folder:\n   %s\nFilename (%s):") % (data_type, ("raster" if is_raster else "vector"), zone, download_folder, ext[1:])

        # User confirmation
        filename, ok_pressed = QInputDialog.getText(None, title, confirmation_text, QLineEdit.Normal, filename)
        if not ok_pressed or not local_filename:
            return
        local_filename = "%s_%s%s" % (filename, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"), ext)

        # Get URL with FME action
        url = get_clip_data_url(data_type, rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum(), download_operation_code)
        ##print("Download URL: %s" % url)
        if not url:
            print(self.tr("Error, can't find product as available to download") % data_type)
            return

        # Load layer
        group_name = self.tr("Download")
        try:
            if is_compressed:
                # We suppose that compressed file contains a QLR file
                if not self.layers.add_remote_layer_definition_file(url, local_filename, group_name=group_name, group_pos=0):
                    # If can't load QLR, we suppose that compressed file contains Shapefiles
                    self.layers.add_vector_files([os.path.join(download_folder, local_filename)], group_name=group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.regex_styles_list)
            elif is_raster:
                self.layers.add_remote_raster_file(url, local_filename, group_name=group_name, group_pos=0, only_one_visible_map_on_group=False, color_default_expansion=data_type.lower().startswith("met"))
            else:
                self.layers.add_remote_vector_file(url, local_filename, group_name=group_name, group_pos=0, only_one_visible_map_on_group=False, regex_styles_list=self.regex_styles_list)
        except Exception as e:
            error = str(e)
            # If server don't return error message (replied empty), we return a generic error
            if error.endswith("replied: "):
                error = self.tr("Error downloading file or selection is out of reference area")
            QMessageBox.warning(self.iface.mainWindow(), title, error)

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
        layer = self.layers.add_raster_layer(layer_name, "/vsicurl/%s" % dtm_url, style_file=style_file, group_name=group_name, only_one_visible_map_on_group=False),
        # Show colors warning
        QMessageBox.information(self.iface.mainWindow(), self.tr("Height highlighting"),
            self.tr('You can modify the brightness of the "Height hightlghting" layer to adjust the display to your background layer'))
        return layer

    def show_available_products(self):
        """ Show a dialog with a list of all donwloads and linkable products"""
        # Read download menu an delete prefix
        download_prefix_length = len(self.tr("Download %s") % "")
        download_list = [name[download_prefix_length:] for name in self.get_menu_names("download", ["open_download_folder", "select_download_folder"])]
        # Read background maps menu
        link_list = self.get_menu_names("background_maps", ["delete_background"])
        # Generates a product info text
        available_products_text = self.tr("Linkable products:\n- %s\n\nDownloadable products:\n- %s") % ("\n- ".join(link_list), "\n- ".join(download_list))
        LogInfoDialog(available_products_text, self.tr("Available products list"), LogInfoDialog.mode_info, width=600)

    def get_menu_names(self, action_name, exclude_list):
        """ Recover name of submenus options from a menu """
        names_list = []
        for action in self.gui.find_action(action_name).menu().actions():
            subactions_list = action.menu().actions() if action.menu() else [action]
            for subaction in subactions_list:
                if subaction.text() and subaction.objectName() not in exclude_list:
                    names_list.append(subaction.text())
        return names_list

    def check_qgis_version(self, version=31004):
        """ Checks QGIS old versions with plugin problems """
        return Qgis.QGIS_VERSION_INT >= version

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
