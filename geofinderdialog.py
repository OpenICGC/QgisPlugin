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

# Import the PyQt and QGIS libraries
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QAbstractItemView, QHeaderView, QTableWidgetItem

# Load a .ui file without pre-compiling it
ui_geofinder, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_geofinder.ui'))


class GeoFinderDialog(QDialog, ui_geofinder):
    """ Dialog class that allows to show the results of the spatial searches """

    def __init__(self, topodata_list, topoicons_dict, auto_show=True):
        """ Dialog initialization """
        QDialog.__init__(self)

        # Set up the user interface from Designer.
        self.setupUi(topodata_list, topoicons_dict)
        
        # Variables initialization
        self.status = False
        
        # We show the dialog automatically if necessary
        if auto_show:
            self.do_modal()

    def setupUi(self, topodata_list, topoicons_dict):
        """ Setup the components that form the dialog """

        # We Initialize the UI by associating the items in the plugin class
        # For compatibility with the old code QGIS2, we fake the member variable ui with self param 
        # (now it would not be necessary to have .ui)
        super().setupUi(self)
        self.ui = self
        
        # We initialize dialog items
        self.ui.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.tableWidget.setShowGrid(False)
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.ui.tableWidget.setRowCount(len(topodata_list))

        # topodata_list example:
        # [{"nom":"Barcelona","x":"431300","y":"4581740","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"1","nomTipus":"Cap de municipi","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
        for i, topodata in enumerate(topodata_list):
            self.ui.tableWidget.setItem(i, 0, QTableWidgetItem(QIcon(":/plugins/openicgc/images/%s" % topoicons_dict.get(topodata['idTipus'], "geofinder.png")), topodata['nom']))
            self.ui.tableWidget.setItem(i, 1, QTableWidgetItem(topodata['nomTipus'])) ## + " (" + topodata['idTipus'] + ")"))
            self.ui.tableWidget.setItem(i, 2, QTableWidgetItem(topodata['nomMunicipi']))
            self.ui.tableWidget.setItem(i, 3, QTableWidgetItem(topodata['nomComarca']))

        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.resizeRowsToContents()

        if len(topodata_list) > 0:
            self.ui.tableWidget.selectRow(0)

    def do_modal(self):
        """ Show GeoFinder dialog and makes it modal """
        self.show()
        self.status = self.exec_()
        return self.status

    def get_selection_index(self):
        """ Return number of selected dialog row """
        return self.ui.tableWidget.currentRow() if self.status else -1
