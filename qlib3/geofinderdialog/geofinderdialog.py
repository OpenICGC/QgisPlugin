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


class GeoFinderDialog(QDialog, ui_geofinder):
    """ Dialog class that allows to show the results of the spatial searches """
    test = False

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
        14:'river.png', 15:'river.png', #Curs fluvial, hidrografia
        1000:'address.png', #Adreça (codi propi del geofinder)
        1001:'road.png', #Carretera (codi propi del geofinder)
        1002:'cadastral.png' #Carretera (codi propi del geofinder)
        }

    def __init__(self, geofinder_instance, geofinder_dict_list=[], title=None, columns_list=[], keep_scale_text=None, default_scale=1000, create_layer_text=None, default_create_layer=True, auto_show=False, parent=None):
        """ Dialog initialization """
        QDialog.__init__(self, parent)

        # Set up the user interface from Designer.
        self.setupUi(title, columns_list, keep_scale_text, default_scale, create_layer_text, default_create_layer)

        # Set up values
        self.geofinder = geofinder_instance
        self.geofinder_dict_list = geofinder_dict_list
        self.set_data(self.geofinder_dict_list)

        # We show the dialog automatically if necessary
        self.status = False
        if auto_show:
            self.do_modal()

    def setupUi(self, title, columns_list, keep_scale_text, default_scale, create_layer_text, default_create_layer=True):
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

        # Setup first scale text "keep scale"
        if keep_scale_text:
            self.comboBox_scale.setItemText(0, keep_scale_text)
        # Initialize default scale value
        pos = max(self.comboBox_scale.findText(str(default_scale)), 0)
        self.comboBox_scale.setCurrentIndex(pos)

        # Setup create layer text
        if create_layer_text:
            self.checkBox_layer.setText(create_layer_text)
        # Initialize default create layer value
        self.checkBox_layer.setChecked(default_create_layer)

    def set_test_mode(self, test=True):
        """ Activa el mode test que fa que el do_modal no esperi entrada de dades """
        self.test = test
        self.setModal(not test)

    def set_data(self, topodata_list):
        self.tableWidget.setSortingEnabled(False)
        self.tableWidget.setRowCount(len(topodata_list))

        # topodata_list example:
        # [{"nom":"Barcelona","x":"431300","y":"4581740","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"1","nomTipus":"Cap de municipi","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
        for i, topodata in enumerate(topodata_list):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(QIcon(":/lib/qlib3/geofinderdialog/images/%s" % self.TOPOICONS_DICT.get(topodata['idTipus'], "geofinder.png")), topodata['nom']))
            self.tableWidget.setItem(i, 1, QTableWidgetItem(topodata['nomTipus'])) ## + " (" + topodata['idTipus'] + ")"))
            self.tableWidget.setItem(i, 2, QTableWidgetItem(topodata['nomMunicipi']))
            self.tableWidget.setItem(i, 3, QTableWidgetItem(topodata['nomComarca']))
            # Ens guardem la posició original de l'item per si després s'ordena la llista i canvia l'index
            self.tableWidget.item(i, 0).setData(Qt.UserRole, i);

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()
        self.tableWidget.setSortingEnabled(True)

        if len(topodata_list) > 0:
            self.tableWidget.selectRow(0)

    def do_modal(self):
        """ Show GeoFinder dialog and makes it modal """
        if self.test:
            # En mode test només mostrem el diàleg, bloquejem esperant resposta
            self.status = 1
        else:
            self.show()
            self.status = self.exec_()
        return self.status

    def get_selection_index(self):
        """ Return number of selected dialog row """
        if not self.status or self.tableWidget.currentRow() < 0:
            return -1
        return self.tableWidget.item(self.tableWidget.currentRow(), 0).data(Qt.UserRole)

    def find(self, text, default_epsg):
        # Find text
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.geofinder_dict_list = self.geofinder.find(text, default_epsg)
        finally:
            QApplication.restoreOverrideCursor()

        # We show the found places in a dialog
        self.comboBox_scale.setEnabled(not self.geofinder.is_rectangle(self.geofinder_dict_list))
        self.set_data(self.geofinder_dict_list)
        if not self.do_modal():
            return False
        self.selected = self.get_selection_index()
        if self.selected < 0:
            return False
        ##print("Selected: %s" % self.geofinder_dict_list[self.selected]['nom'])

        return True

    def is_rectangle(self):
        return self.geofinder.is_rectangle(self.geofinder_dict_list)

    def get_rectangle(self):
        return self.geofinder.get_rectangle(self.geofinder_dict_list)

    def get_point(self):
        return self.geofinder.get_point(self.geofinder_dict_list, self.selected)

    def get_scale(self):
        scale = int(self.comboBox_scale.currentText()) if self.comboBox_scale.currentIndex() else None
        return scale

    def get_name(self):
        return self.geofinder.get_name(self.geofinder_dict_list, self.selected)

    def get_create_layer(self):
        create_layer = self.checkBox_layer.isChecked()
        return create_layer
