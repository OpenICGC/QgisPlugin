# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AssignaEspaiDialog
                                 A QGIS plugin
 Assigna un disc i un servidor a un bloc
                             -------------------
        begin                : 2012-02-10
        copyright            : (C) 2012 by ICC
        email                : j.arnaldich@icc.cat
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QAbstractItemView, QHeaderView, QTableWidgetItem

# Càrrega d'.ui sense precompilar-lo
ui_geofinder, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_geofinder.ui'))


class GeoFinderDialog(QDialog, ui_geofinder):
    def __init__(self, title, topoheader_list, topodata_list, topoicons_dict, auto_show=True):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.setupUi(title, topoheader_list, topodata_list, topoicons_dict)
        # Inicialitzem variables internes
        self.status = False
        # Mostrem el diàleg automàticament si cal
        if auto_show:
            self.do_modal()

    def setupUi(self, title, topoheader_list, topodata_list, topoicons_dict):
        # Inicialitza la UI associant els items a la classe del plugin
        super().setupUi(self)
        # Per compatibilitat amb el codi antic, "falsejo" la variable membre ui amb el self (ara no caldria tenir .ui)
        self.ui = self
        
        # Inicialitzem el títol de la finestra
        if title:
            self.setWindowTitle(title)

        # Inicialitzem els items
        self.ui.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.tableWidget.setShowGrid(False)
        self.ui.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tableWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.ui.tableWidget.setColumnCount(len(topoheader_list))
        self.ui.tableWidget.setHorizontalHeaderLabels(topoheader_list)
        self.ui.tableWidget.setRowCount(len(topodata_list))

        # [{"nom":"Barcelona","x":"431300","y":"4581740","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"1","nomTipus":"Cap de municipi","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
        for i, topodata in enumerate(topodata_list):
            self.ui.tableWidget.setItem(i, 0, QTableWidgetItem(QIcon(":/plugins/geofinder/%s" % topoicons_dict.get(topodata['idTipus'], "geofinder.png")), topodata['nom']))
            self.ui.tableWidget.setItem(i, 1, QTableWidgetItem(topodata['nomTipus']))## + " (" + topodata['idTipus'] + ")"))
            self.ui.tableWidget.setItem(i, 2, QTableWidgetItem(topodata['nomMunicipi']))
            self.ui.tableWidget.setItem(i, 3, QTableWidgetItem(topodata['nomComarca']))

        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.resizeRowsToContents()

        if len(topodata_list) > 0:
            self.ui.tableWidget.selectRow(0)

    def do_modal(self):
        self.show()
        self.status = self.exec_()
        return self.status

    def get_selection_index(self):
        return self.ui.tableWidget.currentRow() if self.status else -1
