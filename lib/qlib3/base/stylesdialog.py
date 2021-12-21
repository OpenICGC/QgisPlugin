# encoding: utf-8
"""
*******************************************************************************
Mòdul amb funcions i classes fer gestionar diàlegs amb estils de capes a BBDD
---
Module with functions and classes to manage dialogs with BBDD style layers
bars
                             -------------------
        begin                : 2019-07-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QComboBox, QCheckBox

ui_loginfo, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_styles.ui'))


class StylesDialog(QDialog, ui_loginfo):
    """ Classe d'estils de les capes seleccionades
        ---
        Dialog class of styles of selected layers
        """

    def __init__(self, layers_dict={}, title=None, autoshow=True, parent=None):
        """ Inicialitza el diàleg d'estils a partir de les capes seleccionades 
            Opcionalment es pot especificar:
            - title: títol del diàleg
            - autoshow: mostra el diàleg al declarar-lo
            - parent: finestra pare del diàleg
            ---
            Initializes styles dialog from selected layers
            Optionally you can specify:
            - title: dialog title
            - autoshow: show dialog on declaration
            - parent: parent window of the dialog
            """
        QDialog.__init__(self, parent)
        self.setupUi(self)        
        self.ui = self # Per compatibilitat QGIS2/3
        # Canviem el títol
        if title:
            self.setWindowTitle(title)
        # Carreguem les dades
        if layers_dict:
            self.set_layers_styles(layers_dict)
        # Mostrem el diàleg
        if autoshow:
            self.return_value = self.do_modal()
        else:
            self.return_value = None

    def do_modal(self):
        """ Mostra el diàleg en mode modal
            ---
            Show modal dialog
            """
        self.show()
        self.return_value = self.exec_()
        return self.return_value

    def is_cancelled(self):
        """ Retorna si s'ha sortit amb el botó de cancel·lar
            ---
            Return if exit with cancel button
            """
        return self.return_value == 0
    
    def set_layers_styles(self, layers_styles_dict_list):
        """ Carrega la informació de capes i estils a mostrar
            ---
            Load style layers information
            ---            
            layers_styles_dict_list: [(layer_id, layer_name, current_style_id, available_styles_dict),]
                available_styles_dict: {style_id: (style_name, style_description)
            """
        # Preparem una llista d'estils globals
        global_styles_set = set()

        # Resetejem la taula del diàleg
        self.tableWidget.reset()        
        # Carreguem la informació de les capes
        self.tableWidget.setRowCount(len(layers_styles_dict_list))
        for index, (layer_id, layer_name, visible, current_style_id, styles_dict) in enumerate(layers_styles_dict_list):
            # Afegim un check per activar/desactivar
            check = QCheckBox()
            check.setChecked(visible)
            self.ui.tableWidget.setCellWidget(index, 0, check)
            # Mostrem el nom de la capa
            itemColumn = QTableWidgetItem(layer_name)
            itemColumn.setWhatsThis(layer_id)
            itemColumn.setFlags(Qt.ItemIsEnabled)
            self.ui.tableWidget.setItem(index ,1, itemColumn)
            # Mostrem un combobox amb els estils disponibles
            combo = QComboBox()
            current_style_pos = -1
            for style_index, (style_id, (style_name, style_description)) in enumerate(styles_dict.items()):
                combo.addItem(style_name, style_id)
                if style_id == current_style_id:
                    current_style_pos = style_index
                # Guardem l'estil a la llista de globals
                global_styles_set |= set((style_name, ))
            combo.setCurrentIndex(current_style_pos)
            self.ui.tableWidget.setCellWidget(index, 2, combo)            
        # Ajustem les mides de la taula
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeRowsToContents()

        # Carreguem els estils globals
        self.comboBox.clear()
        self.comboBox.addItem("")
        for style_name in global_styles_set:
            self.comboBox.addItem(style_name)

    def get_layers_styles(self):
        """ Retorna l'estil seleccioanat per cada capa
            ---
            Return selected style for every layer
            """
        style_layers_list = []
        for row in range(0, self.tableWidget.rowCount()):
            visible = self.tableWidget.cellWidget(row, 0).isChecked()
            layer_id = self.tableWidget.item(row, 1).whatsThis()
            style_id = self.tableWidget.cellWidget(row, 2).currentData()
            style_layers_list.append((layer_id, visible, style_id))
        return style_layers_list

    def global_styles_currentIndexChanged(self, style_name):
        """ Canvia l'estil de totes les capes que suportin el nom d'estil seleccionat
            ---
            Changes style of all layers that supports selected style name
            """
        if not style_name:
            return
        # Canviem l'estil de totes les capes que poguem
        for row in range(0, self.tableWidget.rowCount()):
            combo = self.tableWidget.cellWidget(row, 2)
            index = combo.findText(style_name) #, QtCore.Qt.MatchFixedString)
            if index >= 0:
                combo.setCurrentIndex(index)


if __name__ == "__main__":
    pass
