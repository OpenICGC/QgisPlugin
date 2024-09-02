# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with the implementation PluginBase, which creates an intermediate layer
between the plugin and the pyQGIS API that adds functionalities for the
management of the graphical interface, transformation of coordinates, project
file templates, access to plugin metadata, translation, debug and add
additional pre-programmed tools

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os
import sys
import glob
import re
import random
import console
import datetime
import codecs
import fnmatch
import pathlib
import urllib
import urllib.request
import urllib.parse
import socket
import configparser
import subprocess
import base64
import zipfile
import io
import tempfile
import shutil
from xml.etree import ElementTree
from importlib import reload
try:
    from osgeo import ogr, osr
except:
    import ogr, osr
import unittest
reload(unittest)

from PyQt5.QtCore import Qt, QSize, QSettings, QObject, QTranslator, qVersion, QCoreApplication
from PyQt5.QtCore import QVariant, QDateTime, QDate, QLocale, QUrl
from PyQt5.QtWidgets import QApplication, QAction, QToolBar, QLabel, QMessageBox, QMenu, QToolButton
from PyQt5.QtWidgets import QFileDialog, QWidgetAction, QDockWidget, QShortcut, QTableView
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QDialog, QSizePolicy
from PyQt5.QtGui import QPainter, QCursor, QIcon, QColor, QKeySequence, QDesktopServices, QFontDatabase
from PyQt5.QtXml import QDomDocument

from qgis.gui import QgsProjectionSelectionDialog, QgsAttributeDialog
from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsCoordinateTransform, QgsProject, QgsWkbTypes, QgsRectangle, QgsPointXY
from qgis.core import QgsRasterMinMaxOrigin, QgsDataSourceUri, QgsHueSaturationFilter, QgsRasterLayer, QgsVectorLayer, QgsLayerTreeGroup
from qgis.core import QgsLayerTreeLayer, QgsLayerDefinition, QgsReadWriteContext, QgsLayoutItemMap, QgsContrastEnhancement
from qgis.core import QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsRendererRange, QgsGraduatedSymbolRenderer, QgsRenderContext, QgsRendererRangeLabelFormat
from qgis.core import QgsSymbol, QgsMarkerSymbol, QgsFillSymbol, QgsBilinearRasterResampler, QgsCubicRasterResampler, QgsSimpleLineSymbolLayer
from qgis.core import QgsEditorWidgetSetup, QgsPrintLayout, QgsSpatialIndex, QgsFeatureRequest, QgsMapLayer, QgsField, QgsVectorFileWriter
from qgis.core import QgsLayoutExporter, QgsFields, Qgis, QgsExpression
from qgis.utils import plugins, reloadPlugin, showPluginHelp

from . import resources_rc

from . import progressdialog
reload(progressdialog)
from .progressdialog import ProgressDialog

from . import loginfodialog
reload(loginfodialog)
from .loginfodialog import LogInfoDialog

from . import transparencydialog
reload(transparencydialog)
from .transparencydialog import TransparencyDialog

from . import timeseriesdialog
reload(timeseriesdialog)
from .timeseriesdialog import TimeSeriesDialog

from . import anaglyphdialog
reload(anaglyphdialog)
from .anaglyphdialog import AnaglyphDialog

from . import stylesdialog
reload(stylesdialog)
from .stylesdialog import StylesDialog

from . import aboutdialog
reload(aboutdialog)
from .aboutdialog import AboutDialog

from . import download
reload(download)
from .download import DownloadManager

from . import log
reload(log)
from .log import PluginLogger


###############################################################################
# Overwrite QGIS function than it don't works in QGIS3.18/windows
def showPluginHelp(packageName: str = None, filename: str = "index", section: str = ""):
    """Open help in the user's html browser. The help file should be named index-ll_CC.html or index-ll.html or index.html.

    :param str packageName: name of package folder, if None it's using the current file package. Defaults to None. Optional.
    :param str filename: name of file to open. It can be a path like 'doc/index' for example. Defaults to 'index'.
    :param str section: URL path to open. Defaults to empty string.
    """
    try:
        source = ""
        if packageName is None:
            import inspect

            source = inspect.currentframe().f_back.f_code.co_filename
        else:
            source = sys.modules[packageName].__file__
    except:
        return
    path = os.path.dirname(source)
    locale = str(QLocale().name())
    helpfile = os.path.join(path, filename + "-" + locale + ".html")
    if not os.path.exists(helpfile):
        helpfile = os.path.join(path, filename + "-" + locale.split("_")[0] + ".html")
    if not os.path.exists(helpfile):
        helpfile = os.path.join(path, filename + "-en.html")
    if not os.path.exists(helpfile):
        helpfile = os.path.join(path, filename + "-en_US.html")
    if not os.path.exists(helpfile):
        helpfile = os.path.join(path, filename + ".html")
    if os.path.exists(helpfile):
        #url = "file://" + helpfile
        #if section != "":
        #    url = url + "#" + section
        #QDesktopServices.openUrl(QUrl(url))
        url = QUrl.fromLocalFile(helpfile)
        if section != "":
            url.setFragment(section)
        QDesktopServices.openUrl(url)
###############################################################################


class WaitCursor:
    """ Classe per mostrar el cursor d'espera en un context 
        ---
        Class to display the wait cursor in a given context """
    def __enter__(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

    def __exit__(self, type, value, traceback):
        QApplication.restoreOverrideCursor()


class GuiBase(object):
    """ Classe per manegar les operacions GUI
        ---
        Class to manage GUI operations
        """
    class MenuItemWidget(QWidget):
        """ Classe per crear entrades de menú amb botons
            ---
            SubClass to creates menu items with buttons 
            """
        def __init__(self, text, icon, buttons_list, parent, icon_size=20, font_size=9):
            """ Crea una entrada de menú amb text, icona i botons extra
                buttons_list = [(name, callback, icon), ...]
                ---
                Creates a menu item with text, icon and extra buttons
                buttons_list = [(name, callback, icon), ...]
                """
            super().__init__(parent)
        
            self.label_icon = QLabel()
            self.label_icon.setPixmap(icon.pixmap(QSize(icon_size, icon_size)))
            self.label_icon.setFixedSize(QSize(icon_size, icon_size))
        
            self.label_text = QLabel(text)
        
            self.push_button_list = []
            for button_text, button_callback, button_icon in buttons_list:
                push_button = QPushButton()
                push_button.setFlat(True)
                push_button.setToolTip(button_text)
                if button_icon:
                    push_button.setIcon(button_icon)
                push_button.setFixedSize(QSize(icon_size, icon_size))
                if button_callback:
                    push_button.released.connect(button_callback)
                self.push_button_list.append(push_button)

            self.layout = QHBoxLayout(self)
            self.layout.addWidget(self.label_icon)
            self.layout.addWidget(self.label_text)
            for push_button in self.push_button_list:
                self.layout.addWidget(push_button)
            self.layout.setContentsMargins(7, 3, 7, 3)
            self.layout.setSpacing(6)

            self.container = QWidget()
            self.container.setLayout(self.layout)
        
            self.container_layout = QHBoxLayout(self)
            self.container_layout.setContentsMargins(0, 0, 0, 0)
            self.container_layout.addWidget(self.container)
        
            self.setLayout(self.container_layout)
            self.setStyleSheet(
                #"QWidget:hover {background: palette(highlight); color: white;} " \
                "QWidget:hover {background: palette(highlight);} " \
                "QLabel {font-size: %dpt;}" \
                % font_size)

    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare i a l'iface.
            Creació d'estructures per manager la GUI del plugin.
            ---
            Initialization of member variables pointing to parent and iface.
            Creating structures to manage the GUI of the plugin
            """
        self.parent = parent
        self.iface = parent.iface

        # Inicialitzem les llistes d'elements de la GUI que gestionem
        self.toolbars = []
        self.menus = []
        self.disable_unmapped_gui = False # Desactiva les opcions de menú / toolbar que no tinguin callback o submenús
        self.shortcuts = []
        self.action_plugin = None # Entrada al menú de plugins
        self.actions = [] # Parelles (menu, acció)
        self.widget_actions_set = set([]) # Serveix per evitar controls repetits en les toolbars/menús si no s'anul·len...

    def remove(self):
        """ Neteja d'estructures GUI del plugin
            ---
            Cleaning of GUI structures of the plugin
            """
        # Desactiva les toolbar custom
        self.enable_tool(None)
        # Esborra els accions de menus i toolbars
        for control, action in self.actions:
            control.removeAction(action)
        self.actions = []
        # Esborra les entrades del plugin
        if self.action_plugin:
            self.iface.removePluginMenu(self.action_plugin.text(), self.action_plugin)
            self.iface.removeToolBarIcon(self.action_plugin)
        # Esborrem els shortcuts
        for description, keyseq, shortcut in self.shortcuts:
            if shortcut:
                shortcut.setEnabled(False)
        self.shortcuts = []
        # Els menús s'esborren sols quan no tenen actions
        self.menus = []
        # Esborra les toolbars (canviem el títol per no trobar-les metres s'esborren retardadament...)
        for toolbar in self.toolbars:
            toolbar.setWindowTitle("[DELETE] %s" % toolbar.windowTitle())
            toolbar.deleteLater()
        self.toolbars = []

    ###########################################################################
    # Plugins menú
    #
    def configure_plugin(self, name=None, callback=None, icon=None, \
        add_to_plugins_toolbar=True, add_to_plugins_menu=True, standard_menu_or_button_menu=True):
        """ Crea una entrada en el menú de plugins, amb una funcionalitat i icona associada
            Per defecte utilitza el nom del plugin, icona i obre l'about
            Retorna QAction que executa el callback
            ---
            Create an entry in the plugins menu, with a functionality and associated icon
            Default uses plugin name, icon and open about dialog
            Returns QAction with triggered callback
            """
        if not name:
            name = self.parent.metadata.get_name()
        if not callback:
            callback = self.parent.show_about
        if not icon:
            icon = self.parent.metadata.get_icon()

        self.action_plugin = QAction(icon, name, self.iface.mainWindow())
        self.action_plugin.triggered.connect(callback)
        
        if add_to_plugins_toolbar:
            self.iface.addToolBarIcon(self.action_plugin) # Afegeix l'acció com un botó a la toolbar general de complements
        if add_to_plugins_menu:
            if standard_menu_or_button_menu:
                self.iface.addPluginToMenu(name, self.action_plugin) # Afegeix l'acció com un submenú al menú de complements
            else:
                self.iface.pluginMenu().addAction(self.action_plugin) # Afegeix l'acció com un botó al menú de complements
        return self.action_plugin

    ###########################################################################
    # Toolbars & Menús
    #
    def configure_GUI(self, title, names_callbacks, parent_menu=None, parent_menu_pos=None, menu_icon=None, toolbar_droplist_name=None, toolbar_droplist_icon=None, position=None, append_if_exist=True, add_separator=True):
        """ Crea menús i toolbars equivalents simultànicament. Veure funció: __parse_entry
            Atenció: els elements de tipus "control" només es poden utilitzar un cop, per tant es crearàn només a la toolbar i no al menú
            ---
            Create equivalent menus and toolbars simultaneously. See function: __parse_entry
            Warning: elements of "control" type only can be used one time, it will be created only on toolbar and not on menu
            """
        # Creem la toolbar
        toolbar = self.configure_toolbar(title, names_callbacks, toolbar_droplist_name, toolbar_droplist_icon, position, add_separator)
        # Creem el menú
        menu = self.configure_menu(title, names_callbacks, parent_menu, parent_menu_pos, menu_icon, position, append_if_exist, add_separator)
        return menu, toolbar

    def insert_at_GUI(self, menu_or_toolbar, position, names_callbacks):
        """ Afegeix nous items a un menu o toolbar. Veure funció: __parse_entry
            ---
            Add new items to a menu or toolbar. See function: __parse_entry
            """
        # Determinem on cal insertar els items al menú
        ref_action = None
        if position != None and position < len(menu_or_toolbar.actions()):
            ref_action = menu_or_toolbar.actions()[position]

        for entry in names_callbacks:
            # Ignorem les entrades a None
            if entry is None:
                continue
            # Recollim les dades de usuari
            eseparator, elabel, eaction, econtrol, name, callback, toggle_callback, icon, enabled, checkable, id, tooltip, subentries_list, subentries_as_buttons = self.__parse_entry(entry)

            # Creem el menu o toolbar
            if eseparator != None:
                # Ens passen un separador
                if ref_action:
                    action = menu_or_toolbar.insertSeparator(ref_action)
                else:
                    action = menu_or_toolbar.addSeparator()
            elif elabel != None:
                # Ens passen només un text
                label = QLabel(" " + elabel + " ")
                if type(menu_or_toolbar) == QToolBar:
                    if ref_action:
                        action = menu_or_toolbar.insertWidget(ref_action, label)
                    else:
                        action = menu_or_toolbar.addWidget(label)
                elif type(menu_or_toolbar) == QMenu:
                    action = QWidgetAction(menu_or_toolbar)
                    action.setDefaultWidget(label)
                    if ref_action:
                        menu_or_toolbar.insertAction(ref_action, action)
                    else:
                        menu_or_toolbar.addAction(action)
            elif eaction != None:
                # Ens passen una acció
                if ref_action:
                    action = menu_or_toolbar.insertAction(ref_action, eaction)
                else:
                    action = menu_or_toolbar.addAction(eaction)
            elif econtrol != None:
                # És passen un control
                # ATENCIÓ, NOMÉS EL PODEM FER SERVIR UN COP, SI NO ANUL·LA ELS DOS!!
                if econtrol in self.widget_actions_set:
                    continue
                self.widget_actions_set.add(econtrol)
                # Inserim el control
                if type(menu_or_toolbar) == QToolBar:
                    if ref_action:
                        action = menu_or_toolbar.insertWidget(ref_action, econtrol)
                    else:
                        action = menu_or_toolbar.addWidget(econtrol)
                elif type(menu_or_toolbar) == QMenu:
                    action = QWidgetAction(menu_or_toolbar)
                    action.setDefaultWidget(econtrol)
                    if ref_action:
                        menu_or_toolbar.insertAction(ref_action, action)
                    else:
                        menu_or_toolbar.addAction(action)
            else:
                # Ens passen una acció "desglossada"
                if icon:
                    action = QAction(icon, name, self.iface.mainWindow())
                else:
                    action = QAction(name, self.iface.mainWindow())
                if id:
                    action.setObjectName(id)
                if callback:
                    action.triggered.connect(callback)
                if toggle_callback:
                    action.toggled.connect(toggle_callback)
                if not subentries_list:
                    # Menú "normal"
                    if ref_action:
                        menu_or_toolbar.insertAction(ref_action, action)
                    else:
                        menu_or_toolbar.addAction(action)
                elif subentries_as_buttons:
                    # Menú amb botons a la dreta
                    # Obtenim tots els botons a generar
                    buttons_list = [(name, callback, icon) \
                        for _eseparator, _elabel, _eaction, _econtrol, name, callback, _toggle_callback, icon, _enabled, _checkable, _id, _tooltip, _subentries_list, _subentries_as_buttons \
                        in [self.__parse_entry(entry) for entry in subentries_list]]
                    # Creem el control d'entrada de menú amb els botons extra
                    menu_item = self.MenuItemWidget(name, icon, buttons_list, menu_or_toolbar)
                    self.widget_actions_set.add(menu_item)
                    # Inserim el control
                    if type(menu_or_toolbar) == QToolBar:
                        if ref_action:
                            action = menu_or_toolbar.insertWidget(ref_action, menu_item)
                        else:
                            action = menu_or_toolbar.addWidget(menu_item)
                    elif type(menu_or_toolbar) == QMenu:
                        action = QWidgetAction(menu_or_toolbar)
                        action.setDefaultWidget(menu_item)
                        if ref_action:
                            menu_or_toolbar.insertAction(ref_action, action)
                        else:
                            menu_or_toolbar.addAction(action)
                    action.triggered.connect(callback)
                else:
                    # Submenú
                    submenu = QMenu()
                    submenu.setToolTipsVisible(True)
                    self.add_to_menu(submenu, subentries_list)
                    # Guardem el submenu (si no, si està buit, dóna problemes afegint-lo a un menú)
                    self.menus.append(submenu)
                    # Depenent de si tenim toolbar o menu pare, fem una cosa o un altre
                    if type(menu_or_toolbar) == QToolBar:
                        toolButton = QToolButton()
                        toolButton.setMenu(submenu)
                        toolButton.setPopupMode(QToolButton.MenuButtonPopup)
                        if checkable:
                            action.setCheckable(True)
                        toolButton.setDefaultAction(action)
                        if ref_action:
                            subaction = menu_or_toolbar.insertWidget(ref_action, toolButton)
                        else:
                            subaction = menu_or_toolbar.addWidget(toolButton)
                    # Depenent de si tenim toolbar o menu pare, fem una cosa o un altre
                    elif type(menu_or_toolbar) == QMenu:
                        action.setMenu(submenu)
                        #submenu.setTitle(name)
                        #if icon:
                        #    submenu.setIcon(icon)
                        if ref_action:
                            subaction = menu_or_toolbar.insertMenu(ref_action, submenu)
                        else:
                            subaction = menu_or_toolbar.addMenu(submenu)
                    if id:
                        subaction.setObjectName(id)
                    if not enabled:
                        subaction.setEnabled(False)
                    if checkable:
                        subaction.setCheckable(True)
                    self.actions.append((menu_or_toolbar, subaction))

            # Activem / desactivem, checkable o no
            if not enabled:
                action.setEnabled(False)
            if checkable:
                action.setCheckable(True)
            if tooltip:
                menu_or_toolbar.setToolTipsVisible(True)
                if type(action) == QWidgetAction and not subentries_as_buttons:
                    action.defaultWidget().defaultAction().setToolTip(tooltip)
                else:
                    action.setToolTip(tooltip)

            #Ens guardem els items de menu o toolbar, si no no apareix...
            self.actions.append((menu_or_toolbar, action))

    def __parse_entry(self, entry):
        """ Tipus de menús /toolbars acceptats, llistes de:
                None o "---" o "" --> separador
                "text" --> Label
                QAction --> Acció amb icona i funció a executar
                Altres_tipus --> Suposem que és un control (combobox, lineedit, ...)
                Tupla:
                    (Nom, [funció | (funció_activació, funció_toggle)], [icona], [enabled], [checkable], [id], [tooltip], [submenu_llista], [submenu_com_botons])
            ---
            Types of accepted menus / toolbars, lists of:
                 None or "---" or "" -> separator
                 "text" -> Label
                 QAction -> Action with icon and function to execute
                 Other_type -> Suppose it is a control (combobox, lineedit, ...)
                 Tuple:
                     (Name, [function | (enable_fuction, toggle_function)], [icon], [enabled], [checkable], [id], [sub-menu], [sub-menu_as_buttons])

            Exemple:
                [
                    "Cercar:", # Label
                    self.combobox, # Control
                    (self.TOOLTIP_TEXT, self.run, QIcon(":/plugins/geofinder/icon.png")), # Button with icon
                    ("GeoFinder reload", self.reload_plugin, QIcon(":/lib/qlib3/base/images/python.png")), # Button with icon
                ]

            Exemple2:
                [
                    ("&Ortofoto color",
                        lambda:self.parent.layers.add_wms_layer("WMS Ortofoto color", "https://geoserveis.icgc.cat/icc_mapesmultibase/utm/wms/service", ["orto"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, None, only_one_map),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5k.png")),
                    ("Ortofoto &infraroja",
                        lambda:self.parent.layers.add_wms_layer("WMS Ortofoto infraroja", "https://geoserveis.icgc.cat/icc_mapesbase/wms/service", ["ortoi5m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, None, only_one_map),
                        QIcon(":/lib/qlib3/base/images/cat_ortho5ki.png")),
                    ("Ortofoto &històrica", None, QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png"), [ # Subnivell
                        ("&Ortofoto 1:5.000 vol americà sèrie B blanc i negre",
                            lambda:self.parent.layers.add_wms_layer("WMS Ortofoto vol americà sèrie B 1:5.000 BN", "https://geoserveis.icgc.cat/icc_ortohistorica/wms/service",  ["ovab5m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, None, only_one_map),
                            QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                        ("&Ortofoto 1:10.000 vol americà sèrie A blanc i negre (1945-1946)",
                            lambda:self.parent.layers.add_wms_layer("WMS Ortofoto vol americà sèrie A 1:10.000 BN", "https://geoserveis.icgc.cat/icc_ortohistorica/wms/service", ["ovaa10m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, None, only_one_map),
                            QIcon(":/lib/qlib3/base/images/cat_ortho5kbw.png")),
                        ]), # Fi de subnivell
                    "---", # Separador
                    ("blablabla", ...)
            """

        ##self.iniConsole()
        separator = None
        label = None
        action = None
        control = None
        name = None
        callback = None
        toggle_callback = None
        icon = None
        enabled = True
        checkable = False
        id = None
        tooltip = None
        subentries_list = None
        subentries_as_buttons = False

        if type(entry) != tuple:
            if entry == None or entry == "---" or entry == "":
                ##print("separator", entry)
                separator = True
            elif type(entry) in [str, unicode]:
                ##print("label", entry)
                label = entry
            elif type(entry) == QAction:
                ##print("label", action)
                action = entry
            else:
                ##print("control", entry)
                control = entry
        else:
            ##print("user")
            name = entry[0]
            if name == "---":
                separator = True
            if len(entry) > 1:
                if type(entry[1]) == tuple:
                    callback, toggle_callback = entry[1]
                else:
                    callback = entry[1]
                if len(entry) > 2:
                    icon = entry[2]
                if len(entry) > 3:
                    if type(entry[3]) == list:
                        subentries_list = entry[3]
                        subentries_as_buttons = entry[4] if len(entry) > 4 else False
                    else:
                        enabled = entry[3]
                        if len(entry) > 4:
                            if type(entry[4]) == list:
                                subentries_list = entry[4]
                                subentries_as_buttons = entry[5] if len(entry) > 5 else False
                            else:
                                checkable = entry[4]
                                if len(entry) > 5:
                                    if type(entry[5]) == list:
                                        subentries_list = entry[5]
                                        subentries_as_buttons = entry[6] if len(entry) > 6 else False
                                    else:
                                        id = entry[5]
                                        if len(entry) > 6:
                                            if type(entry[6]) == list:
                                                subentries_list = entry[6]
                                                subentries_as_buttons = entry[7] if len(entry) > 7 else False
                                            else:
                                                tooltip = entry[6]
                                                if len(entry) > 7:
                                                    if type(entry[7]) == list:
                                                        subentries_list = entry[7]
                                                        subentries_as_buttons = entry[8] if len(entry) > 8 else False
        # Si la icona no és de tipus QIcon, suposem que és un identificador d'icona i intentem carregar-la
        if icon and type(icon) is not QIcon:
            icon = self.get_icon(icon)
        # Si la entrada no té callback (i no és un control) la desactivem
        if self.disable_unmapped_gui and not separator and not label and not action and not control and not callback \
            and not toggle_callback and not subentries_list:
            enabled = False
        return separator, label, action, control, name, callback, toggle_callback, icon, enabled, checkable, id, tooltip, subentries_list, subentries_as_buttons

    def find_action(self, id, actions_list=None):
        """ Cerca una acció a partir del seu objectName
            ---
            Find a action by objectName
            """
        if actions_list == None:
            actions_list = [action for menu_or_toolbar, action in self.actions]
        for action in actions_list:
            if action:
                if action.objectName() == id:
                    return action
                if action.menu():
                   subaction = self.find_action(id, action.menu().actions())
                   if subaction:
                       return subaction
        return None

    def enable_gui_items(self, menu_or_toolbar, items_id_list, enable=True, recursive=True):
        """ Activa una llista d'items pel seu id d'una toolbar
            ---
            Activates toolbars items by id
            """
        actions_count = 0
        for action in menu_or_toolbar.actions():
            if type(action) == QWidgetAction:
                if recursive:
                    self.enable_gui_items(action.defaultWidget().menu(), items_id_list, enable, recursive)
                if action.objectName() in items_id_list:
                    action.defaultWidget().defaultAction().setEnabled(enable)
                    actions_count += 1
            else:
                if action.objectName() in items_id_list:
                    action.setEnabled(enable)
                    actions_count += 1
        return actions_count

    ###########################################################################
    # Menus
    #
    def configure_menu(self, title, names_callbacks, parent_menu=None, parent_menu_pos=None, menu_icon=None, position=None, append_if_exist=True, add_separator=True):
        """ Crea o amplia un menús segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
            Create or expand menus according to the <callbacks> list. See function: __parse_entry
            """
        menu = self.get_menu_by_name(title)

        # Si no tenim menú creem un menu nou
        if not menu or not append_if_exist:
            menu = QMenu()
            menu.setTitle(title)
            if menu_icon:
                menu.menuAction().setIcon(menu_icon)
            # Ens guardem el ménu, si no no apareix...
            self.menus.append(menu)
            # Associem el nou menu com una entrada de la barra de menu principal
            if not parent_menu:
                parent_menu = self.iface.mainWindow().menuBar()
            if parent_menu_pos != None:
                before = parent_menu.actions()[parent_menu_pos]
                action = parent_menu.insertMenu(before, menu)
            else:
                action = parent_menu.addMenu(menu)
            self.actions.append((parent_menu, action))
            # Li associem les seves entrades
            self.add_to_menu(menu, names_callbacks)
        else:
            # Li associem les seves entrades
            if position != None:
                is_separator = len(menu.actions()) == 0 or menu.actions()[0].isSeparator()
                self.insert_at_menu(menu, position, names_callbacks if is_separator or not add_separator else names_callbacks + ["---"])
            else:
                is_separator = len(menu.actions()) == 0 or menu.actions()[-1].isSeparator()
                self.add_to_menu(menu, names_callbacks if is_separator or not add_separator else ["---"] + names_callbacks)

        return menu

    def add_to_menu(self, menu, names_callbacks):
        """ Amplia un menús pel final segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
           Expand a menu for the end according to the <callbacks> list. See function: __parse_entry
           """
        self.insert_at_menu(menu, None, names_callbacks)

    def insert_at_menu(self, menu, position, names_callbacks):
        """ Amplia un menús en la posició indicada segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
            Expand a menu in the position indicated by the <callbacks> list. See function: __parse_entry
            """
        self.insert_at_GUI(menu, position, names_callbacks)

    def clear_menu(self, menu):
        """ Esborra els items d'un menu
            ---
            Clear menu items
            """
        # Desregistrem les accions del menú existents
        self.actions = list(set(self.actions) - set([(menu, action) for action in menu.actions()]))
        # Esborrem els items del menú
        menu.clear()

    def get_menus(self):
        """ Retorna la llista del menus visibles a la GUI
            ---
            Returns the GUI visible menu list
            """
        return [action.menu() for action in self.iface.mainWindow().menuBar().actions()]

    def get_menu_by_name(self, name):
        """ Retorna un objecte menú a partir del seu nom
            ---
            Returns a menu object from its name
            """
        menus = self.get_menus()
        menus_names = [unicode(m.title()) for m in menus]
        if name in menus_names:
            pos = menus_names.index(name)
            return menus[pos]
        else:
            return None

    def enable_menu_items(self, menu, items_id_list, enable=True):
        return self.enable_gui_items(menu, items_id_list, enable)

    def enable_menu_items_by_name(self, menu_name, items_id_list, enable=True):
        """ Activa una llista d'items pel seu id d'una toolbar pel seu nom
            ---
            Activates toolbars items by id and toolbar_name
            """
        menu = self.get_menu_by_name(menu_name)
        if not menu:
            return 0
        return self.enable_menu_items(menu, items_id_list, enable)

    ###########################################################################
    # Toolbars
    #
    def configure_toolbar(self, title, names_callbacks, toolbar_droplist_name=None, toolbar_droplist_icon=None, position=None, add_separator=True):
        """ Crea o amplia una toolbar segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
            Create or expand a toolbar according to the <callbacks> list. See function: __parse_entry
            """
        # Si ens passen una icona de toolbar desplegable, creem un nivell d'anidament a la toolbar
        if toolbar_droplist_icon:
            names_callbacks = [((toolbar_droplist_name if toolbar_droplist_name else title), None, toolbar_droplist_icon, names_callbacks)]

        # Si no existeix la toolbar, la creem i li afegim les entrades
        toolbar = self.get_toolbar_by_name(title)
        if not toolbar:
            toolbar = self.iface.addToolBar(title)
            self.add_to_toolbar(toolbar, names_callbacks)
        else:
            if position != None:
                is_separator = len(toolbar.actions()) == 0 or toolbar.actions()[0].isSeparator()
                self.insert_at_toolbar(toolbar, position, names_callbacks if is_separator or not add_separator else names_callbacks + ["---"])
            else:
                is_separator = len(toolbar.actions()) == 0 or toolbar.actions()[-1].isSeparator()
                self.add_to_toolbar(toolbar, names_callbacks if is_separator or not add_separator else ["---"] + names_callbacks)
        self.toolbars.append(toolbar)
        return toolbar

    def add_to_toolbar(self, toolbar, names_callbacks):
        """ Amplia una toolbar pel final segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
            Extend a toolbar to the end according to the <callbacks> list. See function: __parse_entry
            """
        self.insert_at_toolbar(toolbar, None, names_callbacks)

    def insert_at_toolbar(self, toolbar, position, names_callbacks):
        """ Amplia una toolbar en una posició indicada segons la llista de <callbacks>. Veure funció: __parse_entry
            ---
            Expand a toolbar in a position indicated by the <callbacks> list. See function: __parse_entry
            """
        self.insert_at_GUI(toolbar, position, names_callbacks)

    def get_toolbars(self):
        """ Retorna la llista de toolbars de QGIS
            ---
            Returns the list of QGIS toolbars
            """
        return [t for t in self.iface.mainWindow().children() if type(t) == QToolBar]

    def get_toolbar_by_object_name(self, name):
        """ Retorna un objecte toolbar a partir del seu nom d'objecte
            ---
            Returns a toolbar from its object's name
            """
        toolbars_list = self.get_toolbars()
        toolbars_names = [unicode(t.objectName()) for t in toolbars_list]
        if name in toolbars_names:
            pos = toolbars_names.index(name)
            return toolbars_list[pos]
        else:
            return None

    def get_toolbar_by_name(self, name):
        """ Retorna un objecte toolbar a partir del seu nom
            ---
            Returns a toolbar from its name
            """
        toolbars_list = self.get_toolbars()
        toolbars_names = [unicode(t.windowTitle()) for t in toolbars_list]
        if name in toolbars_names:
            pos = toolbars_names.index(name)
            toolbar = toolbars_list[pos]
            return toolbar
        else:
            return None

    def get_toolbar_action_by_names(self, toolbar_name, item_name, item_pos=0):
        """ Retorna una acció d'una toolbar a partir dels seus noms
            ---
            Returns an action from a toolbar based on its names
            """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return None
        return self.get_toolbar_action_by_action_name(toolbar, item_name, item_pos)

    def get_toolbar_actions(self, toolbar):
        """ Retorna la llista d'accions d'una toolbar
            ---
            Returns the list of actions in a toolbar
            """
        actions_list = []
        for action in toolbar.actions():
            widget = toolbar.widgetForAction(action)
            if widget:
                actions_list += widget.actions() # Botó
                if type(widget) == QToolButton:
                    menu = widget.menu()
                    if menu:
                        actions_list += menu.actions() # Menú
                else:
                    actions_list.append(action) # Separador
        return actions_list

    def get_toolbar_action_by_item_name(self, toolbar, item_name, item_pos=0):
        """ Retorna una acció d'una toolbar a partir del seu nom
            ---
            Returns an action from a toolbar based on its name
            """
        actions_list = self.get_toolbar_actions(toolbar)
        item_actions = [action for action in actions_list if action.text() == item_name]
        if not item_actions:
            return None
        return item_actions[item_pos]

    def get_toolbar_action(self, toolbar, item_pos):
        """ Retorna una acció d'una toolbar a partir de la seva posició
            ---
            Returns an action from a toolbar based on its position
            """
        actions_list = self.get_toolbar_actions(toolbar)
        return actions_list[item_pos]

    def set_item_icon(self, item_id, icon, tooltip_text=None):
        """ Canvia la icona d'una acció partir del seu id
            ---
            Changes an action icon from its id
            """
        action = self.find_action(item_id)
        if not action:
            return False
        if type(action) == QWidgetAction:
            action = action.defaultWidget().defaultAction()
        action.setIcon(icon)
        if tooltip_text is not None:
            action.setToolTip(tooltip_text)

    def set_check_item(self, item_id, check=True):
        """ Xequeja una acció a partir del seu id
            Si check es None, canvia l'estat del check
            ---
            Checks an action from its id
            If check is None, it changes check status
            """
        action = self.find_action(item_id)
        if not action:
            return False
        if type(action) == QWidgetAction:
            action = action.defaultWidget().defaultAction()
        action.setCheckable(True)
        if check is None:
            check = not action.isChecked()
        action.setChecked(check)
        return True

    def set_check_toolbar_item_by_item_name(self, toolbar, item_name, check=True, item_pos=0):
        """ Xequeja una acció d'una toolbar a partir del seu nom
            Si check es None, canvia l'estat del check
            ---
            Checks an action from a toolbar based on its name
            If check is None, it changes check status
            """
        action = self.get_toolbar_action_by_item_name(toolbar, item_name, item_pos)
        if not action:
            return False
        if type(action) == QWidgetAction:
            action = action.defaultWidget().defaultAction()
        action.setCheckable(True)
        if check is None:
            check = not action.isChecked()
        action.setChecked(check)
        return True

    def set_check_toolbar_item_by_names(self, toolbar_name, item_name, check=True, item_pos=0):
        """ Xequeja una acció d'una toolbar a partir dels seus noms
            ---
            Checks an action from a toolbar based on its names
            """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return False
        return self.set_check_toolbar_item_by_item_name(toolbar, item_name, check, item_pos)

    def enable_toolbar_item_by_item_name(self, toolbar, item_name, enable=True, item_pos=0):
        """ Activa una acció d'una toolbar a partir del seu nom
            ---
            Activate an action from a toolbar based on its name
            """
        action = self.get_toolbar_action_by_item_name(toolbar, item_name, item_pos)
        if not action:
            return False
        action.setEnabled(enable)
        return True

    def enable_toolbar_item_by_names(self, toolbar_name, item_name, enable=True, item_pos=0):
        """ Activa una acció d'una toolbar a partir dels seus noms
            ---
            Activates an action from a toolbar based on its names
            """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return False
        return self.enable_toolbar_item_by_item_name(toolbar, item_name, enable, item_pos)

    def enable_toolbar_items_by_name(self, toolbar_name, items_id_list, enable=True):
        """ Activa una llista d'items pel seu id d'una toolbar pel seu nom
            ---
            Activates toolbars items by id and toolbar_name
            """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return 0
        return self.enable_toolbar_items(toolbar, items_id_list, enable)

    def enable_toolbar_items(self, toolbar, items_id_list, enable=True):
        return self.enable_gui_items(toolbar, items_id_list, enable)

    def organize_toolbars(self):
        """ Organitza les toolbars dins l'espai disponible
            ---
            Organize the toolbars within available space
            """
        toolbars = [t for t in self.iface.mainWindow().children() if type(t) == QToolBar and t.isVisible()]
        toolbars.sort(key=lambda t:(t.y()*1000000+t.x())) # Ordenem les toolbars per colocació a pantalla
        mainwindow_width = self.iface.mainWindow().size().width()
        pos_x = 0
        for toolbar in toolbars:
            ##print("toolbar:", unicode(toolbar.windowTitle()), "sizeHint", toolbar.sizeHint(), "size", toolbar.size(), "left", toolbar.x(), "right", toolbar.x() + toolbar.sizeHint().width())
            self.iface.mainWindow().removeToolBarBreak(toolbar)
            pos_x += (toolbar.sizeHint().width() + 25)
            if pos_x >= mainwindow_width:
                pos_x = 0
                self.iface.mainWindow().insertToolBarBreak(toolbar)

    def enable_toolbar_by_name(self, toolbar_name, enable=True):
        """ Activa / Desactiva toolbar per nom de la toolbar
            ---
            Enable / Disable toolbar by toolbar name 
            """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return
        if enable:
            toolbar.show()
        else:
            toolbar.hide()

    def enable_toolbar_by_object_name(self, toolbar_object_name, enable=True):
        """ Activa / Desactiva toolbar per nom de l'objecte
            ---
            Enable / Disable toolbar by object name 
            """
        toolbar = self.get_toolbar_by_object_name(toolbar_object_name)
        if not toolbar:
            return
        if enable:
            toolbar.show()
        else:
            toolbar.hide()


    ###########################################################################
    # Shortcuts
    #
    def configure_shortcuts(self, shortcuts_callbacks_list):
        """ Crea shortcuts segons la llista de <callbacks>
            ---
            Create shortcuts based on the <callbacks> list
            ---
            shortcuts_callbacks_list: [(<description>, <keyseq>, <callback>)]
            """
        for shortcut_info in shortcuts_callbacks_list:
            if shortcut_info == "---":
                description, keyseq, callback = shortcut_info, None, None
            else:
                description, keyseq, callback = shortcut_info
            self.add_shortcut(description, keyseq, callback)

    def add_shortcut(self, description, keyseq, callback):
        """ Mapeja un nou shortcut a QGIS i el retorna
            ---
            Map a new shortcut to QGIS and return it
            """
        if keyseq is None or callback is None:
            shortcut = None
        else:
            shortcut = QShortcut(QKeySequence(keyseq), self.iface.mainWindow())
            shortcut.activated.connect(callback)
        self.shortcuts.append((description, keyseq, shortcut))
        return shortcut

    def get_all_shortcuts_description(self, this_plugin_not_all_plugins=True, show_plugin_name=False, show_plugin_newline=True):
        """ Retorna un text amb informació de tots els shortcuts mapejats
            ---
            Returns a text with information about all the mapped shortcuts
            """
        if this_plugin_not_all_plugins:
            plugin_info_list = [(u'Self', self.parent)]
        else:
            plugin_info_list = plugins.items()

        shortcut_description = ""
        prefix = "   " if show_plugin_name else ""
        for plugin_name, plugin in plugin_info_list:
            # Excloem els shotcuts sense descripció, Incloem els "espais": shortcut a None
            if plugin.__dict__.get('gui'):
                shortcut_info_list = [(description, keyseq, shortcut) for (description, keyseq, shortcut) in plugin.gui.shortcuts if description or not shortcut]
            else:
                shortcut_info_list = []
            if show_plugin_name and shortcut_info_list:
                shortcut_description += "Plugin: %s\n" % plugin_name
            for description, keyseq, shortcut in shortcut_info_list:
                if keyseq:
                    shortcut_description += "%s%s: %s\n" % (prefix, keyseq, description)
                else:
                    shortcut_description += "\n"
            if show_plugin_newline and shortcut_info_list:
                shortcut_description += "\n"

        return shortcut_description

    def show_shortcuts(self, checked=None, title="Tecles d'accesos directes"): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Mostra ajuda sobre shortcuts HTML """
        shortcuts_info = self.get_all_shortcuts_description()
        QMessageBox.information(self.iface.mainWindow(), title, shortcuts_info)


    ###########################################################################
    # Tools
    #
    def enable_tool(self, map_tool):
        """ Activa una eina seleccionada
            ---
            Activate a selected tool
            """
        if map_tool:
            self.iface.mapCanvas().setMapTool(map_tool)
        else:
            self.iface.actionPan().trigger()

    ###########################################################################
    # DockWidgets
    #
    def get_dock_widgets(self):
        """ Retorna una llista amb tots els DockWidgets de QGIS
            ---
            Returns a list of all QGIS DockWidgets
            """
        return [w for w in self.iface.mainWindow().children() if type(w) == QDockWidget]

    ###########################################################################
    # Other
    #
    def get_icon(self, icon_name):
        """ Carrega una icona a partir del seu path (relatiu o absolut) 
            o el seu nom (a partir d'un fitxer de recursos)
            --- 
            Loads icon by pathname (relative or absolut) or by name
            (from resource file)
            """
        # Verifiquem tenir extensió
        if not os.path.splitext(icon_name)[1]:
            icon_name += ".png"
        # Mirem si ens han passat un path complet de la icona
        if os.path.isabs(icon_name):
            return QIcon(icon_name)
        # Cerquem a la carpeta del plugin
        icon_pathname = os.path.join(self.parent.plugin_path, icon_name)
        if os.path.exists(icon_pathname):
            return QIcon(icon_pathname)
        # Cerquem a la carpeta del plugin / images
        icon_pathname = os.path.join(self.parent.plugin_path, "images", icon_name)
        if os.path.exists(icon_pathname):
            return QIcon(icon_pathname)
        # Cerquem a la carpeta de QLib3 / images
        icon_pathname = os.path.join(os.path.dirname(__file__), "images", icon_name)
        if os.path.exists(icon_pathname):
            return QIcon(icon_pathname)
        # Cerquem als recursos del plugin
        icon = QIcon(":/plugins/%s/images/%s" % (self.parent.plugin_id, icon_name))
        if not icon.isNull():
            return icon
        # Cerquem als recursos de QLib
        icon = QIcon(":/lib/qlib3/base/images/%s" % icon_name)
        if not icon.isNull():
            return icon
        return None

    def open_file_folder(self, folder):
        """ Obre una carpeta en el navegador d'arxius del sistema 
            ---
            Open folder in system file explorer 
            """
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            opener ="open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, folder])       


class ProjectBase(object):
    """ Classe per accedir a informació del projecte
        ---
        Class to access project information
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare i a l'iface
            ---
            Initialization of member variables pointing to parent and iface
            """
        self.parent = parent
        self.iface = parent.iface

    def get_crs(self):
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def get_epsg(self, asPrefixedText=False):
        """ Retorna el codi EPSG del projecte, com a text o text prefixat amb EPSG
            ---
            Returns EPSG code of the project, as text or text prefixed with EPSG
            """
        text = self.get_crs().authid()
        return self.parent.crs.format_epsg(text, asPrefixedText)

    def set_epsg(self, epsg):
        """ Assigna el codi EPSG del projecte
            ---
            Assign EPSG code to the project
            """
        crs = self.parent.crs.get_crs(epsg)
        self.iface.mapCanvas().mapSettings().setDestinationCrs(crs)
        QgsProject.instance().setCrs(crs)

    def create_qgis_project_file(self, project_file, template_file, host, dbname, dbusername, excluded_users_list = [], excluded_db_list = []):
        """ Crea un projecte QGIS (.qgs) a partir de:
            - Plantilla projecte amb connexions a BBDD
            - Connexió a BBDD (host, dbname, username)
            Substitueix les connexions a BBDD existens per la BBDD especificada (saltant-se els usuaris i BBDD excloses)
            ---
            Create a QGIS project (.qgs) from:
             - Project template with connections to BBDD
             - Connection to BBDD (host, dbname, username)
            Replace existing BBDD connections for the specified BBDD (skipping users and BBDD excluded)
            """
        # Llegim la plantilla de projecte
        ##print("Template", template_file)
        ##print("DB", dbname)
        ##print("Temporal project", project_file, "\n")
        with open(template_file, "r") as ftemplate:
            lines = ftemplate.readlines()

        # Modifiquem les dades de la plantilla (accés a BBDD i path a imatges de reports)
        for i, line in enumerate(lines):
            # BBDD pex: <datasource>dbname='ortho_resources' host=perry.icc.local port=5432 user='qgis_ro' password='User123$' sslmode=disable key='gid' table="comarques" (the_geom) sql=upper(geometrytype("the_geom")) IN ('POLYGON','MULTIPOLYGON')</datasource>
            # Canviem la BBDD
            found = re.search(r"dbname='([\w\-.$]+)'", line)
            if found:
                old_dbname = found.groups()[0]
                if old_dbname not in excluded_db_list:
                    line = line.replace(old_dbname, dbname)
                    ##print("user", old_dbname, dbname)
                    # Canviem el host
                    found = re.search(r"host=([\w\-.$]+) ", line)
                    if found:
                        old_host = found.groups()[0]
                        line = line.replace(old_host, host)
                        ##print("user", old_host, host)

            # Canviem tots els usaris pel nostre
            found = re.search(r"user='(\w+)'", line)
            if found:
                old_dbusername = found.groups()[0]
                if old_dbusername not in excluded_users_list:
                    line = line.replace(old_dbusername, dbusername)
                    ##print("user", old_dbusername, getuser(), excluded_users_list)
                    # Canviem tots els passwords
                    found = re.search(r"password='([\w.$]+)'", line)
                    if found:
                        old_dbpassword = found.groups()[0]
                        line = line.replace(old_dbpassword, 'User123$')
                        ##print("password", old_dbpassword, 'User123$')

            # Canviem els path relatius per paths absoluts al template
            line = line.replace('<datasource>./', '<datasource>%s/' % os.path.dirname(template_file))

            lines[i] = line

        # Escrivim el nou projecte
        with open(project_file, "w") as fproject:
            fproject.writelines(lines)


class LayersBase(object):
    """ Classe per manegar capes de QGIS
        ---
        Class to manage QGIS layers
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare a i l'iface
            ---
            Initialization of member variables pointing to parent and iface
            """
        self.parent = parent
        self.iface = parent.iface
        self.root = QgsProject.instance().layerTreeRoot()

        self.time_series_dict = {}

        self.download_manager = DownloadManager()

        # Configurem l'event de refresc de mapa perquè ens avisi
        self.map_refreshed = True
        self.iface.mapCanvas().mapCanvasRefreshed.connect(self.on_map_refreshed)

    def remove(self):
        """ Desmapeja l'event de refresc finalitzat
            ---
            Unmap fishined refresh event
            """
        self.iface.mapCanvas().mapCanvasRefreshed.disconnect(self.on_map_refreshed)

    def on_map_refreshed(self):
        """ Funció auxiliar per detectar quan s'ha acabat de refrescar el mapa
            ---
            Auxiliary function to detect when the map has finished refreshing
            """
        self.map_refreshed = True

    def refresh_map(self, wait_refreshed=False):
        """ Refresca el contingut del mapa, si s'especifica que esperi, la funció no retorna fins que es rep l'event de final de refresc
            ---
            Refresh the content of the map, if it is specified that you wait, the function does not return until the end event is received
            """
        self.map_refreshed = False
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
        # self.iface.mapCanvas().refresh() 
        # ATENCIÓ: A partir de la versió 3.16 refreshAllLayers deselecciona els elements. Anteriorment feiem server refresh però a vegades no refrescava correctament.
        # Caldrà valorar quines de les dues deixem.
        # ---------------------------------------------------------------------------------------------------------------------------------------------------------------
        self.iface.mapCanvas().refreshAllLayers()
        if wait_refreshed:
            # Espera a que es refresqui el mapa
            while not self.map_refreshed:
                QApplication.instance().processEvents()

    def get_layers_by_id(self, idprefix):
        """ Retorna llista de capes segons un prefix d'identificador
            ---
            Returns a list of layers according to an identifier prefix
            """
        layers_dict = QgsProject.instance().mapLayers()
        layers_list = [layer for id, layer in layers_dict.items() if id.startswith(idprefix)]
        return layers_list

    def get_by_id(self, idprefix, pos=0):
        """ Retorna una capa segons un prefix d'identificador i la repetició del prefix
            ---
            Returns a layer according to an identifier prefix and the prefix repeat
            """
        if not idprefix:
            return None
        layers_dict = QgsProject.instance().mapLayers()
        layer = layers_dict.get(idprefix, None)
        if layer:
            return layer
        layers_list = [layer for id, layer in layers_dict.items() if id.startswith(idprefix)]
        if not layers_list or pos < 0 or pos >= len(layers_list):
            return None
        return layers_list[pos]

    def get_by_name(self, name):
        """ Retorna una capa segons un el seu nom
            ---
            Returns a layer by name
            """
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == name:
                return layer
        return None

    def get_by_pos(self, pos):
        """ Retorna una capa segons la seva posició
            ---
            Returns a layer according to its position
            """
        layers_list = QgsProject.instance().mapLayers().values()
        if not layers_list or pos < 0 or pos >= len(layers_list):
            return None
        return list(layers_list)[pos]

    def get_connection_string_dict_by_id(self, idprefix, pos=0):
        """ Retorna un diccionari amb el string de conexió de la capa a partir del seu id (se li passa prefix d'id)
            ---
            Returns a dictionary with the connection string of the layer from its id (id prefix is passed)
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return {}
        return self.get_connection_string_dict(layer)

    def get_connection_string_dict(self, layer):
        """ Retorna un diccionari amb el string de conexió de la capa
            ---
            Returns a dictionary with the layer's connection string
            """
        connection_string = layer.dataProvider().dataSourceUri()
        return dict([pair.split('=') for pair in connection_string.split() if len(pair.split('=')) == 2])

    def get_visible_features(self, layer, features_list):
        """ Retorna els elements visibles d'una capa (a partir d'una llista)
            ---
            Returns visible layer's features (from a list)
            """
        visible_features = []        
        if layer and layer.renderer():
            renderer = layer.renderer().clone()
            ctx = QgsRenderContext()
            renderer.startRender(ctx, QgsFields())
            for feature in features_list:
                ctx.expressionContext().setFeature(feature)
                if renderer.willRenderFeature(feature, ctx):
                    visible_features.append(feature)
            renderer.stopRender(ctx)
        return visible_features

    def get_feature_by_id(self, idprefix, feature_id, pos=0):
        """ Retorna l'element de l'id especificat
            ---
            Returns feature from specified id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.get_feature(layer, feature_id)

    def get_feature(self, layer, feature_id):
        """ Retorna l'element de l'id especificat
            ---
            Returns feature from specified id
            """
        feature_request = QgsFeatureRequest()
        feature_request.setFilterFid(feature_id)
        feature_list = list(layer.getFeatures(feature_request))
        return feature_list[0] if feature_list else None

    def get_feature_by_attribute_by_id(self, idprefix, field_name, field_value, pos=0):
        """ Retorna l'element especificat pel valor d'attribut
            ---
            Returns feature from specified attribute value
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.get_feature_by_attribute(layer, field_name, field_value)

    def get_feature_by_attribute(self, layer, field_name, field_value):
        """ Retorna l'element de l'id especificat
            ---
            Returns feature from specified id
            """
        expression = QgsExpression("%s = %s" % ( \
            field_name, "'%s'" % field_value if type(field_value)==str else field_value))
        feature_request = QgsFeatureRequest(expression)
        feature_list = list(layer.getFeatures(feature_request))
        return feature_list[0] if feature_list else None

    def get_feature_attribute_by_id(self, idprefix, entity, field_name, pos=0):
        """ Retorna el valor d'un camp (columna) d'una entitat d'una capa (fila)
            ---
            Returns the value (column) of a layer entity (row)
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.get_feature_attribute(layer, entity, field_name)

    def get_feature_attribute(self, layer, entity, field_name):
        """ Retorna el valor d'un camp (columna) d'una entitat d'una capa (fila) a partir del seu id (se li passa prefix d'id)
            ---
            Returns the value of a field (column) of an layer entity (row) based on its id (id prefix is passed)
            """
        if field_name.lower() in ('footprint', 'geometry', 'the_geom', 'geometria'):
            return entity.geometry()
        index = layer.dataProvider().fieldNameIndex(field_name)
        if index < 0:
            return None
        value = entity[index]
        return value

    def get_attributes_by_id(self, layer_idprefix, fields_name_list, max_items=None, pos=0):
        """ Retorna una llista amb els atributs especificats dels elements de la capa indicada a partir del seu id
            ---
            Returns a list with the specified attributes of the elements of the indicated layer based on its id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return []
        return self.get_attributes(layer, fields_name_list, max_items)

    def get_attributes(self, layer, fields_name_list, max_items=None):
        """ Retorna una llista amb els atributs especificats dels elements de la capa indicada
            ---
            Returns a list with the specified attributes of the elements of the indicated layer
            """
        return self.__get_attributes([layer], fields_name_list, False, None, None, max_items)

    def get_attribute_by_id(self, layer_idprefix, field_name, max_items=None, pos=0):
        """ Retorna una llista amb l¡atribut especificat dels elements de la capa indicada a partir del seu id
            ---
            Returns a list with the specified attribute of the elements of the indicated layer based on its id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return []
        return self.get_attribute(layer, field_name, max_items)

    def get_attribute(self, layer, field_name, max_items=None):
        """ Retorna una llista amb l'atribut especificat dels elements de la capa indicada
            ---
            Returns a list with the specified attribute of the elements of the indicated layer
            """
        attributes_tuple_list = self.get_attributes(layer, [field_name], max_items)
        return [attributes_tuple[0] for attributes_tuple in attributes_tuple_list]

    def get_attribute_selection_by_id(self, layer_idprefix, field_name, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista amb l'atribut especificat dels elements seleccionats a QGIS de la capa indicada
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list with the specified attribute of the selected elements in QGIS of the indicated layer
            You can specify a function error_function(res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection_by_id(layer_idprefix, field_name, error_function, error_message, max_items)

    def get_attribute_selection(self, layer, field_name, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista amb l'atribut especificat dels elements seleccionats a QGIS de la capa indicada.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list with the specified attribute of the selected elements in QGIS of the indicated layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection(layer, field_name, error_function, error_message, max_items)

    def get_attributes_selection_by_id(self, layer_idprefix, fields_name_list, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la capa indicada.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS of the indicated layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary.
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection_by_id(layer_idprefix, fields_name_list, error_function, error_message, max_items)

    def get_attributes_selection(self, layer, fields_name_list, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la capa indicada.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS of the indicated layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection(layer, fields_name_list, error_function, error_message, max_items)

    def get_attribute_selection_by_id_list(self, layer_idprefix_list, field_name, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista amb l'atribut especificats dels elements seleccionats a QGIS de la llista de capes indicada.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list with the specified attribute of the selected elements in QGIS from the indicated list of layers.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection_by_id(layer_idprefix_list, field_name, error_function, error_message, max_items)

    def get_attribute_selection_by_list(self, layers_list, field_name, error_function = None, error_message = None, max_items = None):
        """ Retorna una llista amb l'atribut especificats dels elements seleccionats a QGIS de la llista de capes indicada
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list with the specified attribute of the selected elements in QGIS from the indicated list of layers.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection(layers_list, field_name, error_function, error_message, max_items)

    def get_attributes_selection_by_id_list(self, layer_idprefix_list, fields_name_list, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la llista de capes indicada
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS from the indicated list of layers
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection_by_id(layer_idprefix_list, fields_name_list, error_function, error_message, max_items)

    def get_attributes_selection_by_list(self, layers_list, fields_name_list, error_function = None, error_message = None, max_items = None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la llista de capes indicada
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS from the indicated list of layers.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes_selection(layers_list, fields_name_list, error_function, error_message, max_items)

    def __get_attributes_selection_by_id(self, layer_idprefix_or_list, field_name_or_list, error_function = None, error_message = None, max_items = None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la llista de capes indicada
            o de la capa activa.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal.
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS from the indicated list of layers
            or the active layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary.
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        # Validem el tipus de dades del idprefix (acceptem llista o valor)
        if type(layer_idprefix_or_list) != list:
            layer_idprefix_or_list = [layer_idprefix_or_list]
        selected_layers = [self.get_by_id(layer_idprefix) for layer_idprefix in layer_idprefix_or_list]
        return self.__get_attributes_selection(selected_layers, field_name_or_list, error_function, error_message, max_items)

    def __get_attributes_selection(self, layer_or_list_or_none, field_name_or_list, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS de la llista de capes indicada
            o de la capa activa.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal.
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS from the indicated list of layers
            or the active layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary.
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        return self.__get_attributes(layer_or_list_or_none, field_name_or_list, True, error_function, error_message, max_items)

    def __get_attributes(self, layer_or_list_or_none, field_name_or_list, only_selection, error_function=None, error_message=None, max_items=None):
        """ Retorna una llista de tuples amb els atributs especificats dels elements seleccionats a QGIS o de tots els elements
            de la llista de capes indicada o de la capa activa.
            Se li pot especificar una funció error_function(res_list) que retorna un booleà, que evalua casos d'error
            i automàticament mostra error_message si cal.
            ---
            Returns a list of tuples with the specified attributes of the selected elements in QGIS or all elements
            from the indicated list of layers or from the active layer.
            You can specify a function error_function (res_list) that returns a Boolean, which evaluates error cases
            and automatically shows error_message if necessary.
            ---
            Pex: error_funciton=lambda res_list: len(res_list) < 1, error_message="A selected item is required" """
        selection = []
        layers_selected = []
        current_layer = self.iface.mapCanvas().currentLayer()
        current_layer_selection = []

        # Treballem amb llista i si no en tenim la generem
        if not layer_or_list_or_none:
            layers_list = [self.iface.activeLayer()]
        elif type(layer_or_list_or_none) != list:
            layers_list = [layer_or_list_or_none]
        else:
            layers_list = layer_or_list_or_none

        # Cerquem selecció a totes les capes indicades
        for layer in layers_list:
            if layer:
                # Obtenim els elements seleccionats
                if only_selection:
                    selected_features = layer.getSelectedFeatures()
                else:
                    selected_features = list(layer.getFeatures())[:max_items]
                # Obtenim la selecció de la capa fields_name_or_list (acceptem llista o valor)
                if type(field_name_or_list) != list:
                    layer_selection = [self.get_feature_attribute(layer, feature, field_name_or_list) for feature in selected_features]
                else:
                    layer_selection = [tuple([self.get_feature_attribute(layer, feature, field_name) for field_name in field_name_or_list]) for feature in selected_features]
                selection += layer_selection
                # Comptem quantes capes tenen selecció
                if len(layer_selection) > 0:
                    layers_selected.append(unicode(layer.name()))
                # Si és la capa activa, ens guardem la selecció a part
                if layer == current_layer:
                    current_layer_selection = layer_selection

        # No volem tenir seleccions a múltiples capes
        if len(layers_selected) > 1:
           # Si no hi ha capa activa (dins la nostra llista) sortim
            if not current_layer_selection:
                QMessageBox.warning(self.iface.mainWindow(),
                    "Selection multilayer",
                    "There are selected elements on %d differents layers:\n   - %s\n\nThe operation will be cancelled" % (len(layers_selected), "\n   - ".join(layers_selected)))
                return None
           # Si tenim seleccions a múltiples capes, proposem la selecció de la capa activa
            if QMessageBox.warning(self.iface.mainWindow(),
                "Selection multilayer",
                "There are selected elements on %d differents layers:\n   - %s\n\nDo you want continue with current layer?:\n   - %s" % (len(layers_selected), "\n   - ".join(layers_selected), unicode(current_layer.name())),
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return None
            return current_layer_selection

        # Si ens ho demanen gestionem que hi hagi selecció
        if error_function:
            if error_function(selection):
                if error_message:
                    QMessageBox.warning(self.iface.mainWindow(), "Error", error_message)
                return None

        # Si ens demanen només un element, convertim la llista en valors
        if max_items == 1:
            if selection:
                selection = selection[0]
            else:
                selection = None

        return selection

    def get_attribute_by_area_by_id(self, layer_idprefix, field_name, area, area_epsg=None, pos=0):
        """ Retorna una llista amb l'atribut especificat de la capa dels elements seleccionats per l'àrea especificada
            ---
            Returns a list with the specified attribute of the layer of the selected elements for the specified area
            """
        layer = self.get_by_id(layer_idprefix, pos)
        return self.get_attributes_by_area(layer, [field_name], area, area_epsg)

    def get_attribute_by_area(self, layer, field_name, area, area_epsg=None):
        """ Retorna una llista amb l'atribut especificat de la capa dels elements seleccionats per l'àrea especificada
            ---
            Returns a list with the specified attribute of the layer of the selected elements for the specified area
            """
        return self.get_attributes_by_area(layer, [field_name], area, area_epsg)

    def get_attributes_by_area_by_id(self, layer_idprefix, fields_name_list, area, area_epsg=None, pos=0):
        """ Retorna una llista de tuples amb els atributs especificats de la capa dels elements seleccionats per l'àrea especificada
            ---
            Returns a list of tuples with the specified attributes of the layer of the selected elements for the specified area
            """
        layer = self.get_by_id(layer_idprefix, pos)
        return self.get_attributes_by_area(layer, fields_name_list, area, area_epsg)

    def get_attributes_by_area(self, layer, fields_name_list, area, area_epsg=None):
        """ Retorna una llista de tuples amb els atributs especificats de la capa dels elements seleccionats per l'àrea especificada (rectangle)
            ---
            Returns a list of tuples with the specified attributes of the layer of the selected elements for the specified area (rect)
            """
        # Obtenim l'area a buscar, i la reprojectem si cal a coordenades de la serie50k
        if area_epsg and self.get_epsg(layer) != area_epsg:
            area = self.parent.crs.transform_bounding_box(area, area_epsg, self.parent.layers.get_epsg(layer))

        # Cerquem elements que intersequin amb l'àrea
        feature_request = QgsFeatureRequest()
        feature_request.setFilterRect(area) 
        feature_list = layer.getFeatures(feature_request)

        # Recuperem els camps demanats
        if len(fields_name_list) == 1:
            layer_selection = [self.get_feature_attribute(layer, feature, fields_name_list[0]) \
                for feature in feature_list if feature.geometry().intersects(area)]
        else:
            layer_selection = [tuple([self.get_feature_attribute(layer, feature, field_name) for field_name in fields_name_list]) \
                for feature in feature_list if feature.geometry().intersects(area)]
        return layer_selection

    def refresh_by_id(self, layer_idprefix, unselect=False, pos=0):
        """ Refresca el pintant de la capa especificada i la deselecciona tots els elements si cal
            ---
            Refresh the painting of the specified layer and deselect all items if necessary
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.refresh(layer, unselect)
        return True

    def refresh(self, layer, unselect=False):
        """ Refresca el pintant de la capa especificada i la deselecciona tots els elements si cal
            ---
            Refresh the painting of the specified layer and deselect all items if necessary
            """
        if unselect:
            self.set_selection(layer, [])
        layer.triggerRepaint()
        self.refresh_legend(layer)
        
        # Desactivo la crida a refresh_map perquè la funció refreshAllLayers (que es crida dins)
        # deselecciona a pinyó tots els elements de totes les capes a QGIS 3.22 (a QGIS 3.10 no passava)
        #self.refresh_map()

    def set_selection_by_id(self, layer_idprefix, values_list, field_name=None, pos=0):
        """ Selecciona els elements de la capa vectorial especificada indicats a la llista "values_list".
            Si no s'especifica el camp a comparar s'utilitza "id"
            ---
            Select the specified vector layer elements indicated in the "values_list" list.
            If you do not specify the field to compare "id" is used
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.set_selection(layer, values_list, field_name)

    def set_selection(self, layer, values_list, field_name=None):
        """ Selecciona els elements de la capa vectorial especificada indicats a la llista "values_list".
            Si no s'especifica el camp a comparar s'utilitza "id"
            ---
            Select the specified vector layer elements indicated in the "values_list" list.
            If you do not specify the field to compare "id" is used
            """
        # Si la capa no és vectorial no va la selecció...
        if type(layer) != QgsVectorLayer:
            return False

        # Si ens passem camps buits, deseleccionem tot
        if not values_list or len(values_list) == 0:
            layer.selectByIds([])
            return True

        # Si no tenim camp indicat, suposem que la llista és de ids i fem la crida "normal"
        if not field_name:
            layer.selectByIds(values_list)
            return True

        # Obtenim els camps de la capa
        dp = layer.dataProvider()
        fields_names = [f.name() for f in dp.fields().toList()]
        if field_name not in fields_names:
            return False
        # Seleccionem pel camp indicat
        expression_filter = "\"%s\" IN ('%s')" % (field_name, "', '".join([str(v).replace("\\", "\\\\") for v in values_list]))
        layer.selectByExpression(expression_filter)
        return True

    def zoom_to_selection_by_id(self, layer_idprefix, scale=None, pos=0):
        """ Fa zoom als elements seleccionats de la capa indicada per id amb una determinada escala
            ---
            Zoom to the selected elements of the indicated layer by id with a certain scale
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.zoom_to_selection(layer, scale)
        return True

    def zoom_to_selection(self, layer, scale=None):
        """ Fa zoom als elements seleccionats de la capa indicada amb una determinada escala
            ---
            Zoom to the selected elements of the indicated layer with a certain scale"""
        self.iface.mapCanvas().zoomToSelected(layer)
        if scale:
            self.iface.mapCanvas().zoomScale(scale)

    def zoom_to_by_id(self, layer_idprefix, items_list, field_name=None, set_selection=True, scale=None, pos=0):
        """ Fa zoom als elements indicats per "item_list" i "field_name" de la capa especificada per id amb
            una certa escala, podent deixar els elements seleccionats o no
            ---
            Zoom to the items indicated by "item_list" and "field_name" of the specified layer by id with
            a certain scale, being able to leave the selected elements or not
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.zoom_to(layer, items_list, field_name, set_selection, scale)
        return True

    def zoom_to(self, layer, items_list, field_name=None, set_selection=True, scale=None):
        """ Fa zoom als elements indicats per "item_list" i "field_name" de la capa determinada amb
            una determinada escala, podent deixar els elements seleccionats o no
            ---
            Zoom to the items indicated by "item_list" and "field_name" of the specified layer with
            a certain scale, being able to leave the selected elements or not
            """
        self.set_selection(layer, items_list, field_name)
        self.zoom_to_selection(layer, scale)
        if not set_selection:
            self.set_selection(layer, [])

    def get_epsg_by_id(self, layer_idprefix, asPrefixedText=False, pos=0):
        """ Obté el codi EPSG d'una capa per id
            ---
            Get the EPSG code of a layer for id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_epsg(layer, asPrefixedText)

    def get_epsg(self, layer, asPrefixedText=False):
        """ Obté el codi EPSG d'una capa
            ---
            Get the EPSG code of a layer by id
            """
        text = layer.crs().authid()
        return self.parent.crs.format_epsg(text, asPrefixedText)

    def load_style_by_id(self, layer_baseid, style_file, replace_dict=None, exclude_rules_labels_list=None, exclude_rules_filter_list=None, pos=0, refresh=True, visible=True, expanded=True):
        """ Carrega un fitxer d'estil a una capa per id
            ---
            Load a style file to a layer by id
            """
        layer = self.get_by_id(layer_baseid, pos)
        if not layer:
            return None
        return self.load_style(layer, style_file, replace_dict, exclude_rules_labels_list, exclude_rules_filter_list, refresh, visible, expanded)

    def load_style(self, layer, style_file, replace_dict=None, exclude_rules_labels_list=None, exclude_rules_filter_list=None, refresh=True, visible=True, expanded=True):
        """ Carrega un fitxer d'estil a una capa
            ---
            Load a style file to a layer
            """
        # Obtenim el path de l'arxiu
        if not os.path.splitext(style_file)[1]:
            style_file += '.qml'
        if os.path.dirname(style_file):
            style_pathname = style_file
        elif self.parent.plugin_path and os.path.exists(os.path.join(self.parent.plugin_path, style_file)):
            style_pathname = os.path.join(self.parent.plugin_path, style_file)
        elif self.parent.plugin_path and os.path.exists(os.path.join(self.parent.plugin_path, "symbols", style_file)):
            style_pathname = os.path.join(self.parent.plugin_path, "symbols", style_file)
        elif os.environ.get('APP_PATH', None) and os.path.exists(os.path.join(os.environ["APP_PATH"], "symbols", style_file)):
            style_pathname = os.path.join(os.environ["APP_PATH"], "symbols", style_file)
        else:
            for plugin_path in os.environ["QGIS_PLUGINPATH"].split(';'):
                style_pathname = os.path.join(plugin_path, "..\\symbols", style_file)
                if os.path.exists(style_pathname):
                    break
        if not os.path.exists(style_pathname):
            return None

        # Si tenim que substituir valors, creem un arxiu temporal
        tmp_style_pathname = None
        if replace_dict and os.path.exists(style_pathname):
            with codecs.open(style_pathname, encoding='utf-8', mode='r') as fin:
                text = fin.read()
            for old_value, new_value in sorted(replace_dict.items(), key=lambda item: len(item[0]), reverse=True):
                text = text.replace(old_value, new_value)
            tmp_style_pathname = os.path.join(os.environ['temp'], os.path.basename(style_pathname))
            with codecs.open(tmp_style_pathname, encoding='utf-8', mode="w") as fout:
                fout.write(text)
            style_pathname = tmp_style_pathname

        # Carreguem l'estil
        text = layer.loadNamedStyle(style_pathname)
        ##print("Style status: %s %s %s" % (unicode(layer.name()), style_pathname, text))

        # Esborrem arxius temporals si cal
        if tmp_style_pathname and os.path.exists(tmp_style_pathname):
            os.remove(tmp_style_pathname)

        # Esborrem les regles de la llista
        if exclude_rules_labels_list or exclude_rules_filter_list:
            renderer = layer.renderer()
            root_rule = renderer.rootRule()
            rules_list = root_rule.children()
            for i in range(len(rules_list) - 1, -1, -1):
                # Busquem la etiqueta dins la llista d'exclusions
                exclude = False
                if exclude_rules_labels_list:
                    label = rules_list[i].label()
                    exclude = label in exclude_rules_labels_list
                # Busquem  el filtre dins la llista d'exclusions
                if not exclude and exclude_rules_filter_list:
                    filter = rules_list[i].filterExpression()
                    exclude = len([f for f in exclude_rules_filter_list if filter.find(f if f is not None else "NULL") >= 0]) > 0
                # Esborrem la regla
                if exclude:
                    root_rule.removeChildAt(i)
        # Refresquem la llegenda
        if refresh:
            self.refresh_legend(layer, visible, expanded)

        return text

    def load_xml_style_by_id(self, layer_baseid, xml_style, pos=0, refresh=True):
        """ Carrega un XML d'estil a una capa per id
            ---
            Load a XML style to a layer by id
            """
        layer = self.get_by_id(layer_baseid, pos)
        if not layer:
            return None
        return self.load_xml_style(layer, xml_style, refresh)

    def load_xml_style(self, layer, xml_style, refresh=True):
        """ Carrega un XML d'estil a una capa
            ---
            Load a XML style to a layer
            """
        # Carreguem el XML en un document
        style_doc = QDomDocument("qgis")
        style_doc.setContent(xml_style)
        # Carreguem el document XML a la capa
        status, error = layer.importNamedStyle(style_doc)

        # Refresquem la llegenda
        if refresh:
            self.refresh_legend(layer, True, True)
        return status

    def get_db_styles_by_id(self, layer_basename, pos=0):
        """ Obté els estils disponibles per una capa en una BBDD
            ---
            Get db styles from layer
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return None
        return self.get_db_styles(layer)

    def get_db_styles(self, layer):
        """ Obté els estils disponibles per una capa en una BBDD
            ---
            Get db styles from layer
            ---
            Return:
                layer_styles_dict: {style_id: (style_name, style_description), }
            """
        split_point_layer_styles, id_list, name_list, description_list, error = layer.listStylesInDatabase()
        # Ens quedem només amb els estils compatibles amb la capa (els "split_point_layer_styles" primers)
        layer_styles_dict = dict([(id, (name, description)) for id, name, description in zip(id_list[:split_point_layer_styles], name_list[:split_point_layer_styles], description_list[:split_point_layer_styles])])
        return layer_styles_dict

    def set_db_style_by_id(self, layer_basename, db_style_id, pos=0):
        """ Carrega un estil de BBDD a la capa
            ---
            Loads DB style to layer
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.set_db_style(layer, db_style_id)
        return True

    def set_db_style(self, layer, db_style_id):
        """ Carrega un estil de BBDD a la capa
            ---
            Loads DB style to layer
            """
        style_qml, error = layer.getStyleFromDatabase(db_style_id)
        style_doc = QDomDocument("qgis")
        style_doc.setContent(style_qml)
        layer.importNamedStyle(style_doc)
        self.refresh(layer)

    def set_visible_by_id(self, layer_basename, enable=True, pos=0):
        """ Fa visible o invisible una capa per id
            ---
            Make a layer visible or invisible for id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.set_visible(layer, enable)
        return True

    def set_visible(self, layer, enable=True):
        """ Fa visible o invisible una capa
            ---
            Make a layer visible or invisible for id
            """
        self.root.findLayer(layer.id()).setItemVisibilityChecked(enable)

    def is_visible_by_id(self, layer_basename, pos=0):
        """ Retorna si és visible una capa per id
            ---
            Returns if a layer is visible for id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return None
        return self.is_visible(layer)

    def is_visible(self, layer):
        """ Retorna si és visible una capa
            ---
            Returns if a layer is visible
            """
        return self.root.findLayer(layer.id()).isVisible()

    def set_scale_based_visibility_by_id(self, layer_basename, minimum_scale=None, maximum_scale=None, pos=0):
        """ Configura la visibilitat d'una capa per id segons escala de zoom.
            Si les escales són None, es desactiva
            ---
            Configure the visibility of a layer by id according to the scale.
            If the scales are None, it is deactivated
            """
        # Ens guardem la capa activa
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.layerScaleBasedVisibility2(layer, minimum_scale, maximum_scale)
        return True

    def set_scale_based_visibility(self, layer, minimum_scale=None, maximum_scale=None):
        """ Configura la visibilitat d'una capa segons escala de zoom.
            Si les escales són None, es desactiva
            ---
            Configure the visibility of a layer according to the scale.
            If the scales are None, it is deactivated
            """
        if minimum_scale is None or maximum_scale is None:
            layer.setScaleBasedVisibility(False)
        else:
            layer.setScaleBasedVisibility(True)
            layer.setMinimumScale(minimum_scale)
            layer.setMaximumScale(maximum_scale)

    def is_scale_based_visibility_by_id(self, layer_basename, pos=0):
        """ Retorna de si la capa per id té activada la visibilitat segons escala de zoom
            ---
            Returns if the layer by id has visibility enabled depending on the zoom scale
            """
        # Ens guardem la capa activa
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        return self.is_scale_based_bisibility(layer)

    def is_scale_based_visibility(self, layer):
        """ Informa de si la capa té activada la visibilitat segons escala de zoom
            ---
            Returns if the layer has visibility enabled depending on the zoom scale
            """
        return layer.hasScaleBasedVisibility()

    def collapse_by_id(self, layer_basename, collapse=True, pos=0):
        """ Colapsa o expandeix una capa per id
            ---
            Collapse or expand a layer for id
            """
        return self.expand_by_id(layer_basename, not collapse, pos)

    def collapse(self, layer, collapse=True):
        """ Colapsa o expandeix una capa
            ---
            Collapse or expand a layer
            """
        return self.expand(layer, not collapse)

    def expand_by_id(self, layer_basename, expand=True, pos=0):
        """ Expandeix o colapsa una capa per id
            ---
            Expand or collapse a layer for id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.expand(layer, expand)
        return True

    def expand(self, layer, expand=True):
        """ Expandeix o colapsa una capa
            ---
            Expand or collapse a layer
            """
        self.root.findLayer(layer.id()).setExpanded(expand)

    def is_expanded_by_id(self, layer_basename, pos=0):
        """ Retorna si una capa està expandida per id
            ---
            Returns if a layer is expanded by id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return None
        return self.is_expanded(layer)

    def is_expanded(self, layer):
        """ Informa de si una capa està expandida
            ---
            Returns if a layer is expanded
            """
        return self.root.findLayer(layer.id()).isExpanded()

    def enable_feature_count_by_id(self, layer_basename, enable=True, pos=0):
        """ Activa o desactiva el comptador d'elements d'una capa per id
            ---
            Enable or disable layer item's counter from id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        return self.enable_feature_count(layer, enable)

    def enable_feature_count(self, layer, enable=True):
        """ Activa o desactiva el comptador d'elements d'una capa
            ---
            Enable or disable layer item's counter
            """
        root = QgsProject.instance().layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        if not layer_node:
            return False
        layer_node.setCustomProperty("showFeatureCount", enable)
        return True

    def get_category_nodes_by_id(self, layer_basename, pos=0):
        """ Obté les categories d'una capa per id
            ---
            Gets layer categories by id
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return []
        return self.get_category_nodes(layer)

    def get_category_nodes(self, layer):
        """ Obté les categories d'una capa
            ---
            Gets layer categories
            """
        root = QgsProject.instance().layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        model = self.iface.layerTreeView().model().sourceModel()
        cat_nodes_list = model.layerLegendNodes(layer_node)
        return cat_nodes_list

    #def classification_by_id(self, layer_basename, values_list, color_list=None, border_color_list=None, transparency_list=None, width_list=None, pos=0):
    #    """ Classifica els valors d'una capa per id segons la llista de valors.
    #        Addicionalment se li pot passar una llista de colors, transparencia o amplada a aplicar
    #        (si és més curta que el nombre de valors, es repetiran colors utilitzant l'operador de mòdul)
    #        ---
    #        Classify the values of a layer by id according to the list of values.
    #        Additionally you can pass a list of colors to apply, transparency or width
    #        (if it is shorter than the number of values, colors will be repeated using module operator)
    #        """
    #    layer = self.get_by_id(layer_basename, pos)
    #    if not layer:
    #        return False
    #    self.classification(layer, values_list, color_list, border_color_list, transparency_list, width_list)
    #    return True

    #def classification(self, layer, values_list, color_list=None, border_color_list=None, transparency_list=None, width_list=None):
    #    """ Classifica els valors d'una capa segons la llista de valors.
    #        Addicionalment se li pot passar una llista de colors, transparència o amplada a aplicar
    #        (si és més curta que el nombre de valors, es repetiran colors utilitzant mòdul)
    #        ---
    #        Classify the values of a layer according to the list of values.
    #        Additionally you can pass a list of colors to apply, transparency or width
    #        (if it is shorter than the number of values, colors will be repeated using module operator)
    #        """
    #    # Esborrem la classificació per categories prèvia
    #    renderer = layer.renderer()
    #    renderer.deleteAllCategories()
    #    # Afegim un categoria per cada data
    #    for i, value in enumerate(values_list):
    #        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    #        if color_list:
    #            color = color_list[i % len(color_list)]
    #            symbol.setColor(color)
    #        if border_color_list:
    #            color = border_color_list[i % len(border_color_list)]
    #            symbol.symbolLayer(0).setStrokeColor(color)
    #        if transparency_list:
    #            transparency = transparency_list[i % len(transparency_list)]
    #            symbol.setOpacity(transparency)
    #        if width_list:
    #            width = width_list[i % len(width_list)]
    #            if type(symbol) == QgsMarkerSymbol:
    #                symbol.setSize(width)
    #            else:
    #                symbol.setWidth(width)
    #        cat = QgsRendererCategory(value, symbol, value)
    #        renderer.addCategory(cat)
    #
    #    # Activem la capa i refresquem la seva llegenda
    #    show = self.is_visible(layer)
    #    if not show:
    #        self.set_visible(layer, True)
    #    self.refresh_legend(layer)
    #    if not show:
    #        self.set_visible(layer, False)

    def classification_ranges_by_id(self, layer_basename, class_attribute, ranges_list, color_list=None, border_color_list=None, transparency_list=None, width_list=None, pos=0, suffix=None):
        """ Classifica els valors d'una capa per id segons la llista de rang de valors.
            Addicionalment se li pot passar una llista de colors, transparencia o amplada a aplicar
            (si és més curta que el nombre de valors, es repetiran colors utilitzant l'operador de mòdul)
            suffix permet afegir un text al final de l'etiqueta de cada categoria (p.e.: unitats)
            ---
            Classify the values of a layer by id according to the list of value ranges.
            Additionally you can pass a list of colors to apply, transparency or width
            (if it is shorter than the number of values, colors will be repeated using module operator)
            suffix allows the user to append a text to each of the categories (e.g.: units)
            """
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.classification_ranges(layer, class_attribute, ranges_list, color_list, border_color_list, transparency_list, width_list, suffix)
        return True

    def classification_ranges(self, layer, class_attribute, ranges_list, color_list=None, border_color_list=None, transparency_list=None, width_list=None, suffix=None):
        """ Classifica els valors d'una capa segons la llista de rang de valors.
            Addicionalment se li pot passar una llista de colors, transparencia o amplada a aplicar
            (si és més curta que el nombre de valors, es repetiran colors utilitzant mòdul)
            suffix permet afegir un text al final de l'etiqueta de cada categoria (p.e.: unitats)
            ---
            Classify the values of a layer according to the list of value ranges.
            Additionally you can pass a list of colors to apply, transparency or width
            (if it is shorter than the number of values, colors will be repeated using module operator)
            suffix allows the user to append a text to each of the categories (e.g.: units)
            """
        # Afegim un categoria per cada data
        renderers_list = []
        for i, (begin_value, end_value) in enumerate(ranges_list):
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            if color_list:
                color = color_list[i % len(color_list)]
                symbol.setColor(color)
            if border_color_list:
                color = border_color_list[i % len(border_color_list)]
                symbol.symbolLayer(0).setStrokeColor(color)
            if transparency_list:
                transparency = transparency_list[i % len(transparency_list)]
                symbol.setOpacity(transparency)
            if width_list:
                width = width_list[i % len(width_list)]
                if type(symbol) == QgsMarkerSymbol:
                    symbol.setSize(width)
                else:
                    symbol.setWidth(width)
            label = f"{begin_value} - {end_value}" if begin_value != end_value else str(end_value)
            if suffix:
                label += f" {suffix}"
            renderers_list.append(QgsRendererRange(begin_value, end_value, symbol, label))

        # Assignem la visualització per rangs a la capa
        renderer = QgsGraduatedSymbolRenderer(class_attribute, renderers_list)
        layer.setRenderer(renderer)

        # Activem la capa i refresquem la seva llegenda
        show = self.is_visible(layer)
        if not show:
            self.set_visible(layer, True)
        self.refresh_legend(layer)
        if not show:
            self.set_visible(layer, False)

    def classify_by_id(self, layer_idprefix, class_attribute=None, values_list=None, color_list=None, border_color_list=None, expand=None, width=None, size=None, opacity=None, use_current_symbol=True, base_symbol=None, label_function=None, alpha=None, sort=False, interpolate_colors=False, pos=0):
        """ Classifica els valors d'una capa per id segons la llista de valors i un camp de la capa.
            layer: capa a processar
            class_attribute: si no s'especifica, assumim que es vol partir de la classificació anterior
            values_list: llista de valors a utilitzar
            colors_list, border_list: Addicionalment se li pot passar una llista de colors a aplicar (si no hi ha colors s'utilitzan colors aleatoris)
               (si és més curta que el nombre de valors, es repetiran colors utilitzant mòdul)
            interpolate_colors: Interpola colors entre la llista de colors inicial per aconseguir un color per categoria
            width: amplada de les linies de la simbolització
            use_current_symbol: utilitza la simbolització actual canviant els colors
            base_symbol: simbol base a utilitzar canviant els colors
            label_function: genera una etiqueta a partir del valor de la categoria (p.e.: canvia representació de dates: lambda x: x.toPyDate())
            opacity: aplica opacitat a tot el símbol. Rang entre 0 (transparent) i 1 (opac)
            alpha: aplica transparència al color de l'emplenament. Rang entre 0 (transparent) i 1 (opac)
            expand: expandeix la llegenda de la capa
            sort: ordena les categories
            pos: index de la capa amb layer_idprefix a processar
            ---
            Classify the values of a layer, according to the values list and a layer field.
            layer: layer to process
            class_attribute: if not given, the old categories will be used as a starting point
            values_list: list of values to use
            colors_list, border_list: Additionally you can pass a list of colors to apply (if no colors, random colors are used)
               (if it is shorter than the number of values, colors will be repeated using module)
            interpolate_colors: Interpolate colors betwen initial colors list to gets one color per category
            width: width symbol lines
            use_current_symbol: use current symbol changing colors
            base_symbol: use this symbol changing colors
            label_function: generate a label from a category value (e.g.: tune representation of dates: lambda x: x.toPyDate())
            opacity: set opacity for the symbol. Range between 0 (fully transparent) and 1 (fully opaque)
            alpha: set transparency only to the fill color. Range between 0 (fully transparent) and 1 (fully opaque)
            expand: expand layer legend
            sort: sort categories
            pos: index of layer with layer_idprefix to process
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.classify(layer, class_attribute, values_list, color_list, border_color_list, expand, width, size, opacity, use_current_symbol, base_symbol, label_function, alpha, sort, interpolate_colors)
        return True

    def classify(self, layer, class_attribute=None, values_list=None, color_list=None, border_color_list=None, expand=None, width=None, size=None, opacity=None, use_current_symbol=True, base_symbol=None, label_function=None, alpha=None, sort=False, interpolate_colors=False):
        """ Classifica els valors d'una capa segons la llista de valors i un camp de la capa.
            layer: capa a processar
            class_attribute: si no s'especifica, assumim que es vol partir de la classificació anterior
            values_list: llista de valors a utilitzar
            colors_list, border_list: Addicionalment se li pot passar una llista de colors a aplicar (si no hi ha colors s'utilitzan colors aleatoris)
               (si és més curta que el nombre de valors, es repetiran colors utilitzant mòdul)
            interpolate_colors: Interpola colors entre la llista de colors inicial per aconseguir un color per categoria
            width: amplada de les linies de la simbolització
            size: mida per elements puntuals
            use_current_symbol: utilitza la simbolització actual canviant els colors
            base_symbol: simbol base a utilitzar canviant els colors
            label_function: genera una etiqueta a partir del valor de la categoria (p.e.: canvia representació de dates: lambda x: x.toPyDate())
            opacity: aplica opacitat al símbol. Rang entre 0 (transparent) i 1 (opac)
            alpha: aplica transparència al color de l'emplenament. Rang entre 0 (transparent) i 1 (opac)
            expand: expandeix la llegenda de la capa
            sort: ordena les categories
            ---
            Classify the values of a layer, according to the values list and a layer field.
            layer: layer to process
            class_attribute: if not given, the old categories will be used as a starting point
            values_list: list of values to use
            colors_list, border_list: Additionally you can pass a list of colors to apply (if no colors, random colors are used)
               (if it is shorter than the number of values, colors will be repeated using module)
            interpolate_colors: Interpolate colors betwen initial colors list to gets one color per category
            width: width symbol lines
            size: size of point features
            use_current_symbol: use current symbol changing colors
            base_symbol: use this symbol changing colors
            label_function: generate a label from a category value (e.g.: tune representation of dates: lambda x: x.toPyDate())
            opacity: set opacity for the symbol. Range between 0 (fully transparent) and 1 (fully opaque)
            alpha: set transparency only to the fill color. Range between 0 (fully transparent) and 1 (fully opaque)
            expand: expand layer legend
            sort: sort categories
            """
        # Guardo l'estat de la capa (de vegades en reclassificar es perd)
        layer_is_expanded = self.is_expanded(layer)

        # Si hem d'aprofitar símbols, ens guardem un base symbol. Cal clonar-lo ara, si no de vegades QGIS peta vilment
        if use_current_symbol:
            # Prioritzem el símbol base de la capa. Si no està definit, agafem el de la primera categoria
            renderer = layer.renderer()
            if renderer:
                if len(renderer.symbols(QgsRenderContext())):
                    base_symbol = renderer.symbols(QgsRenderContext())[0].clone()
                elif hasattr(renderer, 'sourceSymbol') and renderer.sourceSymbol():
                    base_symbol = renderer.sourceSymbol().clone()

        # Recupera el renderer o crea un de nou
        if hasattr(layer.renderer(), 'categories'):
            # Aprofita el renderer antic (així conservem propietats com el base_symbol)
            if class_attribute:
                # Inicialitza una nova classificació amb el camp que ens passen
                renderer.deleteAllCategories()
                renderer.setClassAttribute(class_attribute)
            else:
                # Parteix de la classificació antiga tal qual (després afegirem o eliminarem classes)
                class_attribute = renderer.classAttribute()
        else:
            # Crea un nou renderer des de zero (l'antic no era tipus Categorized)
            renderer = QgsCategorizedSymbolRenderer(class_attribute, [])

        # Si no tenim llista de valors, la generem
        if not values_list:
            field_pos = layer.fields().indexFromName(class_attribute)
            values_list = list(set([f.attributes()[field_pos] for f in layer.getFeatures() if f.attributes()[field_pos]]))

        ## Partim de la classificació existent i mirem si falten o sobren categories
        #delete_list = []
        #if len(renderer.categories()):
        #    old_categories_list = [c.value() for c in renderer.categories()]
        #    delete_list = [c for c in old_categories_list if not c in values_list] # Categories que sobren (les eliminarem)
        #    values_list = [v for v in values_list if not v in old_categories_list] # Categories que falten (les crearem)

        # Esborrem la classificació existent per recrear-la amb els elements ordenats
        delete_list = [c.value() for c in renderer.categories()]
        for value in delete_list:
            index = renderer.categoryIndexForValue(value)
            renderer.deleteCategory(index)

        # Detectem si els color d'omplir i el de border són el mateix
        linked_colors = base_symbol and not border_color_list and base_symbol.color().rgb() == base_symbol.symbolLayer(0).strokeColor().rgb()
        # Si hem d'interpolar colors, ho fem
        if border_color_list and interpolate_colors:
            border_color_list = self.get_interpolated_color_list(border_color_list, len(values_list))
        if color_list:
            # Si hem d'interpolar colors, ho fem
            if interpolate_colors:
                color_list = self.get_interpolated_color_list(color_list, len(values_list))
        else:
            # Si no tenim llista de colors, generarem una llista aleatòria
            # Recupero els colors de la classificació antiga (si n'hi ha)
            used_colors = [QColor(category.symbol().color()) for category in renderer.categories()]

        # Afegim una categoria per cada valor nou
        for i, value in enumerate(values_list):
            # Obtenim el color a aplicar
            if color_list:
                # Obtenim un color de la llista
                color = color_list[i % len(color_list)]
            else:
                # Calculem un color random no repetit
                color = None
                while color in used_colors or not color:
                    color = QColor.fromRgb(random.randint(0,255), random.randint(0,255), random.randint(0,255)) # Color aleatori
                used_colors.append(color)
            # Obtenim el color de borde
            if border_color_list:
                border_color = border_color_list[i % len(border_color_list)]
            elif linked_colors:
                border_color = QColor(color)
            else:
                border_color = None

            # Recupera la transparència del color d'emplenament original (en crear un nou color es perd)
            #if base_symbol:
            #    color.setAlpha(base_symbol.color().alpha())

            # Generem el símbol
            symbol = base_symbol.clone() if base_symbol else QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(color)

            # Aplica estils opcionals al símbol
            if border_color:
                # pinta les línies
                symbol.symbolLayer(0).setStrokeColor(border_color)
            if opacity is not None:
                # aplica transparència al símbol sencer
                symbol.setOpacity(opacity)
            if alpha is not None:
                # aplica transparència a l'emplenament
                color.setAlphaF(alpha)
                symbol.symbolLayer(0).setFillColor(color)
            if width is not None:
                if type(symbol) == QgsFillSymbol:
                    # gruix del borde dels polígons
                    if type(symbol.symbolLayer(0)) == QgsSimpleLineSymbolLayer:
                        symbol.symbolLayer(0).setWidth(width)
                    else:
                        symbol.symbolLayer(0).setStrokeWidth(width)
                else:
                    # gruix per línies
                    symbol.setWidth(width)
            if size is not None and type(symbol) == QgsMarkerSymbol:
                # Mida dels punts
                symbol.setSize(size)

            # Generem l'etiqueta a partir del valor
            label = label_function(value) if label_function else value

            # Creem la categoria
            cat = QgsRendererCategory(value, symbol, unicode(label))
            renderer.addCategory(cat)

        ## Eliminem categories sense dades
        #if len(delete_list):
        #    for value in delete_list:
        #        index = renderer.categoryIndexForValue(value)
        #        renderer.deleteCategory(index)

        # Ordenem categories. Cal guardar l'estat de les caselles de renderització (en ordenar es perd)
        if sort:
            state_dict = {c.value(): c.renderState() for c in renderer.categories()}
            renderer.sortByLabel()
            for category in renderer.categories():
                index = renderer.categoryIndexForValue(category.value())
                renderer.updateCategoryRenderState(index, state_dict[category.value()])

        # Refresquem la capa
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        # Refresquem la llegenda
        self.refresh_legend(layer, expanded = expand if expand is not None else layer_is_expanded)

    def get_interpolated_color_list(self, base_color_list, steps):
        """ Returns a interpolated colors list from initial n colors and a number of steps """
        # Special cases
        if not base_color_list or steps < 1:
            return []
        if len(base_color_list) == 1 or steps == 1:
            return base_color_list[0:1] * steps
        # Interpolate colors two by two
        substeps = float(steps) / (len(base_color_list) - 1)
        colors_list = []
        for i in range(steps):
            base_color_index = int((i * (len(base_color_list) - 1)) / steps)
            begin_color = base_color_list[base_color_index]
            end_color = base_color_list[base_color_index + 1]

            r_factor = (end_color.red() - begin_color.red()) / substeps
            g_factor = (end_color.green() - begin_color.green()) / substeps
            b_factor = (end_color.blue() - begin_color.blue()) / substeps
            a_factor = (end_color.alpha() - begin_color.alpha()) / substeps

            r = int(begin_color.red() + (float(i) - (base_color_index * substeps)) * r_factor)
            g = int(begin_color.green() + (float(i) - (base_color_index * substeps)) * g_factor)
            b = int(begin_color.blue() + (float(i) - (base_color_index * substeps)) * b_factor)
            a = int(begin_color.alpha() + (float(i) - (base_color_index * substeps)) * a_factor)
            colors_list.append(QColor(r, g, b, a))
        # Round problems can do than we don't arrive to last color, we force it
        colors_list[-1] = base_color_list[-1]
        return colors_list

    def get_color_list(self, begin_color, end_color, steps):
        """ Returns a colors list from initial, end color and a number of steps """
        r_factor = float(end_color.red() - begin_color.red()) / steps
        g_factor = float(end_color.green() - begin_color.green()) / steps
        b_factor = float(end_color.blue() - begin_color.blue()) / steps
        a_factor = float(end_color.alpha() - begin_color.alpha()) / steps
        colors_list = []
        for i in range(steps):
            r = int(begin_color.red() + i * r_factor)
            g = int(begin_color.green() + i * g_factor)
            b = int(begin_color.blue() + i * b_factor)
            a = int(begin_color.alpha() + i * a_factor)
            colors_list.append(QColor(r, g, b, a))
        return colors_list

    def delete_categories_by_id(self, layer_idprefix, values_list, pos=0):
        """ Elimina les categories d'una capa per id segons la llista de valors i un camp de la capa.
            Per exemple, elimina un rang de dates d'una capa de fotogrames categoritzats per data de vol
            ---
            Delete the categories of a layer by id according to the values list and a layer field.
            For instance, delete a range of dates from a photograms layer categorized by flight date
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return
        self.delete_categories(layer, values_list)

    def delete_categories(self, layer, values_list):
        """ Elimina les categories d'una capa segons la llista de valors i un camp de la capa.
            Per exemple, elimina un rang de dates d'una capa de fotogrames categoritzats per data de vol
            ---
            Delete the categories of a layer according to the values list and a layer field.
            For instance, delete a range of dates from a photograms layer categorized by flight date
            """
        # Partim de la classificació existent
        renderer = layer.renderer()

        # Eliminem les categories de la llista
        for value in values_list:
            index = renderer.categoryIndexForValue(value)
            if index < 0:
                continue
            renderer.deleteCategory(index)

        # Refresquem la capa
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        # Refresquem la llegenda
        self.refresh_legend(layer, expanded=self.is_expanded(layer))

    def get_classification_field_by_id(self, layer_idprefix, pos=0):
        """ Retorna el camp de la classificació actual a partir d'un id de capa
            ---
            Given a layer id return the current classification field
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_classification_field(layer)

    def get_classification_field(self, layer):
        """ Retorna el camp de la classificació actual
            ---
            Return the current classification field
            """
        if not hasattr(layer.renderer(), 'classAttribute'):
            return None
        return layer.renderer().classAttribute()

    def get_classification_colors_by_id(self, layer_idprefix, pos=0):
        """ Retorna els colors de la classificació actual a partir d'un id de capa
            ---
            Given a layer id return the colors of the current classification
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_classification_colors(layer)

    def get_classification_colors(self, layer):
        """ Retorna els colors de la classificació actual
            ---
            Return the colors of the current classification
            """
        renderer = layer.renderer()
        return [symbol.color() for symbol in renderer.symbols(QgsRenderContext())]

    def get_categories_by_id(self, layer_idprefix, pos=0):
        """ Obté la llista categories a partir d'un id de capa
            ---
            Gets layer categories from a layer id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_categories(layer)

    def get_categories(self, layer):
        """ Obté la llista categories d'una capa
            ---
            Gets layer categories
            """
        renderer = layer.renderer()
        if type(renderer) is not QgsCategorizedSymbolRenderer:
            return None

        # Si no ens passen cap llista de categories la generem
        categories_list = [c.value() for c in renderer.categories()]
        return categories_list

    def set_categories_visible_by_id(self, layer_idprefix, categories_list=None, enable=True, pos=0):
        """ Fa visibles o invisibles les categories de la llista a partir d'un id de capa
            Si no es passa cap llista, s'actualitzaran totes les categories
            ---
            Given a layer id make a list of categories visible or invisible
            If no list is given, all categories will be updated
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return
        self.set_categories_visible(layer, categories_list=categories_list, enable=enable)

    def set_categories_visible(self, layer, categories_list=None, enable=True):
        """ Fa visibles o invisibles les categories de la llista
            Si no es passa cap llista, s'actualitzaran totes les categories
            ---
            Given a layer id make a list of categories visible or invisible
            If no list is given, all categories will be updated
            """
        renderer = layer.renderer()
        if type(renderer) is not QgsCategorizedSymbolRenderer:
            return

        # Si no ens passen cap llista de categories la generem
        if categories_list is None:
            categories_list = [c.value() for c in renderer.categories()]

        # Activa/desactiva la visibilitat de les categories de la llista
        for category_name in categories_list:
            index = renderer.categoryIndexForValue(category_name)
            if index < 0:
                continue
            renderer.updateCategoryRenderState(index, enable)

        # Refresca la capa
        layer.setRenderer(renderer)
        layer.triggerRepaint()

        # Refresca la llegenda
        self.refresh_legend(layer, expanded=self.is_expanded(layer))

    #def enable_categories_by_id(self, layer_basename, enable=True, categories_filter_list=[], pos=0):
    #    """ Activa o desactiva les categories d'una capa per id
    #        ---
    #        Enable or disable layer categories by id
    #        """
    #    layer = self.get_by_id(layer_basename, pos)
    #    if not layer:
    #        return False
    #    return self.layerEnableCategories2(layer, enable, categories_filter_list)

    #def enable_categories(self, layer, enable=True, categories_filter_list=[]):
    #    """ Activa o desactiva les categories d'una capa
    #        ---
    #        Enable or disable layer categories
    #        """
    #    cat_nodes_list = self.get_category_nodes(layer)
    #    label_filter_list = [str(c) for c in categories_filter_list]
    #    check = Qt.Checked if enable else Qt.Unchecked
    #    for node in cat_nodes_list:
    #        if label_filter_list and node.data(Qt.DisplayRole).split(' [')[0] not in label_filter_list:
    #            continue
    #        node.setData(check, Qt.CheckStateRole)

    def zoom_to_full_extent_by_id(self, layer_idprefix, buffer=0, pos=0):
        """ Fa zoom a tot el contingut d'una capa per id. Opcionalment se li pot afegir una orla "buffer"
            ---
            Zoom in to the entire contents of a layer by id. Optionally you can add a "buffer"
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.zoom_to_full_extent(layer, buffer)

    def zoom_to_full_extent(self, layer, buffer=0):
        """ Fa zoom a tot el contingut d'una capa. Opcionalment se li pot afegir una orla "buffer"
            ---
            Zoom in to the entire contents of a layer. Optionally you can add a "buffer"
            """
        # Obtenim l'area de la capa
        if type(layer) is QgsVectorLayer and layer.featureCount() < 1:
            return False
        area = layer.extent()
        if area.area() == float('inf'):
            return False
        # Reprojectem les coordenades si cal
        layer_epsg = self.get_epsg(layer)
        project_epsg = self.parent.project.get_epsg()
        if layer_epsg and project_epsg and layer_epsg != project_epsg:
            area = self.parent.crs.transform_bounding_box(area, self.get_epsg(layer))
        # Ampliem el rectangle si cal
        if buffer:
            area = area.buffered(buffer)
        # Fem zoom a l'area
        self.iface.mapCanvas().setExtent(area)
        return True

    def ensure_visible_by_id(self, layer_idprefix, pos=0):
        """ Asegura que els elements d'una capa per id són visibles fent un zoom a la extensió si cal
            ---
            Ensure that the elements of a layer by id are visible by zooming in the extension if necessary
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.ensure_visible(layer)

    def ensure_visible(self, layer):
        """ Asegura que els elements d'una capa són visibles fent un zoom a la extensió, si cal
            ---
            Ensure that the elements of a layer are visible by zooming in the extension, if necessary
            """
        if layer.featureCount() < 1:
            return False
        if self.iface.mapCanvas().extent().contains(layer.extent()):
            return True
        return self.zoom_to_full_extent(layer)

    def get_current_layer(self):
        """ Retorna la capa seleccionada
            ---
            Return selected layer
            """
        return self.iface.activeLayer()

    def get_selected_layers(self):
        """ Retorna les capes seleccionades
            ---
            Return selected layers
            """
        return self.iface.layerTreeView().selectedLayers()

    def get_group_layers(self, group):
        """ Retorna les capes d'un grup
            ---
            Return group's layers
            """
        return self.get_group_layers_by_id(group.name())

    def get_group_layers_by_id(self, group_id):
        """ Retorna les capes d'un grup a partir del nom de group
            ---
            Return group's layers by group name
            """
        return self.get_group_children_by_id(group_id, True)

    def get_group_children(self, group, only_layers=False):
        """ Retorna els fills d'un grup o només els de tipus capa
            ---
            Return all group's children or only children type layer
            """
        return self.get_group_children_by_id(group.name())

    def get_group_children_by_id(self, group_id, only_layers=False, only_groups=False):
        """ Retorna els fills d'un grup o només els de tipus capa a partir del nom de grup
            ---
            Return all group's children or only children type layer by group name
            """
        group = self.root.findGroup(group_id)
        if not group:
            return []
        return [c.layer() if type(c) == QgsLayerTreeLayer else c for c in group.children() \
            if (type(c) == QgsLayerTreeLayer or not only_layers) and (type(c) == QgsLayerTreeGroup or not only_groups)]

    def get_group_layer_by_id(self, group_id, layer_id):
        """ Retorna les capes d'un grup
            ---
            Return group's layers
            """
        layers_list = self.get_group_layers_by_id(group_id)
        for layer in layers_list:
            if layer.id().startswith(layer_id):
                return layer
        return None

    def set_current_layer_by_id(self, idprefix, pos=0):
        """ Selecciona la capa indicada per id
            ---
            Select the layer indicated by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.set_current_layer(layer)
        return True

    def set_current_layer(self, layer):
        """ Selecciona la capa indicada
            ---
            Select the layer indicated
            """
        self.iface.setActiveLayer(layer)
        self.iface.mapCanvas().setCurrentLayer(layer)

    def get_filter_by_id(self, layer_prefix, pos=0):
        """ Retorna el filtre d'una capa per id
            ---
            Returns the filter layer by id
            """
        layer = self.get_by_id(layer_prefix, pos)
        if not layer:
            return None
        return self.get_filter(layer)

    def get_filter(self, layer):
        """ Retorna el filtre d'una capa
            ---
            Returns the filter layer
            """
        return layer.subsetString()

    def set_filter_by_id(self, layer_prefix, sql_filter, pos = 0):
        """ Assigna el filtre d'una capa per id (Equivalent a set_subset_string)
            ---
            Assign the filter of a layer by id (Equivalent to set_subset_string)
            """
        return self.set_subset_string_by_id(layer_prefix, sql_filter, pos)

    def set_filter(self, layer, sql_filter):
        """ Assigna el filtre d'una capa (Equivalent a set_subset_string)
            ---
            Assign the filter of a layer (Equivalent to set_subset_string)
            """
        return self.set_subset_string(layer, sql_filter)

    def set_subset_string_by_id(self, layer_prefix, sql_filter, pos=0):
        """ Assigna el filtre d'una capa per id (Equivalent a set_filter)
            ---
            Assign the filter of a layer by id (Equivalent to set_filter)
            """
        layer = self.get_by_id(layer_prefix, pos)
        if not layer:
            return False
        return self.set_subset_string(layer, sql_filter)

    def set_subset_string(self, layer, sql_filter):
        """ Assigna el filtre d'una capa (Equivalent a set_filter)
            ---
            Assign the filter of a layer (Equivalent to set_filter)
            """
        return layer.setSubsetString(sql_filter)

    def add_layer(self, layer):
        """ Afegeix una capa
            ---
            Add a layer
            """
        QgsProject.instance().addMapLayer(layer)

    def remove_layer_by_id(self, layer_idprefix, pos=0):
        """ Esborra una capa a partir del seu id
            ---
            Delete a layer by id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.remove_layer(layer)
        return True

    def remove_layer(self, layer):
        """ Esborra una capa
            ---
            Delete a layer
            """
        QgsProject.instance().removeMapLayer(layer.id())

    def save_shape_file_by_id(self, idprefix, pathname, encoding="utf-8", epsg=None, pos=0):
        """ Guarda el contingut d'una capa vectorial per id com un shape
            ---
            Save the contents of a vector layer by id as a shape
            """
        return self.save_vector_file_by_id(idprefix, pathname, "ESRI Shapefile", encoding, epsg, pos)

    def save_shape_file(self, layer, pathname, encoding="utf-8", epsg=None):
        """ Guarda el contingut d'una capa vectorial com un shape
            ---
            Save the contents of a vector layer as a shape
            """
        return self.save_vector_file(layer, pathname, "ESRI Shapefile", encoding, epsg)

    def save_vector_file_by_id(self, idprefix, pathname, format="GeoJSON", encoding="utf-8", epsg=None, pos=0):
        """ Guarda el contingut d'una capa vectorial per id com un fitxer vectorial
            ---
            Save the contents of a vector layer by id as a vectorial file
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.save_vector_file(layer, pathname, format, encoding, epsg)

    def save_vector_file(self, layer, pathname, format="GeoJSON", encoding="utf-8", epsg=None):
        """ Guarda el contingut d'una capa vectorial com un fitxer vectorial
            ---
            Save the contents of a vector layer as a vectorial file
            """
        if not epsg:
            epsg = self.get_epsg(layer)
        crs = self.parent.crs.get_crs(epsg)
        return QgsVectorFileWriter.writeAsVectorFormat(layer, pathname, encoding, crs, format) == QgsVectorFileWriter.NoError

    def rename_fields_by_id(self, idprefix, rename_dict, pos=0):
        """ Reanomena camps d'una capa a partir del seu id
            ---
            Rename fields of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.rename_fields(layer, rename_dict)

    def rename_fields(self, layer, rename_dict):
        """ Reanomena camps d'una capa
            ---
            Rename fields of a layer
            """
        new_names_dict = dict([(layer.dataProvider().fieldNameIndex(field.name()), rename_dict[field.name()]) for field in layer.fields() if field.name() in rename_dict]) if layer else {}
        if not new_names_dict:
            return False
        layer.dataProvider().renameAttributes(new_names_dict)
        layer.updateFields()
        return True

    def set_field_alias_by_id(self, layer_idprefix, field_index, field_alias, pos=0):
        """ Assigna un alias a un camp d'una capa
            ---
            Assign an alias to a layer's field
        """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.set_field_alias(layer, field_index, field_alias)
        return True

    def set_field_alias(self, layer, field_index, field_alias):
        """ Assigna un alias a un camp d'una capa
            ---
            Assign an alias to a layer's field
        """
        layer.setFieldAlias(field_index, field_alias)

    def set_fields_alias_by_id(self, idprefix, alias_dict, pos=0):
        """ Assigna alies als camps d'una capa a partir del seu id
            ---
            Set alias of field layers by id
            """
        """ Reanomena camps d'una capa a partir del seu id
            ---
            Rename fields of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.set_fields_alias(layer, alias_dict)

    def set_fields_alias(self, layer, alias_dict):
        """ Assigna alies als camps d'una capa
            ---
            Set alias of field layers
            """
        for field_name, alias in  alias_dict.items():
            layer.setFieldAlias(layer.fields().indexFromName(field_name), alias)

    def delete_fields_by_id(self, idprefix, names_list, pos=0):
        """ Esborra camps d'una capa per id
            ---
            Delete fields of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.delete_fields(layer, names_list)

    def delete_fields(self, layer, names_list):
        """ Esborra camps d'una capa
            ---
            Delete fields of a layer
            """
        layer.dataProvider().deleteAttributes([layer.dataProvider().fieldNameIndex(field_name) for field_name in names_list])
        layer.updateFields()
        return True

    def enable_color_expansion_by_id(self, idprefix, enable=True, pos=0):
        """ Activa la expansió de colors un una capa raster per id
            ---
            Enable raster layer color expansion by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.enable_color_expansion(layer, enable)
        return True

    def enable_color_expansion(self, layer, enable=True):
        """ Activa la expansió de colors un una capa raster
            ---
            Enable raster layer color expansion
            """
        if enable:
            layer.setContrastEnhancement(QgsContrastEnhancement.StretchToMinimumMaximum, QgsRasterMinMaxOrigin.MinMax)
        else:
            layer.setContrastEnhancement(QgsContrastEnhancement.NoEnhancement)

    def set_nodata_by_id(self, idprefix, no_data, pos=0):
        """ Assigna un valor no data a una capa raster per id
            ---
            Assign a no data value to a raster layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.set_nodata(layer, no_data)

    def set_nodata(self, layer, no_data):
        """ Assigna un valor no data a una capa raster
            ---
            Assign a no data value to a raster layer
            """
        renderer = layer.renderer() # Si el WMS no carrega dades, el renderer és None
        if not renderer:
            return False
        if layer.bandCount() > 1:
            renderer.rasterTransparency().initializeTransparentPixelList(no_data, no_data, no_data) # Per imatges color
        else:
            renderer.rasterTransparency().initializeTransparentPixelList(no_data) # Per imatges BW
        return True

    def set_transparency_by_id(self, idprefix, transparency, pos=0):
        """ Canvia la transparència d'una capa per id
            ---
            Change the transparency of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.set_transparency(layer, transparency)

    def set_transparency(self, layer, transparency):
        """ Canvia la transparència d'una capa
            ---
            Change the transparency of a layer
            """
        opacity = (100 - transparency) / 100
        if layer.type() == 0: # Si es vectorial
            layer.setOpacity(opacity)
        else:
            renderer = layer.renderer() # Si el WMS no carrega dades, el renderer és None
            if not renderer:
                return False
            renderer.setOpacity(opacity)
        return True

    def set_custom_properties_by_id(self, idprefix, properties_dict, pos=0):
        """ Canvia propietats custom d'una capa per id
            ---
            Change custom properties of a layer for id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.set_custom_properties_by_id(layer, properties_dict)
        return True

    def set_custom_properties(self, layer, properties_dict):
        """ Canvia propietats custom d'una capa
            ---
            Change custom properties of a layer
            """
        for property, value in properties_dict.items():
            layer.setCustomProperty(property, value)

    def set_properties_by_id(self, idprefix, visible=None, collapsed=None, group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, min_scale=None, max_scale=None, transparency=None, saturation=None, set_current=False, properties_dict=None, pos=0):
        """ Canvia les propietats d'una capa. Veure set_properties per opcions
            ---
            Change custom properties of a layer. See set_properties for options
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.set_properties(layer, visible, collapsed, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, min_scale, max_scale, transparency, saturation, set_current, properties_dict)
        return True

    def set_saturation_by_id(self, idprefix, saturation, refresh=False, pos=0):
        """ Canvia la saturació de color d'una capa per id
            ---
            Change color saturation of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.set_saturation(layer, saturation, refresh)
        return True

    def set_saturation(self, layer, saturation, refresh=False):
        """ Canvia la saturació de color d'una capa
            ---
            Change color saturation of a layer
            """
        filter = QgsHueSaturationFilter()
        filter.setSaturation(saturation)
        layer.pipe().set(filter)
        if refresh:
            layer.triggerRepaint()

    def set_properties(self, layer, visible=None, collapsed=None, group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, min_scale=None, max_scale=None, transparency=None, saturation=None, set_current=False, properties_dict=None):
        """ Canvia les propietats d'una capa:
            - visible: Carrega la capa deixant-la visible o no
            - collapsed: Colapsa la llegenda de la capa
            - group_name: Crea o utilitza un grup on posar totes les capes
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - only_one_map_on_group: Indica que només pot haver una imatge en el grup, la última imatge esborra les capes anterior
            - only_one_visible_map_on_group: Especifica que només tindrem una única capa visible dins el grup
            - min_scale, max_scala: Activa la visualització per escala
            - transparency: Activa factor de transparència
            - saturation: Saturació de color [-100, 100]
            - properties_dict: defineix propietats particulars d'usuari
            ---
            Change custom properties of a layer:
            - visible: Load the layer by leaving it visible or not
            - collapsed: Collapse the legend of the layer
            - group_name: Create or use a group where to put all the layers
            - group_pos: Create group on specific position (if None then to the end)
            - only_one_map_on_group: Indicates that there can only be an image in the group, the last image deletes the previous layers
            - only_one_visible_map_on_group: Specifies that we will only have one visible layer in the group
            - min_scale, max_scale: Activates the scale view
            - transparency: Activate transparency factor
            - saturation: Color saturation [-100, 100]
            - properties_dict: define custom properties
            """
        # Canviem la visiblitat per escala si cal
        if min_scale != None and max_scale != None:
            self.set_scale_based_visibility(layer, min_scale, max_scale)
        # Canviem la transparència si cal
        if transparency is not None:
            self.set_transparency(layer, transparency)
        # Canvia la saturació dels canals
        if saturation is not None:
            self.set_saturation(layer, saturation)
        # Canviem propiestats custom
        if properties_dict is not None:
            self.set_custom_properties(layer, properties_dict)
        # Vellugem la capa dins un grup si cal
        if group_name:
            group = self.parent.legend.get_group_by_name(group_name)
            if group:
                self.parent.legend.set_group_visible(group)
                if only_one_map_on_group:
                    self.parent.legend.empty_group_by_name(group_name, exclude_list=[layer])
                elif only_one_visible_map_on_group:
                    self.parent.legend.set_group_items_visible_by_name(group_name, False)
            self.parent.legend.move_layer_to_group_by_name(group_name, layer, True, group_pos)
        # Canviem la visibilitat si cal
        if visible is not None:
            self.set_visible(layer, visible)
        # Canviem el colapsament si cal
        if collapsed is not None:
            self.collapse(layer, collapsed)
        # Seleccionem la capa si cal
        if set_current:
            self.set_current_layer(layer)

    def add_remote_layer_definition_file(self, remote_file, local_file=None, download_folder=None, group_name=None, group_pos=None, create_qlr_group=True, select_folder_text=None):
        """ Descarrega fitxers QLR o ZIP via http en la carpeta especificada i els obre a QGIS.
            Veure add_layer_definition_file per opcions
            ---
            Download http QLR or ZIP files in the specified folder and open them to QGIS.
            See add_layer_definition_file for options
            """
        # Descarreguem el fitxer si cal
        local_pathname = self.download_remote_file(remote_file, local_file, download_folder, select_folder_text)
        if not local_pathname:
            return False
        # Carreguem el fitxer
        return self.add_layer_definition_file(local_pathname, group_name, group_pos, create_qlr_group)

    def add_layer_definition_file(self, qlr_pathname, group_name=None, group_pos=None, create_qlr_group=True, unzip=True):
        """ Carrega un arxiu de definició de capes QLR a l'arrel del projecte o dins un carpeta
            - qlr_pathname: Arxiu a carregar
            - group_name: Crea o utilitza un grup on posar totes les capes
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - create_qlr_group: Crea un grup amb el nom del fitxer QLR
            - unzip: Si el fitxer és un zip, el descomprimeix o no (si no es descomprimeix les capes seràn de només lectura)
            Retorna True si tot ha anat bé
            ---
            Loads a layer definition file on project's root or in a specified folder
            - qlr_pathname: File to load
            - group_name: Create or use a group where to put all the layers
            - group_pos: Create group on specific position (if None then to the end)
            - create_qlr_group: Create group with QLR filename
            - unzip: If file is a zipfile then unzip it or not (if not descompress layers, layers will be read only)
            Returns True if all ok
            """
        # Si ens passen un arxiu comprimit, mirem si a dins hi ha un QLR
        filename, ext = os.path.splitext(os.path.basename(qlr_pathname.lower()))

        # Obtenim la referència del grup on carregar l'arxiu QLR (el creem si cal)
        if group_name:
            group = self.parent.legend.get_group_by_name(group_name)
            if not group:
                group = self.parent.legend.add_group(group_name, group_pos=group_pos)
        else:
            group = QgsProject.instance().layerTreeRoot()
        if create_qlr_group:
            group = self.parent.legend.add_group(filename, group_parent_name=group_name) # Crea el pare si cal

        # Carreguem el QLR
        is_zipped_file = (ext == ".zip")
        qlr_data = None
        if is_zipped_file:
            if unzip:
                # Descomprimim el zip
                unzip_folder = os.path.splitext(qlr_pathname)[0]
                with zipfile.ZipFile(qlr_pathname) as zip_file:
                    zip_file.extractall(unzip_folder)
                # Esborrem el zip
                os.remove(qlr_pathname)
                # Obtenim el qlr descomprimit (Si hi ha més d'un ens quedem el primer)
                pathnames_list = [os.path.join(unzip_folder, filename) for filename in os.listdir(unzip_folder) if os.path.splitext(filename.lower())[1] == ".qlr"]
                if not pathnames_list:
                    return False
                qlr_pathname = pathnames_list[0]
                # Carreguem les capes del QLR a partir del fitxer QLR descomprimit
                ##print("Arxiu QLR: %s" % (qlr_pathname))
                status, error = QgsLayerDefinition().loadLayerDefinition(qlr_pathname, QgsProject.instance(), group)
            else:
                # ATENCIÓ!! Treballar amb QLRs dins de zips sense descomprimir fa que els shapes associats no siguin editables
                # Generem una llista amb tots els shapes dins el zip
                with zipfile.ZipFile(qlr_pathname) as zip_file:
                    pathnames_list = [compressed_file for compressed_file in zip_file.namelist() if os.path.splitext(compressed_file.lower())[1] == ".qlr"]
                    if not pathnames_list:
                        return False
                    ##print("Arxiu QLR: %s/%s" % (qlr_pathname, pathnames_list[0]))
                    # Llegim el primer QLR que trobem, els altres els IGNORA
                    with zip_file.open(pathnames_list[0]) as qlr_file:
                        qlr_data = qlr_file.read().decode('utf-8')
                if not qlr_data:
                    return False

                # Modifiquem el QLR perquè apunti als fitxers que hi ha dins el ZIP
                qlr_data = qlr_data.replace('./', '/vsizip/%s/' % qlr_pathname)
                qlr_data = qlr_data.replace('\ufeff', '') # Elimina codificació BOM (en UTF8)

                # Generem un document amb les capes del QLR a partir de les dades XML modificades
                qlr_doc = QDomDocument()
                qlr_doc.setContent(qlr_data)
                context = QgsReadWriteContext()

                # Carreguem el QLR
                #layers_list = QgsLayerDefinition.loadLayerDefinitionLayers(qlr_doc, context)
                ##print("QLR layers %s" % [layer.name() for layer in layers_list])
                #QgsProject.instance().addMapLayers(layers_list, False)
                ## Afegim les capes a QGIS dins el grup que calgui
                #for layer in layers_list:
                #    group.addLayer(layer)
                #status = layers_list != []
                status, error = QgsLayerDefinition().loadLayerDefinition(qlr_doc, QgsProject.instance(), group, context)
        else:
            # Carreguem les capes del QLR a partir del fitxer QLR
            ##print("Arxiu QLR: %s" % (qlr_pathname))
            status, error = QgsLayerDefinition().loadLayerDefinition(qlr_pathname, QgsProject.instance(), group)

        # Colapsem el grup
        if status and create_qlr_group:
            self.parent.legend.collapse_group_by_name(filename)

        return status

    def add_raster_files(self, files_list, group_name=None, group_pos=None, epsg=None, ref_layer=None, min_scale=None, max_scale=None, no_data=None, layer_name=None, color_default_expansion=False, visible=True, expanded=False, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False, style_file=None, properties_dict_list=[], only_one_map_on_group=False, only_one_visible_map_on_group=True):
        """ ATENCIÓ, TÉ UNA REIMPLEMENTACIÓ A pluginicgcbase
            Afegeix una llista de capes raster a partir dels seus fitxers. Opcionament se li pot especificar:
            - group_name: Crea o utilitza un grup on posar totes les capes
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - ref_layer: Capa de referencia de la qual ens copiem la visualització per escala
            - epsg: Especifica el sistema de coordenades de la imatge (epsg int)
            - min_scale, max_scala: Activa la visualització per escala
            - no_data: Especifica valor per nodata
            - layer_name: Especifica el nom de la capa, per defecte és el mateix que el nom de fitxer
            - color_default_expansion: Activa la expansió de colors automàtica
            - visible: Carrega la capa deixant-la visible o no
            - expanded: Espandeix la llegenda de la capa
            - transparency: Activa factor de transparència
            - saturation: Canvia el valor de saturació de la imatge
            - set_current: Selecciona la capa com l'activa
            - style_file: Especifica un fitxer d'estil .qgs a carregar amb les propietats de la capa
            - properties_dict_list: defineix propietats particulars d'usuari per cada capa carregada
            - only_one_map_on_group: Indica que només pot haver una imatge en el grup, la última imatge esborra les capes anterior
            - only_one_visible_map_on_group: Especifica que només tindrem una única capa visible dins el grup
            ---
            Adds a list of raster layers from your files. Options can be specified:
            - group_name: Create or use a group where to put all the layers
            - group_pos: Create group on specific position (if None then to the end)
            - epsg: Specifies coordinates system of image (epsg int)
            - ref_layer: Reference layer from which we copied the view by scale
            - min_scale, max_scale: Activates the scale view
            - no_data: Specifies value for nodata
            - layer_name: Specifies the name of the layer, the default is the same as the file name
            - color_default_expansion: Enables automatic color expansion
            - visible: Load the layer by leaving it visible or not
            - expanded: Expand the legend of the layer
            - transparency: Activate transparency factor
            - saturation: Changes saturation value
            - set_current: Set layer as current selected layer
            - style_file: Specifies a .qgs style file to load with the properties of the layer
            - properties_dict_list: define custom properties for each loaded layer
            - only_one_map_on_group: Indicates that there can only be an image in the group, the last image deletes the previous layers
            - only_one_visible_map_on_group: Specifies that we will only have one visible layer in the group
            """
        # Ens guardem la capa activa
        active_layer = self.iface.activeLayer()

        ### Recuperem les capes que hi ha dins el grup (si ens el passen)
        ##layers_list = self.get_group_layers_id(group_name) if group_name else []

        # Obtenim el min i max escala de visualitzacio
        if not min_scale or not max_scale:
            if ref_layer:
                if not min_scale:
                    min_scale = ref_layer.minimumScale()
                if not max_scale:
                    max_scale = ref_layer.maximumScale()

        # Afegim totes les ortos que ens passen
        layers_list = []
        error_files = []
        for i, filename in enumerate(files_list):
            # Determinem el nom de la capa
            if not layer_name:
                name = os.path.splitext(os.path.basename(filename))[0]
            elif layer_name.find('%s') >= 0:
                name = (layer_name % os.path.splitext(os.path.basename(filename))[0])
            else:
                name = layer_name
            ### Si existeix la capa no cal afegir-la
            ##if any([str(layer).startswith(name) for layer in layers_list]):
            ##    continue

            # Detectem si existeix el fitxer
            if not os.path.exists(filename):
                error_files.append(filename)
                layers_list.append(None)

            # Si no existeix la capa l'afegim
            properties_dict = properties_dict_list[i] if properties_dict_list else None
            last_layer = self.add_raster_layer(name, filename, group_name, group_pos, epsg, ref_layer, min_scale=min_scale, max_scale=max_scale, no_data=no_data, color_default_expansion=color_default_expansion, visible=visible, expanded=expanded, transparency=transparency, saturation=saturation, resampling_bilinear=resampling_bilinear, resampling_cubic=resampling_cubic, set_current=set_current, style_file=style_file, properties_dict=properties_dict, only_one_map_on_group=only_one_map_on_group, only_one_visible_map_on_group=only_one_visible_map_on_group)
            if not last_layer:
                error_files.append(filename)
            layers_list.append(last_layer)

        # Mostrem errors
        if len(error_files) > 0:
            LogInfoDialog(
                "Error files not found: %d:\n   %s" % (len(error_files), "\n   ".join(error_files)),
                "Error raster files",
                LogInfoDialog.mode_error)

        # Restaurem la capa activa
        self.iface.setActiveLayer(active_layer)

        # Retornem la última imatge processada
        return layers_list

    def add_raster_layer(self, name, filename, group_name=None, group_pos=None, epsg=None, ref_layer=None, min_scale=None, max_scale=None, no_data=None, color_default_expansion=False, visible=True, expanded=False, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False, style_file=None, properties_dict=None, only_one_map_on_group=False, only_one_visible_map_on_group=True):
        """ Afegeix una capa raster a partir d'un nom de capa i un fitxer. Opcionament se li pot especificar:
            - group_name: Crea o utilitza un grup on posar totes les capes
            - ref_layer: Capa de referencia de la qual ens copiem la visualització per escala
            - epsg: Especifica el sistema de coordenades de la imatge (epsg int)
            - min_scale, max_scala: Activa la visualització per escala
            - no_data: Especifica valor per nodata
            - color_default_expansion: Activa la expansió de colors automàtica
            - visible: Carrega la capa deixant-la visible o no
            - expanded: Espandeix la llegenda de la capa
            - transparency: Activa factor de transparència
            - saturation: Canvia el valor de saturació de la imatge
            - set_current: Selecciona la capa com l'activa
            - style_file: Especifica un fitxer d'estil .qgs a carregar amb les propietats de la capa
            - properties_dict: defineix propietats particulars d'usuari
            - only_one_map_on_group: Indica que només pot haver una imatge en el grup, la última imatge esborra les capes anterior
            - only_one_visible_map_on_group: Especifica que només tindrem una única capa visible dins el grup
            ---
            Adds a raster layer from layer name an file. Options can be specified:
            - group_name: Create or use a group where to put all the layers
            - ref_layer: Reference layer from which we copied the view by scale
            - epsg: Specifies coordinates system of image (epsg int)
            - min_scale, max_scale: Activates the scale view
            - no_data: Specifies value for nodata
            - color_default_expansion: Enables automatic color expansion
            - visible: Load the layer by leaving it visible or not
            - expanded: Expand the legend of the layer
            - transparency: Activate transparency factor
            - saturation: Changes saturation value
            - set_current: Set layer as current selected layer
            - style_file: Specifies a .qgs style file to load with the properties of the layer
            - properties_dict: define custom properties
            - only_one_map_on_group: Indicates that there can only be an image in the group, the last image deletes the previous layers
            - only_one_visible_map_on_group: Specifies that we will only have one visible layer in the group
            """
        # Detectem si hi ha algun grup seleccionat (que s'expandirà al carregar la capa i no volem)
        selected_groups = self.parent.legend.get_selected_groups()
        parent_group = selected_groups[0] if len(selected_groups) == 1 else None
        collapsed_parent_group = parent_group and not parent_group.isExpanded()

        # Afegim la capa raster
        layer = self.iface.addRasterLayer(filename, name)
        if not layer:
            return None

        # Assignem l'EPSG de la capa
        if epsg:
            layer.setCrs(layer.crs().fromEpsgId(epsg))
        # Canviem l'estil de la capa si cal
        if style_file:
            self.load_style(layer, style_file, refresh=True)
        # Assigne el valor no data si cal
        if no_data is not None:
            self.set_nodata(layer, no_data)
        # Desactivem la expansió de colors si cal
        if not color_default_expansion:
            self.enable_color_expansion(layer, False)
        # Obtenim el min i max escala de visualitzacio
        if not min_scale or not max_scale:
            if ref_layer:
                if not min_scale:
                    min_scale = ref_layer.minimumScale()
                if not max_scale:
                    max_scale = ref_layer.maximumScale()
        # Ajustem el mostreig si cal
        if resampling_bilinear:
            resample_filter = layer.resampleFilter()
            resample_filter.setZoomedInResampler(QgsBilinearRasterResampler())
            resample_filter.setZoomedOutResampler(QgsBilinearRasterResampler())
        if resampling_cubic:
            resample_filter = layer.resampleFilter()
            resample_filter.setZoomedInResampler(QgsCubicRasterResampler())
            resample_filter.setZoomedOutResampler(QgsCubicRasterResampler())
        # Canviem les propiedats de la capa
        self.set_properties(layer, visible, not expanded, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, min_scale, max_scale, transparency, saturation, set_current, properties_dict)

        # Si he mogut la capa dins un grup, no volem que s'expandeix el grup que hi havia seleccionat
        if group_name:
            if collapsed_parent_group:
                parent_group.setExpanded(False)

        return layer

    def get_download_path(self, select_folder_text=None):
        """ Obté la carpeta de descàrregues i opcionalment (select_folder_text<>None) la pregunta si no està definida o no existeix
            ---
            Gets the download folder and optionally (select_folder_text <> None) asks if it is not defined or does not exist
        """
        # Obtenim la carpeta de la configuració del plugin
        download_folder = self.parent.get_setting_value("download_folder")
        if (not download_folder or not os.path.exists(download_folder)) and select_folder_text:
            # Si no tenim la carpeta definida, la preguntem
            download_folder = self.set_download_path(select_folder_text, download_folder)
        return download_folder

    def set_download_path(self, select_folder_text, default_folder=None):
        """ Assigna la carpeta de descàrregues
            ---
            Sets download folder
        """
        # Obtenim la carpeta de descàrrega per defecte
        if not default_folder:
            default_folder = self.parent.get_setting_value("download_folder")
        if not default_folder:
            default_folder = str(pathlib.Path.home())

        # Preguntem la nova carpeta de descàrregues
        download_folder = QFileDialog.getExistingDirectory(self.iface.mainWindow(),
            select_folder_text, default_folder, QFileDialog.ShowDirsOnly)
        if not download_folder:
            return None

        # Guardem la configuració
        self.parent.set_setting_value("download_folder", download_folder)

        return download_folder

    def open_download_path(self, select_folder_text=None, filename=None):
        """ Obre l'arxiu especificat o la carpeta de descàrregues i opcionalment (select_folder_text<>None)
            la pregunta si no està definida o no existeix
            ---
            Open specified file or the download folder and optionally (select_folder_text <> None)
            asks if it is not defined or does not exist
        """
        download_folder = self.get_download_path(select_folder_text)
        if filename:
            download_folder = os.path.join(download_folder, filename)
        if download_folder and os.path.exists(download_folder):
            self.parent.gui.open_file_folder(download_folder)

    def download_remote_file(self, remote_file, local_filename=None, download_folder=None, select_folder_text=None, unzip=False):
        """ Descarrega un fitxer via http en la carpeta especificada
            ---
            Download a http file in the specified folder
            """
        # Si no ens la especifiquem, obtenim la carpeta de descàrrega de la
        # configuració del plugin
        if not download_folder:
            download_folder = self.get_download_path(select_folder_text)
            if not download_folder:
                return None

        # Construim el path de descàrrega
        if not local_filename:
            local_filename = os.path.basename(remote_file)
        local_pathname = os.path.join(download_folder, local_filename)

        # Descarreguem el fitxer
        self.download_manager.download(remote_file, local_pathname)
        
        # Descomprimim el fitxer si cal
        unzip_folder, ext = os.path.splitext(local_pathname)
        is_zipped_file = (ext == ".zip")
        if is_zipped_file and unzip:
            # Descomprimim
            with zipfile.ZipFile(local_pathname) as zip_file:
                zip_file.extractall(unzip_folder)
            # Esborrem el zip
            os.remove(local_pathname)
            local_pathname = unzip_folder

        return local_pathname

    def add_remote_raster_file(self, remote_file, local_file=None, download_folder=None, group_name=None, group_pos=None, epsg=None, ref_layer=None, min_scale=None, max_scale=None, no_data=None, layer_name=None, color_default_expansion=False, visible=True, expanded=False, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False, style_file=None, properties_dict=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, select_folder_text=None):
        """ Descarrega fitxers raster via http en la carpeta especificada i els obre a QGIS.
            Veure add_raster_files per opcions
            ---
            Download http raster files in the specified folder and open them to QGIS.
            See add_raster_files for options
            """
        # Descarreguem el fitxer si cal
        local_pathname = self.download_remote_file(remote_file, local_file, download_folder, select_folder_text)
        if not local_pathname:
            return None
        # Carreguem el fitxer
        return self.add_raster_layer(layer_name, local_pathname, group_name, group_pos, epsg, ref_layer, min_scale, max_scale, no_data, color_default_expansion, visible, expanded, transparency, saturation, resampling_bilinear, resampling_cubic, set_current, style_file, properties_dict, only_one_map_on_group, only_one_visible_map_on_group)

    def add_remote_raster_files(self, remote_files_list, download_folder=None, group_name=None, group_pos=None, epsg=None, ref_layer=None, min_scale=None, max_scale=None, no_data=None, layer_name=None, color_default_expansion=False, visible=True, expanded=False, transparency=None, saturation=None, set_current=False, style_file=None, properties_dict_list=[], only_one_map_on_group=False, only_one_visible_map_on_group=True, select_folder_text=None):
        """ Descarrega fitxers raster via http en la carpeta especificada i els obre a QGIS.
            Veure add_raster_files per opcions
            ---
            Download http raster files in the specified folder and open them to QGIS.
            See add_raster_files for options
            """
        layers_list = []
        for remote_file in remote_files_list:
            # Descarreguem el fitxer si cal
            local_pathname = self.download_remote_file(remote_file, None, download_folder, select_folder_text)
            # Carreguem el fitxer
            if local_pathname:
                last_layer = self.add_raster_layer(layer_name, local_pathname, group_name, group_pos, epsg, ref_layer, min_scale, max_scale, no_data, color_default_expansion, visible, expanded, transparency, saturation, set_current, style_file, properties_dict_list, only_one_map_on_group, only_one_visible_map_on_group)
            else:
                last_layer = None
            layers_list.append(last_layer)
        # Retorna la última capa
        return layers_list

    def add_vector_files(self, files_list, group_name=None, group_pos=None, min_scale=None, max_scale=None, layer_name=None, visible=True, expanded=False, transparency=None, set_current=False, style_file=None, regex_styles_list=None, properties_dict_list=[], only_one_map_on_group=False, only_one_visible_map_on_group=True):
        """ Afegeix capes vectorials a partir d'una llista de fitxers. Opcionament se li pot especificar:
            - group_name: Crea o utilitza un grup on posar totes les capes
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - min_scale, max_scala: Activa la visualització per escala
            - layer_name: Especifica el nom de la capa, per defecte és el mateix que el nom de fitxer
            - visible: Carrega la capa deixant-la visible o no
            - expanded: Espandeix la llegenda de la capa
            - transparency: Activa factor de transparència
            - set_current: Selecciona la capa com l'activa
            - style_file: Especifica un fitxer d'estil .qgs a carregar amb les propietats de la capa
            - regex_style_list: Especifica una llista de fitxers d'estil .qgs amb una expressió regular associada
            - properties_dict_list: defineix propietats particulars d'usuari per cada capa carregada
            - only_one_map_on_group: Indica que només pot haver una imatge en el grup, la última imatge esborra les capes anterior
            ---
            Adds vector layers from a list of files. Options can be specified:
            - group_name: Create or use a group where to put all the layers
            - group_pos: Create group on specific position (if None then to the end)
            - min_scale, max_scale: Activates the scale view
            - layer_name: Specifies the name of the layer, the default is the same as the file name
            - visible: Load the layer by leaving it visible or not
            - expanded: Expand the legend of the layer
            - transparency: Activate transparency factor
            - set_current: Set layer as current selected layer
            - style_file: Specifies a .qgs style file to load with the properties of the layer
            - regex_styles_List: Specifies a .qgs styles list with an associated regular expression
            - properties_dict_list: define custom properties for each loaded layer
            - only_one_map_on_group: Indicates that there can only be an image in the group, the last image deletes the previous layers
            """
        # Ens guardem la capa activa
        active_layer = self.iface.activeLayer()

        ### Recuperem les capes que hi ha dins el grup (si ens el passen)
        ##layers_list = self.get_group_layers_id(group_name) if group_name else []

        # Afegim totes les imatges que ens passin
        layers_list = []
        error_files = []
        last_layer = None
        for i, filename in enumerate(files_list):
            # Obtenim el nom de la capa a crear
            if not layer_name:
                name = os.path.splitext(os.path.basename(filename))[0]
            elif layer_name.find('%s') >= 0:
                name = (layer_name % os.path.splitext(os.path.basename(filename))[0])
            else:
                name = layer_name
            ### Si existeix la capa, ens la saltem
            ##if any([str(layer).startswith(name) for layer in layers_list]):
            ##    continue

            # Detectem si existeix el fitxer
            if not os.path.exists(filename):
                error_files.append(filename)
                layers_list.append(None)
                continue

            # Creem la capa (alguns arxius multicapa, no retornen la capa)
            last_layer = self.add_vector_layer(name, filename, group_name, group_pos, min_scale, max_scale, visible, expanded, transparency, set_current, style_file, regex_styles_list, properties_dict_list, only_one_map_on_group, only_one_visible_map_on_group)
            if not last_layer:
                 error_files.append(filename)
            layers_list.append(last_layer)

        # Mostrem errors
        if len(error_files) > 0:
            LogInfoDialog(
                "Error files not found: %d:\n   %s" % (len(error_files), "\n   ".join(error_files)),
                "Error vector files",
                LogInfoDialog.mode_error)

        # Restaurem la capa activa
        self.iface.setActiveLayer(active_layer)

        # Retornem la última capa inserida
        return layers_list

    def add_vector_layer(self, name, pathname, group_name=None, group_pos=None, min_scale=None, max_scale=None, visible=True, expanded=False, transparency=None, set_current=False, style_file=None, regex_styles_list=None, properties_dict_list=[], only_one_map_on_group=False, only_one_visible_map_on_group=True):
        """ Afegeix una cape vectorial a partir d'un nom de capa i un fitxer. Opcionament se li pot especificar:
            - layer_name: Especifica el nom de la capa, per defecte és el mateix que el nom de fitxer
            - group_name: Crea o utilitza un grup on posar totes les capes
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - min_scale, max_scala: Activa la visualització per escala
            - visible: Carrega la capa deixant-la visible o no
            - expanded: Espandeix la llegenda de la capa
            - transparency: Activa factor de transparència
            - set_current: Selecciona la capa com l'activa
            - style_file: Especifica un fitxer d'estil .qgs a carregar amb les propietats de la capa
            - regex_style_list: Especifica una llista de fitxers d'estil .qgs amb una expressió regular associada
            - properties_dict_list: defineix propietats particulars d'usuari per cada capa carregada
            - only_one_map_on_group: Indica que només pot haver una imatge en el grup, la última imatge esborra les capes anterior
            ---
            Adds a vector layer from a layer name and file. Options can be specified:
            - layer_name: Specifies the name of the layer, the default is the same as the file name
            - group_name: Create or use a group where to put all the layers
            - group_pos: Create group on specific position (if None then to the end)
            - min_scale, max_scale: Activates the scale view
            - visible: Load the layer by leaving it visible or not
            - expanded: Expand the legend of the layer
            - transparency: Activate transparency factor
            - set_current: Set layer as current selected layer
            - style_file: Specifies a .qgs style file to load with the properties of the layer
            - regex_styles_List: Specifies a .qgs styles list with an associated regular expression
            - properties_dict_list: define custom properties for each loaded layer
            - only_one_map_on_group: Indicates that there can only be an image in the group, the last image deletes the previous layers
            """
        # Detectem si hi ha algun grup seleccionat (que s'expandirà al carregar la capa i no volem)
        selected_groups = self.parent.legend.get_selected_groups()
        parent_group = selected_groups[0] if len(selected_groups) == 1 else None
        collapsed_parent_group = parent_group and not parent_group.isExpanded()

        # Detectem arxius zip per tractar-los con la càrrega de N arxius
        filename, ext = os.path.splitext(os.path.basename(pathname.lower()))
        is_zipped_file = ext == ".zip"
        is_geopackage_file = ext == ".gpkg"
        add_geopackage_group = is_geopackage_file and not self.parent.check_qgis_version(32200)
        if is_zipped_file:
            # Generem una llista amb tots els shapes dins el zip
            with zipfile.ZipFile(pathname) as zip_file:
                pathnames_list = ["/vsizip/%s/%s" % (pathname, compressed_file) for compressed_file in zip_file.namelist() if os.path.splitext(compressed_file.lower())[1] == ".shp"]
                styles_list = [compressed_file for compressed_file in zip_file.namelist() if os.path.splitext(compressed_file.lower())[1] == ".qml"]
                styles_dict = {}
                for compressed_file in styles_list:
                    with zip_file.open(compressed_file) as fin:
                        styles_dict[os.path.splitext(compressed_file)[0]] = fin.read().decode()
                # Si tenim llista d'estils a aplicar, ordenarem els fitxers seguint el criteri de la llista
                if regex_styles_list:
                    # Utilitzo una funció local per fer la ordenació seguint el criteri de la llista d'estils
                    def sort_file_index(pathname):
                        filename = os.path.basename(pathname)
                        for index, (style_regex, _style_qml) in enumerate(regex_styles_list):
                            if re.match(style_regex, filename):
                                ##print("Filename order", index, filename)
                                return index
                        return 9999
                    pathnames_list.sort(key=sort_file_index, reverse=True)
            pathnames_list = [(pathname, name) for pathname in pathnames_list]
        elif is_geopackage_file:
            # Generem una llista amb totes les capes dins el geopackage
            layers_list = [layer.GetName() for layer in ogr.Open(pathname)]
            layers_list.sort(reverse=True)
            if add_geopackage_group:
                # Si hem de crear un grup "manualment" generem una llista amb el nom de fitxer/capa i nom capa
                pathnames_list = [("%s|layername=%s" % (pathname, layer_name),
                    re.sub(r"_\d+_", "", layer_name, 1)
                    ) for layer_name in layers_list if layer_name != "layer_styles"] # En saltem la taula d'estils...
            else:
                # Si no cal afegir grup de geopackage "manualment", carreguem ja el fitxer...
                layer = self.iface.addVectorLayer(pathname, filename, "ogr")
                if self.parent.legend.is_group_by_name(filename):                               
                    # Si es crear un grup automàticament amb el nom de fitxer, només cal moure el grup dins del grup indicat
                    self.parent.legend.collapse_group_by_name(filename)
                    pathnames_list = [(layer.id(), 
                        re.sub(r"_\d+_", "", layer.name(), 1)                    
                        ) for layer in self.get_group_layers_by_id(filename)]
                elif len(layers_list) > 1:
                    # Si tenim les capes per separat, estaran totes prefixades pel nom de fitxer
                    # Generem una llista amb el nom de capes i nom "maco" per poder aplicar estils, si cal
                    pathnames_list = [(
                        self.get_by_name("%s — %s" % (filename, layer_name)).id(),
                        "%s — %s" % (filename, re.sub(r"_\d+_", "", layer_name, 1))
                        ) for layer_name in layers_list if layer_name != "layer_styles"] # En saltem la taula d'estils...
                else:
                    pathnames_list = [(layer.id(), layer.name())]
            styles_dict = None
        else:
            pathnames_list = [(pathname, name)]
            styles_dict = None
        if is_zipped_file or is_geopackage_file:
            # Creem una carpeta amb el nom del zip (dins d'una carpeta contenidora si cal)
            if is_zipped_file or (is_geopackage_file and add_geopackage_group):
                self.parent.legend.add_group(filename, False)
            if group_name:
                self.parent.legend.set_group_visible_by_name(group_name)
                self.parent.legend.move_group_to_group_by_name(filename, group_name, autocreate_parent_group=True, parent_group_pos=group_pos)
            # Marquem que les dades s'hauran de carregar dins la "carpeta zip"
            if self.parent.legend.is_group_by_name(filename):
                group_name = filename

        # Obrim el fixer vectorial (pot ser N capes en cas d'arxius comprimits)
        for i, (vector_pathname, layer_name) in enumerate(pathnames_list):
            if is_geopackage_file and not add_geopackage_group:
                # Si es tracta d'un Geopackage i no cal crear grup manualment, ja està la capa carregada
                layer = self.get_by_id(vector_pathname) # En aquest cas és el nom de la capa carregada prèviament ...
            else:   
                # Carreguem la capa indicada
                layer = self.iface.addVectorLayer(vector_pathname, layer_name, "ogr")
            if layer:
                # Canviem el nom de la capa si cal
                if layer_name:
                    layer.setName(layer_name)
                # Canviem l'estil de la capa si cal
                if style_file:
                    ##print("Style file", style_file)
                    # Si tenim un fitxer d'estil el carreguem
                    self.load_style(layer, style_file, refresh=True)
                else:
                    # Si tenim un qml dins el zip, el carregeuem
                    xml_style = None
                    if is_zipped_file:
                        layer_name = os.path.splitext(os.path.basename(vector_pathname))[0]
                        xml_style = styles_dict.get(layer_name, None)
                        if xml_style:
                            ##print("Style XML", "%s.qml" % (os.path.splitext(vector_pathname)[0]))
                            self.load_xml_style(layer, xml_style, refresh=True)
                    # Si tenim una expressió regular que concordi amb la capa, carreguem el seu estil
                    regex_style_file = None
                    if not xml_style and regex_styles_list:
                        if is_geopackage_file and add_geopackage_group:
                            layer_name = vector_pathname.split("|layername=")[1]
                        elif is_zipped_file:
                            layer_name = os.path.splitext(os.path.basename(vector_pathname))[0]
                        else:
                            layer_name = name
                        for style_regex, style_qml in regex_styles_list:
                            if re.match(style_regex, filename):
                                if style_qml:
                                    regex_style_file = style_qml
                                else:
                                    visible = False # Si l'estil es None, fem no visualitzem la capa
                                ##print("Style regex", regex_style_file)
                                break
                        if regex_style_file:
                            self.load_style(layer, regex_style_file, refresh=True)
                # Canviem les propiedats de la capa i movem la capa a un grup si cal
                self.set_properties(layer, visible, not expanded, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, min_scale, max_scale, transparency, None, set_current, properties_dict_list[i] if properties_dict_list else None)
        # Si carreguem arxiu multicapa, hem creat un grup per ell i volem el grup colapsat
        if group_name:
            if is_zipped_file or (is_geopackage_file and add_geopackage_group):
                self.parent.legend.collapse_group_by_name(group_name)
            if parent_group and collapsed_parent_group:
                parent_group.setExpanded(False)

        return layer

    def add_remote_vector_file(self, remote_file, local_filename=None, download_folder=None, group_name=None, group_pos=None, min_scale=None, max_scale=None, layer_name=None, visible=True, expanded=False, transparency=None, set_current=False, style_file=None, regex_styles_list=None, properties_dict=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, select_folder_text=None):
        """ Descarrega fitxers vectorials via http en la carpeta especificada i els obre a QGIS.
            Veure add_vector_files per opcions
            ---
            Download http vector files in the specified folder and open them to QGIS.
            See add_vector_layer for options
            """
        # Descarreguem el fitxer si cal
        local_pathname = self.download_remote_file(remote_file, local_filename, download_folder, select_folder_text)
        if not local_pathname:
            return None
        # Carreguem el fitxer
        return self.add_vector_layer(layer_name, local_pathname, group_name, group_pos, min_scale, max_scale, visible, expanded, transparency, set_current, style_file, regex_styles_list, properties_dict, only_one_map_on_group, only_one_visible_map_on_group)

    def add_remote_vector_files(self, remote_files_list, download_folder=None, group_name=None, group_pos=None, min_scale=None, max_scale=None, layer_name=None, visible=True, expanded=False, transparency=None, set_current=False, style_file=None, regex_styles_list=None, properties_dict_list=[], only_one_map_on_group=False, only_one_visible_map_on_group=True, select_folder_text=None):
        """ Descarrega fitxers vectorials via http en la carpeta especificada i els obre a QGIS.
            Veure add_vector_files per opcions
            ---
            Download http vector files in the specified folder and open them to QGIS.
            See add_vector_files for options
            """
        layers_list = []
        for remote_file in remote_files_list:
            # Descarreguem el fitxer si cal
            local_pathname = self.download_remote_file(remote_file, None, download_folder, select_folder_text)
            # Carreguem el fitxer
            if local_pathname:
                last_layer = self.add_vector_files([local_pathname], group_name, group_pos, min_scale, max_scale, layer_name, visible, expanded, transparency, set_current, style_file, regex_styles_list, properties_dict_list, only_one_map_on_group, only_one_visible_map_on_group)
            else:
                last_layer = None
            layers_list.append(last_layer)
        # Retornem la última capa
        return layers_list

    def add_wms_t_layer(self, layer_name, url, layer_id=None, default_time=None, style="default", image_format="image/png", time_series_list=None, time_series_regex=None, epsg=None, extra_tags="", group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, saturation=None, resampling_bilinear=False, resampling_cubic=False, set_current=False):
        """ Afegeix una capa WMS-T a partir de la URL base i una capa amb informació temporal.
            Veure add_wms_layer per la resta de paràmetres
            ---
            Adds a WMS-T layer from the base URL and a layer with temporary information.
            See add_wms_layer for the rest of parameters
            """
        # Obtenim la llista de capes temporals i la registrem associada a la url
        if time_series_list:
            # Utilitzem la llista de (<time_name>, <time_url>) per simular una sèrie temporal
            if url:
                if not default_time:
                    default_time = dict([(layer_id, time_name) for (time_name, layer_id) in time_series_list])[layer_id]
                default_layer = layer_id
                url_time = url
            else:
                if not default_time:
                    default_time = layer_id
                default_layer = layer_id
                url_time = dict(time_series_list)[default_layer]
        elif time_series_regex:
            # Utilitzem la expressió regular per cercar capes i simular una sèrie temporal
            time_series_list, default_time2 = self.get_wms_t_time_series(url, None, time_series_regex)
            if not time_series_list:
                return None
            default_time = default_time or default_time2
            if not default_time:
                default_time = time_series_list[-1][0]
            default_layer = dict(time_series_list)[default_time]
            url_time = url
        else:
            # Obtenim els temps disponibles per una capa
            time_series_list, default_time2 = self.get_wms_t_time_series(url, layer_id)
            if not time_series_list:
                return None
            default_time = default_time or default_time2
            if not default_time:
                default_time = time_series_list[-1][0]
            default_layer = dict(time_series_list)[default_time]
            is_question_mark = url.find("?") >= 0
            url_time = "%s%stime=%s" % (url, "%26" if is_question_mark else "?", default_time)

        # Obtenim el nom del temps per defecte i creem la capa
        time_layer_name = "%s [%s]" % (layer_name, default_time)
        if url:
            layer = self.add_wms_layer(time_layer_name, url_time, [default_layer], [style],
                image_format, epsg, extra_tags, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group,
                collapsed, visible, transparency, saturation, set_current)
        else:
            layer = self.add_raster_layer(time_layer_name, url_time, group_name, group_pos, epsg,
                color_default_expansion=True, visible=visible, expanded=not collapsed, transparency=transparency, saturation=saturation,
                resampling_bilinear=resampling_bilinear, resampling_cubic=resampling_cubic,
                set_current=set_current, only_one_map_on_group=only_one_map_on_group, only_one_visible_map_on_group=only_one_visible_map_on_group)

        # Registrem les capes temporals de la url i refresquem la capa activa
        self.time_series_dict[layer] = time_series_list
        self.iface.layerTreeView().currentLayerChanged.emit(layer)

        return layer

    def parse_wms_t_layer(self, layer):
        # Obté la URL base i la capa / temps de la URL d'una capa
        if layer.dataProvider().dataSourceUri().find("%26") >= 0:
            # Cas especial on la url ja té un ? i s'ha afegit el paràmetre time amb "%26"
            reg_ex = r"url=([\w\d\-\?_:./=]+)(?:\%26time=([\d\-/:]+))*.+layers=([\w\d\-_]+)"
        else:
            reg_ex = r"url=([\w\d\-_:./=]+)(?:\?time=([\d\-/:]+))*.+layers=([\w\d\-_]+)"
        found = re.search(reg_ex, layer.dataProvider().dataSourceUri(), flags=re.IGNORECASE)
        if not found:
            return None, None, None
        url, current_time, current_layer = found.groups()
        return url, current_layer, current_time

    def is_wms_t_layer(self, layer):
        # Obtenim el nom de la capa associada al temps escollit
        time_series_list = self.time_series_dict.get(layer, [])
        return len(time_series_list) > 0

    def update_wms_t_layer_current_time(self, layer, wms_time):
        """ Actualitza la capa a llegir d'un servidor WMS
            ---
            Update WMS layer to read
            """
        # Obtenim el nom de la capa associada al temps escollit
        time_series_list = self.time_series_dict.get(layer, [])
        if not time_series_list:
            return
        layer_id = dict(time_series_list)[wms_time]

        # Actualitzem la capa
        ##print("update wms-t time", layer_id, wms_time)
        self.update_wms_layer(layer, layer_id, wms_time)

        # Canviem el nom de la capa
        base_name = layer.name().split(' [')[0]
        new_name = "%s [%s]" % (base_name, wms_time)
        layer.setName(new_name)
        return new_name

    def get_wms_t_time_series(self, url, layer_id, ts_regex=None, version="1.1.1", timeout_seconds=5, retries=3):
        """ Obté informació temporal d'una capa d'un servidor WMS-T o d'un grup de capes (via expresió regular)
            Retona:
            - llista de tuples [(<name>, <layer_id>), ...]
            - text <default_time>
            ---
            Gets temporary informacion of a WMS-T layer or a group layers (using regular expression)
            Returns:
            - list of tupes [(<name>, <layer_id>), ...]
            - string <default_time>
            """
        time_series_list = []
        default_time = None

        # Llegim el capabilities del servei
        is_question_mark = url.find("?") >= 0
        capabilities_request = "%s%sREQUEST=GetCapabilities&SERVICE=WMS&VERSION=%s" % (url, "&" if is_question_mark else "?", version)
        ##print("request", capabilities_request)
        capabilities_xml = None
        while retries:
            try:
                response = urllib.request.urlopen(capabilities_request, timeout=timeout_seconds)
                capabilities_xml = response.read()
                retries = 0
            except socket.timeout:
                retries -= 1
                self.parent.log.warning("WMS-T URL: %s retries: %s", url, retries)
            except Exception as e:
                retries = 0
                self.parent.log.exception("Error WMS-T: %s", e)
        if not capabilities_xml:
            return [], None
        ##print("xml", capabilities_xml)

        # Cerquem les capes amb el camp "Dimension" tipus "time" o "Dimension" + "Extent" tipus "time"
        time_series_list = []
        default_time = None
        root = ElementTree.fromstring(capabilities_xml)
        layers = root.find('Capability').find("Layer")
        for layer in layers.findall('Layer'):
            # Si tenim un identificador de capa, cerquem aquella capa i obtenim les seves marques temporals
            if layer_id:
                if layer.find("Name").text != layer_id:
                    continue
                ##print("layer", layer_id)

                dimension = layer.find("Dimension")
                if dimension is None or dimension.get("name") != "time":
                    continue
                if dimension.text:
                    #<Dimension name="time" units="ISO8601" default="2018-09" nearestValue="0">
                    #2015-12,2016-03,2016-04,2016-05,2016-06,2016-07,2016-08,2016-09,2016-10,2016-11,2016-12,2017-01,2017-02,2017-03,2017-04,2017-05,2017-06,2017-07,2017-08,2017-09,2017-10,2017-11,2017-12,2018-01,2018-02,2018-03,2018-04,2018-05,2018-06,2018-07,2018-08,2018-09
                    #</Dimension>
                    dimension_text = dimension.text
                    default_time = dimension.get("default")
                else:
                    #<Extent name="time" default="2018" nearestValue="0">#2015-12,...</Extent>
                    extent = layer.find("Extent")
                    if extent is None or extent.get("name") != "time" or not extent.text:
                        continue
                    dimension_text = extent.text
                    default_time = extent.get("default")
                ##print("Dimensions", layer_id, dimension_text, default_time)

                # Recuperem les dimension (de tipus llista d1,d2... o de tipus rang d1/d2 o d1-d2)
                # Els rangs de moment només funcionen per anys!
                if dimension_text.find(',') > 0:
                    time_series_list = [(time.strip(), layer_id) for time in dimension_text.split(',')]
                else:
                    for range_separator in ['/', '-']:
                        if dimension_text.find(range_separator) > 0:
                            time_begin, time_end = dimension_text.split(range_separator)[0:2]
                            if time_begin.isdigit() and time_end.isdigit():
                                time_series_list = [(str(time), layer_id) for time in range(int(time_begin), int(time_end) + 1)]
                                break
                ##print("time series", time_series_list)
                ##print("Default time", default_time)
                break

            # Si ens passen una expressió regular, cerquem totes les capes que compleixin amb la expressió
            elif ts_regex:
                layer_id = layer.find("Name").text
                found = re.findall(ts_regex, layer_id)
                if found:
                    time = found[0]
                    time_series_list.append((time, layer_id))
                layer_id = None

        return time_series_list, default_time

    def add_wms_layer(self, layer_name, url, layers_list, styles_list, image_format, epsg=None, extra_tags="", group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, saturation=None, set_current=False, resampling_bilinear=False, resampling_cubic=False):
        """ Afegeix una capa a partir de la URL base, una llista de capes WMS, una llista d'estils i un format d'imatge.
            Retorna la capa.
            Opcionalment es pot especificar:
            - epsg: codi EPSG (per defecte el del projecte),
            - extra_tags: tags addicional per enviar al servidor
            - group_name: un nom de grup / carpeta QGIS on afegir la capa
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - only_one_map_on_group: Especifica que només tindrem una capa en el grup i la última carregada esborra les anteriors
            - only_one_visible_map_on_group: Especifica que només tindrem una única capa visible dins el grup
            - collapsed: Indica si volem carregar la capa amb la llegenda colapsada
            - visible: Indica si volem carregar la capa deixant-la visible o no
            ---
            Adds a layer from the base URL, a list of WMS layers, a list of styles and an image format.
            Returns the layer.
            Optionally you can specify:
            - epsg: EPSG code (by default the project),
            - extra_tags: additional tags to send to the server
            - group_name: a QGIS group name / folder where to add the layer
            - group_pos: Create group on specific position (if None then to the end)
            - only_one_map_on_group: Specifies that we will only have one layer in the group and the last loaded deletes the previous ones
            - only_one_visible_map_on_group: Specifies that we will only have one visible layer in the group
            - collapsed: Indicates whether we want to load the layer with collapsed legend
            - visible: Indicates whether we want to load the layer by leaving it visible or not
            """
        uri = self.generate_wms_layer_uri(url, layers_list, styles_list, image_format, epsg, extra_tags)
        return self.add_raster_uri_layer(layer_name, uri, "wms", group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, saturation, set_current, resampling_bilinear, resampling_cubic)

    def generate_wms_layer_uri(self, url, layers_list, styles_list, image_format, epsg=None, extra_tags=""):
        """ Retorna el string uri a partir dels paràmetres WMS
            ---
            Return WMS uri string from WMS paràmeters
            """
        # Si no tenim EPSG agafem el del projecte
        if not epsg:
            epsg = self.parent.project.get_epsg()
        # Cal tenir el mateix nombre d'estils que de capes
        if not styles_list:
            styles_list = []
        if len(styles_list) != len(layers_list):
            if len(styles_list) == 1:
                styles_list = styles_list * len(layers_list)
            else:
                styles_list += [""] * (len(layers_list) - len(styles_list))
        # Preparem la connexió
        uri = "url=%s&crs=EPSG:%s&format=%s&styles=%s&layers=%s" % (url, epsg, image_format, "&styles=".join(styles_list), "&layers=".join(layers_list))
        if extra_tags:
            uri += "&%s" % extra_tags
        uri += "&IgnoreGetMapUrl=1"
        return uri
        
    def add_wms_url_query_layer(self, layer_name, url_query, group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, saturation=None, set_current=False):
        """ Afegeix una capa WMS a partir d'una petició WMS (URL). Retorna la capa.
            Veure add_wms_layer per opcions
            ---
            Adds a WMS layer from a WMS request (URL). Returns the layer
            See add_wms_layer for options
            """
        uri = "url=%s" % url_query.lower().replace("epsg:", "epsg:").replace("srs=", "crs=").replace("?", "&")
        uri += "&IgnoreGetMapUrl=1"
        return self.add_raster_uri_layer(layer_name, uri, "wms", group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, saturation, set_current)

    def update_wms_layer(self, layer, wms_layer=None, wms_time=None, wms_style=None):
        """ Actualitza la capa a llegir d'un servidor WMS
            ---
            Update WMS layer to read
            """
        # Obtenim la capa actual carregada
        url, current_layer, current_time = self.parse_wms_t_layer(layer)
        current_style = None

        if url and current_layer:
            # Actualitzem la capa a WMS carregar (pot ser un canvi de capa (fals WMS-T) o un canvi de temps)
            if self.parent.check_qgis_version(31600): 
                # Incompatible with version 3.4 and 3.10 (not update value)            
                new_uri = layer.source()
            else:
                new_uri = layer.dataProvider().dataSourceUri()
            if wms_layer:
                new_uri = new_uri.replace("layers=%s" % current_layer, "layers=%s" % wms_layer)
            if wms_time:
                new_uri = new_uri.replace("time=%s" % (current_time), "time=%s" % (wms_time))
            if wms_style:
                found = re.search(r"(styles=[^&]+)", new_uri, re.IGNORECASE)
                if found:
                    current_style = found.groups()[0]
                    new_uri = new_uri.replace(current_style, "styles=%s" % wms_style)
                else:
                    new_uri += "&styles=%s" % wms_style
        else:
            # Si tenim un fals WMS-T amb link a arxius raster, cal fer més refrescos...
            new_uri = wms_layer
            
        if self.parent.check_qgis_version(31600): 
            # Incompatible with version 3.4 and 3.10 (not updated)
            layer.setDataSource(new_uri, layer.name(), layer.dataProvider().name(), layer.dataProvider().ProviderOptions())
        else:
            layer.dataProvider().setDataSourceUri(new_uri)
            layer.dataProvider().reloadData()
            layer.reload()
            layer.triggerRepaint()

    def is_anaglyph_layer(self, layer):
        """ Retorna si una capa té informació WMS anaglif 
            ---
            Returns layer is WMS anaglyph
            """
        uri = layer.source()
        found = re.search(r"(styles=[^&]+)", uri.lower(), re.IGNORECASE)
        if not found:
            return False
        anaglyph_params = found.groups()[0].split(",")
        return len(anaglyph_params) == 3

    def add_raster_uri_layer(self, layer_name, uri, provider, group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, saturation=None, set_current=False, resampling_bilinear=False, resampling_cubic=False):
        """ Afegeix una capa raster a partir d'un URI i proveidor de dades (wms, oracle ...). Retorna la capa.
            Veure add_wms_layer per opcions
            ---
            Adds a raster layer from a URI and data provider (wms, oracle ...). Returns the layer.
            See add_wms_layer for options
            """
        ##print("URI", uri)
        # Creem la capa
        layer = self.iface.addRasterLayer(uri, layer_name, provider)
        if not layer:
            return layer
        # Ajustem el mostreig si cal
        if resampling_bilinear:
            resample_filter = layer.resampleFilter()
            resample_filter.setZoomedInResampler(QgsBilinearRasterResampler())
            resample_filter.setZoomedOutResampler(QgsBilinearRasterResampler())
        if resampling_cubic:
            resample_filter = layer.resampleFilter()
            resample_filter.setZoomedInResampler(QgsCubicRasterResampler())
            resample_filter.setZoomedOutResampler(QgsCubicRasterResampler())
        # Canviem les propiedats de la capa
        self.set_properties(layer, visible, collapsed, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, transparency=transparency, saturation=saturation, set_current=set_current)
        return layer

    def add_wms_ortoxpres_layer(self, year, gsd, layer_prefix="ortoXpres", url="https://www.ortoxpres.cat/server/sgdwms.dll/WMS", styles_list=["default"], image_format="image/jpeg", epsg=None, extra_tags="", group_name="", group_pos=None, only_one_map=False):
        """ Afegeix una capa tipus WMS ICGC ortoXpres a partir d'un any i GSD. Retorna la capa.
            Opcionalment es pot especificar un grup on afegir la capa i si volem només tenir una capa dins el grup alhora.
            ---
            Adds a layer type WMS ICGC ortoXpres from one year and GSD. Returns the layer.
            Optionally a group can be specified where to add the layer and if we only have one layer within the group at the same time.
            """
        # Configurem el nom de la capa WMS del servidor a la que accedirem
        wms_layer = "Catalunya %dcm. %d" % (gsd * 100, year)
        layer_name = "%s %s" % (layer_prefix, wms_layer)
        ##print("WMS ortoXpres, capa:", layer_name)
        # Afegim la capa
        layer = self.add_wms_layer(layer_name, url, [wms_layer], styles_list, image_format, epsg, extra_tags, group_name, group_pos, only_one_map)
        return layer

    def add_vector_db_layer(self, host, port, dbname, schema, table, user, password, geometry_column=None, filter=None, key_column=None, provider='postgres',
                            epsg=25831, wkbtype=QgsWkbTypes.Polygon, layer_name=None, group_name="", group_pos=None, only_one_map_on_group=False,
                            only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, set_current=False, style_file=None, 
                            if_empty_retry_without_geo=False):
        """ Afegeix una capa tipus BBDD. Retorna la capa
            Paràmetres de la connexió: host, port, dbname, schema, table, user, password, geometry_column, filter, key_column
            Veure add_wms_layer per opcions de capa
            ---
            Add a DB connection layer. Returns the layer
            Connection parameters: host, port, dbname, schema, table, user, password, geometry_column, filter, key_column
            See add_wms_layer for layer options
            """
        # configurem la connexió a la BBDD
        uri = QgsDataSourceUri()
        uri.setConnection(host, str(port), dbname, user, password)
        if geometry_column:
            uri.setSrid(str(epsg))
            uri.setWkbType(wkbtype)
        uri.setDataSource(schema, table, geometry_column, filter, key_column)
        # afegim la capa
        layer = self.add_vector_uri_layer(layer_name, uri.uri(), provider, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, set_current, style_file)
        # CAS ESPECIAL! A VEGADES NO CARREGA BÉ VISTES POSTGRES SI CAP ELEMENT TÉ GEOMETRIA... 
        # EN AQUEST CAS PODEM FORÇAR CARREGAR LA CAPA SENSE GEOMETRIA
        if if_empty_retry_without_geo and layer and layer.featureCount() < 1:
            self.remove_layer(layer)
            uri = QgsDataSourceUri()
            uri.setConnection(host, str(port), dbname, user, password)
            uri.setDataSource(schema, table, None, filter, key_column)
            layer = self.add_vector_uri_layer(layer_name, uri.uri(), provider, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, set_current, style_file)
        return layer

    def add_wfs_layer(self, layer_name, url, layers_list, epsg=None, filter=None, extra_tags="", version="2.0.0", group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, set_current=False, style_file=None):
        """ Afegeix una capa vectorial a partir de la URL base i una llista de capes WFS.
            Retorna la capa.
            Opcionalment es pot especificar:
            - epsg: codi EPSG (per defecte el del projecte),
            - extra_tags: tags addicional per enviar al servidor
            - group_name: un nom de grup / carpeta QGIS on afegir la capa
            - group_pos: Crea el grup en la posició indicada (si és None, al final)
            - only_one_map_on_group: Especifica que només tindrem una capa en el grup i la última carregada esborra les anteriors
            - only_one_visible_map_on_group: Especifica que només tindrem una única capa visible dins el grup
            - collapsed: Indica si volem carregar la capa amb la llegenda colapsada
            - visible: Indica si volem carregar la capa deixant-la visible o no
            ---
            Adds a vector layer from the base URL and a list of WFS layers.
            Returns the layer.
            Optionally you can specify:
            - epsg: EPSG code (by default the project),
            - extra_tags: additional tags to send to the server
            - group_name: a QGIS group name / folder where to add the layer
            - group_pos: Create group on specific position (if None then to the end)
            - only_one_map_on_group: Specifies that we will only have one layer in the group and the last loaded deletes the previous ones
            - only_one_visible_map_on_group: Specifies that we will only have one visible layer in the group
            - collapsed: Indicates whether we want to load the layer with collapsed legend
            - visible: Indicates whether we want to load the layer by leaving it visible or not
            """
        # Preparem la cadena URI
        if not epsg:
            epsg = self.parent.project.get_epsg()
        separator = "&" if url.find("?") >= 0 else "?"
        uri = "url=%s%sservice=WFS&version=%s&request=GetFeature&typename=%s&srsname=EPSG:%s" % (url, separator, version, ",".join(layers_list), epsg)
        if extra_tags:
            uri += "&%s" % extra_tags
        ds_uri = QgsDataSourceUri()
        ds_uri.setEncodedUri(uri)
        # Apliquem un filtrat si cal
        if filter:
            ds_uri.setSql(filter)
        # Carreguem la capa WFS
        layer = self.add_vector_uri_layer(layer_name, ds_uri.uri(), "WFS", group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, collapsed, visible, transparency, set_current, style_file=None)
        # Carreguem l'estil després del filtrat si cal
        if layer and style_file:
            self.load_style(layer, style_file)
        return layer

    def add_vector_uri_layer(self, layer_name, uri, provider, group_name="", group_pos=None, only_one_map_on_group=False, only_one_visible_map_on_group=True, collapsed=True, visible=True, transparency=None, set_current=False, style_file=None):
        """ Afegeix una capa vectorial a partir d'un URI i proveidor de dades (wms, oracle ...). Retorna la capa.
            Veure add_wms_layer per opcions
            ---
            Adds a vector layer from a URI and data provider (wfs, oracle ...). Returns the layer.
            See add_wfs_layer for options
            """
        layer = self.iface.addVectorLayer(uri, layer_name, provider)
        if not layer:
            return layer

        # Canviem l'estil de la capa si cal
        if style_file:
            self.load_style(layer, style_file, refresh=True)

        # Canviem les propiedats de la capa
        self.set_properties(layer, visible, collapsed, group_name, group_pos, only_one_map_on_group, only_one_visible_map_on_group, transparency=transparency, set_current=set_current)
        return layer

    def refresh_attributes_table_by_id(self, layer_id):
        """ Refresca la taula d'atributs de la capa indicada a partir d' id
            ---
            Refresh the attribute table of the specified layer by id
            """
        layer = self.get_by_id(layer_id)
        if not layer:
            return False
        self.refresh_attributes_table(layer)
        return True

    def refresh_attributes_table(self, layer):
        """ Refresca la taula d'atributs de la capa indicada
            ---
            Refresh the attribute table of the specified layer
            """
        self.refresh_attributes_tables(layer.name())

    def refresh_attributes_tables(self, layer_name_not_all=None):
        """ Refresca totes les taules d'atributs obertes o la de la capa especificada (per nom, no per id)
            ---
            Refresh all open tables of attributes or that of the specified layer name (by name, no for id)
            """
        # Obtenim tots els diàlegs de taula d'atributes o el de la capa indicada (segons layer_name_not_all)
        dialogs_list = [dialog for dialog in QApplication.instance().allWidgets()
            if dialog.objectName() == 'QgsAttributeTableDialog'
            and (layer_name_not_all is None or dialog.windowTitle().split(' - ')[1].split(' :: ')[0] == layer_name_not_all)]

        # Refresquem els diàlegs
        for dialog in dialogs_list:
            # Recuperem un objecte de tipus QDialog però sabem que és un QgsAttributeDialog
            # Obtenim el widget de taula/graella i el model de dades
            dialog.__class__ = QgsAttributeDialog
            table = dialog.findChildren(QTableView)[0]
            model = table.model()
            # Reordenem 2 vegades (ascendent i descendent) per forçar un refresc de les dades (CUTRE!!!)
            if model.sortColumn() >= 0:
                model.sort(model.sortColumn(), not model.sortOrder())
                model.sort(model.sortColumn(), not model.sortOrder())
            else:
                model.sort(0, Qt.DescendingOrder)
                model.sort(model.sortColumn(), not model.sortOrder())

    def show_attributes_table_by_id(self, idprefix, multiinstance=False, filter_expression=None, pos=0):
        """ Mostra la taula de atributs d'una capa a partir del seu id
            ---
            Shows the table of contents of a layer from its id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.show_attributes_table(layer, multiinstance, filter_expression)

    def show_attributes_table(self, layer, multiinstance=False, filter_expression=None):
        """ Mostra la taula de continguts d'una capa
            ---
            Shows the table of contents of a layer
            """
        table_dialog = self.get_attributes_table(layer)
        if multiinstance or not table_dialog:
            table_dialog = self.iface.showAttributeTable(layer, filter_expression)
        else:
            table_dialog.showNormal()
            table_dialog.activateWindow()
            table_dialog.setFocus()
        return table_dialog

    def get_attributes_table_by_id(self, idprefix, pos=0):
        """ Obté la taula d'atributs d'una capa a partir del seu id
            ---
            Gets the attribute table of a layer by id
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.get_attributes_table(layer)

    def get_attributes_table(self, layer):
        """ Obté la taula d'atributs d'una capa
            ---
            Gets the attribute table of a layer
            """
        # Busquem si tenim una taula oberta de aquesta capa
        dialogs_list = [d for d in QApplication.instance().allWidgets() if d.objectName() == 'QgsAttributeTableDialog' and d.windowTitle().split(' - ')[1].split(' :: ')[0] == layer.name()]
        return dialogs_list[0] if len(dialogs_list) > 0 else None

    def show_attributes_dialog_by_id(self, layer_idprefix, feature, edit_mode=False, modal_mode=False, width=100, height=100, pos=0):
        """ Mostra el formulari d'edició de camps de l'element amb id especificat o seleccionat
            ---
            Shows edition feature form of specificated feature id or current selected id
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.show_attributes_dialog(layer, feature, edit_mode, modal_mode, width, height)
    
    def show_attributes_dialog(self, layer, feature, edit_mode=False, modal_mode=False, width=None, height=None):
        """ Mostra el formulari d'edició de camps de l'element amb el valor especificat o seleccionat
            ---
            Shows edition feature form of specificated feature value or current selected id
            """
        # Activem el mode edició si cal
        if edit_mode:
            layer.startEditing()
        # Mostrem el diàleg
        dlg = self.iface.getFeatureForm(layer, feature)
        dlg.setSizeGripEnabled(True)
        dlg.setMinimumSize(300, 200)
        if width and height:
            dlg.resize(width, height)
        else:
            dlg.adjustSize()
        if modal_mode or edit_mode:
            status_ok = (dlg.exec() == QDialog.Accepted)
        else:
            dlg.show()
            status_ok = dlg.isVisible()
        # Guardem o cancel·lem canvis si cal
        if edit_mode:
            if status_ok:
                feature.setAttributes(dlg.feature().attributes())
                layer.commitChanges()
            else:
                layer.rollBack()
            layer.endEditCommand()
        return status_ok

    def refresh_legend_by_id(self, idprefix, visible=None, expanded=None, pos=0):
        """ Refresca la llegenda d'una capa a partir del seu id.
            Pot actualitzar la visibilitat i expansió de la llegenda de la capa
            ---
            Refresh the legend of a layer by id.
            You can update the visibility and expansion of the layer's legend
            """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.refresh_legend(layer, visible, expanded)
        return True

    def refresh_legend(self, layer, visible=None, expanded=None):
        """ Refresca la llegenda d'una capa
            Pot actualitzar la visibilitat i expansió de la llegenda de la capa
            ---
            Refresh the legend of a layer by id.
            You can update the visibility and expansion of the layer's legend
            """
        #if layer.providerType() != "memory": # Si faig el refresc en una capa de memòria s'esborren les dades...
        #    layer.setDataSource(layer.source(), layer.name(), layer.providerType(), layer.dataProvider().ProviderOptions()) # Force layer counter update
        if type(layer) is QgsVectorLayer:
            try: # Force layer counter update
                layer.countSymbolFeatures(True)
            except: # En linux i versions antigues de QGIS3 va sense paràmetres?
                layer.countSymbolFeatures()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        if visible is not None:
            self.set_visible(layer, visible)
        if expanded is not None:
            self.expand(layer, expanded)

    def configure_edition_dialog_by_id(self, layer_idprefix, config_list, pos=0):
        """ Configura el diàleg d'edició d'una capa.
            Config_list representa una tupla amb una llista de camps corresponents al nom de la columna,
            els possibles valors que pot tenir, l'alias que voldriem aplicar (si cal), i si serà visible u no
            en l'edició del diàleg.
            La llista de valors pot ser únic valor o una llista de parelles clau/valor en cas de mostrar un desplegable
            ---
            Configure the edit dialog for a layer.
            Config_list represents a tuple with a list of fields corresponding to the name of the column,
            the possible values that you can have, the alias that we would like to apply (if necessary), and if it will not be visible
            in the editing of the dialogue.
            The list of values can be only value or a list of key / value pairs if you have a drop-down list
            """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.configure_edition_dialog(layer, config_list)
        return True

    def configure_edition_dialog(self, layer, config_list):
        """ Configura el diàleg d'edició d'una capa.
            Config_list representa una tupla amb una llista de camps corresponents al nom de la columna,
            els possibles valors que pot tenir, l'alias que voldriem aplicar (si cal), i si serà visible u no
            en l'edició del diàleg.
            La llista de valors pot ser únic valor o una llista de parelles clau/valor en cas de mostrar un desplegable
            ---
            Configure the edit dialog for a layer.
            Config_list represents a tuple with a list of fields corresponding to the name of the column,
            the possible values that you can have, the alias that we would like to apply (if necessary), and if it will not be visible
            in the editing of the dialogue.
            The list of values can be only value or a list of key / value pairs if you have a drop-down list
            """
        hidden_setup = QgsEditorWidgetSetup('Hidden', {})
        for field_name, values_list, field_alias, visibility in config_list:
            # actualitzem l'alias si té:
            field_index = layer.fields().indexFromName(field_name)
            if field_alias:
                layer.setFieldAlias(field_index, field_alias)

            # comprovem si el camp serà visible o no
            if not visibility:
                layer.setEditorWidgetSetup(field_index, hidden_setup)

            # montem un desplegable si existeixen més d'un valor
            if values_list and  len(values_list) > 1:
                values_dict = dict([(item[0], item[1]) for item in values_list])
                editor_widget_setup = QgsEditorWidgetSetup('ValueMap', {'map' : values_dict})
                layer.setEditorWidgetSetup(field_index, editor_widget_setup)

    def copy_vector_layer_to_memory(self, source_layer, include_fields_list=[], rename_fields_dict={}, qdate_format=None, qdatetime_format=None, date_text_len=10, add_to_legend=True):
        """ Crea una copia de la capa en una capa de tipus memory i tradueix el noms dels camps i transforma les dates a text si cal
            ---
            Creates a layer copy of type memory and translate fields names and transform dates to text if is required
            """
        # Creem una nova capa del mateix tipus a memòria
        layer_name = source_layer.name()
        if source_layer.type() == QgsMapLayer.VectorLayer:
            if source_layer.geometryType() == QgsWkbTypes .PointGeometry:
                creation_text = "Point"
            elif source_layer.geometryType() == QgsWkbTypes .LineGeometry:
                creation_text = "LineString"
            elif source_layer.geometryType() == QgsWkbTypes .PolygonGeometry:
                creation_text = "Polygon"
            else:
                creation_text = "None"
        else:
            creation_text = "None"
        epsg = self.get_epsg(source_layer)
        if epsg:
            creation_text += "?crs=epsg:%s" % epsg
        layer = QgsVectorLayer(creation_text, layer_name, 'memory')
        if not layer:
            return None
        dp = layer.dataProvider()

        # Creem els atributs de la capa i els omplim
        dp.addAttributes([
            QgsField(f.name(), QVariant.String, "String", date_text_len) if (qdatetime_format and f.type() == QVariant.DateTime) or (qdate_format and f.type() == QVariant.Date) else f for f in source_layer.fields()])

        # Afegim la informació a la capa
        layer.startEditing()
        features_list = []
        for feature in source_layer.getFeatures():
            for i, attribute in enumerate(feature.attributes()):
                if qdatetime_format and type(attribute) == QDateTime:
                    feature.setAttribute(i, attribute.toString(qdatetime_format))
                elif qdate_format and type(attribute) == QDate:
                    feature.setAttribute(i, attribute.toString(qdate_format))
            features_list.append(feature)
        layer.addFeatures(features_list)
        layer.commitChanges()
        layer.updateExtents()

        # Modifiquem la copia si cal
        if include_fields_list:
            fields_to_remove_list = list(set([f.name() for f in layer.fields()]) - set(include_fields_list))
            self.delete_fields(layer, fields_to_remove_list)
        if rename_fields_dict:
            self.rename_fields(layer, rename_fields_dict)

        # Registrem la capa i la retornem
        if add_to_legend:
            QgsMapLayerRegistry.instance().addMapLayer(layer)
        return layer


class LegendBase(object):
    """ Classe per manegar la llegenda de QGIS
        ---
        Class to manage QGIS lengend
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare, a l'iface i a l'arrel de la llegenda
            ---
            Initialization of member variables pointing to parent, iface and legend root
            """
        self.parent = parent
        self.iface = parent.iface
        self.root = QgsProject.instance().layerTreeRoot()

    def get_group_by_name(self, group_name):
        """ Obté un grup a partir del seu nom
            ---
            Get a group based on name
            """
        group = self.root.findGroup(group_name)
        if not group or not self.is_group(group):
            return None
        return group

    def get_selected_groups(self):
        """ Retorna les capes seleccionades
            ---
            Return selected layers
            """
        group_list = [g for g in self.iface.layerTreeView().selectedNodes() if type(g) == QgsLayerTreeGroup]
        return group_list

    def get_group_layer(self, layer):
        """ Retorna el group al qual pertany la capa
            ---
            Return parent group from layer
            """
        root_layer = self.root.findLayer(layer.id())
        if not root_layer:
            return None
        return root_layer.parent()

    def get_group_layer_by_name(self, layer_idprefix, pos=0):
        """ Retorna el group al qual pertany la capa a partir del seu id
            ---
            Return parent group from layer id
            """
        layer = self.parent.layers.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_group_layer(layer)

    #def set_selected_group_by_name(self, group_name):
    #    """ Selecciona el grup indicat
    #        ---
    #        Select group
    #    """
    #    group = self.get_group_by_name(group_name)
    #    self.set_selected_group(group)

    #def set_selected_group(self, group):
    #    """ Selecciona el grup indicat
    #        ---
    #        Select group
    #    """
    #    #self.iface.layerTreeView().setSelection(group)
    #    self.iface.layerTreeView().selectionModel().select(group)

    def is_group(self, item):
        """ Verifique que un item sigui de tipus grup
            ---
            Verify that an item is group type
            """
        return type(item) == QgsLayerTreeGroup

    def is_group_by_name(self, group_name):
        """ Indica si el nom de grup correspon realment a un grup existent
            ---
            Indicates if the group name really corresponds to an existing group
            """
        return self.get_group_by_name(group_name) is not None

    def get_group_position_by_name(self, group_name, parent_group_name=None):
        """ Retorna la posició d'un grup dins un altre grup per nom(per defecte root)
            ---
            Returns group position in a other group by name (root default)
            """
        group = self.get_group_by_name(group_name)
        parent_group_name = self.get_group_by_name(parent_group_name) if parent_group_name else None
        return self.get_group_position(group, parent_group_name)

    def get_group_position(self, group, parent_group=None):
        """ Retorna la posició d'un grup dins un altre grup (per defecte root)
            ---
            Returns group position in a other group (root default)
            """
        if not parent_group:
            parent_group = QgsProject.instance().layerTreeRoot()
        if group not in parent_group.children():
            return -1
        return parent_group.children().index(group)

    def add_group(self, group_name, expanded=True, visible_group=True, layer_list=[], group_parent_name=None, group_pos=None):
        """ Afegeix un grup a la llegenda i retorna l'objecte.
            Opcionalment podem especificar:
            - expanded: Indica si el grup tindrà la llegenda expandida o no
            - visible_group: Indica si el grup estarà marcat com visible
            - layers_list: Llista de capa a vellugar dins el grup
            - group_parent_name: grup pare dins el qual crearem el nou grup
            - group_pos: posició on insertar el nou grup
            ---
            Adds a group to legend and return the object.
            Optionally we can specify:
            - expanded: Indicates whether the group will have the legend expanded or not
            - visible_group: Indicates whether the group will be marked as visible
            - layers_list: List of layer to vellugar within the group
            - group_parent_name: parent group in which we will create the new group
            - group_pos: insert group position
            """
        group_parent = self.get_group_by_name(group_parent_name) if group_parent_name else None
        if group_pos is not None and not group_parent:
            group = self.root.insertGroup(group_pos, group_name)
        else:
            group = self.root.addGroup(group_name)
            if group_parent:
                group = self.move_group_to_group(group, group_parent, group_pos)
        if layer_list:
            self.move_layers_to_group(group, layer_list, visible_layer=visible_group)
        group.setExpanded(expanded)
        return group

    def remove_group_by_name(self, group_name):
        """ Esborra un grup per nom
            ---
            Delete a group by name """
        # Recuperem el grup
        group = self.get_group_by_name(group_name)
        if group is None:
            return False
        return self.remove_group(group)

    def remove_group(self, group):
        """ Esborra un grup
            ---
            Delete a group
            """
        # Esborrem el contingut del grup
        self.empty_group(group)
        # Esborrem el grup
        group.parent().removeChildNode(group)
        return True

    def empty_group_by_name(self, group_name, exclude_list=[]):
        """ Esborra el contingut d'un grup per nom
            ---
            Clear the content of a group by name
            """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.empty_group(group, exclude_list)
        return True

    def empty_group(self, group, exclude_list=[]):
        """ Esborra el contingut d'un grup
            ---
            Clear the content of a group
            """
        # Esborrem les capes del grup
        if exclude_list:
            item_names_list = [item.name() for item in exclude_list]
            for child in group.children():
                if child.name() not in item_names_list:
                    group.removeChildNode(child)
        else:
            group.removeAllChildren()

    def move_layer_to_group_by_name(self, group_name, layer, autocreate_group=False, group_pos=None, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat per nom.
            Opcionalment es pot indicar que es crei el grup en cas de no existir.
            Veure move_layers_to_group per la resta d'opcions
            ---
            Move the indicated layer (layer object) within the specified group by name.
            Optionally it can be indicated that the group is created if it does not exist.
            See move_layers_to_group for all other options
            """
        return self.move_layers_to_group_by_name(group_name, [layer], autocreate_group, group_pos, visible_layer, pos, remove_repeated_layers)

    def move_layers_to_group_by_name(self, group_name, layers_list, autocreate_group=False, group_pos=None, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga las capes indicades (objectes capa) dins el group especificat per nom.
            Opcionalment es pot indicar que es crei el grup en cas de no existir.
            Veure move_layers_to_group per la resta d'opcions
            ---
            Move the indicated layer list (layer objects) within the specified group by name.
            Optionally it can be indicated that the group is created if it does not exist.
            See move_layers_to_group for all other options
            """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if not group and autocreate_group:
            group = self.add_group(group_name, True, True, group_pos=group_pos)
        if group:
            # Movem les capes
            self.move_layers_to_group(group, layers_list, visible_layer, pos, remove_repeated_layers)
        return group

    def move_layer_to_group(self, group, layer, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat.
            Veure move_layers_to_group per la resta d'opcions
            ---
            Move the indicated layer (layer object) within the specified group.
            See move_layers_to_group for all other options
            """
        self.move_layers_to_group(group, [layer], visible_layer, pos, remove_repeated_layers)

    def move_layers_to_group(self, group, layers_list, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga les capes indicades(llista d'objectes capa) dins el group especificat
            Opcionalment es pot especificar:
            - visible_layer: Indica si volem que les capes siguin visibles o no
            - pos: Indica la posició de les capes dins el grup
            - remove_repeaterd_layers: Indica si voles esborrar capes repetides
            ---
            Move the indicated layer list (layer objects) within the specified group.
            Optionally you can specify:
            - visible_layer: Indicates whether we want the layers to be visible or not
            - pos: Indicates the position of the layers within the group
            - remove_repeaterd_layers: Indicates if you want to erase repeated layers
            """
        for layer in layers_list:
            if not layer:
                continue

            # Obtenim la posició de la capa dins l'arbre
            old_tree_layer = self.root.findLayer(layer.id())

            # Esborrem repetits
            if remove_repeated_layers:
                repeated_list = [child for child in group.children() if child.name() == layer.name() and child != old_tree_layer]
                for repeated_layer in repeated_list:
                    group.removeChildNode(repeated_layer)

            # Si la capa ja està dins el grup, no fem res
            if old_tree_layer in group.children():
                old_tree_layer.setItemVisibilityCheckedRecursive(visible_layer)
                continue

            # Si la capa no està dins el grup, la clonem dins el grup
            new_tree_layer = old_tree_layer.clone()
            new_tree_layer.setItemVisibilityCheckedRecursive(visible_layer)
            group.insertChildNode(pos, new_tree_layer)

            # Esborrem la capa original
            old_tree_layer.parent().removeChildNode(old_tree_layer)

    def move_group_to_group_by_name(self, group_name, parent_group_name, autocreate_parent_group=False, parent_group_pos=None):
        """ Velluga el grup indicat dins el group especificat per noms
            ---
            Move the indicated group within the specified group by names
            """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        parent_group = self.get_group_by_name(parent_group_name)
        if not group:
            return None
        if not parent_group:
            if not autocreate_parent_group:
                return None
            parent_group = self.add_group(parent_group_name, group_pos=parent_group_pos)
            if not parent_group:
               return None
        return self.move_group_to_group(group, parent_group)

    def move_group_to_group(self, group, parent_group, pos=0):
        """ Velluga el grup indicat dins el group especificat
            ---
            Move the indicated group within the specified group
            """
        # Movem el group dins el grup pare
        new_tree_group = group.clone()
        parent_group.insertChildNode(0 if pos is None else pos, new_tree_group)
        # Esborrem el grup inicial
        group.parent().removeChildNode(group)
        return new_tree_group

    def set_group_visible_by_name(self, group_name, enable=True):
        """ Fa visibles o invisibles un grup per nom
            ---
            Fa visibles o invisibles un grup by name
            """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.set_group_visible(group, enable)
        return True

    def set_group_visible(self, group, enable=True, recursive=False):
        """ Fa visibles o invisibles un grup
            ---
            Fa visibles o invisibles un grup"""
        if recursive:
            group.setItemVisibilityCheckedRecursive(enable)
        else:
            group.setItemVisibilityChecked(enable)

    def set_group_items_visible_by_name(self, group_name, enable):
        """ Fa visibles o invisibles els elements d'un grup per nom
            ---
            Make the elements of a group visible or invisible by name
            """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.set_group_items_visible(group, enable)
        return True

    def set_group_items_visible(self, group, enable):
        """ Fa visibles o invisibles els elements d'un grup
            ---
            Make the elements of a group visible or invisible
            """
        for child in group.children():
            child.setItemVisibilityCheckedRecursive(enable)

    def is_group_visible_by_name(self, group_name):
        """ Informa de si el grup és visible per nom
            ---
            Report if the group is visible by name
            """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        return self.is_group_visible(group)

    def is_group_visible(self, group):
        """ Informa de si el grup és visible
            ---
            Report if the group is visible
            """
        return group.isVisible()

    def collapse_group_by_name(self, group_name, collapse=True):
        """ Colapsa o expandeix un grup per nom
            ---
            Collapse or expand a group by name
            """
        return self.expand_group_by_name(group_name, not collapse)

    def collapse_group(self, group, collapse=True):
        """ Colapsa o expandeix un grup
            ---
            Collapse or expand a group
            """
        self.expand_group(group, not collapse)

    def expand_group_by_name(self, group_name, expand=True):
        """ Expandeix o colapsa un grup per nom
            ---
            Expand or collapse a group by name
            """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.expand_group(group, expand)
        return True

    def expand_group(self, group, expand=True):
        """ Expandeix o colapsa un grup
            ---
            Expand or collapse a group
            """
        group.setExpanded(expand)

    def is_group_expanded_by_name(self, group_name):
        """ Informa de si està expandit un grup per nom
            ---
            Informs if a group is expanded by name
            """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        return self.is_group_expanded(group)

    def is_group_expanded(self, group):
        """ Informa de si està expandit un grup
            ---
            Informs if a group is expanded
            """
        return group.isExpanded()

    #def collapse_all(self):
    #    """ Colapsa tots els elements de la llegenda
    #        ---
    #        Collapse all legend elements
    #        """
    #    legend = self.iface.legendInterface();
    #    legend_items = len(legend.groupLayerRelationship())
    #    for i in range(0, legend_items):
    #        legend.setGroupExpanded(i, False)

    def zoom_to_full_extent_group_by_name(self, group_name, buffer=0, refresh=True):
        """ Ajusta la visualització del mapa per visualitzar els elements d'un grup per nom
            ---
            Adjusts the map view to display the elements of a group by name
            """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.zoom_to_full_extent_group(group, buffer, refresh)
        return True

    def zoom_to_full_extent_group(self, group, buffer=0, refresh=True):
        """ Ajusta la visualització del mapa per visualitzar els elements d'un grup
            ---
            Adjusts the map view to display the elements of a group by name
            """
        # Inicialitzem l'area del zoom
        extent = QgsRectangle()
        extent.setMinimal()

        # A partir del grup, iterem les seves capes i combinem l'area de cada capa
        project_epsg = self.parent.project.get_epsg()
        for tree_layer in group.findLayers():
            layer = tree_layer.layer()
            # Descartem si es una capa només amb dades (sense cap tipus de geometria)
            if type(layer) is QgsVectorLayer and layer.geometryType() in [QgsWkbTypes.UnknownGeometry, QgsWkbTypes.NullGeometry]:
                continue
            area = layer.extent()
            if area.isNull() or area.isEmpty():
                continue
            # Reprojectem les coordenades si cal
            layer_epsg = self.parent.layers.get_epsg(layer)
            if not layer_epsg:
                continue
            if layer_epsg != project_epsg:
                area = self.parent.crs.transform_bounding_box(area, layer_epsg, project_epsg)
            # Ampliem el rectangle si cal
            if buffer:
                area = area.buffered(buffer)
            # Combinem l'area
            extent.combineExtentWith(area)

        # Fem zoom a l'area
        self.iface.mapCanvas().setExtent(extent)
        if refresh:
            self.iface.mapCanvas().refresh()

    def refresh_legend(self):
        """ Refresca tots els elements de la llegenda (excepte capes ràster)
            ---
            Refresh all the elements of the legend (except raster layers)
            """
        #for layer in self.iface.mapCanvas().layers():
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsRasterLayer):
                self.parent.layers.refresh_legend(layer)


class ComposerBase(object):
    """ Classe per manegar el compositor d'informes de QGIS
        ---
        Class to manage QGIS composer
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare a l'iface
            ---
            Initialization of member variables pointing to parent and iface
            """
        self.parent = parent
        self.iface = parent.iface

    def get_composer_item_by_id(self, composer_view, item_id):
        """ Obté un item del composer a partir de l'id
            ---
            Gets a composer item by id
            """
        selected_items = [item for item in composer_view.items() if hasattr(item, 'id') and item.id() == item_id]
        return selected_items[0] if len(selected_items) > 0 else None

    def get_composer_map_item_by_pos(self, composer_view, map_pos=0):
        """ Obté un item de tipus mapa del composer a partir de la seva posició
            ---
            Gets a map item of the composer from its position
            """
        selected_items = [item for item in composer_view.items() if type(item) == QgsLayoutItemMap]
        return selected_items[map_pos] if len(selected_items) > map_pos else None

    def get_composer_view(self, title):
        """ Obté la vista de composer amb el titol indicat
            ---
            Get the composer's view by title
            """
        layouts_list = QgsProject.instance().layoutManager().layouts()
        selected_layout_list = [layout for layout in layouts_list if layout.name() == title]
        return selected_layout_list[0] if len(selected_layout_list) > 0 else None

    #def get_composer_view(self, composer_name):
    #    composer_views = self.iface.activeComposers()
    #    composer_titles = [view.composerWindow().windowTitle() for view in composer_views]
    #    if not composer_name in composer_titles:
    #        return None
    #    composer_view = composer_views[composer_titles.index(composer_name)]
    #    return composer_view

    def show_composer_view(self, composer_view, enable_atlas=False, enable_edit_tools=True):
        """ Mostra el diàleg de composició d'informes
            ---
            Show composer report dialog
            """
        # Mostrem el diàleg del compositor
        layout_designer = self.iface.openLayoutDesigner(composer_view)
        if not layout_designer:
            return None

        # Configurem el diàleg
        # Atles
        if enable_atlas:
            layout_designer.setAtlasPreviewEnabled(enable_atlas)
        # Toolbars
        layout_designer.navigationToolbar().show()
        if enable_edit_tools:
            layout_designer.layoutToolbar().show()
            layout_designer.actionsToolbar().show()
            layout_designer.atlasToolbar().show()
        else:
            layout_designer.actionsToolbar().hide()
            if enable_atlas:
                layout_designer.layoutToolbar().hide()
                layout_designer.atlasToolbar().show()
            else:
                layout_designer.layoutToolbar().show()
                layout_designer.atlasToolbar().hide()
        # Menús
        layout_designer.atlasMenu().setEnabled(enable_edit_tools)
        layout_designer.editMenu().setEnabled(enable_edit_tools)
        layout_designer.itemsMenu().setEnabled(enable_edit_tools)
        layout_designer.layoutMenu().setEnabled(enable_edit_tools or not enable_atlas)
        layout_designer.settingsMenu().setEnabled(enable_edit_tools)
        layout_designer.viewMenu().setEnabled(True)

        return layout_designer

    def get_composition(self, report_pathname, atlas_layer=None, atlas_filter=None, zoom_to_view=False, zoom_to_view_buffer=0, zoom_to_view_map_id_list=[], open_composer=True, enable_edit_tools=True):
        """ Carrega un compositor a partir d'un fitxer i retorna l'objecte
            ---
            Load a composer from a file and return the object
            """
        # Carreguem el template en un document per poder pasar-li al QgsPrintLayout
        if os.path.splitext(report_pathname)[1].lower() != '.qpt':
            report_pathname += '.qpt'
        if not os.path.isabs(report_pathname):
            if os.path.exists(os.path.join(self.parent.plugin_path, report_pathname)):
                report_pathname = os.path.join(self.parent.plugin_path, report_pathname)
            elif os.path.exists(os.path.join(self.parent.plugin_path, "reports", report_pathname)):
                report_pathname = os.path.join(self.parent.plugin_path, "reports", report_pathname)
            elif os.environ.get('APP_PATH', None) and os.path.exists(os.path.join(os.environ['APP_PATH'], report_pathname)):
                report_pathname = os.path.join(os.path.abspath(os.environ['APP_PATH']), report_pathname)
            elif os.environ.get('APP_PATH', None) and os.path.exists(os.path.join(os.environ['APP_PATH'], "reports", report_pathname)):
                report_pathname = os.path.join(os.path.abspath(os.environ['APP_PATH']), "reports", report_pathname)
        with open(report_pathname, "r") as template_file:
            report_content = template_file.read()
        # Modifiquem els path relatius a paths absoluts a memòria
        report_path = os.path.dirname(report_pathname).replace("\\", "/")
        report_content = report_content.replace('"./', '"%s/' % report_path)
        report_content = report_content.replace('"../', '"%s/../' % report_path)

        # Creem l'objecte de l'informe
        document = QDomDocument()
        document.setContent(report_content)
        layout = QgsPrintLayout(QgsProject.instance())
        layout.loadFromTemplate(document, QgsReadWriteContext(), True)

        # Refresquem els objectes tipus mapa
        if zoom_to_view:
            for item in layout.items():
               if type(item) is QgsLayoutItemMap and (item.id() in zoom_to_view_map_id_list or not zoom_to_view_map_id_list):
                    item.zoomToExtent(self.parent.iface.mapCanvas().extent().buffered(zoom_to_view_buffer))
                    item.setMapRotation(self.iface.mapCanvas().rotation())
            layout.refresh()

        # Activem atles si cal
        if atlas_layer:
            atlas = layout.atlas()
            atlas.setEnabled(True)
            atlas.setCoverageLayer(atlas_layer)
            if atlas_filter:
                atlas.setFilterFeatures(True)
                atlas.setFilterExpression(atlas_filter)

        # Mostrem el diàleg si cal
        if open_composer:
            self.show_composer_view(layout, True if atlas_layer else False, enable_edit_tools)

        return layout

    def export_composition(self, composition, out_pathname):
        # Només suportem exportar PDFs
        if os.path.splitext(out_pathname)[1].lower() != ".pdf":
            return False

        # Si tenim atles, renderitzem totes les pàgines
        atlas = composition.atlas()
        if atlas and atlas.enabled():
            exporter = QgsLayoutExporter(atlas.layout())
            status, error = exporter.exportToPdf(atlas, out_pathname, QgsLayoutExporter.PdfExportSettings())
        else:
            # Generem el fitxer de sortida
            exporter = QgsLayoutExporter(composition)
            status = exporter.exportToPdf(out_pathname, QgsLayoutExporter.PdfExportSettings())
        return status == QgsLayoutExporter.ExportResult.Success

    def export_composition_as_image(self, composition, filepath):
        """ Exporta el contingut d'un composer com una imatge
            ---
            Export a composer's content as an image
            """
        dpi = composition.printResolution()
        dpmm = dpi / 25.4
        width = int(dpmm * composition.paperWidth())
        height = int(dpmm * composition.paperHeight())

        # create output image and initialize it
        image = QImage(QSize(width, height), QImage.Format_RGB888)
        image.setDotsPerMeterX(dpmm * 1000)
        image.setDotsPerMeterY(dpmm * 1000)
        image.fill(0)

        # render the composition
        imagePainter = QPainter(image)
        composition.renderPage(imagePainter, 0)
        imagePainter.end()

        # save as image
        filename, extension = os.path.splitext(os.path.basename(filepath))
        image.save(filepath, extension[1:])


class CrsToolsBase(object):
    """ Classe per manegar sistemes de coordenades
        ---
        Class to manages coordinates systems
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare a l'iface
            ---
            Initialization of member variables pointing to parent and iface
            """
        self.parent = parent
        self.iface = parent.iface

    def format_epsg(self, text, asPrefixedText):
        """ Formateja un codi epsg text segons si volem prefix o no
            Retorna "EPSG:25831" o "25831" (string)
            ---
            Format an epsg text code based on whether we want to prefix or not
            Returns "EPSG: 25831" or "25831" (string)
            """
        if not text:
            return text
        parts = text.split(':')
        if asPrefixedText:
            if len(parts) > 1:
                return text
            else:
                return "EPSG:" + text
        else:
            if len(parts) > 1:
                return parts[1]
            else:
                return text

    def select_epsg(self, asPrefixedText = False):
        """ Obté un codi epsg a escollir en el diàleg estàndar QGIS
            ---
            Get an epsg code to choose from the standard QGIS dialog
            """
        ps = QgsProjectionSelectionDialog()
        ps.exec_()
        crs = ps.crs()
        if crs:
            return self.format_epsg(crs.authid(), asPrefixedText)
        else:
            return None

    def get_crs(self, epsg):
        """ Obté un objecte CRS a partir d'un codi epsg
            ---
            Obtain a CRS object from an epsg code
            """
        epsg = self.format_epsg(str(epsg), True) # Gets "EPSG:<code>"
        crs = QgsCoordinateReferenceSystem(epsg)
        return crs

    def get_transform(self, in_epsg, out_epsg):
        """ Obté un objecte transformació a partir de 2 codis epsg
            ---
            Obtains a transformation object from 2 epsg codes
            """
        ct = QgsCoordinateTransform(self.get_crs(in_epsg), self.get_crs(out_epsg), QgsProject.instance())
        return ct

    def transform_point(self, x, y, source_epsg, destination_epsg=None):
        """ Converteix la coordenada x,y d'un epsg origen a un destí,
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat
            ---
            Converts the x, y coordinate of an epsg source to a destination,
            if the destination is not specified, the project loaded will be used
            """
        if not destination_epsg:
            destination_epsg = self.parent.project.get_epsg()
        if int(source_epsg) == int(destination_epsg):
            return x, y

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        point = ct.transform(x, y)
        return point.x(), point.y()

    def transform_bounding_box(self, area, source_epsg, destination_epsg=None):
        """ Converteix l'àrea especificada d'un epsg origen a un destí,
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat
            ---
            Converts the specified area from an epsg source to a destination,
            if the destination is not specified, the project loaded will be used
            """
        if not destination_epsg:
            destination_epsg = int(self.parent.project.get_epsg())
        if int(source_epsg) == int(destination_epsg):
            return area

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        area = ct.transformBoundingBox(area)
        return area

    def transform_polygon(self, poly, source_epsg, destination_epsg=None):
        """ Converteix la geometria especificada d'un epsg origen a un destí,
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat
            ---
            Converts the specified geometry from an epsg source to a destination,
            if the destination is not specified, the project loaded will be used
            """
        if not destination_epsg:
            destination_epsg = int(self.parent.project.get_epsg())
        if int(source_epsg) == int(destination_epsg):
            return poly

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        poly = ct.transformPolygon(poly)
        return poly

    def transform(self, geo, source_epsg, destination_epsg=None):
        """ Converteix la geometria especificada d'un epsg origen a un destí,
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat
            ---
            Converts the specified geometry from an epsg source to a destination,
            if the destination is not specified, the project loaded will be used
            """
        if not destination_epsg:
            destination_epsg = int(self.parent.project.get_epsg())
        if int(source_epsg) == int(destination_epsg):
            return geo

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        if type(geo) == QgsPointXY:
            # Tranformació de punt
            new_geo = ct.transform(geo) 
        elif type(geo) == QgsRectangle:
            # Tranformació de rectangle
            new_geo = ct.transformBoundingBox(geo)
        else:
            # Transformació de geometria (in place, per això duplico la geometria)
            new_geo = QgsGeometry(geo)
            new_geo.transform(ct)
        return new_geo


class DebugBase(object):
    """ Classe per amb funcions de debug i test
        ---
        Class with debug and test functions
        """
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare, a l'iface,
            inicialització de llista de timestamps i consola de QGIS
            ---
            Initialization of member variables pointing to parent and iface,
            timestamp list initialization and QGIS console
            """
        self.parent = parent
        self.iface = parent.iface

        # Inicialitzem els comptadors de temps
        self.ini_timestamps()

        # Inicialitem la consola
        self.ini_console()

    ###########################################################################
    # Gestió de consola QGIS
    #
    def ini_console(self):
        """ Inicialitza la consola de QGIS perquè els plugins puguin printar-hi
            ---
            Initializes the QGIS console so that the plugins can be printed
            """
        # Forcem crear l'objecte consola del modul "console.console" perquè la resta de plugins
        # puguin printar logs i l'amaguem
        if console.console._console is None:
            parent = self.iface.mainWindow() if self.iface else None
            console.console._console = console.console.PythonConsole( parent )
            ##console.console._console.hide()
            self.show_console(False)

    def show_console(self, show = True):
        """ Mostra / Oculta la consola de QGIS
            ---
            Show / Hide the QGIS console
            """
        if show == console.console._console.isHidden():
            self.toggle_console()

    def toggle_console(self):
        """ Mostra / Oculta la consola de QGIS (canvia l'estat previ)
            ---
            Show / Hide the QGIS console (change previous state)
            """
        console.show_console() # Fa toggle

    ###########################################################################
    # Recàrrega de plugins
    #
    def reload_plugins(self, plugins_list=None, plugins_id_wildcard="qp*"):
        """ Recarrega els plugins que coincideixin amb el wildcard
            ---
            Reload the plugins that match the wildcard
            """
        # Recarreguem els plugins
        if not plugins_list:
            plugins_list = [plugin_id for plugin_id in plugins.keys() if fnmatch.fnmatch(plugin_id, plugins_id_wildcard)]
        with ProgressDialog('Llegint geometries...', len(plugins_list), "Recarregant plugins", cancel_button_text = "Cancel·lar", autoclose = True) as progress:
            for plugin_id in plugins_list:
                progress.set_label("Recarregant %s" % plugin_id)
                self.reload_plugin(plugin_id)
                if progress.was_canceled():
                    return
                progress.step_it()

    def reload_plugin(self, plugin_id):
        """ Recarrega el plugin indicat per l'id
            ---
            Reload the plugin indicated by the id
            """
        if self.parent.log:
            self.parent.log.debug("Reload: %s", plugin_id)
        with WaitCursor():
            reloadPlugin(plugin_id)
        # Restaurem el cursor, per si algún plugin l'ha deixat penjat
        QApplication.restoreOverrideCursor()

    ###########################################################################
    # Unit tests
    #
    def is_test_available(self, plugin_subfolder="test", test_files_pattern="test*.py"):
        """ Retorna True si el plugin té UnitTest disponbiles
            ---
            Returns True if plugin has UnitTests availables
            """
        test_files_path = os.path.join(self.parent.plugin_path, plugin_subfolder)
        if not os.path.exists(test_files_path):
            return False        
        return len(glob.glob(os.path.join(test_files_path, test_files_pattern))) > 0

    def get_test_suite(self, plugin_subfolder="test", test_files_pattern="test*.py"):
        """ Detecta arxius de test i retorna un UnitTestSuit 
            ---
            Detects test files and return a UnitTestSuit
            """
        test_files_path = os.path.join(self.parent.plugin_path, plugin_subfolder)
        if not os.path.exists(test_files_path):
            return None
        test_suite = unittest.defaultTestLoader.discover(test_files_path, test_files_pattern)
        return test_suite

    def get_test_names(self, plugin_subfolder="test", test_files_pattern="test*.py", suite=None):
        """ Retorna una llista de tuples amb els tests disponibles [(<test_name>, <test_class>), ...]
            ---
            Returns a tuple list with all availabes tests [(<test_name>, <test_class>), ...]
            """
        if not suite:
            suite = self.get_test_suite()
        names_list = []
        if hasattr(suite, '__iter__'):
            for t in suite:
                names_list += self.get_test_names(suite=t)
        else:
            names_list.append(str(suite))
        return names_list

    def get_test(self, test_name, suite):
        """ Retorna la funció de test corresponent a <test_name>
            ---
            Returns test call named as <test_name>
            """
        if not suite:
            suite = self.get_test_suite()
        test_call = None
        if hasattr(suite, '__iter__'):
            for t in suite:
                test_call = self.get_test_names(suite=t)
                if test_call:
                    break
        else:
            test_call = suite if str(suite) == test_name else None
        return test_call
        
    def test_plugin(self, test_name=None, plugin_subfolder="test", test_files_pattern="test*.py"):
        """ Executa els UnitsTests del plugin i retorna objecte UnitTestResult i un text amb el resultat del test
            ---
            It execute UnitTests and return UnitTestResult objent and test text result
            """
        test_suite = self.get_test_suite(plugin_subfolder, test_files_pattern)
        if test_name:
            test_call = self.get_test(test_name, test_suite)
            if test_call:
                test_suit = test_call
        with io.StringIO() as memory:
            test_result = unittest.TextTestRunner(stream=memory, verbosity=2).run(test_suite)
            memory.seek(0)
            test_text = memory.read()
        return test_result, test_text

    def show_test_plugin(self, title="Unit Tests", test_name=None, plugin_subfolder="test", test_files_pattern="test*.py"):
        """ Mostra el resultat dels UnitTests en un diàleg
            ---
            Show UnitTest results in a dialog
            """
        test_result, test_text = self.test_plugin(test_name, plugin_subfolder, test_files_pattern)
        # Test result attributes: test_result.errors, test_result.failures, test_result.skipped
        log_info_mode = LogInfoDialog.mode_info if not test_result.errors and not test_result.failures else LogInfoDialog.mode_error
        LogInfoDialog(test_text, title, log_info_mode, width=1000, height=800)


    ###########################################################################
    # Gestió de timestamps
    #
    def ini_timestamps(self, description=None, timestamp_env='QGIS_STARTUP', timestamp_format="%d/%m/%Y %H:%M:%S.%f"):
        """ Afegeix un timestamp a partir d'una variable d'entorn amb l'hora d'inici de QGIS si existex
            ---
            Add a timestamp from an environment variable with the QGIS start time if it exists
            """
        self.timestamps = []

        # Obtenim el timestamp d'inici de QGIS, si no en tenim no fem res més
        timestamp_text = os.environ.get(timestamp_env, None)
        if not timestamp_text:
            return

        # Registrem la data d'ini del QGIS
        try:
            # Eliminem el dia de la setmana i dobles espais
            timestamp_text = " ".join([v for v in timestamp_text.replace(",", ".").split()[-2:] if v])
            # Obtenim la data i la hora
            timestamp = datetime.datetime.strptime(timestamp_text, timestamp_format) if timestamp_text else None
        except Exception as e:
            timestamp = None
        if timestamp:
            self.add_timestamp(description if description else "QGIS ini\t", timestamp)

    def add_timestamp(self, description, timestamp = None):
        """ Afegeix una timestamp a la llista de timestamps a mostrar
            ---
            Add a timestamp to the list of timestamps to show
            """
        self.timestamps.append((description, datetime.datetime.now() if timestamp is None else timestamp))

    def get_timestamps_total_time(self):
        """ Retorna el temps total registrat 
            --- 
            Retuns registered total time
            """
        if len(self.timestamps) < 2:
            return None
        return self.timestamps[-1][1] - self.timestamps[0][1]
    
    def get_timestamps_info(self, info = "Load times"):
        """ Obté informació dels timestamps existents
            ---
            Get information about existing timestamps
            """
        times_list = ["%s\t%s %s %s" % (description, timestamp, \
            ("(%s)" % (timestamp - self.timestamps[i-1][1]) if i > 0 else ""), \
            ("(%s)" % (timestamp - self.timestamps[0][1]) if i > 0 else "")) \
            for i, (description, timestamp) in enumerate(self.timestamps)]
        return "%s:\n   %s\nTotal: %s" % (info, "\n   ".join(times_list), self.timestamps[-1][1] - self.timestamps[0][1])

    def print_timestamps_info(self, info = "Load times"):
        """ Mostra per consola informació dels timestamps existents
            ---
            Prints console information for existing timestamps
            """
        print(self.get_timestamps_info(info))


class ToolsBase(object):
    """ Classe amb eines d'alt nivell a afegir opcionalment a QGIS
        ---
        Class with high level tools to optionally add to QGIS
        """
    # Components a desactivar de QGIS per defecte
    disable_menus_ids = [u'mProjectMenu', u'mEditMenu', u'mViewMenu', u'mLayerMenu', u'mSettingsMenu', u'mPluginMenu', u'mVectorMenu',
        u'mRasterMenu', u'processing', u'mHelpMenu', u'mDatabaseMenu', u'mWebMenu', u'mMeshMenu'
        ]
    #disable_menus_titles = [
    #    u'P&roject', u'&Edit', u'&View', u'&Layer', u'&Settings', u'&Plugins', u'Vect&or',
    #    u'&Raster', u'&Database', u'&Web', u'Processing',
    #    ##u'&Help',
    #    u'P&royecto', u'&Edición', u'&Ver', u'&Capa', u'C&onfiguración', u'Co&mplementos',
    #    ##u'Vect&orial', u'&Ráster',
    #    u'Base de &datos', u'&Web', u'Procesado',
    #    u'A&yuda'
    #    ]
    disable_toolbars_ids = [
        u'mFileToolBar', u'mLayerToolBar',
        # u'mDigitizeToolBar',
        u'mAdvancedDigitizeToolBar',
        # u'mMapNavToolBar', u'mAttributesToolBar',
        u'mPluginToolBar', u'mHelpToolBar', u'mRasterToolBar', u'mLabelToolBar', u'mVectorToolBar', u'mDatabaseToolBar', u'mWebToolBar',
        u'mSnappingToolBar', u'mDataSourceManagerToolBar', u'mShapeDigitizeToolBar'
        ]
    #disable_toolbars_titles = [
    #    u'File', u'Manage Layers', u'Digitizing', u'Advanced Digitizing',
    #    u'Plugins', u'Help', u'Raster', u'Label', u'Vector', u'Database', u'Web', u'GRASS',
    #    ##u'Map Navigation', u'Attributes',
    #    u'Archivo', u'Administrar capas',
    #    ##u'Digitalización',
    #    u'Digitalización avanzada',
    #    u'Complementos', u'Ayuda', u'Ráster', u'Etiqueta', u'Vectorial', u'Base de datos', u'Web', u'GRASS',
    #    ##u'Navegación de mapas', u'Atributos'
    #    ]
    disable_dockwidgets_ids = [
        u'UserInputDockWidget', u'undo/redo dock', u'AdvancedDigitizingTools', u'StatistalSummaryDockWidget', u'BookmarksDockWidget',
        #u'Layers',
        u'LayerOrder',
        #u'Overview',
        u'LayerStyling', u'Browser', u'Browser2', u'GPSInformation',
        #u'MessageLog',
        u'CoordinateCapture', u'theTileScaleDock',
        ]
    #disable_dockwidgets_titles = [
    #    u'Browser', u'Browser (2)', u'GPS Information',
    #    u'Layer order', u'Shortest path', u'Tile scale', u'Toolbox', u'Undo/Redo'
    #    ##u'Layers', u'Overview', u'Log Messages', u'Coordinate Capture',
    #    u'Explorador', u'Explorador (2)', u'Información de GPS',
    #    u'Orden de capas', u'Ruta más corta', u'Escala de tesela', u'Caja de herramientas', u'Deshacer/Rehacer',
    #    ##u'Capas', u'Vista general', u'Mensajes de, registro', u'Captura de coordenadas']
    #    ]

    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare, a l'iface i
            inicialització de llistes de components inicials de QGIS
            ---
            Initialization of member variables pointing to parent, iface and
            initialization of QGIS initial component lists
            """
        self.parent = parent
        self.iface = parent.iface

        # Activació / desactivació eines QGIS
        self.initial_menus = []
        self.initial_toolbars = []
        self.initial_dockwidgets_and_areas = []
        self.last_disable_mode = None

        # Diàlegs auxiliars i gestió de time series
        self.transparency_dialog = None
        self.time_series_dialog = None
        self.anaglyph_dialog = None

        # Map change current layer event
        self.iface.layerTreeView().currentLayerChanged.connect(self.on_change_current_layer)
        QgsProject.instance().layerRemoved.connect(self.on_layer_removed)

    def remove(self):
        """ Desmapeja l'event de canvi de capa activa
            ---
            Unmap changes current layer event
            """
        self.iface.layerTreeView().currentLayerChanged.disconnect(self.on_change_current_layer)
        QgsProject.instance().layerRemoved.disconnect(self.on_layer_removed)
        if self.time_series_dialog:
            self.time_series_dialog.close()
            self.iface.removeDockWidget(self.time_series_dialog)
            self.time_series_dialog = None
        if self.transparency_dialog:
            self.transparency_dialog.close()
            self.iface.removeDockWidget(self.transparency_dialog)
            self.transparency_dialog = None
        if self.anaglyph_dialog:
            self.anaglyph_dialog.close()
            self.iface.removeDockWidget(self.anaglyph_dialog)
            self.anaglyph_dialog = None

    def add_shortcut_QGIS_options(self, description = "Eines QGIS", keyseq = "Ctrl+Alt+F12"):
        """ Afegeix un shortcut per mostrar / ocultar els menús / toolbars de QGIS
            ---
            Add a shortcut to show / hide QGIS menus / toolbars
            """
        #Creem un shortcut per activer les opcions per defecte de QGIS
        self.parent.gui.add_shortcut(description, keyseq, self.toggle_QGIS_options)

    def toggle_QGIS_options(self, hide_not_remove=None):
        """ Mostra / Oculta els menús / toolbars de QGIS (canvia l'estat previ)
            ---
            Show / Hide QGIS menus / toolbars (change previous state)
            """
        actions_name = [a.text() for a in self.iface.mainWindow().menuBar().actions() if a.isVisible()]
        is_plugins_menu = self.iface.pluginMenu().title() in actions_name
        # Gestionem les opcions per defecte de QGIS
        if is_plugins_menu:
            # Esborrem els menus addicionals
            self.enable_QGIS_options(False, hide_not_remove)
        else:
            # Afegim opcions al menú
            self.enable_QGIS_options(True, hide_not_remove)

    def enable_QGIS_options(self, enable, hide_not_remove = True, menus_ids = None, toolbars_ids = None, dockwidgets_ids = None):
        """ Mostra / Oculta els menús / toolbars de QGIS
            ---
            Show / Hide QGIS menus / toolbars
            """
        # Ens guardem el components originals de QGIS
        if not self.initial_menus:
            self.initial_menus = self.parent.gui.get_menus()
        if not self.initial_toolbars:
            self.initial_toolbars = self.parent.gui.get_toolbars()
        if not self.initial_dockwidgets_and_areas:
            self.initial_dockwidgets_and_areas = [(w, self.iface.mainWindow().dockWidgetArea(w)) for w in self.parent.gui.get_dock_widgets()]

        # Determinem quins components amagar (si no hi ha els agafem per defecte)
        if hide_not_remove == None:
            hide_not_remove = self.last_disable_mode
        else:
            self.last_disable_mode = hide_not_remove
        if not menus_ids:
            menus_ids = self.disable_menus_ids
        if not toolbars_ids:
            toolbars_ids = self.disable_toolbars_ids
        if not dockwidgets_ids:
            dockwidgets_ids = self.disable_dockwidgets_ids

        # Determinem quines opcions tenim actualment actives
        current_menus = self.parent.gui.get_menus()
        current_toolbars = self.parent.gui.get_toolbars()
        current_dockwidgets = self.parent.gui.get_dock_widgets()

        # Desactivem/Activem els menus
        for menu in self.initial_menus:
            if menu.objectName() in menus_ids:
                if enable:
                    if menu not in current_menus:
                        self.iface.mainWindow().menuBar().addMenu(menu)
                    else:
                        menu.menuAction().setVisible(True)
                else:
                    if menu in current_menus:
                        if hide_not_remove:
                            menu.menuAction().setVisible(False)
                        else:
                            self.iface.mainWindow().menuBar().removeAction(menu.menuAction())

        # Desactivem/Activem les toolbars
        for toolbar in self.initial_toolbars:
            if toolbar.objectName() in toolbars_ids:
                if enable:
                    ##print("Toolbar show", toolbar.windowTitle())
                    ##if toolbar not in current_toolbars: # Sempre estan??
                    self.iface.addToolBar(toolbar)
                    toolbar.show()
                else:
                    if toolbar in current_toolbars:
                        if hide_not_remove:
                            ##print("Toolbar hide", toolbar.windowTitle())
                            toolbar.hide()
                        else:
                            ##print("Toolbar remove", toolbar.windowTitle())
                            self.iface.mainWindow().removeToolBar(toolbar)

        # Desactivem/Activem els dockwidtgets
        for widget, area in self.initial_dockwidgets_and_areas:
            if widget.objectName() in dockwidgets_ids:
                if enable:
                    ##if widget not in current_dockwidgets: # Sempre estan??
                    self.iface.addDockWidget(area, widget)
                    widget.hide() # Per defecte es visualitzen i molesten...
                else:
                    if widget in current_dockwidgets:
                        if hide_not_remove:
                            widget.hide()
                        else:
                            self.iface.removeDockWidget(widget)

        # Reorganitzem les toolbars
        self.parent.gui.organize_toolbars()

    def add_shortcut_organize_toolbars(self, description = "Organitzar toolbar", keyseq = "Ctrl+Alt+F10"):
        """ Afegeix un shortcut per organitzar la toolbar de QGIS
            ---
            Add a shortcut to organize the QGIS toolbar
            """
        self.parent.gui.add_shortcut(description, keyseq, self.parent.gui.organize_toolbars)

    def add_shortcut_console(self, description = "Consola python", keyseq = "Ctrl+Alt+F9"):
        """ Afegeix un shortcut per mostrar la consola de QGIS
            ---
            Add a shortcut to display the QGIS console
            """
        self.parent.gui.add_shortcut(description, keyseq, self.parent.debug.toggle_console)

    def add_tool_console(self, tool_name="&Consola de Python", toolbar_name="&Manteniment", menu_name="&Manteniment", add_separator=True):
        """ Afegeix un botó per mostrar la consola de QGIS
            ---
            Add a button to display the QGIS console
            """
        if toolbar_name:
            self.parent.gui.configure_toolbar(toolbar_name, [
                (tool_name, self.parent.debug.toggle_console, QIcon(":/lib/qlib3/base/images/console.png"))
                ], add_separator=add_separator)
        if menu_name:
            self.parent.gui.configure_menu(menu_name, [
                (tool_name, self.parent.debug.toggle_console, QIcon(":/lib/qlib3/base/images/console.png"))
                ], add_separator=add_separator)

    def add_tool_reload_plugins(self, plugins_id_list=[], plugins_id_wildcard = "*Q", tool_name="&Recarregar plugins ICGC", toolbar_and_menu_name="&Manteniment"):
        """ Afegeix eina per recarregar els plugins que coincideixin amb el wildcard
            ---
            Add tool to reload plugins that match the wildcard
            """
        self.parent.gui.configure_GUI(toolbar_and_menu_name, [
            (tool_name, lambda l=plugins_id_list, w=plugins_id_wildcard : self.parent.debug.reload_plugins(l, w), QIcon(":/lib/qlib3/base/images/python.png"))
            ])

    def add_tool_refresh_map_and_legend(self, tool_name, remove_refresh_map, id="ToolRefreshMapAndLegend"):
        """ Afegeix o actualitza el botó de refresc per actualitzar també la llegenda
            ---
            Add or refresh the refresh button to also update the legend
            """
        self.action_refresh_all = self.parent.gui.find_action(id, self.iface.mapNavToolToolBar().actions())
        # Si no existeix creem l'acció
        if not self.action_refresh_all:
            self.action_refresh_all = QAction(QIcon(":/lib/qlib3/base/images/refresh_all.png"), tool_name, self.iface.mainWindow())
            self.action_refresh_all.setObjectName(id)
            self.action_refresh_all.triggered.connect(self.parent.refresh_all)
            # Afegim el botó de la eina a la toolbar
            if remove_refresh_map:
                self.iface.mapNavToolToolBar().removeAction(self.iface.mapNavToolToolBar().actions()[-1])
            self.iface.mapNavToolToolBar().addAction(self.action_refresh_all)
            # Registro l'acció perquè el destructor del plugin l'esborri automàticament al descarregar-lo
            self.parent.gui.actions.append((self.iface.mapNavToolToolBar(), self.action_refresh_all))

    def show_transparency_dialog(self, title=None, layer=None, transparency=None, show=True):
        """ Mostra un diàleg simplificat per escollir la transparència d'una capa
            ---
            Show simplified transparency layer dialog
            """
        if not self.transparency_dialog:
            self.transparency_dialog = TransparencyDialog(title, layer, transparency, show, self.iface.mainWindow())
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.transparency_dialog)
        else:
            if show:
                if title:
                    self.transparency_dialog.setWindowTitle(title)
                if transparency:
                    self.transparency_dialog.set_transparency(transparency)
                if layer:
                    self.transparency_dialog.set_layer(layer)
                self.transparency_dialog.show()
            else:
                self.transparency_dialog.hide()

    def toggle_transparency_dialog(self, title=None, layer=None, transparency=None):
        self.show_transparency_dialog(title, layer, transparency, not self.transparency_dialog.isVisible() if self.transparency_dialog else True)

    def show_time_series_dialog(self, layer, title=None, current_prefix="", show=True):
        # Mostrem o ocultem el diàleg de sèries temporals
        if show:
            # Obtenim la llista de capes temporal del diccionari de sèries temporals
            time_series_tuple_list = self.parent.layers.time_series_dict.get(layer, [])
            if not time_series_tuple_list:
                return
            # Obtenim la url de la capa i la capa seleccionada
            url, current_layer, current_time = self.parent.layers.parse_wms_t_layer(layer)
            # Obtenim el nom de la capa actual (per wms-t fake tipus arxiu http)
            if not current_layer:
                current_layer = layer.dataProvider().dataSourceUri()
            # Obtenim el nom de la capa actual dins de la time serie (per wms-t fake tipus wms)
            if not current_time:
                current_time = dict([(layer_id, name) for name, layer_id in time_series_tuple_list])[current_layer]
            time_series_list = [name for name, layer_id in time_series_tuple_list]

            # Si no tenim el diàleg el creem i el mostrem
            update_callback = lambda current_time: self.parent.layers.update_wms_t_layer_current_time(layer, current_time)
            if not self.time_series_dialog:
                self.time_series_dialog = TimeSeriesDialog(time_series_list, current_time,
                    layer.name().replace(" [%s]" % current_time, ""), update_callback,
                    title, current_prefix, True, self.iface.mainWindow())
                self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.time_series_dialog)
                # Mapegem l'event de visibilitat per detectar quan tanquin el widget i poder refrescar
                # algun botó si cal... en principi això està implementat en l'event de canvi de capa
                # (que detecta si es tracta d'una capa WMS-T o no) per això emeto un un signal perquè
                # s'executi
                self.time_series_dialog.visibilityChanged.connect(lambda dummy:self.iface.layerTreeView().currentLayerChanged.emit(self.iface.mapCanvas().currentLayer()))
            else:
                # Configurem el diàleg
                if title:
                    self.time_series_dialog.setWindowTitle(title)
                if layer:
                    self.time_series_dialog.set_time_series(time_series_list, current_time, layer.name(), update_callback)
                # Activem els controls
                self.time_series_dialog.set_enabled(True)
                # Mostrem el diàleg
                self.time_series_dialog.show()
        else:
            if self.time_series_dialog:
                self.time_series_dialog.hide()

    def toggle_time_series_dialog(self, layer, title=None, current_prefix=""):
        self.show_time_series_dialog(layer, title, current_prefix, not self.time_series_dialog.isVisible() if self.time_series_dialog else True)

    def show_anaglyph_dialog(self, layer=None, title=None, parallax_label="", inverted_stereo_label="", show=True):
        # Mostrem o ocultem el diàleg de sèries temporals
        if show:
            if not layer:
                layer = self.parent.layers.get_current_layer()
            # Obtenim els valors de paral·laxi
            photo_id = "dummy"
            parallax = 100
            inverted_stereo = False
            found = re.search(r"styles=([^&]+)", layer.dataProvider().uri().uri().lower() if layer else "")
            if found:
                anaglyph_params_list = found.groups()[0].split(",")
                if len(anaglyph_params_list) == 3:
                    photo_id =  anaglyph_params_list[0]
                    parallax = int(anaglyph_params_list[1])
                    inverted_stereo = anaglyph_params_list[2] == "true"
            # Si no tenim el diàleg el creem i el mostrem
            update_callback = lambda parallax, inverted_stereo: self.parent.layers.update_wms_layer(layer, wms_style=",".join([photo_id, str(parallax), "true" if inverted_stereo else "false"]))
            if not self.anaglyph_dialog:
                self.anaglyph_dialog = AnaglyphDialog(layer.name() if layer else "", update_callback, parallax, inverted_stereo,
                    title, parallax_label, inverted_stereo_label, True, self.iface.mainWindow())
                self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.anaglyph_dialog)
                # Mapegem l'event de visibilitat per detectar quan tanquin el widget i poder refrescar
                # algun botó si cal... en principi això està implementat en l'event de canvi de capa
                # (que detecta si es tracta d'una capa WMS-T o no) per això emeto un un signal perquè
                # s'executi
                #self.anaglyph_dialog.visibilityChanged.connect(lambda dummy:self.iface.layerTreeView().currentLayerChanged.emit(self.iface.mapCanvas().currentLayer()))
            else:
                # Configurem el diàleg
                if title:
                    self.anaglyph_dialog.setWindowTitle(title)
                if layer:
                    self.anaglyph_dialog.update_title(layer.name())
                    self.anaglyph_dialog.set_callback(update_callback)
                self.anaglyph_dialog.set_anaglyph(parallax, inverted_stereo)
                # Mostrem el diàleg
                self.anaglyph_dialog.show()
            # Activem els controls
            self.anaglyph_dialog.set_enabled(self.parent.layers.is_anaglyph_layer(layer) if layer else False)
        else:
            if self.anaglyph_dialog:
                self.anaglyph_dialog.hide()

    def toggle_anaglyph_dialog(self, layer, title=None, current_prefix=""):
        self.show_anaglyph_dialog(layer, title, current_prefix, not self.anaglyph_dialog.isVisible() if self.anaglyph_dialog else True)

    def on_change_current_layer(self, layer):
        """ Activa o desactiva les opcions de sèries temporals / transparència segons la capa seleccionada
            ---
            Enable disable time series options / transparency according to the selected layer
            """
        # Disable time series dialog or refresh it
        if self.time_series_dialog:
            is_wms_t = layer is not None and self.parent.layers.is_wms_t_layer(layer)
            self.time_series_dialog.set_enabled(is_wms_t)
            if is_wms_t and self.time_series_dialog.isVisible():
                self.show_time_series_dialog(layer)
        # Refresh transparence dialog
        if self.transparency_dialog:
            if self.transparency_dialog.isVisible():
                self.show_transparency_dialog(layer=layer)
        # Refresh anaglyph dialog
        if self.anaglyph_dialog:
            is_anaglyph = layer is not None and self.parent.layers.is_anaglyph_layer(layer)
            self.anaglyph_dialog.set_enabled(is_anaglyph)
            if is_anaglyph and self.anaglyph_dialog.isVisible():
                self.show_anaglyph_dialog(layer=layer)

    def on_layer_removed(self, layer):
        if self.parent and self.parent.layers and self.parent.layers.time_series_dict:
            time_series_list = self.parent.layers.time_series_dict.get(layer, [])
            if time_series_list:
                self.parent.layers.time_series_dict.pop(layer)

    #def is_selected_db_styled_layers(self):
    #    """ Obtenim hi ha alguna capa seleccionada amb estil de bbdd, incloent grups
    #        ---
    #        Gets if there are any db styled layer includes layers in groups
    #        """
    #    layers_list = []
    #    selected_groups_list = self.parent.legend.get_selected_groups()
    #    for group in selected_groups_list:
    #        layers_list += self.parent.layers.get_group_layers_by_id(group.name())
    #    layers_list += self.parent.layers.get_selected_layers()

    #    for layer in layers_list:
    #        if type(layer) == QgsVectorLayer and self.parent.layers.get_db_styles(layer):
    #            return True
    #    return False
    def get_selected_db_styled_layers(self):
        """ Obtenim les capes seleccionades amb estil BD incloent les de dins d'un grup
            ---
            Gets selected layers with db styles includes layers in groups
            """
        layers_list = []
        selected_groups_list = self.parent.legend.get_selected_groups()
        for group in selected_groups_list:
            layers_list += self.parent.layers.get_group_layers_by_id(group.name())
        layers_list += self.parent.layers.get_selected_layers()
        layers_list = [layer for layer in list(set(layers_list)) if type(layer) == QgsVectorLayer and self.parent.layers.get_db_styles(layer)]

        return layers_list

    def get_group_db_styled_layers(self, group):
        """ Obtenim les capes amb estil BD de dins d'un grup
            ---
            Gets layers with db styles from a group
            """
        layers_list = self.parent.layers.get_group_layers_by_id(group.name())
        db_layers_list = [layer for layer in layers_list if type(layer) == QgsVectorLayer and self.parent.layers.get_db_styles(layer)]
        return db_layers_list

    def is_current_group_db_styled_layers(self):
        """ Obtenim si el grup actual té capes amb estil BD
            ---
            Gets if current group has layers with db styles
            """
        node = self.iface.layerTreeView().currentNode()
        is_geopackage_layer = type(node) == QgsLayerTreeGroup and len(self.get_group_db_styled_layers(node)) > 0
        return is_geopackage_layer

    def show_db_styles_dialog(self, title=None, show=True):
        """ Mostra el diàleg d'estils per capes amb estils a bbdd
            ---
            Show styles dialog por db styled layers
            """
        # Obtenim les capes seleccionades incloent les de dins d'un grup
        layers_list = self.get_selected_db_styled_layers()

        # Generem una llista de capes amb un diccionari amb l'id d'estil i tupla de (nom, descripció)
        layers_styles_dict_list = [(layer.id(), layer.name(), self.parent.layers.is_visible(layer), None, self.parent.layers.get_db_styles(layer)) for layer in layers_list]
        layers_styles_dict_list.sort(key = lambda v:v[1])

        # Mostrem el diàleg d'stils
        dlg = StylesDialog(layers_styles_dict_list, title, True, self.iface.mainWindow())
        if dlg.is_cancelled():
            return

        # Carreguem els nous estils
        layers_style_list = dlg.get_layers_styles()
        for layer_id, visible, style_id in layers_style_list:
            if layer_id:
                self.parent.layers.set_visible_by_id(layer_id, visible)
                if style_id:
                    self.parent.layers.set_db_style_by_id(layer_id, style_id)

    def send_email(self, mail_to, subject="", body="", copy_to="", hidden_copy_to=""):
        """ Envia un email fent servir el client del sistema
            ---
            Send email using system email client
            """
        mail_url = "mailto:%s?subject=%s%s%s%s" % (
            mail_to,
            subject or " ",
            ("&body=%s" % urllib.parse.quote(body, safe="")) if body else "",
            ("&cc=%s" % copy_to) if copy_to else "",
            ("&bcc=%s" % hidden_copy_to) if hidden_copy_to else "")
        return self.parent.show_url(mail_url)


class MetadataBase(object):
    """ Classe per accedir a les metadades del plugin
        ---
        Class to access to plugin metadata
        """
    def __init__(self, parent, plugin_pathname):
        """ Inicialització de variables membre apuntant al pare, a l'iface i
            càrrega del fitxer de metadades del plugin
            ---
            Initialization of member variables pointing to parent, iface and
            loading the metadata file for the plugin
            """
        self.parent = parent
        self.iface = parent.iface

        # Carreguem informació del metadata.txt
        self.metadata = configparser.ConfigParser()
        self.metadata.read(os.path.join(os.path.dirname(plugin_pathname), 'metadata.txt'), "utf8")

    def get(self, option, section="general", default_value=""):
        """ Retorna una metadada del plugin especificada en el fitxer metadata.txt
            ---
            Returns a metadata value of the plugin specified in the metadata.txt file
            """
        return self.metadata.get(section, option) if self.metadata.has_option(section, option) else default_value

    def get_name(self):
        """ Obté el nom del plugin actual
            ---
            Gets the name of the current plugin
            """
        return self.get("name")

    def get_icon(self, icon_name="icon.png"):
        """ Obté el QIcon del plugin per defecte (:/plugins/<plugin_name>/icon.png)
            ---
            Gets plugin default QIcon object (:/plugins/<plugin_name>/icon.png)
            """
        #icon_ref = ":/plugins/%s/%s" % (self.parent.plugin_id.lower(), icon_name)
        #icon = QIcon(icon_ref)
        if not os.path.splitext(icon_name)[1]:
            icon_name += ".png"
        if not os.path.isabs(icon_name):
            icon_pathname = os.path.join(self.parent.plugin_path, icon_name)
        else:
            icon_pathname = icon_name
        icon = QIcon(icon_pathname)
        return icon

    def get_version(self):
        """ Obté la versió del plugin actual
            ---
            Gets the version of the current plugin
            """
        return self.get("version")

    def get_description(self, language=None):
        """ Obté la descripció curta del plugin actual en l'idioma especificat (per defecte l'idioma de QGIS)
            ---
            Gets the short description of the current plugin in the specified language (QGIS language defect)
            """
        # Carreguem la descripció curta segon l'idioma del QGIS
        if not language:
            language = self.parent.translation.get_qgis_language()
        if language == self.parent.translation.LANG_CA:
            # Català
            description = self.get("description_ca")
        elif language == self.parent.translation.LANG_ES:
            # Castellà
            description = self.get("description_es")
        else:
            # Per defecte anglés
            description = self.get("description_en")
        if not description:
            # Si no agafem la descripció estàndar que hem fet servir en el metadata.txt
            description =self.get("description")

        return description

    def get_about(self, replace_text_with_newline="  ", language_split_text="---\n", language=None):
        """ Obté la descripció llarga del plugin actual en l'idioma especificat (per defecte d'idioma de QGIS)
            ---
            Gets the long description of the current plugin in the specified language (QGIS language defect)
            """
        # Detectem si tenim un about multi idioma (separats per doble canvi de linia)
        multi_about_list = self.get("about").split(language_split_text)

        # Carreguem la descripció llarga segon l'idioma del QGIS
        if not language:
            language = self.parent.translation.get_qgis_language()
        if language == self.parent.translation.LANG_CA:
            # Català
            about = self.get("about_ca")
            if not about and len(multi_about_list) > 1:
                # Suposo que el català està en segona posició
                about = multi_about_list[1]
        elif language == self.parent.translation.LANG_ES:
            # Castellà
            about = self.get("about_es")
            if not about and len(multi_about_list) > 2:
                # Suposo que el castellà està en tercera posició
                about = multi_about_list[2]
        else:
            # Per defecte anglés
            about = self.get("about_en")
            if not about and len(multi_about_list) > 0:
                # Suposo que l'anglés està en primera posició
                about = multi_about_list[0]
        if not about:
            # Si no agafem la descripció llarga estàndar que hem fet servir en el metadata.txt
            about = self.get("about")

        # Canviem una cadena de caràcters per canvi de linia si així ens ho demanen
        if replace_text_with_newline:
            about = about.replace(replace_text_with_newline, "\n")

        return about

    def get_author(self):
        """ Obté el desenvolupador del plugin actual
            ---
            Get the author of the current plugin
            """
        return self.get("author")

    def get_email(self):
        """ Obté l'email de contacte del plugin actual
            ---
            Get the contact email of the current plugin
            """
        return self.get("email")

    def get_changelog(self):
        """ Obté els canvis del plugin actual
            ---
            Get changelog of the current plugin
            """
        return self.get("changelog")

    def get_info(self):
        """ Retorna informació general del plugin actual. Inclou: nom, versió, descripció curta i llarga i autor
            ---
            Returns general information about the current plugin. Includes: name, version, short and long description and author
            """
        info = "%s v%s\n%s\n\n%s\n\n%s" % (self.get_name(), self.get_version(), self.get_description(), self.get_about(), self.get_author())
        return info

    def get_repository_plugin_version(self, plugin_tag, repository_plugin_template, regex_version_template, timeout_seconds=1):
        """ Retorna la versió del plugin hostajat en el repositori de software
            ---
            Returns plugin version hosted in software repository
            """
        # Llegim la pàgina web del plugin en el repository de qgis
        if not plugin_tag:
            plugin_tag=self.get_name().replace(" ", "")
        repository_plugin_url = repository_plugin_template % plugin_tag
        try:
            hdr = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)' }
            req = urllib.request.Request(repository_plugin_url, headers=hdr)
            response = urllib.request.urlopen(req, timeout=timeout_seconds)
            html = response.read().decode('utf-8')
        except socket.timeout:
            return None
        except Exception as e:
            return None
        # Busco la última versió del plugin pujada
        regex_version = regex_version_template % plugin_tag if regex_version_template.find("%") >= 0 else regex_version_template
        found = re.search(regex_version, html)
        return found.groups()[0] if found else None

    def get_qgis_repository_plugin_version(self, plugin_tag=None, \
            repository_plugin_template="https://plugins.qgis.org/plugins/%s", \
            regex_version_template=r"\/plugins\/%s\/version\/(.+)\/download", timeout_seconds=5):
        """ Retorna la versió del plugin hostajat en el repositori de plugins QGIS
            ---
            Returns plugin version hosted in QGIS plugins repository
            """
        return self.get_repository_plugin_version(plugin_tag, repository_plugin_template, regex_version_template, timeout_seconds)

    def get_qgis_new_version_available(self, plugin_tag=None):
        """ Retorna la versió del plugin hostajat en el repositori de QGIS si és més nova que la actual
            ---
            Returns plugin version hosted in QGIS repository if it is newer than current version
            """
        def get_version_number(version_text, normalize_parts=4, parts_digits=3):
            version_text += (".0" * (normalize_parts - len(version_text.split("."))))
            version_number = sum([int(value) * ((10 ** parts_digits) ** pos) for pos, value in enumerate(version_text.split(".")[::-1])])
            return version_number
        repo_version = self.get_qgis_repository_plugin_version(plugin_tag)
        current_version = self.get_version()
        if not repo_version or not current_version:
            return None
        return repo_version if get_version_number(repo_version) > get_version_number(current_version) else None

    def get_github_repository_plugin_version(self, plugin_tag=None, \
            repository_plugin_template="https://raw.githubusercontent.com/%s/master/metadata.txt", \
            regex_version_template=r"version=(.+)\s", timeout_seconds=5):
        """ Retorna la versió del plugin hostajat en el repositori GitHub
            ---
            Returns plugin version hosted in GitHub repository
            """
        return self.get_repository_plugin_version(plugin_tag, repository_plugin_template, regex_version_template, timeout_seconds)

    def get_github_new_version_available(self, plugin_tag):
        """ Retorna la versió del plugin hostajat en el repositori GitHub si és més nova que la actual
            ---
            Returns plugin version hosted in GitHub repository if it is newer than current version
            """
        repo_version = self.get_github_repository_plugin_version(plugin_tag)
        current_version = self.get_version()
        if not repo_version or not current_version:
            return None
        return repo_version if repo_version > current_version else None

class TranslationBase(object):
    """ Classe per manegar la traducció del plugin
        ---
        Class to manage plugin translation
        """
    LANG_CA = "ca"
    LANG_ES = "es"
    LANG_EN = "en"

    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare, a l'iface i
            inicialització del diccionari de traduccions
            ---
            Initialization of member variables pointing to parent, iface and
            initialization of the dictionary of translations
            """
        self.parent = parent
        self.iface = parent.iface

        # Carreguem el fitxer de traduccío segons el locale
        self.translator = None
        self.translator_pathname = None
        self.load_translator()

    def get_default_translator_pathname(self, locale=None):
        """ Retorna el fitxer de traducció per l'idioma indicat en cas d'existir.
            Si no s'especifica idioma utilitza l'idioma de QGIS
            ---
            Returns the translation file for the specified language if it exists.
            If no locale is specified, use the QGIS language
            """
        if not locale:
            locale = self.get_qgis_language()
        pathname = os.path.join(self.parent.plugin_path, 'i18n', "%s_%s.qm" % (self.parent.plugin_id.lower(), locale.lower()))
        return pathname if os.path.exists(pathname) else None

    def load_translator(self, translator_pathname=None, locale=None):
        """ Carrega un fitxer de traducció. Si no s'especifica detecta si existeix un fitxer
            dins la carpeta i18n del plugin apropiat per l'idioma indicat o del QGIS.
            ---
            Load a translation file. If it is not specified it detects if a file exists
            within the i18n plugin folder for the indicated language or the QGIS locale.
            """
        # Detectem si existeix un fitxer de traducció per l'idioma indicat
        if not translator_pathname:
            translator_pathname = self.get_default_translator_pathname(locale)
        if not translator_pathname:
            return False
        self.translator_pathname = translator_pathname

        # Carreguem la traducció
        self.translator = QTranslator()
        self.translator.load(self.translator_pathname)
        if qVersion() > '4.3.3':
            QCoreApplication.installTranslator(self.translator)
        return True

    def get_qgis_language(self):
        """ Retorna l'idioma actiu en el QGIS. Pex: ca_ES, es
            ---
            Returns the active language in the QGIS. Pex: ca_ES, es
            """
        return self.parent.settings.value('locale/userLocale', '').split('_')[0]

class PluginBase(QObject):
    """ Classe per facilitar la creació d'un plugin de QGIS amb un conjunt d'utilitats incloses
        ---
        Class to facilitate the creation of a QGIS plugin with a set of utilities included
        """
    def __init__(self, iface, plugin_pathname):
        """ Inicialització d'informació del plugin, accés a iface i accés a classes auxiliar de gestió
            ---
            Initialization of plugin information, access to access and access to auxiliary management classes
            """
        super().__init__()

        self.plugin_pathname = os.path.abspath(plugin_pathname)
        self.plugin_path = os.path.dirname(self.plugin_pathname)
        self.plugin_id = os.path.basename(self.plugin_path)

        self.iface = iface
        self.settings = QSettings()

        self.gui = GuiBase(self)
        self.project = ProjectBase(self)
        self.layers = LayersBase(self)
        self.legend = LegendBase(self)
        self.composer = ComposerBase(self)
        self.crs = CrsToolsBase(self)
        self.debug = DebugBase(self)
        self.tools = ToolsBase(self)
        self.metadata = MetadataBase(self, plugin_pathname)
        self.translation = TranslationBase(self)
        self.log = PluginLogger(self)

        self.about_dlg = None

    def unload(self):
        """ Allibera recursos del plugin
            ---
            Free plugin resources
            """
        # Eliminem dades
        self.gui.remove()
        self.gui = None
        self.project = None
        self.layers.remove()
        self.layers = None
        self.legend = None
        self.composer = None
        self.crs = None
        self.debug = None
        self.tools.remove()
        self.tools = None
        self.metadata = None
        self.translation = None
        self.about_dlg = None
        self.log.remove()
        self.log = None

    def get_plugins_id(self):
        """ Retorna una llista amb els ids dels plugins carregats
            ---
            Returns a list with the ids of the loaded plugins
            """
        return plugins.keys()

    def get_plugin(self, plugin_name):
        """ Obté una referència a un plugin per nom
            ---
            Get a reference to a plugin by name
            """
        return plugins[plugin_name]

    def reload_plugin(self):
        """ Recarrega el plugin actual
            ---
            Reload the current plugin
            """
        self.debug.reload_plugin(self.plugin_id)

    def show_about(self, checked=None, title=None, pixmap=None): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Mostra el diàleg d'informació del plugin
            ---
            Show plugin information (about dialog)
            """
        # About dialog configuration
        if not self.about_dlg:
            if not title:
                locale = self.translation.get_qgis_language()
                if locale == self.translation.LANG_CA:
                    title = "Sobre"
                elif locale == self.translation.LANG_ES:
                    title = "Acerca de"
                else:
                    title = "About"
            self.about_dlg = AboutDialog(self.metadata.get_name(), self.metadata.get_info(), self.metadata.get_icon(),
                pixmap, title, False, parent=self.iface.mainWindow())
        # Show about
        self.about_dlg.do_modal()

    def show_changelog(self, checked=None, title=None, width=800): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Mostra el diàleg de canvis del plugin
            ---
            Show plugin changelog dialog
            """
        if not title:
            locale = self.translation.get_qgis_language()
            if locale == self.translation.LANG_CA:
                title = "Novetats"
            elif locale == self.translation.LANG_ES:
                title = "Novedades"
            else:
                title = "What's new"
        LogInfoDialog(self.metadata.get_changelog(), title, LogInfoDialog.mode_info, width=width)

    def show_help(self, checked=None, path="help", basename="index"): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Mostra l'ajuda del plugin
            ---
            Show plugin help
            """
        if not os.path.isabs(path):
            path = os.path.join(self.plugin_path, path)
        pathname = os.path.join(path, basename)
        filename, ext = os.path.splitext(basename)
        if not ext or ext == ".html":        
            showPluginHelp(filename=pathname)
        else:
            self.gui.open_file_folder(pathname)

    def show_url(self, url, parse_mode=QUrl.TolerantMode):
        """ Mostra una URL en el navegador per defecte 
            ---
            Show URL in default web navigator 
            """
        return QDesktopServices.openUrl(QUrl(url, parse_mode))

    def refresh_all(self):
        """ Refresca mapa, llegenda i taules de contingut
            ---
            Refresh map, legend, and content tables
            """
        self.layers.refresh_map()
        self.layers.refresh_attributes_tables()
        self.legend.refresh_legend()

    def set_map_point(self, x, y, epsg=None, scale=5000):
        """ Situa el mapa en les coordenades indicades a una determinada escala a partir d'un punt central.
            Reprojecta la coordenada al sistema de projecte si cal
            ---
            Locate the map in the coordinates indicated on a given scale from a central point.
            Reproject the coordinate to the project reference system if necessary
            """
        # Cal, transformem les coordenades al sistema del projecte        
        ##print("Coordinate: %s %s EPSG:%s" % (x, y, epsg))
        if epsg and epsg != int(self.project.get_epsg()):
            x, y = self.crs.transform_point(x, y, epsg)
            ##print("Coordinate: %s %s EPSG:%s" % (x, y, self.project.get_epsg()))

        ## Detectem si estem en geogràfiques o no i configurem la escala
        #if not scale:
        #    scale = 0.01 if x < 100 else 1000

        # Situem el centre del mapa i la escala
        mc = self.iface.mapCanvas()
        mc.setCenter(QgsPointXY(x, y))
        if scale:
            mc.zoomScale(scale)
        else:
            mc.refresh()

    def set_map_rectangle(self, west, north, east, south, epsg=None):
        """ Situa el mapa en les coordenades indicades pel rectangle.
            Reprojecta les coordenadas al sistema de projecte si cal
            ---
            Locate the map in the indicated coordinates by rectangle.
            Reproject the coordinates to the project reference system if necessary
            """
        # Cal, transformem les coordenades al sistema del projecte
        ##print("Rectangle: %s %s %s %s EPSG:%s" % west, north, east, south, epsg)
        if epsg and epsg != int(self.project.get_epsg()):
            west, north = self.crs.transform_point(west, north, epsg)
            east, south = self.crs.transform_point(east, south, epsg)
            ##print("Rectangle: %s %s %s %s EPSG:%s" % (west, north, east, south, self.project.get_epsg()))

        # Resituem el mapa
        rect = QgsRectangle(west, south, east, north) # minx, miny, maxx, maxy
        mc = self.iface.mapCanvas()
        mc.setExtent(rect)
        mc.refresh()

    def check_qgis_version(self, version):
        """ Verifica que la versió de QGIS sigui igual o superior a la indicada
            ---
            Checks QGIS version is greater than or equal to the one indicated (31004, 30400, 31600, ...)
            """
        return Qgis.QGIS_VERSION_INT >= version

    def get_settings(self, group_name=None):
        """ Retorna un diccionari amb les variables de configuració del plugin
            ---
            Returns plugin settings dict
            """
        self.settings.beginGroup(group_name or self.plugin_id)
        settings_dict = dict([(key, self.settings.value(key, None)) for key in self.settings.childKeys()])
        self.settings.endGroup();
        return settings_dict

    def get_setting_value(self, key, default_value=None, group_name=None):
        """ Retorna un valor de la configuració del plugin
            ---
            Returns a plugin setting value
            """
        self.settings.beginGroup(group_name or self.plugin_id)
        value = self.settings.value(key, default_value)
        # When setting file qgis.ini has values "@Invalid()" function "value" ignore default_value...
        if value is None:
            value = default_value
        self.settings.endGroup();
        return value

    def set_settings(self, settings_dict, group_name=None):
        """ Carrega un diccionari de valors de configuració del plugin
            ---
            Loads plugin settings dict
            """
        self.settings.beginGroup(group_name or self.plugin_id)
        for key, value in settings_dict.items():
            if value is None:
                self.settings.remove(key)
            else:
                self.settings.setValue(key, value)
        self.settings.endGroup();

    def set_setting_value(self, key, value, group_name=None):
        """ Carrega un valor de configuració del plugin
            ---
            Loads a setting plugin value
            """
        self.settings.beginGroup(group_name or self.plugin_id)
        if value is None:
            self.settings.remove(key)
        else:
            self.settings.setValue(key, value)
        self.settings.endGroup();

    #def get_setting_list(self, key, group_name=None):
    #    values_list = []
    #    self.settings.beginGroup(group_name or self.plugin_id)
    #    count = self.settings.beginReadArray(key)
    #    for i in range(count):
    #        self.settings.setArrayIndex(i)
    #        values_list.append(self.settings.value(key))
    #    self.settings.endArray()
    #    self.settings.endGroup();
    #    return values_list

    #def set_setting_list(self, key, values_list, group_name=None):
    #    self.settings.beginGroup(group_name or self.plugin_id)
    #    if not values_list:
    #        self.settings.remove(key)
    #    else:
    #        self.settings.beginWriteArray(key, len(values_list))
    #        for i, value in enumerate(values_list):
    #            self.settings.setArrayIndex(i)
    #            self.settings.setValue(key, value)
    #        self.settings.endArray()
    #    self.settings.endGroup();

    def get_fonts_temporal_folder(self):
        """ Retorna la carpeta temporal on copiar les fonts
            ---
            Returns temporal fonts folder where we copy fonts
            """
        tmp_path = os.path.join(tempfile.gettempdir(), "%sFonts" % self.plugin_id)
        return tmp_path

    def load_fonts(self, fonts_path=None, file_filter_list=["*.ttf", "*.otf"], copy_to_temporal_folder=True):
        """ Carrega totes les fonts trobades en una carpeta. Per defecte en <plugin_path>\fonts
            Retorna: (bool, [<font_id>,...]) True si ha anat tot bé i la llista d'ids de font
            ---
            Load all found fonts in a folder. Default <plugin_path>\fonts
            Returns: (bool, [<font_id>,...]) True if ok and a font id's list
            """
        # Si no ens passen un path, utilitzem el path per defecte: <plugin_path>\fonts
        if not fonts_path:            
            fonts_path = os.path.join(self.plugin_path, "fonts")
        if not os.path.exists(fonts_path):
            return False, []

        # Creem una carpeta carpeta temporal si cal:
        if copy_to_temporal_folder:
            tmp_path = self.get_fonts_temporal_folder()
            if not os.path.exists(tmp_path):
                os.mkdir(tmp_path)

        # Cerquem fonts dins la carpeta indicada
        status = True
        font_id_list = []
        for file_filter in file_filter_list:
            for font_pathname in glob.glob(os.path.join(fonts_path, file_filter)):
                # Copiem la font a una carpeta temporal si cal
                if copy_to_temporal_folder:
                    temporal_font_pathname = os.path.join(tmp_path, os.path.basename(font_pathname))
                    if not os.path.exists(temporal_font_pathname):
                        shutil.copyfile(font_pathname, temporal_font_pathname)
                    font_pathname = temporal_font_pathname
                # Carreguem la font
                font_id = self.load_font(font_pathname)
                font_id_list.append(font_id)
                status &= (font_id >=0)
        return status, font_id_list

    def load_font(self, font_pathname_or_filename, file_types_list=["ttf", "otf"]):
        """ Carrega un fitxer de font (si no és un path absolut utlitza <plugin_path>/fonts com a path base)
            Retorna l'identificador de font o -1 si error
            ---
            Loads a font file (if not it is a absolute path use <plugin_path>/fonts as source path)
            Returns font id or -1 if error
            """
        # Afegim el path si cal
        font_pathname = font_pathname_or_filename if os.path.isabs(font_pathname_or_filename) \
            else os.path.join(self.plugin_path, "fonts", font_pathname_or_filename)
        # Afegim la extensió si cal
        if not os.path.splitext(font_pathname_or_filename)[1]:
            for file_type in file_types_list:
                if os.path.exists(font_pathname + "." + file_type):
                    font_pathname += ("." + file_type)
                    break                        
        # Carreguem la font
        return QFontDatabase.addApplicationFont(font_pathname)

    def unload_fonts(self, font_id_list, remove_temporal_fonts_folder=False):
        """ Descarrega una llista de fonts d'aplicació
            Retona: booleà, Cert si ok si no fals
            ---
            Unload a list of application fonts
            Returns: bool, True if ok else False
            """
        # Descarrega totes les fonts
        global_status = True
        for font_id in font_id_list:
            if font_id >= 0:
                status = self.unload_font(font_id)
                global_status &= status

        # ATENCIÓ!!! ELS ARXIUS DE FONTS ES QUEDEN BLOQUEJATS I DÓNA ERROR A L'ESBORRAR-LOS
        # DE MOMENT DEIXO LA OPCIÓ DESACTIVADA PER DEFECTE
        # Esborrar la carpeta de fonts temporal si cal
        if remove_temporal_fonts_folder:
            tmp_path = self.get_fonts_temporal_folder()
            if os.path.exists(tmp_path):
                shutil.rmtree(tmp_path)
        return global_status

    def unload_font(self, font_id):
        """ Descarrega una font d'aplicació
            Retona: booleà, Cert si ok si no fals
            ---
            Unload a application font
            Returns: bool, True if ok else False
            """
        return QFontDatabase.removeApplicationFont(font_id)
