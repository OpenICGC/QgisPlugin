# -*- coding: utf-8 -*-

import os
import re
import random
import console
import datetime
import codecs
import fnmatch
import urllib.request
import socket
from importlib import reload

from PyQt5.QtCore import Qt, QSize, QTimer, QSettings
from PyQt5.QtWidgets import QApplication, QAction, QToolBar, QLabel, QMessageBox, QMenu, QToolButton
from PyQt5.QtGui import QPainter, QCursor, QIcon
from qgis.gui import QgsProjectionSelectionTreeWidget
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsWkbTypes, QgsRectangle
from qgis.utils import plugins, reloadPlugin

from . import resources_rc

import configparser

from . import progressdialog
reload(progressdialog)
from .progressdialog import ProgressDialog

from . import loginfodialog
reload(loginfodialog)
from .loginfodialog import LogInfoDialog


class GuiBase(object):
    def __init__(self, parent):
        """ Inicialització de variables membre apuntant al pare a l'iface
            Creació d'estructures per manager la GUI del plugin """
        self.parent = parent
        self.iface = parent.iface

        # Inicialitzem les llistes d'elements de la GUI que gestionem
        self.toolbars = []
        self.menus = []
        self.shortcuts = []
        self.action_plugin = None # Entrada al menú de plugins
        self.actions = [] # Parelles (menu, acció)

    def remove(self):
        """ Neteja d'estructures GUI del plugin """
        # Esborra els accions de menus i toolbars
        for control, action in self.actions:
            control.removeAction(action)
        self.actions = []
        # Esborra les entrades del plugin
        if self.action_plugin:
            self.iface.removePluginMenu(self.action_plugin.text(), self.action_plugin)
            self.iface.removeToolBarIcon(self.action_plugin)
        # Esborrem els shortcuts
        self.shortcuts = []
        # Els menús s'esborren sols quan no tenen actions
        self.menus = []
        # Esborra les toolbars
        self.toolbars = []

    ###########################################################################
    # Plugins menú
    #
    def configure_plugin(self, name, callback, icon):
        """ Crea una entrada en el menú de plugins, amb una funcionalitat i icona associada """
        self.action_plugin = QAction(icon, name, self.iface.mainWindow())
        self.action_plugin.triggered.connect(callback)
        self.iface.addToolBarIcon(self.action_plugin) # Afageix l'acció a la toolbar general de complements
        self.iface.addPluginToMenu(name, self.action_plugin) # Afageix l'acció al menú de complements

    ###########################################################################
    # Toolbars & Menús
    #
    def configure_GUI(self, title, names_callbacks, parent_menu=None, parent_menu_pos=None, menu_icon=None, toolbar_droplist_name=None, toolbar_droplist_icon=None, position=None):
        """ Crea menús i toolbars equivalents simultànicament 
            Veure funció: __parse_entry """
        # Creem el menú
        menu = self.configure_menu(title, names_callbacks, parent_menu, parent_menu_pos, menu_icon, position)
        # Creem la toolbar
        toolbar = self.configure_toolbar(title, names_callbacks, toolbar_droplist_name, toolbar_droplist_icon, position)
        return menu, toolbar

    def insert_at_GUI(self, menu_or_toolbar, position, names_callbacks):
        """ Afegeis nous items a un menu o toolbar 
            Veure funció: __parse_entry """
        # Determinem on cal insertar els items al menú
        ref_action = None
        if position != None and position < len(menu_or_toolbar.actions()):
            ref_action = menu_or_toolbar.actions()[position]

        for entry in names_callbacks:
            # Recollim les dades de usuari
            eseparator, elabel, eaction, econtrol, name, callback, icon, enabled, checkable, subentries_list = self.__parse_entry(entry)

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
                if ref_action:
                    action = menu_or_toolbar.insertWidget(ref_action, label)
                else:
                    action = menu_or_toolbar.addWidget(label)
            elif eaction != None:
                # Ens passen una acció
                if ref_action:
                    action = menu_or_toolbar.insertAction(ref_action, eaction)
                else:
                    action = menu_or_toolbar.addAction(eaction)
            elif econtrol != None:
                # És passen un control
                if ref_action:
                    action = menu_or_toolbar.insertWidget(ref_action, econtrol)
                else:
                    action = menu_or_toolbar.addWidget(econtrol)
            else:
                # Ens passen una acció "desglossada"
                if icon:
                    action = QAction(icon, name, self.iface.mainWindow())
                else:
                    action = QAction(name, self.iface.mainWindow())
                if callback:
                    action.triggered.connect(callback)
                if subentries_list == None:
                    # Menú "normal"
                    if ref_action:
                        menu_or_toolbar.insertAction(ref_action, action)
                    else:
                        menu_or_toolbar.addAction(action)
                else:
                    # Submenú
                    submenu = QMenu()
                    self.add_to_menu(submenu, subentries_list)
                    # Depenent de si tenim toolbar o menu pare, fem una cosa o un altre
                    if type(menu_or_toolbar) == QToolBar:
                        toolButton = QToolButton()
                        toolButton.setMenu(submenu)
                        toolButton.setPopupMode(QToolButton.MenuButtonPopup)
                        if checkable:
                            action.setCheckable(True)
                        toolButton.setDefaultAction(action)
                        if ref_action:
                            action = menu_or_toolbar.insertWidget(ref_action, toolButton)
                        else:
                            action = menu_or_toolbar.addWidget(toolButton)
                    # Depenent de si tenim toolbar o menu pare, fem una cosa o un altre
                    elif type(menu_or_toolbar) == QMenu:
                        submenu.setTitle(name)
                        if icon:
                            submenu.setIcon(icon)
                        if ref_action:
                            action = menu_or_toolbar.insertMenu(ref_action, submenu)
                        else:
                            action = menu_or_toolbar.addMenu(submenu)
                    # Guardem el submenu (si no, si està buit, dóna problemes afegint-lo a un menú)
                    self.menus.append(submenu)

            # Activem / desactivem, checkable o no
            if not enabled:
                action.setEnabled(False)
            if checkable:
                action.setCheckable(True)

            #Ens guardem els items de menu o toolbar, si no no apareix...
            self.actions.append((menu_or_toolbar, action))

    def __parse_entry(self, entry):
        """ Tipus de menús /toolbars acceptats, llistes de:
                None o "---" o "" --> separador
                "text" --> Label
                QAction --> Acció amb icona i funció a executar
                Altres_tipus --> Suposem que és un control (combobox, lineedit, ...)
                Tupla:
                    (Nom, [funció], [icona], [submenu_llista | enabled] [submenu_llista | checkable] [submenu_llista]

            Exemple:
                [
                    "Cercar:", # Label
                    self.combobox, # Control
                    (self.TOOLTIP_TEXT, self.run, QIcon(":/plugins/geofinder/icon.png")), # Botó amb icona
                    ("GeoFinder reload", self.reload_plugin, QIcon(":/lib/qlib3/base/python.png")), # Botó amb icona
                ]

            Exemple2:
                [

                    ("&Ortofoto color", 
                        lambda:self.parent.layers.add_wms_layer("WMS Ortofoto color", "http://mapcache.icc.cat/map/bases/service", ["orto"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map), 
                        QIcon(":/lib/qlib3/base/cat_ortho5k.png")),
                    ("Ortofoto &infraroja", 
                        lambda:self.parent.layers.add_wms_layer("WMS Ortofoto infraroja", "http://shagrat.icc.cat/lizardtech/iserv/ows", ["ortoi5m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map), 
                        QIcon(":/lib/qlib3/base/cat_ortho5ki.png")),
                    ("Ortofoto &històrica", None, QIcon(":/lib/qlib3/base/cat_ortho5kbw.png"), [ # Subnivell
                        ("&Ortofoto 1:5.000 vol americà sèrie B blanc i negre",
                            lambda:self.parent.layers.add_wms_layer("WMS Ortofoto vol americà sèrie B 1:5.000 BN", "http://historics.icc.cat/lizardtech/iserv/ows",  ["ovab5m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
                            QIcon(":/lib/qlib3/base/cat_ortho5kbw.png")),
                        ("&Ortofoto 1:10.000 vol americà sèrie A blanc i negre (1945-1946)",
                            lambda:self.parent.layers.add_wms_layer("WMS Ortofoto vol americà sèrie A 1:10.000 BN", "http://historics.icc.cat/lizardtech/iserv/ows", ["ovaa10m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
                            QIcon(":/lib/qlib3/base/cat_ortho5kbw.png")),
                        ]), # Fi de subnivell
                    "---", # Separador
                    ("blablabla", ...) """
        
        ##self.iniConsole()
        separator = None
        label = None
        action = None
        control = None
        name = None
        callback = None
        icon = None
        enabled = True
        checkable = False
        subentries_list = None

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
                callback = entry[1]
                if len(entry) > 2:
                    icon = entry[2]
                if len(entry) > 3:
                    if type(entry[3]) == list:
                        subentries_list = entry[3]
                    else:
                        enabled = entry[3]
                        if len(entry) > 4:
                            if type(entry[4]) == list:
                                subentries_list = entry[4]
                            else:
                                checkable = entry[4]
                                if len(entry) > 5:
                                    if type(entry[5]) == list:
                                        subentries_list = entry[5]

        return separator, label, action, control, name, callback, icon, enabled, checkable, subentries_list

    ###########################################################################
    # Menus
    #
    def configure_menu(self, title, names_callbacks, parent_menu=None, parent_menu_pos=None, menu_icon=None, position=None):
        """ Crea o amplia un menús segons la llista de <callbacks>
            Veure funció: __parse_entry """

        menu = self.get_menu_by_name(title)

        # Si no tenim menú creem un menu nou
        if not menu:
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
                self.insert_at_menu(menu, position, names_callbacks if is_separator else names_callbacks + ["---"])
            else:
                is_separator = len(menu.actions()) == 0 or menu.actions()[-1].isSeparator()
                self.add_to_menu(menu, names_callbacks if is_separator else ["---"] + names_callbacks)

        return menu

    def add_to_menu(self, menu, names_callbacks):
        """ Amplia un menús pel final segons la llista de <callbacks>
            Veure funció: __parse_entry """
        self.insert_at_menu(menu, None, names_callbacks)

    def insert_at_menu(self, menu, position, names_callbacks):
        """ Amplia un menús en la posició indicada segons la llista de <callbacks>
            Veure funció: __parse_entry """
        self.insert_at_GUI(menu, position, names_callbacks)

    def get_menus(self):
        """ Retorna la llista del menus visibles a la GUI """
        return [action.menu() for action in self.iface.mainWindow().menuBar().actions()]

    def get_menu_by_name(self, name):
        """ Retorna un objecte menú a partir del seu nom """
        menus = self.get_menus()
        menus_names = [unicode(m.title()) for m in menus]
        if name in menus_names:
            pos = menus_names.index(name)
            return menus[pos]
        else:
            return None

    ###########################################################################
    # Toolbars
    #
    def configure_toolbar(self, title, names_callbacks, toolbar_droplist_name=None, toolbar_droplist_icon=None, position=None):
        """ Crea o amplia una toolbar segons la llista de <callbacks>
            Veure funció: __parse_entry """
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
                self.insert_at_toolbar(toolbar, position, names_callbacks if is_separator else names_callbacks + ["---"])
            else:
                is_separator = len(toolbar.actions()) == 0 or toolbar.actions()[-1].isSeparator()
                self.add_to_toolbar(toolbar, names_callbacks if is_separator else ["---"] + names_callbacks)
        self.toolbars.append(toolbar)
        return toolbar

    def add_to_toolbar(self, toolbar, names_callbacks):
        """ Amplia una toolbar pel final segons la llista de <callbacks>
            Veure funció: __parse_entry """
        self.insert_at_toolbar(toolbar, None, names_callbacks)

    def insert_at_toolbar(self, toolbar, position, names_callbacks):
        """ Amplia una toolbar en una posició indicada segons la llista de <callbacks>
            Veure funció: __parse_entry """
        self.insert_at_GUI(toolbar, position, names_callbacks)

    def get_toolbars(self):
        """ Retorna la llista de toolbars de QGIS """
        return [t for t in self.iface.mainWindow().children() if type(t) == QToolBar]

    def get_toolbar_by_name(self, name):
        """ Retorna un objecte toolbar a partir del seu nom """
        toolbars_list = self.get_toolbars()
        toolbars_names = [unicode(t.windowTitle()) for t in toolbars_list]
        if name in toolbars_names:
            pos = toolbars_names.index(name)
            return toolbars_list[pos]
        else:
            return None

    def get_toolbar_action_by_names(self, toolbar_name, item_name, item_pos=0):
        """ Retorna una acció d'una toolbar a partir dels seus noms """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return None
        return self.get_toolbar_action_by_action_name(toolbar, item_name, item_pos)

    def get_toolbar_actions(self, toolbar):
        """ Retorna la llista d'accions d'una toolbar """
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
                    actions.append(action) # Separador                
        return actions_list

    def get_toolbar_action_by_item_name(self, toolbar, item_name, item_pos=0):
        """ Retorna una acció d'una toolbar a partir del seu nom """
        actions_list = self.get_toolbar_actions(toolbar)
        item_actions = [action for action in actions_list if action.text() == item_name]
        if not item_actions:
            return None
        return item_actions[item_pos]

    def get_toolbar_action(self, toolbar, item_pos):
        """ Retorna una acció d'una toolbar a partir de la seva posició """
        actions_list = self.get_toolbar_actions(toolbar)
        return actions_list[item_pos]

    def set_check_toolbar_item_by_item_name(self, toolbar, item_name, check=True, item_pos=0):
        """ Xequeja una acció d'una toolbar a partir del seu nom """
        action = self.get_toolbar_action(toolbar, item_name, item_pos)
        if not action:
            return False
        action.setCheckable(True)
        action.setChecked(check)
        return True

    def set_check_toolbar_item_by_names(self, toolbar_name, item_name, check=True, item_pos=0):
        """ Xequeja una acció d'una toolbar a partir dels seus noms """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return False
        return self.set_check_toolbar_item_by_item_name(toolbar, item_name, check, item_pos)

    def enable_toolbar_item_by_item_name(self, toolbar, item_name, enable=True, item_pos=0):
        """ Activa una acció d'una toolbar a partir del seu nom """
        action = self.get_toolbar_action_by_item_name(toolbar, item_name, item_pos)
        if not action:
            return False
        action.setEnabled(enable)
        return True

    def enable_toolbar_item_by_names(self, toolbar_name, item_name, enable=True, item_pos=0):
        """ Activa una acció d'una toolbar a partir dels seus noms """
        toolbar = self.get_toolbar_by_name(toolbar_name)
        if not toolbar:
            return False
        return self.enable_toolbar_item_by_item_name(toolbar, item_name, enable, item_pos)

    def organize_toolbars(self):
        """ Organitza les toolbars dins l'espai disponible """
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

    ###########################################################################
    # Shortcuts
    #
    def configure_shortcuts(self, shortcuts_callbacks_list):
        for shortcut_info in shortcuts_callbacks_list:
            ##print(shortcut_info)
            if type(shortcut_info) is tuple:
                description, keyseq, callback = shortcut_info
            else:
                description = None
                keyseq = None
                callback = None
            ##print(description, keyseq, callback)
            self.add_shortcut(description, keyseq, callback)

    def add_shortcut(self, description, keyseq, callback):
        ##print(description, keyseq, callback)
        if description is None or keyseq is None or callback is None:
            shortcut = None
        else:
            shortcut = QShortcut(QKeySequence(keyseq), self.iface.mainWindow())
            shortcut.activated.connect(callback)
        self.shortcuts.append((description, keyseq, shortcut))

    def get_all_shortcuts_description(self, this_plugin_not_all_plugins = False, show_plugin_name = False, show_plugin_newline = True):
        if this_plugin_not_all_plugins:
            plugin_info_list = [u'Self', self]
        else:
            plugin_info_list = plugins.items()

        shortcut_description = ""
        prefix = "   " if show_plugin_name else ""
        for plugin_name, plugin in plugin_info_list:
            # Excloem els shotcuts sense descripció, Incloem els "espais": shortcut a None
            shortcut_info_list = [(description, keyseq, shortcut) for (description, keyseq, shortcut) in plugin.__dict__.get('shortcuts', []) if description or not shortcut]
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

    ###########################################################################
    # Tools
    #
    def enable_tool(self, map_tool):
        # No sé perquè el setMapTool no desactiva les eines de zoom, les altres sí
        # en canvi la eina de selecció sí que les desactiva... solució kutre:
        # activo la eina de selecció i després la que toca
        self.iface.actionSelectRectangle().trigger()
        self.iface.mapCanvas().setMapTool(map_tool)

    ###########################################################################
    # DockWidgets
    #
    def get_dock_widgets(self):
        return [w for w in self.iface.mainWindow().children() if type(w) == QDockWidget]

    ###########################################################################
    # Altres
    #
    def get_language(self):
        """ Obté l'idioma del QGIS """
        if not self.language:
            title = self.iface.projectMenu().title()
            lang_dict = {"P&royecto": "esp", "P&rojecte": "cat", "P&roject": "eng"}
            self.language = lang_dict.get(title, "eng")
        return self.language

        
class ProjectBase(object):
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

    def get_epsg(self, asPrefixedText=False):
        text = self.iface.mapCanvas().mapSettings().destinationCrs().authid()
        return self.parent.crs.format_epsg(text, asPrefixedText)

    def set_epsg(self, epsg):
        crs = QgsCoordinateReferenceSystem(epsg, QgsCoordinateReferenceSystem.EpsgCrsId)
        self.iface.mapCanvas().mapSettings().setDestinationCrs(crs)

    def create_qgis_project_file(self, project_file, template_file, host, dbname, dbusername, excluded_users_list = [], excluded_db_list = []):
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
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

        # Configurem l'event de refresc de mapa perquè ens avisi
        self.map_refreshed = True
        self.iface.mapCanvas().mapCanvasRefreshed.connect(self.on_map_refreshed)

    def on_map_refreshed(self):
        """ Funció auxiliar per detectar quan s'ha acabat de refrescar el mapa """
        self.map_refreshed = True

    def refresh_map(self, wait_refreshed=False):
        """ Refresca el contingut del mapa, si s'especifica que esperi, la funció no retorna fins que es rep l'event de final de refresc """            
        self.iface.mapCanvas().refresh()
        if wait_refreshed:
            # Espera a que es refresqui el mapa
            self.map_refreshed = False
            while not self.map_refreshed:
                QApplication.instance().processEvents()

    def get_by_id(self, idprefix, pos=0):
        """ Retorna una capa segons un prefix d'identificador i la repetició del prefix """
        layers_list = [layer for id, layer in QgsMapLayerRegistry.instance().mapLayers().items() if id.startswith(idprefix)]
        if not layers_list or pos < 0 or pos >= len(layers_list):
            return None
        return layers_list[pos]

    def get_by_pos(self, pos):
        """ Retorna una capa segons la seva posició """
        layers_list = QgsMapLayerRegistry.instance().mapLayers().values()
        if not layers_list or pos < 0 or pos >= len(layers_list):
            return None
        return layers_list[pos]

    def get_connection_string_dict_by_id(self, idprefix, pos=0):
        """ Retorna un diccionari amb el string de conexió de la capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return {}
        return self.get_connection_string_dict(layer)

    def get_connection_string_dict(self, layer):
        """ Retorna un diccionari amb el string de conexió de la capa """
        connection_string = layer.dataProvider().dataSourceUri()
        return dict([pair.split('=') for pair in connection_string.split() if len(pair.split('=')) == 2])

    def get_feature_attribute_by_id(self, idprefix, entity, field_name, pos=0):
        """ Retorna el valor d'un camp d'una entitat (fila) d'una capa """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.get_feature_attribute(layer, entity, field_name)

    def get_feature_attribute(self, layer, entity, field_name):
        """ Retorna el valor d'un camp d'una entitat (fila) d'una capa a partir del seu id (se li passa prefix d'id) """
        index = layer.fieldNameIndex(field_name)
        if index < 0:
            return None
        value = entity[index]
        return value
    
    def get_attributes_by_id(self, layer_idprefix, fields_name_list, max_items=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return []
        return self.get_attributes(layer, fields_name_list, max_items)

    def get_attributes(self, layer, fields_name_list, max_items = None):
        return self.__get_attributes([layer], fields_name_list, False, None, None, max_items)

    def get_attribute_selection_by_id(self, layer_idprefix, field_name, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection_by_id(layer_idprefix, field_name, error_function, error_message, max_items)

    def get_attribute_selection(self, layer, field_name, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection(layer, field_name, error_function, error_message, max_items)

    def get_attributes_selection_by_id(self, layer_idprefix, fields_name_list, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection_by_id(layer_idprefix, fields_name_list, error_function, error_message, max_items)

    def get_attributes_selection(self, layer, fields_name_list, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection(layer, fields_name_list, error_function, error_message, max_items)

    def get_attribute_selection_by_id_list(self, layer_idprefix_list, field_name, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection_by_id(layer_idprefix_list, field_name, error_function, error_message, max_items)

    def get_attribute_selection_by_list(self, layers_list, field_name, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection(layers_list, field_name, error_function, error_message, max_items)

    def get_attributes_selection_by_id_list(self, layer_idprefix_list, fields_name_list, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection_by_id(layer_idprefix_list, fields_name_list, error_function, error_message, max_items)

    def get_attributes_selection_by_list(self, layers_list, fields_name_list, error_function = None, error_message = None, max_items = None):
        return self.__get_attributes_selection(layers_list, fields_name_list, error_function, error_message, max_items)

    def __get_attributes_selection_by_id(self, layer_idprefix_or_list, field_name_or_list, error_function = None, error_message = None, max_items = None):
        # Validem el tipus de dades del idprefix (acceptem llista o valor)
        if type(layer_idprefix_or_list) != list:
            layer_idprefix_or_list = [layer_idprefix_or_list]
        selected_layers = [self.get_by_id(layer_idprefix) for layer_idprefix in layer_idprefix_or_list]
        return self.__get_attributes_selection(selected_layers, field_name_or_list, error_function, error_message, max_items)

    def __get_attributes_selection(self, layer_or_list_or_none, field_name_or_list, error_function = None, error_message = None, max_items = None):
        return self.__layersAttributes(layer_or_list_or_none, field_name_or_list, True, error_function, error_message, max_items)
         
    def __get_attributes(self, layer_or_list_or_none, field_name_or_list, only_selection, error_function = None, error_message = None, max_items = None):
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
                    selected_features = layer.selectedFeatures()[:max_items]
                else:
                    layer.selectAll()
                    selected_features = layer.selectedFeatures()[:max_items]
                    layer.setSelectedFeatures([])
                ##print(layer_idprefix, layer, layer.name(), layer.selectedFeatures())
                # Obtenim la selecció de la capa fields_name_or_list (acceptem llista o valor)
                # Validem el tipus de dades de
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
        layer = self.get_by_id(layer_idprefix, pos)
        return self.get_attributes_by_area(layer, [field_name], area, area_epsg)

    def get_attribute_by_area(self, layer, field_name, area, area_epsg=None):
        return self.get_attributes_by_area(layer, [field_name], area, area_epsg)

    def get_attributes_by_area_by_id(self, layer_idprefix, fields_name_list, area, area_epsg=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        return self.get_attributes_by_area(layer, fields_name_list, area, area_epsg)

    def get_attributes_by_area(self, layer, fields_name_list, area, area_epsg=None):
        # Obtenim l'area a buscar, i la reprojectem si cal a coordenades de la serie50k        
        if area_epsg and self.layerEPSG2(layer) != area_epsg:
            area = self.parent.crs.transform_bounding_box(area, area_epsg, self.parent.layers.get_epsg(layer))

        # Cerquem elements que intersequin amb l'àrea
        index = QgsSpatialIndex(layer.getFeatures())
        intersect_id_list = index.intersects(area)

        # Recuperem la informació dels elements trobats
        request = QgsFeatureRequest()
        request.setFilterFids(intersect_id_list)
        features_list = layer.getFeatures(request)
        
        # Recuperem els camps demanats
        if len(fields_name_list) == 1:
            layer_selection = [self.get_feature_attribute(layer, feature, fields_name_list[0]) for feature in features_list]
        else:
            layer_selection = [tuple([self.get_feature_attribute(layer, feature, field_name) for field_name in fields_name_list]) for feature in features_list]
        return layer_selection

    def refresh_by_id(self, layer_idprefix, unselect=False, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.refresh(layer, unselect)
        return True

    def refresh(self, layer, unselect=False):
        if unselect:
            self.set_selection(layer, [])
        self.refresh_legend(layer);
        self.refresh_map()

    def set_selection_by_id(self, layer_idprefix, values_list, field_name=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.set_selection(layer, values_list, field_name)

    def set_selection(self, layer, values_list, field_name=None):
        # Si la capa no és vectorial no va la selecció...
        if type(layer) != QgsVectorLayer:
            return False

        # Si ens passem camps buits, deseleccionem tot
        if not values_list or len(values_list) == 0:
            layer.setSelectedFeatures([])
            return True

        # Si no tenim camp indicat, suposem que la llista és de ids i fem la crida "normal"
        if not field_name:
            layer.setSelectedFeatures(values_list)
            return True

        # Obtenim els camps de la capa
        dp = layer.dataProvider()
        # CANVIS QGIS2
        ##fields_names = [f.name() for f in dp.fields().values()]
        fields_names = [f.name() for f in dp.fields().toList()]
        if field_name not in fields_names:
            return False
        field_index = fields_names.index(field_name)
        fields_ids = list(dp.fields())
        field_id = fields_ids[field_index]

        # Obtenim la llista d'elements seleccionats
        selected_features = []
        for feature in layer.getFeatures():
            field_value = feature[field_index]
            if field_value in values_list:
                selected_features.append(feature.id())

        # Seleccionem els elements filtrats
        layer.setSelectedFeatures(selected_features)
        return True

    def zoom_to_selection_by_id(self, layer_idprefix, scale=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.zoom_to_selection(layer, scale)
        return True

    def zoom_to_selection(self, layer, scale=None):
        self.iface.mapCanvas().zoomToSelected(layer)
        if scale:
            self.iface.mapCanvas().zoomScale(scale)

    def zoom_to_by_id(self, layer_idprefix, items_list, field_name=None, set_selection=True, scale=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not scale:
            return False
        self.layerZoomTo2(layer, items_list, field_name, set_selection, scale)
        return True

    def zoom_to(self, layer, items_list, field_name=None, set_selection=True, scale=None):
        self.set_selection(layer, items_list, field_name)
        self.zoom_to_selection(layer, scale)
        if not set_selection:
            self.set_selection(layer, [])

    def get_epsg_by_id(self, layer_idprefix, asPrefixedText=False, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return None
        return self.get_epsg(layer, asPrefixedText)

    def get_epsg(self, layer, asPrefixedText=False):
        text = layer.crs().authid()
        return self.parent.crs.format_epsg(text, asPrefixedText)

    def load_style_by_id(self, layer_baseid, style_file, replace_dict=None, exclude_rules_labels_list=None, exclude_rules_filter_list=None, pos=0, refresh=True):
        layer = self.get_by_id(layer_baseid, pos)
        if not layer:
            return None
        return self.load_style(layer, style_file, replace_dict, exclude_rules_labels_list, exclude_rules_filter_list, refresh)

    def load_style(self, layer, style_file, replace_dict=None, exclude_rules_labels_list=None, exclude_rules_filter_list=None, refresh=True):
        # Obtenim el path de l'arxiu
        if not os.path.splitext(style_file)[1]:
            style_file += '.qml'
        if os.path.dirname(style_file):
            style_pathname = style_file
        elif self.plugin_path and os.path.exists(os.path.join(self.plugin_path, style_file)):
            style_pathname = os.path.join(self.plugin_path, style_file)
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
        print("Style status: %s %s %s" % (unicode(layer.name()), style_pathname, text))

        # Esborrem arxius temporals si cal
        if tmp_style_pathname and os.path.exists(tmp_style_pathname):
            os.remove(tmp_style_pathname)
        
        # Esborrem les regles de la llista
        if exclude_rules_labels_list or exclude_rules_filter_list:
            renderer = layer.rendererV2()
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
            self.refresh_legend(layer, True, True)
        
        return text

    def set_visible_by_id(self, layer_basename, enable=True, pos=0):
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.set_visible(layer, enable)
        return True

    def set_visible(self, layer, enable=True):
        QgsProject.instance().layerTreeRoot().findLayer(layer.id()).setItemVisibilityChecked(enable)
      
    def is_visible_by_id(self, layer_basename, pos=0):
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return None
        return self.is_visible(layer)

    def is_visible(self, layer):
        legend = self.iface.legendInterface()
        return legend.isLayerVisible(layer)

    def set_scale_based_visibility_by_id(self, layer_basename, minimum_scale=None, maximum_scale=None, pos=0):
        # Ens guardem la capa activa
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.layerScaleBasedVisibility2(layer, minimum_scale, maximum_scale)
        return True

    def set_scale_based_visibility(self, layer, minimum_scale=None, maximum_scale=None):
        if minimum_scale is None or maximum_scale is None:
            layer.setScaleBasedVisibility(False)
        else:
            layer.setScaleBasedVisibility(True)
            layer.setMinimumScale(minimum_scale)   
            layer.setMaximumScale(maximum_scale)     

    def is_scale_based_visibility_by_id(self, layer_basename, pos=0):
        # Ens guardem la capa activa
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        return self.is_scale_based_bisibility(layer)
        
    def is_scale_based_visibility(self, layer):
        return layer.hasScaleBasedVisibility()

    def collapse_by_id(self, layer_basename, collapse=True, pos=0):
        return self.expand_by_id(layer_base, not collapse, pos)

    def collapse(self, layer, collapse=True):
        return self.expand(layer, not collapse)

    def expand_by_id(self, layer_basename, expand=True, pos=0):
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.expand(layer, expand)
        return True

    def expand(self, layer, expand=True):
        QgsProject.instance().layerTreeRoot().findLayer(layer.id()).setExpanded(expand)

    def is_expanded_by_id(self, layer_basename, pos=0):
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return None
        return self.is_expanded(layer)

    def is_expanded(self, layer):
        legend = self.iface.legendInterface()
        return legend.isLayerExpanded(layer)

    def classification_by_id(self, layer_basename, values_list, color_list, transparency_list=None, width_list=None, pos=0):
        # Ens guardem la capa activa
        layer = self.get_by_id(layer_basename, pos)
        if not layer:
            return False
        self.classification(layer, values_list, color_list, transparency_list, width_list)
        return True

    def classification(self, layer, values_list, color_list, transparency_list = None, width_list = None):
        # Esborrem la classificació per categories prèvia
        renderer = layer.rendererV2()
        renderer.deleteAllCategories()
        # Afegim un categoria per cada data
        for i, value in enumerate(values_list):
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            if color_list:
                color = color_list[i % len(color_list)]
                symbol.setColor(color)
            if transparency_list:
                transparency = transparency_list[i % len(transparency_list)]
                symbol.setAlpha(transparency)
            if width_list:
                width = width_list[i % len(width_list)]
                symbol.setWidth(width)

            cat = QgsRendererCategoryV2(value, symbol, value)
            renderer.addCategory(cat)

        # Activem la capa de canvis de protocostures i refresquem la seva llegenda
        show = self.is_visible(layer)
        if not show:
            self.set_visible(layer, True) 
        self.refresh_legend(layer)
        if not show:
            self.set_visible(layer, False)

    def classify_by_id(self, layer_idprefix, class_attribute, values_list=None, color_list=None, expand=None, width=None, alpha=None, use_current_symbol=False, base_symbol=None, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.classify(layer, class_attribute, values_list, color_list, expand, width, alpha, use_current_symbol, base_symbol)
        return True

    def classify(self, layer, class_attribute, values_list=None, color_list=None, expand=None, width=None, alpha=None, use_current_symbol=False, base_symbol=None):
        # Esborrem la classificació per categories prèvia
        renderer = QgsCategorizedSymbolRendererV2(class_attribute, [])

        # Si hem d'aprofitar simbols, en guardem un base_symbol
        if use_current_symbol:
            base_symbol = layer.rendererV2().symbols()[0]

        # Si no tenim dades, ja hem acabat
        if not values_list:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            field_pos = layer.fieldNameIndex(class_attribute)
            values_list = sorted(list(set([f.attributes()[field_pos] for f in layer.getFeatures() if f.attributes()[field_pos]])))
            QApplication.restoreOverrideCursor()

        # Si no tenim llista de colors, generarem una llista aleatoria de colors
        if not color_list:
            colors = set([])
            color = None

        # Afegim un categoria per cada data
        for i, value in enumerate(values_list):
            # Obtenim el color a aplicar
            if color_list:
                # Obtenim un color de la llista
                color = color_list[i % len(color_list)]
            else:            
                # Calculem un color random no repetit
                while color in colors or not color:
                    color = QColor(random.randint(0,255), random.randint(0,255), random.randint(0,255)) # Color aleatori
                colors.add(color)
            # Generem el símbol            
            if base_symbol:
                symbol = base_symbol.clone()
            else:
                symbol = QgsLineSymbolV2.defaultSymbol(layer.geometryType())
            symbol.setColor(color)
            symbol.symbolLayer(0).setOutlineColor(color)
            if alpha:
                symbol.setAlpha(alpha)
            if width:
                symbol.setWidth(width)
            # Creem la categoria
            cat = QgsRendererCategoryV2(value, symbol, unicode(value))
            renderer.addCategory(cat)

        # Refresquem la capa
        layer.setRendererV2(renderer)
        # Refresquem la llegenda
        self.refresh_legend(layer, expanded = expand if expand else self.isLayerExpanded2(layer))

    def zoom_to_full_extent_by_id(self, layer_idprefix, buffer=0, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.zoom_to_full_extent(layer, buffer)
    
    def zoom_to_full_extent(self, layer, buffer=0):
        # Obtenim l'area de la capa
        if layer.featureCount() < 1:
            return False
        area = layer.extent()        
        # Reprojectem les coordenades si cal        
        if self.get_epsg(layer) != self.parent.project.get_epsg():
            area = self.parent.crs.transform_bounding_box(area, self.get_epsg(layer))
        # Ampliem el rectangle si cal
        if buffer:
            area = area.buffer(buffer)
        # Fem zoom a l'area
        self.iface.mapCanvas().setExtent(area)      
        return True

    def ensure_visible_by_id(self, layer_idprefix, pos=0):
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        return self.ensure_visible(layer)

    def ensure_visible(self, layer):
        if layer.featureCount() < 1:
            return False
        if self.iface.mapCanvas().extent().contains(layer.extent()):
            return True
        return self.zoom_to_full_extent(layer)

    def get_current_layer(self):
        return self.iface.activeLayer()

    def set_current_layer_by_id(self, idprefix, pos=0):
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        self.set_current_layer(layer)
        return True

    def set_current_layer(self, layer):
        self.iface.setActiveLayer(layer)
        self.iface.mapCanvas().setCurrentLayer(layer)

    def get_filter_by_id(self, layer_prefix, pos=0):
        layer = self.get_by_id(layer_prefix, pos)
        if not layer:
            return None
        return self.get_filter(layer)

    def get_filter(self, layer):
        return layer.subsetString()

    def set_filter_by_id(self, layer_prefix, sql_filter, pos = 0):
        return self.set_subset_string_by_id(layer_prefix, sql_filter, pos)

    def set_filter(self, layer, sql_filter):
        return self.set_subset_string(layer, sql_filter)
    
    def set_subset_string_by_id(self, layer_prefix, sql_filter, pos=0):
        layer = self.get_by_id(layer_prefix, pos)
        if not layer:
            return False
        return self.set_subset_string(layer, sql_filter)

    def set_subset_string(self, layer, sql_filter):
        return layer.setSubsetString(sql_filter)

    def remove_layer_by_id(self, layer_idprefix, pos=0):
        """ Esborra una capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(layer_idprefix, pos)
        if not layer:
            return False
        self.remove_layer(layer)
        return True

    def remove_layer(self, layer):
        """ Esborra una capa """
        QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

    def save_shapefile_by_id(self, idprefix, pathname, encoding="utf-8", pos=0):
        """ Guarda el contingut d'una capa vectorial com un shape a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.layerSaveShapeFile2(layer, pathname, encoding)

    def save_shapefile(self, layer, pathname, encoding="utf-8"):
        """ Guarda el contingut d'una capa vectorial com un shape """
        return QgsVectorFileWriter.writeAsVectorFormat(layer, pathname, encoding, None, "ESRI Shapefile") == QgsVectorFileWriter.NoError    
        
    def rename_fields_by_id(self, idprefix, rename_dict, pos=0):
        """ Reanomena camps d'una capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.rename_fields(layer, rename_dict)
        
    def rename_fields(self, layer, rename_dict):
        """ Reanomena camps d'una capa """
        new_names_dict = dict([(layer.fieldNameIndex(field.name()), rename_dict[field.name()]) for field in layer.fields() if field.name() in rename_dict]) if layer else {}
        if not new_names_dict:
            return False
        layer.dataProvider().renameAttributes(new_names_dict)
        layer.updateFields()
        return True

    def delete_fields_by_id(self, idprefix, names_list, pos=0):
        """ Esborra camps d'una capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.delete_fields(layer, names_list)

    def delete_fields(self, layer, names_list):
        """ Esborra camps d'una capa """
        layer.dataProvider().deleteAttributes([layer.fieldNameIndex(field_name) for field_name in names_list])
        layer.updateFields()
        return True

    def add_raster_files(self, files_list, group_name=None, ref_layer=None, min_scale=None, max_scale=None, transparency=None, no_data=None, layer_name=None, color_default_expansion=False, ICGC_custom_ED50=False, visible=True, expanded=False, style_file=None, properties_dict_list=[], only_one_map_on_group=False):
        """ Afegeix una capa raster a partir d'un fitxer """
        # Ens guardem la capa activa
        active_layer = self.iface.activeLayer()

        # Recuperem les capes que hi ha dins el grup (si ens el passen)
        layers_list = self.get_group_layers_id(group_name) if group_name else []

        # Obtenim el min i max escala de visualitzacio
        if not min_scale or not max_scale:
            if ref_layer:
                if not min_scale:
                    min_scale = ref_layer.minimumScale()
                if not max_scale:
                    max_scale = ref_layer.maximumScale()

        # Afegim totes les ortos que ens passen
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        last_layer = None
        error_files = []
        for i, filename in enumerate(files_list):
            # Determinem el nom de la capa
            if not layer_name:
                name = os.path.splitext(os.path.basename(filename))[0]
            elif layer_name.find('%s') >= 0:
                name = (layer_name % os.path.splitext(os.path.basename(filename))[0])
            else:
                name = layer_name
            # Si existeix la capa no cal afegir-la
            if any([str(layer).startswith(name) for layer in layers_list]):
                continue

            # Detectem si existeix el fitxer
            if not os.path.exists(filename):
                error_files.append(filename)
                continue
            # Si no existeix la capa l'afegim
            last_layer = self.iface.addRasterLayer(filename, name)
            if not last_layer:
                error_files.append(filename)
                continue

            # Canviem l'estil de la capa si cal
            if style_file:
                self.load_layer_style2(last_layer, style_file, refresh=True)
            # Assigne el valor no data si cal
            if no_data is not None:
                self.set_nodata(last_layer, no_data)
            # Desactivem la expansió de colors si cal
            if not color_default_expansion:
                self.disable_color_expansion(last_layer)
            # Canviem les propiedats de la capa
            self.set_properties(last_layer, visible, not expanded, group_name, only_one_map_on_group, min_scale, max_scale, transparency, properties_dict_list[i] if properties_dict_list else None)

            #if ICGC_custom_ED50:
            #    # Si tenim una capa ED50 i el projecte no és ED50, posem ED50 ICC a la capa
            #    if str(self.layerEPSG2(rl)) == "23031" and self.parent.project.get_epsg() != "23031":
            #        custom_epsg = self.productICCED50EPSG()
            #        rl.setCrs(QgsCoordinateReferenceSystem(int(custom_epsg), QgsCoordinateReferenceSystem.InternalCrsId))
        QApplication.restoreOverrideCursor()

        # Mostrem errors
        if len(error_files) > 0:
            LogInfoDialog(
                "Error files not found: %d:\n   %s" % (len(error_files), "\n   ".join(error_files)),
                "Error raster files",
                LogInfoDialog.mode_error)

        # Restaurem la capa activa
        self.iface.setActiveLayer(active_layer)

        # Retornem la última imatge processada
        return last_layer

    def disable_color_expansion(self, layer):
        """ Desactiva la expansió de colors un una capa raster """
        layer.setContrastEnhancement(QgsContrastEnhancement.NoEnhancement)

    def set_nodata(self, layer, nodata):
        """ Assigna un valor no data a una capa raster """
        if layer.bandCount() > 1:
            layer.renderer().rasterTransparency().initializeTransparentPixelList(no_data, no_data, no_data) # Per imatges color
        else:
            layer.renderer().rasterTransparency().initializeTransparentPixelList(no_data) # Per imatges BW

    def add_vector_files(self, files_list, group_name=None, min_scale=None, max_scale=None, layer_name=None, visible=True, expanded=False, transparency=None, style_file=None, properties_dict_list=[], only_one_map_on_group=False):
        """ Afegeix una capa vectorial a partir d'un fitxer """
        # Ens guardem la capa activa
        active_layer = self.iface.activeLayer()

        # Recuperem les capes que hi ha dins el grup (si ens el passen)
        layers_list = self.get_group_layers_id(group_name) if group_name else []

        # Afegim totes les imatges que ens passin
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
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
            # Si existeix la capa, ens la saltem
            if any([str(layer).startswith(name) for layer in layers_list]):
                continue

            # Detectem si existeix el fitxer
            if not os.path.exists(filename):
                error_files.append(filename)
                continue
            # Creem la capa
            last_layer = self.iface.addVectorLayer(filename, name, "ogr")
            if not last_layer:
                error_files.append(filename)
                continue

            # Canviem l'estil de la capa si cal
            if style_file:
                self.load_layer_style2(last_layer, style_file, refresh=True)
            # Canviem les propiedats de la capa
            self.set_properties(last_layer, visible, not expanded, group_name, only_one_map_on_group, min_scale, max_scale, transparency, properties_dict_list[i] if properties_dict_list else None)
        QApplication.restoreOverrideCursor()

        # Mostrem errors
        if len(error_files) > 0:
            LogInfoDialog(
                "Error files not found: %d:\n   %s" % (len(error_files), "\n   ".join(error_files)),
                "Error vector files",
                LogInfoDialog.mode_error)

        # Restaurem la capa activa
        self.iface.setActiveLayer(active_layer)
        
        # Retornem la última capa inserida
        return last_layer
    
    def add_wms_layer(self, layer_name, url, layers_list, styles_list, image_format, epsg=None, extra_tags="", group_name="", only_one_map_on_group=False, collapsed=True, visible=True):
        """ Afegeix una capa WMS a partir de la URL base i la llista de capes """
        if not epsg:
            epsg = self.parent.project.get_epsg()
        uri = "url=%s&crs=epsg:%s&format=%s&%s&%s" % (url, epsg, image_format, "&".join(["layers=%s" % layer for layer in layers_list]), "&".join(["styles=%s" % style for style in styles_list]))
        if extra_tags:
            uri += "&%s" % extra_tags
        return self.add_raster_uri_layer(layer_name, uri, "wms", group_name, only_one_map_on_group, collapsed, visible)

    def add_wms_url_query_layer(self, layer_name, url_query, group_name="", only_one_map_on_group=False, collapsed=True, visible=True):
        """ Afegeix una capa WMS a partir d'una petició WMS (URL) """
        uri = "url=%s" % url_query.lower().replace("epsg:", "epsg:").replace("srs=", "crs=").replace("?", "&")
        return self.add_raster_uri_layer(layer_name, uri, "wms", group_name, only_one_map_on_group, collapsed, visible)

    def add_raster_uri_layer(self, layer_name, uri, provider, group_name="", only_one_map_on_group=False, collapsed=True, visible=True):
        """ Afegeix una capa raster a partir d'un URI i proveidor de dades (wms, oracle ...)             
            Retorna la capa """
        ##print("URI", uri)
        # Creem la capa
        layer = self.iface.addRasterLayer(uri, layer_name, provider)
        if not layer:
            return layer
        # Canviem les propiedats de la capa
        self.set_properties(layer, visible, collapsed, group_name, only_one_map_on_group)
        return layer

    def set_scale_visibility(layer, min_scale=None, max_scale=None):
        """ Canvia la visiblitat per escala d'una capa. Si algun dels dos valors evalua fals desactiva la visibilitat per escala """
        if not min_scale or not max_scale:
            layer.toggleScaleBasedVisibility(False)
        else:
            layer.setMinimumScale(min_scale)
            layer.setMaximumScale(max_scale)
            layer.toggleScaleBasedVisibility(True)

    def set_transparency(self, layer, transparency):
        """ Canvia la transparència d'una capa """
        layer.renderer().setOpacity(transparency)

    def set_custom_properties(self, layer, properties_dict):
        """ Canvia propietats custom d'una capa """
        for property, value in properties_dict.items():
            layer.setCustomProperty(property, value)

    def set_properties(self, layer, visible=None, collapsed=None, group_name="", only_one_map_on_group=False, min_scale=None, max_scale=None, transparency=None, properties_dict=None):
        """ Canvia les propietats d'una capa """
        # Canviem la visiblitat per escala si cal
        if min_scale != None and max_scale != None:
            self.set_scale_visibility(min_scale, max_scale)
        # Canviem la transparència si cal
        if transparency is not None:
            self.set_transparency(layer, transparency)
        # Canviem la visibilitat si cal
        if visible is not None:
            self.set_visible(layer, visible)
        # Canviem el colapsament si cal
        if collapsed is not None:
            self.collapse(layer, collapsed)
        # Canviem propiestats custom
        if properties_dict is not None:
            self.set_custom_properties(properties_dict)
        # Vellugem la capa dins un grup si cal
        if group_name:
            if self.parent.legend.is_group_by_name(group_name):
                if only_one_map_on_group:
                    self.parent.legend.empty_group_by_name(group_name, exclude_list=[layer])
                else:
                    self.parent.legend.set_group_items_visible_by_name(group_name, False)
            self.parent.legend.move_layer_to_group_by_name(group_name, layer, True)

    def add_wms_ortoxpres_layer(self, year, gsd, layer_prefix="ortoXpres", url="http://www.ortoxpres.cat/server/sgdwms.dll/WMS", styles_list=["default"], image_format="image/jpeg", epsg=None, extra_tags="", group_name="", only_one_map=False):
        """ Afegeix una capa tipus WMS ICGC ortoXpres a partir d'un any i GSD 
            Retorna la capa """
        # Configurem el nom de la capa WMS del servidor a la que accedirem
        wms_layer = "Catalunya %dcm. %d" % (gsd * 100, year)
        layer_name = "%s %s" % (layer_prefix, wms_layer)
        print("WMS ortoXpres, capa:", layer_name)
        # Afegim la capa
        layer = self.add_wms_layer(layer_name, url, [wms_layer], styles_list, image_format, epsg, extra_tags, group_name, only_one_map)
        return layer

    def add_vector_db_layer(self, host, port, dbname, schema, table, user, password, geometry_column, filter=None, provider='oracle', epsg=25831, wkbtype= QgsWkbTypes.Polygon, layer_name=None):
        """ Afegeix una capa tipus BBDD 
            Retorna la capa """
        # configurem la connexió a la BBDD
        uri = QgsDataSourceURI()
        uri.setConnection(host, str(port), dbname, user, password)
        uri.setSrid(str(epsg));
        uri.setWkbType(wkbtype)
        uri.setDataSource(schema, table, geometry_column, filter)
        # afegim la capa
        layer = QgsVectorLayer(uri.uri(), layer_name, provider)
        if layer_name:
            layer.setLayerName(layer_name)
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        return layer

    def refresh_attributes_table_by_id(self, layer_id):
        """ Refresca la taula d'atributs de la capa indicada a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(layer_id)
        if layer:
            self.refresh_attributes_table(layer)

    def refresh_attributes_table(self, layer):
        """ Refresca la taula d'atributs de la capa indicada """
        self.refresh_attributes_tables(layer.name())

    def refresh_attributes_tables(self, layer_name_not_all=None):
        """ Refresca totes les taules d'atributs obertes o la de la capa especificada (per nom! no per id)"""
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

    def show_attributes_table_by_id(self, idprefix, multiinstance = False, pos=0):
        """ Mostra la taula de continguts d'una capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return None
        return self.show_attributes_table(layer, multiinstance)

    def show_attributes_table(self, layer, multiinstance = False):
        """ Mostra la taula de continguts d'una capa """
        table_dialog = self.get_attributes_table(layer)
        if multiinstance or not table_dialog:
            return self.iface.showAttributeTable(layer)
        else:
            table_dialog.showNormal()
            table_dialog.activateWindow()
            table_dialog.setFocus()
            return table_dialog

    def get_attributes_table_by_id(self, idprefix, pos=0):
        """ Obté la taula d'atributs d'una capa a partir del seu id (se li passa prefix d'id) """
        layer = self.get_by_id(idprefix, pos)
        if not layer:
            return False
        return self.get_attributes_table(layer)

    def get_attributes_table(self, layer):        
        """ Obté la taula d'atributs d'una capa """
        # Busquem si tenim una taula oberta de aquesta capa
        dialogs_list = [d for d in QApplication.instance().allWidgets() if d.objectName() == 'QgsAttributeTableDialog' and d.windowTitle().split(' - ')[1].split(' :: ')[0] == layer.name()]
        return dialogs_list[0] if len(dialogs_list) > 0 else None

    def refresh_legend_by_id(self, layer_id, visible=None, expanded=None):
        """ Refresca la llegenda d'una capa a partir del seu id (se li passa prefix d'id) """
        ## Busquem la capa indicada
        #layer = self.get_by_id(layer_id)
        #if not layer:
        #    return
        #self.refresh_legend(layer)
        self.iface.layerTreeView().refreshLayerSymbology(layer_id)
        if visible is not None:
            self.set_visible_by_id(layer_id, visible)
        if expanded is not None:
            self.expand_by_id(layer_id, expanded)

    def refresh_legend(self, layer, visible=None, expanded=None):
        """ Refresca la llegenda d'una capa """
        #legend = self.iface.legendInterface()
        ## Refresquem la llegenda de la capa
        #if type(layer) == QgsVectorLayer:
        #    # Força refrescar el comptador de la capa
        #    layer.setSubsetString(layer.subsetString())
        #    # Força refrescar els comptadors dels grups de l'estil de la capa
        #    layer.invalidateSymbolCountedFlag()
        ## Refresc "estandar"
        #legend.refreshLayerSymbology(layer)
        ## Canvia visibilitat
        #if visible != None:
        #    legend.setLayerVisible(layer, visible)
        ## Canvia expansió
        #if expanded != None:
        #    legend.setLayerExpanded(layer, expanded)
        self.refresh_legend_by_id(layer.id(), visible, expanded)

class LegendBase(object):
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface
        self.root = QgsProject.instance().layerTreeRoot()

    def get_group_by_name(self, group_name):
        """ Obté un grup a partir del seu nom """
        group = self.root.findGroup(group_name)
        if not group or not self.is_group(group):
            return None
        return group

    def is_group(self, item):
        """ Verifique que un item sigui de tipus grup """
        return item.nodeType() == 0 # 0 és tipus grup

    def is_group_by_name(self, group_name):
        """ Indica si el nom de grup passat, correspon realment a un grup existent """
        return self.get_group_by_name(group_name) is not None

    def add_group(self, group_name, expanded = True, visible_group=True, layer_list=[], group_parent_name=None):
        """ Afegeix un grup a la llegenda i retorna l'objecte """
        group = self.root.addGroup(group_name)
        group_parent = self.get_group(group_parent_name) if group_parent_name else None
        if group_parent:
            self.move_group_to_group(group, group_parent)
        if layer_list:
            self.move_layers_to_group(group, layer_list, visible_layer=visible_group)
        return group

    def remove_group_by_name(self, group_name):
        """ Esborra un grup de la llegenda """
        # Recuperem el grup
        group = self.get_group(group_name)
        if group is None:
            return False
        return self.remove_group(group)

    def remove_group(self, group):
        """ Esborra un grup """
        # Esborrem el contingut del grup
        if not self.empty_group(group):
            return False
        # Esborrem el grup
        self.root.removeChildNode(group)
        return True

    def empty_group_by_name(self, group_name, exclude_list=[]):
        """ Esborra el contingut d'un grup """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.empty_group(group, exclude_list)
        return True
    
    def empty_group(self, group, exclude_list=[]):
        """ Esborra el contingut d'un grup """
        # Esborrem les capes del grup
        if exclude_list:
            item_names_list = [item.name() for item in exclude_list]
            for child in group.children():
                if child.name() not in item_names_list:
                    group.removeChildNode(child)
        else:
            group.removeAllChildren()

    def move_layer_to_group_by_name(self, group_name, layer, autocreate_grup=False, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat """        
        return self.move_layers_to_group_by_name(group_name, [layer], autocreate_grup, visible_layer, pos, remove_repeated_layers)

    def move_layers_to_group_by_name(self, group_name, layers_list, autocreate_grup=False, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat """        
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if group:
            # Movem les capes
            self.move_layers_to_group(group, layers_list, visible_layer, remove_repeated_layers)
        else:
            # Creem el grup si cal
            if autocreate_grup:
                group = self.add_group(group_name, True, visible_layer, layers_list, pos)
        return group 

    def move_layer_to_group(self, group, layer, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat """        
        self.move_layers_to_group(group, [layer], visible_layer, pos, remove_repeated_layers)

    def move_layers_to_group(self, group, layers_list, visible_layer=True, pos=0, remove_repeated_layers=True):
        """ Velluga la capa indicada (objecte capa) dins el group especificat """        
        for layer in layers_list:
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
            #self.root.removeChildNode(old_tree_layer)
            self.root.removeLayer(layer)

    def move_group_to_group_by_name(self, group_name, parent_group_name):
        """ Velluga el grup indicat dins el group especificat """        
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        parent_group = self.get_group_by_name(parent_group_name)
        if not group or not parent_group:
            return False
        self.move_group_to_group(group, parent_group)
        return True

    def move_group_to_group(self, group, parent_group, pos=0):
        """ Velluga el grup indicat dins el group especificat """        
        # Movem el group dins el grup pare
        new_tree_group = group.clone()
        parent_group.insertChildNode(pos, new_tree_group)
        # Esborrem el grup inicial
        self.root.removeGroup(group)

    def set_group_visible_by_name(self, group_name, enable):
        """ Fa visibles o invisibles un grup """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.set_group_visible(group, enable)
        return True

    def set_group_visible(self, group, enable):
        """ Fa visibles o invisibles un grup """
        group.setItemVisibilityCheckedRecursive(enable)

    def set_group_items_visible_by_name(self, group_name, enable):
        """ Fa visibles o invisibles els elements d'un grup """
        # Obtenim el grup
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.set_group_items_visible(group, enable)
        return True

    def set_group_items_visible(self, group, enable):
        """ Fa visibles o invisibles els elements d'un grup """
        for child in group.children():
            child.setItemVisibilityCheckedRecursive(enable)

    def is_group_visible_by_name(self, group_name):
        """ Informa de si el grup és visible """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        return self.is_group_visible(group)

    def is_group_visible(self, group):
        """ Informa de si el grup és visible """
        return group.isVisible()

    def collapse_group_by_name(self, group_name, collapse=True):
        """ Colapsa o expandeix un element de la llegenda """
        return self.expand_group_by_name(group_name, not collapse)
    
    def collapse_group(self, group, collapse=True):
        """ Colapsa o expandeix un element de la llegenda """
        self.expand_group(group, not collapse)

    def expand_group_by_name(self, group_name, expand=True):
        """ Expandeix un grup """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.expand_group(group, expand)
        return True

    def expand_group(self, group, expand=True):
        """ Expandeix un grup """
        group.setExpanded(expand)

    def is_group_expanded_by_name(self, group):
        """ Informa de si està expandit un grup """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        return self.is_group_expanded(group)

    def is_group_expanded(self, group):
        """ Informa de si està expandit un grup """
        return group.isExpanded()
        
    #def collapse_all(self):
    #    """ Colapsa tots els elements de la llegenda """
    #    legend = self.iface.legendInterface();
    #    legend_items = len(legend.groupLayerRelationship())
    #    for i in range(0, legend_items):
    #        legend.setGroupExpanded(i, False)

    def zoom_to_full_extent_group_by_name(self, group_name, buffer=0, refresh=True):
        """ Ajusta la visualització del mapa per visualitzar els elements d'un grup """
        group = self.get_group_by_name(group_name)
        if not group:
            return False
        self.zoom_to_full_extent_group(group, buffer, refresh)
        return True

    def zoom_to_full_extent_group(self, group, buffer=0, refresh=True):
        """ Ajusta la visualització del mapa per visualitzar els elements d'un grup """
     
        # Inicialitzem l'area del zoom
        extent = QgsRectangle()
        extent.setMinimal()

        # A partir del grup, iterem les seves capes i combinem l'area de cada capa        
        for tree_layer in group.findLayers():
            layer = tree_layer.layer()
            # Descartem si es una capa només amb dades (sense cap tipus de geometria)
            if layer.wkbType() == 100:
                continue
            area = layer.extent()        
            # Reprojectem les coordenades si cal        
            if self.parent.layers.get_epsg(layer) != self.parent.project.get_epsg():
                area = self.parent.crs.transform_bounding_box(layer.extent(), self.parent.layers.get_epsg(layer))
            # Ampliem el rectangle si cal
            if buffer:
                area = area.buffer(buffer)
            # Combinem l'area
            extent.combineExtentWith(area)

        # Fem zoom a l'area
        self.iface.mapCanvas().setExtent(extent)
        if refresh:
            self.iface.mapCanvas().refresh()        

    def refresh_legend(self):
        """ Refresca tots els elements de la llegenda """
        for layer in self.iface.mapCanvas().layers():
            self.parent.layers.refresh_legend(layer)


class ComposerBase(object):
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

    def get_composer_item_by_id(self, composer_items, item_id):
        """ Obté un item del composer a partir de l'id """
        selected_items = [item for item in composer_items if hasattr(item, 'id') and item.id() == item_id]
        return selected_items[0] if (selected_items) > 0 else None

    def get_composer_map_item_by_pos(self, composer_items, map_pos):
        """ Obté un item de tipus mapa del composer a partir de la seva posició """
        selected_items = [item for item in composer_items if type(item) == QgsComposerMap]
        return selected_items[map_pos] if len(selected_items) > map_pos else None

    def get_composer_view(self, title):
        """ Obté la vista de composer amb el titol indicat """
        selected_composers = [view for view in self.iface.activeComposers() if view.composerWindow().windowTitle() ==  title]
        return selected_composers[0] if len(selected_composers) > 0 else None

    #def get_composer_view(self, composer_name):
    #    composer_views = self.iface.activeComposers()
    #    composer_titles = [view.composerWindow().windowTitle() for view in composer_views]        
    #    if not composer_name in composer_titles:
    #        return None
    #    composer_view = composer_views[composer_titles.index(composer_name)]
    #    return composer_view

    def get_composition(self, report_pathname, open_composer=True):
        """ Carrega un compositor a partir d'un fitxer i retorna l'objecte """
        if not os.path.isabs(report_pathname) and os.environ.get('APP_PATH', None):
            report_pathname = os.path.join(os.environ['APP_PATH'], report_pathname)
        if os.path.splitext(report_pathname)[1].lower() != '.qpt':
            report_pathname += '.qpt'

        template_file = file(report_pathname)
        template_content = template_file.read()
        template_file.close()
        
        document = QDomDocument()
        document.setContent(template_content)
         
        if open_composer:
            composer = self.iface.createNewComposer()    
            composition = composer.composition()       
        else:
            # ------------------------------------------------------------------------------------------------------
            # ATENCIÓ: Amb Windows 10 executar les dues instruccions:
            # -> composition = QgsComposition(self.iface.mapCanvas().mapSettings())   
            # -> composition.loadFromTemplate(document)
            # provoca un error que tanca QGIS. Amb el visor d'events parla de la PIL però ho he trobat la solució.
            # ------------------------------------------------------------------------------------------------------
            #composition = QgsComposition(self.iface.mapCanvas().mapSettings())                        
            composer = self.iface.createNewComposer()
            composition = composer.composition()
            composer.composerWindow().close()

        composition.loadFromTemplate(document)
        return composition

    def export_composition_as_image(self, composition, filepath):
        """ Exporta el contingut d'un composer com una imatge """
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
    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

    def format_epsg(self, text, asPrefixedText):
        """ Formateja un codi epsg text segons si volem prefix o no
            return "epsg:25831" o "25831" (string) """
        if not text:
            return text
        parts = text.split(':')
        if asPrefixedText:
            if len(parts) > 1:
                return text
            else:
                return "epsg:" + text
        else:
            if len(parts) > 1:
                return parts[1]
            else:
                return text

    def select_epsg(self, asPrefixedText = False):
        """ Obté un codi epsg a escollir en el diàleg estàndar QGIS """
        ps = QgsProjectionSelectionTreeWidget()
        ps.exec_()
        crsId = ps.selectedCrsId()
        if crsId > 0:
            self.crs = QgsCoordinateReferenceSystem()
            self.crs.createFromId(crsId, QgsCoordinateReferenceSystem.InternalCrsId)
            return format_epsg(self.crs.authid(), asPrefixedText)
        else:
            return None

    def get_crs(self, epsg):
        """ Obté un objecte CRS a partir d'un codi epsg """
        crs = QgsCoordinateReferenceSystem(int(epsg), type=QgsCoordinateReferenceSystem.EpsgCrsId)
        return crs

    def get_transform(self, in_epsg, out_epsg):
        """ Obté un objecte transformació a partir de 2 codis epsg """
        ct = QgsCoordinateTransform(self.get_crs(in_epsg), self.get_crs(out_epsg), QgsProject.instance())
        return ct

    def transform_point(self, x, y, source_epsg, destination_epsg=None):
        """ Converteix la coordenada x,y d'un epsg origen a un destí
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat """

        if not destination_epsg:
            destination_epsg = self.parent.project.get_epsg()
        if int(source_epsg) == int(destination_epsg):
            return x, y

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        point = ct.transform(x, y)
        return point.x(), point.y()

    def transform_bounding_box(self, area, source_epsg, destination_epsg=None):
        """ Converteix la coordenada x,y d'un epsg origen a un destí
            en cas de no especificar el destí, s'utilitzarà el del projecte carregat """

        if not destination_epsg:
            destination_epsg = int(self.parent.project.get_epsg())
        if int(source_epsg) == int(destination_epsg):
            return area

        # Preparem la transformació de les coordenades
        ct = self.get_transform(source_epsg, destination_epsg)
        area = ct.transformBoundingBox(area)
        return area


class DebugBase(object):    
    def __init__(self, parent):
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
        """ Inicialitza la consola de QGIS perquè els plugins puguin printar-hi """
        # Forcem crear l'objecte consola del modul "console.console" perquè la resta de plugins
        # pugin printar logs i l'amaguem
        if console.console._console is None:
            parent = self.iface.mainWindow() if self.iface else None
            console.console._console = console.console.PythonConsole( parent )
            ##console.console._console.hide()
            self.show_console(False)

    def show_console(self, show = True):
        """ Mostra / Oculta la consola de QGIS """
        if show == console.console._console.isHidden():
            self.toggle_console()

    def toggle_console(self):
        """ Mostra / Oculta la consola de QGIS (canvia l'estat previ) """
        console.show_console() # Fa toggle

    ###########################################################################
    # Recàrrega de plugins
    #

    def reload_plugins(self, plugins_id_wildcard = "qp*"):
        """ Recarrega els plugins que coincideixin amb el wildcard """
        # Recarreguem els plugins
        selected_plugins = [plugin_id for plugin_id in plugins.keys() if fnmatch.fnmatch(plugin_id, plugins_id_wildcard)]        
        with ProgressDialog('Llegint geometries...', len(selected_plugins), "Recarregant plugins", cancel_button_text = "Cancel·lar", autoclose = True) as progress:
            for plugin_id in selected_plugins:
                progress.set_label("Recarregant %s" % plugin_id)
                self.reload_plugin(plugin_id)
                if progress.was_canceled():
                    return
                progress.step_it()
        # Restaurem el cursor, per si algún plugin l'ha deixat penjat
        QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))

    def reload_plugin(self, plugin_id):
        """ Recarrega el plugin indicat per l'id """
        print("Reload:", plugin_id)
        reloadPlugin(plugin_id)

    ###########################################################################
    # Gestió de timestatmps
    #
    def ini_timestamps(self, description=None, timestamp_env='QGIS_STARTUP', timestamp_format="%d/%m/%Y %H:%M:%S.%f"):
        """ Afegeix un timestamp a partir d'una variable d'entorn amb l'hora d'inici de QGIS si existex """
        self.timestamps = []

        # Obtenim el timestamp d'inici de QGIS
        timestamp_text = os.environ.get(timestamp_env, '').replace(',', '.')
        timestamp = datetime.datetime.strptime(timestamp_text, timestamp_format) if timestamp_text else None
        if timestamp:
            self.add_timestamp(description if description else "QGIS ini", timestamp)

    def add_timestamp(self, description, timestamp = None):
        """ Afegeix una timestamp a la llista de timestamps a mostrar """
        self.timestamps.append((description, datetime.datetime.now() if timestamp is None else timestamp))

    def get_timestamps_info(self, info = "Load times:"):
        """ Obté informació dels timestamps existents """
        times_list = ["%s\t%s (%s) (%s)" % (description, timestamp, (timestamp - self.timestamps[i-1][1] if i > 0 else None), (timestamp - self.timestamps[0][1] if i > 0 else None)) for i, (description, timestamp) in enumerate(self.timestamps)]
        return "%s\n   " % info + "\n   ".join(times_list)

    def print_timestamps_info(self, info = "Load times:"):
        """ Mostra per consola informació dels timestamps existents """
        print(self.get_timestamps(info))


class ToolsBase(object):
    # Components a desactivar de QGIS per defecte
    disable_menus_titles = [
        u'P&roject', u'&Edit', u'&View', u'&Layer', u'&Settings', u'&Plugins', u'Vect&or',
        u'&Raster', u'&Database', u'&Web', u'Processing',
        ##u'&Help',
        u'P&royecto', u'&Edición', u'&Ver', u'&Capa', u'C&onfiguración', u'Co&mplementos',
        ##u'Vect&orial', u'&Ráster',
        u'Base de &datos', u'&Web', u'Procesado',
        u'A&yuda'
        ]
    disable_toolbars_titles = [
        u'File', u'Manage Layers', u'Digitizing', u'Advanced Digitizing',
        u'Plugins', u'Help', u'Raster', u'Label', u'Vector', u'Database', u'Web', u'GRASS',
        ##u'Map Navigation', u'Attributes',
        u'Archivo', u'Administrar capas',
        ##u'Digitalización',
        u'Digitalización avanzada',
        u'Complementos', u'Ayuda', u'Ráster', u'Etiqueta', u'Vectorial', u'Base de datos', u'Web', u'GRASS',
        ##u'Navegación de mapas', u'Atributos'
        ]
    disable_dockwidgets_titles = [
        u'Browser', u'Browser (2)', u'GPS Information',
        u'Layer order', u'Shortest path', u'Tile scale', u'Toolbox', u'Undo/Redo'
        ##u'Layers', u'Overview', u'Log Messages', u'Coordinate Capture',
        u'Explorador', u'Explorador (2)', u'Información de GPS',
        u'Orden de capas', u'Ruta más corta', u'Escala de tesela', u'Caja de herramientas', u'Deshacer/Rehacer',
        ##u'Capas', u'Vista general', u'Mensajes de, registro', u'Captura de coordenadas']
        ]

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

        # Activació / desactivació eines QGIS
        self.initial_menus = []
        self.initial_toolbars = []
        self.initial_dockwidgets_and_areas = []
        self.last_disable_mode = None

    def add_shortcut_QGIS_options(self, description = "Eines QGIS", keyseq = "Ctrl+Alt+F12"):
        """ Afegeix un shortcut per mostrar / ocultar els menús / toolbars de QGIS """
        #Creem un shortcut per activer les opcions per defecte de QGIS
        self.add_shortcut(description, keyseq, self.toggle_QGIS_options)

    def toggle_QGIS_options(self):
        """ Mostra / Oculta els menús / toolbars de QGIS (canvia l'estat previ) """
        actions_name = [a.text() for a in self.iface.mainWindow().menuBar().actions()]
        is_plugins_menu = self.iface.pluginMenu().title() in actions_name
        # Gestionem les opcions per defecte de QGIS
        if is_plugins_menu:
            # Esborrem els menus addicionals
            self.enable_QGIS_options(False)
        else:
            # Afegim opcions al menú
            self.enable_QGIS_options(True)

    def enable_QGIS_options(self, enable, hide_not_remove = None, menus_titles = None, toolbars_titles = None, dockwidgets_titles = None):
        """ Mostra / Oculta els menús / toolbars de QGIS """
        # Ens guardem el components originals de QGIS
        if not self.initial_menus:
            self.initial_menus = self.paent.gui.get_menus()
        if not self.initial_toolbars:
            self.initial_toolbars = self.parent.gui.get_toolbars()
        if not self.initial_dockwidgets_and_areas:
            self.initial_dockwidgets_and_areas = [(w, self.iface.mainWindow().dockWidgetArea(w)) for w in self.parent.gui.get_dock_widgets()]

        # Determinem quins components amagar (si no hi ha els agafem per defecte)
        if hide_not_remove == None:
            hide_not_remove = self.last_disable_mode
        else:
            self.last_disable_mode = hide_not_remove
        if not menus_titles:
            menus_titles = self.disable_menus_titles
        if not toolbars_titles:
            toolbars_titles = self.disable_toolbars_titles
        if not dockwidgets_titles:
            dockwidgets_titles = self.disable_dockwidgets_titles

        # Determinem quines opcions tenim actualment actives
        current_menus = self.parent.gui.get_menus()
        current_toolbars = self.parent.gui.get_toolbars()
        current_dockwidgets = self.parent.gui.get_dock_widgets()

        # Desactivem/Activem els menus
        for menu in self.initial_menus:
            if menu.menuAction().text() in menus_titles:
                if enable:
                    if menu not in current_menus:
                        self.iface.mainWindow().menuBar().addMenu(menu)
                else:
                    if menu in current_menus:
                        self.iface.mainWindow().menuBar().removeAction(menu.menuAction())

        # Desactivem/Activem les toolbars
        for toolbar in self.initial_toolbars:
            if toolbar.windowTitle() in toolbars_titles:
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
            if widget.windowTitle() in dockwidgets_titles:
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
        """ Afegeix un shortcut per organitzar la toolbar de QGIS """
        self.add_shortcut(description, keyseq, self.parent.gui.organize_toolbars)
                     
    def add_shortcut_console(self, description = "Consola python", keyseq = "Ctrl+Alt+F9"):
        """ Afegeix un shortcut per mostrar la consola de QGIS """
        self.add_shortcut(description, keyseq, self.parent.debug.toggle_console)
    
    def add_tool_console(self, tool_name = "&Consola de Python", toolbar_and_menu_name = "&Manteniment"):
        """ Afegeix un botó per mostrar la consola de QGIS """
        self.configureGUI(toolbar_and_menu_name, [
            (tool_name, self.parent.debug.toggle_console, QIcon(":/lib/qlib3/base/console.png"))
            ])

    def add_tool_reload_plugins(self, tool_name = "&Recarregar plugins ICGC", toolbar_and_menu_name = "&Manteniment", plugins_id_wildcard = "qp*"):
        """ Afegeix eina per recarregar els plugins que coincideixin amb el wildcard """
        self.configureGUI(toolbar_and_menu_name, [
            (tool_name, lambda p = plugins_id_wildcard : self.parent.debug.reload_plugins(p), QIcon(":/lib/qlib3/base/python.png"))
            ])

    def add_tool_refresh_map_and_legend(self, tool_name, remove_refresh_map):
        """ Afegeix o actualitza el botó de refresc per actualitzar també la llegenda """
        self.action_refresh_all = QAction(QIcon(":/lib/qlib3/base/refresh_all.png"), tool_name, self.iface.mainWindow())
        self.action_refresh_all.triggered.connect(self.parent.refresh_all)
        # Afegim el botó de la eina a la toolbar
        if remove_refresh_map:
            self.iface.mapNavToolToolBar().removeAction(self.iface.mapNavToolToolBar().actions()[-1])
        if self.action_refresh_all.text() not in [a.text() for a in self.iface.mapNavToolToolBar().actions()]:
            self.iface.mapNavToolToolBar().addAction(self.action_refresh_all)

    def add_tool_WMS_background_maps_lite(self, toolbar_name="&Mapes de fons", tool_text="&Mapes de fons", delete_text="&Esborrar mapes de fons", group_name="Mapes de fons", only_one_map=False):
        """ Afegeix un menú / toolbar amb recursos WMS """
        # Obtenim les capes històriques del servidor WMS d'històrics
        ##wms_url, historic_ortho_list = self.get_historic_ortho()
        wms_url, historic_ortho_list = None, []
        historic_ortho_menu_list = [
            (layer_name, 
            lambda dummy, lname=layer_name, lid=layer_id: self.parent.layers.add_wms_layer(lname, wms_url, [lid], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
            QIcon(":/lib/qlib3/base/cat_ortho5k%s.png" % ("bw" if color_type == "bw" else ""))) 
            for layer_id, layer_name, color_type, scale, year in historic_ortho_list if color_type != "ir"
            ]
        historic_infrared_ortho_menu_list = [
            (layer_name, 
            lambda dummy, lname=layer_name, lid=layer_id: self.parent.layers.add_wms_layer(lname, wms_url, [lid], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
            QIcon(":/lib/qlib3/base/cat_ortho5ki.png")) 
            for layer_id, layer_name, color_type, scale, year in historic_ortho_list if color_type == "ir"
            ]

        # Afegim les capes WMS al menú (les capes actuals suposem que tenen URL coneguda)
        self.parent.gui.configure_toolbar(toolbar_name, [
            ("&Topogràfic (piràmide topogràfica)",
                lambda:self.parent.layers.add_wms_layer("WMS Topogràfic (piràmide topogràfica)", "http://mapcache.icc.cat/map/bases/service", ["topo"], ["default"], "image/png", None, "BGCOLOR=0x000000", group_name, only_one_map),
                QIcon(":/lib/qlib3/base/cat_topo50k.png")),
            ("&Topogràfic 1:5.000", 
                lambda:self.parent.layers.add_wms_layer("WMS Topogràfic 1:5.000", "http://shagrat.icc.cat/lizardtech/iserv/ows", ["mtc5m"], ["default"], "image/png", None, "BGCOLOR=0x000000", group_name, only_one_map), 
                QIcon(":/lib/qlib3/base/cat_topo5k.png")),
            ("T&opogràfic 1:50.000", 
                lambda:self.parent.layers.add_wms_layer("WMS Topogràfic 1:50.000", "http://shagrat.icc.cat/lizardtech/iserv/ows", ["mtc50m"], ["default"], "image/png", None, "BGCOLOR=0x000000", group_name, only_one_map),
                QIcon(":/lib/qlib3/base/cat_topo50k.png")),
            ("To&pogràfic 1:250.000", 
                lambda:self.parent.layers.add_wms_layer("WMS Topogràfic 1:250.000", "http://shagrat.icc.cat/lizardtech/iserv/ows", ["mtc250m"], ["default"], "image/png", None, "BGCOLOR=0x000000", group_name, only_one_map), 
                QIcon(":/lib/qlib3/base/cat_topo250k.png")),
            "---",
            ("&Ortofoto color",
                lambda:self.parent.layers.add_wms_layer("WMS Ortofoto color", "http://mapcache.icc.cat/map/bases/service", ["orto"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
                QIcon(":/lib/qlib3/base/cat_ortho5k.png")),
            ##("Ortofoto &històrica", None, QIcon(":/lib/qlib3/base/cat_ortho5kbw.png"), historic_ortho_menu_list),
            ("Ortofoto &infraroja", 
                lambda:self.parent.layers.add_wms_layer("WMS Ortofoto infraroja", "http://shagrat.icc.cat/lizardtech/iserv/ows", ["ortoi5m"], ["default"], "image/jpeg", None, "BGCOLOR=0x000000", group_name, only_one_map),
                QIcon(":/lib/qlib3/base/cat_ortho5ki.png")),
            ##("Ortofoto in&fraroja històrica", None, QIcon(":/lib/qlib3/base/cat_ortho5ki.png"), historic_infrared_ortho_menu_list),
            "---",            
            (delete_text, lambda:self.parent.legend.empty_group_by_name(group_name), QIcon(":/lib/qlib3/base/wms_remove.png"))        
            ], 
            tool_text,
            QIcon(":/lib/qlib3/base/wms.png"))
    
    def get_historic_ortho(self, timeout_seconds=5, retries=3):
        """ Obté la URL del servidor d'ortofotos històriques i la llista "neta" de capes disponibles (sense dades redundants) 
            Retorna: URL, [(layer_id, layer_name, color_type, scale, year)] 
            color_type: "rgb"|"ir"|"bw" 
            """
        # Consultem el Capabilities del servidor WMS d'ortofotos històriques
        url_base = "http://historics.icc.cat/lizardtech/iserv/ows"
        url = "%s?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1" % url_base
        while retries:
            try:
                response = None
                response = urllib.request.urlopen(url, timeout=timeout_seconds)
                retries = 0
            except socket.timeout:
                retries -= 1
                print("retries", retries)
        if response:            
            response_data = response.read()
            response_data = response_data.decode('utf-8')
        else:
            response_data = ""

        # Recuperem les capes històriques
        reg_ex = "<Name>(\w+)</Name>\s+<Title>(.+)</Title>"
        wms_list = re.findall(reg_ex, response_data)
        
        # Corregim noms de capa
        wms_list = [(layer_id, layer_name.replace("sèrie B 1:5.000", "sèrie B 1:5.000 (1956-57)")) 
            for layer_id, layer_name in wms_list
            if layer_name.lower().find("no disponible") < 0]
        # Afegim escala i any com a llista
        wms_ex_list = [
            (layer_id,
            layer_name,
            [v.replace(".", "") for v in re.findall("1:([\d\.]+)", layer_name)],
            re.findall("[\s(](\d{4})", layer_name))
            for layer_id, layer_name in wms_list]
        # Afegim tipus de color i corregim tipus de dades de escala i any a enter
        wms_ex_list = [
            (layer_id, 
            layer_name, 
            ("ir" if layer_name.lower().find("infraroja") >= 0 else "rgb" if year_list and int(year_list[0]) >= 2000 else "bw"), 
            int(scale_list[0]) if scale_list else None, 
            int(year_list[0]) if year_list else None) 
            for layer_id, layer_name, scale_list, year_list in wms_ex_list]

        # Netegem resolucions redundants        
        wms_names_list = [layer_name for layer_id, layer_name in wms_list]
        wms_ex_list = [(layer_id, layer_name, color_type, scale, year) 
            for layer_id, layer_name, color_type, scale, year in wms_ex_list
            if scale in (1000, 2500, 5000, 10000)
            and (scale != 5000 or layer_name.replace(":5.000", ":2.500") not in wms_names_list)            
            ]

        # Ordenem per any
        wms_ex_list.sort(key=lambda p: p[4], reverse=True)

        return url_base, wms_ex_list


class MetadataBase(object):
    def __init__(self, parent, plugin_pathname):
        self.parent = parent
        self.iface = parent.iface

        # Carreguem informació del metadata.txt
        self.metadata = configparser.ConfigParser()
        self.metadata.read(os.path.join(os.path.dirname(plugin_pathname), 'metadata.txt'))

    def get(self, option, section="general", default_value=""):
        return self.metadata.get(section, option) if self.metadata.has_option(section, option) else default_value

    def get_name(self):
        """ Obté el nom del plugin actual """
        return self.get("name")

    def get_version(self):
        """ Obté la versió del plugin actual """
        return self.get("version")

    def get_description(self):
        """ Obté la descripció curta del plugin actual """
        # Carreguem la descripció curta segon l'idioma del QGIS
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

    def get_about(self):
        """ Obté la descripció llarga del plugin actual """
        # Detectem si tenim un about multi idioma (separats per doble canvi de linia)
        multi_about_list = self.get("about").split("\n\n")

        # Carreguem la descripció llarga segon l'idioma del QGIS
        language = self.parent.translation.get_qgis_language()
        if language == self.parent.translation.LANG_CA:
            # Català
            about = self.get("about_ca")
            if not about:
                # Suposo que el català està en segona posició
                about = multi_about_list[0]
        elif language == self.parent.translation.LANG_ES:
            # Castellà
            about = self.get("about_es")
            if not about and len(multi_about_list) > 1:
                # Suposo que el castellà està en segona posició
                about = multi_about_list[1]
        else:
            # Per defecte anglés
            about = self.get("about_en")        
            if not about and len(multi_about_list) > 2: 
                # Suposo que l'anglés està en tercera posició
                about = multi_about_list[2]
        if not about:
            # Si no agafem la descripció llarga estàndar que hem fet servir en el metadata.txt
            about = self.get("about")
        
        return about

    def get_author(self):
        """ Obté el desenvolupador del plugin actual """
        return self.get("author")

    def get_email(self):
        """ Obté el desenvolupador del plugin actual """
        return self.get("email")

    def get_info(self):
        info = "%s v%s\n%s\n\n%s\n\n%s" % (self.get_name(), self.get_version(), self.get_description(), self.get_about(), self.get_author())
        return info

class TranslationBase(object):
    LANG_CA = "ca_ES"
    LANG_ES = "es"
    LANG_EN = "en_US"

    def __init__(self, parent):
        self.parent = parent
        self.iface = parent.iface

        # Preparem un diccionari de traduccions
        self.translation_dict = {}

    def get_qgis_language(self):
        """ Retorna l'idioma actiu en el QGIS. Pex: ca_ES, es_ES """
        return QSettings().value('locale/userLocale')

    def set_text(self, language, key, text):
        """ Guarda un text en un determinat idioma en el diccionari de traduccions """
        if language not in self.translation_dict:
            self.translation_dict[language] = {}
        self.translation_dict[language][key] = text

    def get_text(self, key, default_text="", language=None):
        """ Recupera un text en un determinat idioma del diccionari de traduccions """
        # Per defecte intentem recuperar el text en l'idioma del QGIS
        if not language:
            language = self.get_qgis_language()
        # Si l'idioma no està al diccionar, intentem recuperar anglés
        if language not in self.translation_dict:
            language = self.LANG_EN
        # Si tot falla retornem el text per defecte
        return self.translation_dict[language].get(key, default_text) if language in self.translation_dict else default_text


class PluginBase(object):
    # $$$ Afegir mapejos d'events per defecte??

    # Inicialització de la classe
    def __init__(self, iface, plugin_pathname):
        self.plugin_pathname = plugin_pathname
        self.plugin_path = os.path.dirname(self.plugin_pathname)
        self.plugin_id = os.path.basename(self.plugin_path)

        self.iface = iface

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
                
    def unload(self):
        # Eliminem dades
        self.gui.remove()
        self.gui = None
        self.project = None
        self.layers = None
        self.legend = None
        self.composer = None
        self.crs = None
        self.debug = None
        self.tools = None
        self.metadata = None
        self.translation = None

    def get_plugins_id(self):
        """ Retorna una llista amb els ids dels plugins carregats """
        return plugins.keys()

    def get_plugin(self, plugin_name):
        """ Obté una referència a un plugin per nom """
        return plugins[plugin_name]
    
    def reload_plugin(self):
        """ Recarrega el plugin actual """
        self.debug.reload_plugin(self.plugin_id)

    def refresh_all(self):
        """ Refresca mapa, llegenda i taules de contingut """
        self.layers.refresh_map()
        self.layers.refresh_attributes_tables()
        self.legend.refresh_legend()

    def set_map_point(self, x, y, epsg=None, scale=None):
        """ Situa el mapa en les coordenades indicades a una determinada escala a partir d'un punt central
            Reprojecte la coordenade al sistema de projecte si cal """
        print("Coordinate: %s %s EPSG:%s" % (x, y, epsg))
        
        # Detectem si estem en geogràfiques o no i configurem la escala
        if not scale:
            scale = 0.01 if x < 100 else 1000

        # Calculem el rectangle a visualitzar
        west = x-scale/2
        south = y-scale/2
        east = x+scale/2
        north = y+scale/2
        self.set_map_rectangle(west, north, east, south, epsg)

    def set_map_rectangle(self, west, north, east, south, epsg=None):
        """ Situa el mapa en les coordenades indicades
            Reprojecte la coordenade al sistema de projecte si cal """

        # Cal, transformem les coordenades al sistema del projecte
        if epsg and epsg != int(self.project.get_epsg()):
            west, north = self.crs.transform_point(west, north, epsg)
            east, south = self.crs.transform_point(east, south, epsg)
        print("Rectangle: %s %s %s %s EPSG:%s" % (west, north, east, south, self.project.get_epsg()))

        # Resituem el mapa
        rect = QgsRectangle(west, south, east, north) # minx, miny, maxx, maxy
        mc = self.iface.mapCanvas()
        mc.setExtent(rect)
        mc.refresh()
