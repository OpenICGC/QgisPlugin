# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with the implementation of the dialog that allows to show the results 
of the spatial searches
                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os
from importlib import reload

# Import the PyQt and QGIS libraries
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QDialog, QAbstractItemView, QHeaderView, QTableWidgetItem, QApplication

# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Load a .ui file without pre-compiling it
ui_geofinder, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_geofinder.ui'))

# Import GeoFinder class
import geofinder3.geofinder
reload(geofinder3.geofinder)
from geofinder3.geofinder import GeoFinder


class GeoFinderDialog(QDialog, ui_geofinder):
    """ Dialog class that allows to show the results of the spatial searches """

    # We prepare a toponym mapping with the icon to show
    TOPOICONS_DICT = {
        1:'town.png', 2:'town.png', #Cap municipi, municipi
        3:'flag.png', 17:'flag.png', #Entitat de població, comarca
        4:'build.png', #Edifici
        20:'history.png', #Edifici històric
        21:'house.png', 16:'house.png', #Nucli, barri
        18:'crossroad.png', 19:'crossroad.png', 22:'crossroad.png', 99:'crossroad.png', #diss., diss., e.m.d., llogaret carrerer
        6:'mountain.png', 7:'mountain.png', 8:'mountain.png', 9:'mountain.png', 10:'mountain.png', #Serra, orografia, cim, coll, litoral
        11:'pin.png', #Indret
        12:'equipment.png', #Equipaments
        13:'communications.png', #Comunicacions
        14:'river.png', 15:'river.png' #Curs fluvial, hidrografia
        }

    def __init__(self, geofinder_dict_list=[], title=None, columns_list=[], auto_show=False):
        """ Dialog initialization """
        QDialog.__init__(self)

        # Set up the user interface from Designer.
        self.setupUi(title, columns_list)
        
        # Set up values
        self.geofinder = GeoFinder()
        self.geofinder_dict_list = geofinder_dict_list
        self.set_data(self.geofinder_dict_list)
                
        # We show the dialog automatically if necessary
        self.status = False
        if auto_show:
            self.do_modal()

    def setupUi(self, title, columns_list):
        """ Setup the components that form the dialog """

        # We Initialize the UI by associating the items in the plugin class
        # For compatibility with the old code QGIS2, we fake the member variable ui with self param 
        # (now it would not be necessary to have .ui)
        super().setupUi(self)
        
        # Setup dialog title
        if title:
            self.setWindowTitle(title)

        # We initialize dialog items
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget.setShowGrid(False)
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # Setup column names
        if columns_list:
            for i, col_name in enumerate(columns_list):
                self.tableWidget.horizontalHeaderItem(i).setText(col_name)

    def set_data(self, topodata_list):
        self.tableWidget.setRowCount(len(topodata_list))

        # topodata_list example:
        # [{"nom":"Barcelona","x":"431300","y":"4581740","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"1","nomTipus":"Cap de municipi","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
        for i, topodata in enumerate(topodata_list):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(QIcon(":/lib/qlib3/geofinderdialog/images/%s" % self.TOPOICONS_DICT.get(topodata['idTipus'], "geofinder.png")), topodata['nom']))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(topodata['nomTipus'])) ## + " (" + topodata['idTipus'] + ")"))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(topodata['nomMunicipi']))
            self.tableWidget.setItem(i, 3, QTableWidgetItem(topodata['nomComarca']))

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()

        if len(topodata_list) > 0:
            self.tableWidget.selectRow(0)

    def do_modal(self):
        """ Show GeoFinder dialog and makes it modal """
        self.show()
        self.status = self.exec_()
        return self.status

    def get_selection_index(self):
        """ Return number of selected dialog row """
        return self.tableWidget.currentRow() if self.status else -1

    def find(self, text, default_epsg):
        # Find text
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.geofinder_dict_list = self.geofinder.find(text, default_epsg)
        finally:
            QApplication.restoreOverrideCursor()

        # If we have a rectangle, we do not have to do anything, we get the coordinates and access
        if self.geofinder.is_rectangle(self.geofinder_dict_list):
            # Get rectangle coordinates
            self.selected = 0        
        else:
            # We show the found places in a dialog
            self.set_data(self.geofinder_dict_list)
            if not self.do_modal():
                return False
            self.selected = self.get_selection_index()
            if self.selected < 0:
                return False
            print("Selected: %s" % self.geofinder_dict_list[self.selected]['nom'])

        return True 

    def is_rectangle(self):
        return self.geofinder.is_rectangle(self.geofinder_dict_list)

    def get_rectangle(self):
        return self.geofinder.get_rectangle(self.geofinder_dict_list)

    def get_point(self):
        return self.geofinder.get_point(self.geofinder_dict_list, self.selected)