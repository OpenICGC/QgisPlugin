# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb classe diàleg per mostrar informació bàsica del plugin i logo el ICGC
---
Module with a dialog class to display basic information of plugin and ICGC logo

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFontMetrics, QPixmap
from PyQt5.QtWidgets import QStyle, QDialogButtonBox, QDialog, QApplication

ui_transparency, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_transparency.ui'))


class TransparencyDialog(QDialog, ui_transparency):
    """ Classe diàleg per mostrar informació bàsica del plugin i logo el ICGC
        ---
        Class to display basic information of plugin and ICGC logo
        """

    layer = None

    def __init__(self, title=None, layer=None, transparency=None, autoshow=True, parent=None):
        """ Inicialització del diàleg "about", cal informar de:
            - app_name: Títol del diàleg
            - app_icon: Icona del diàleg
            - info: Informació a mostrar
            Opcionalment:
            - autoshow: Mostra el diàleg automàticament al crear-lo
            - parent: Especifica la finestra pare del diàleg
            - new_line: Caràcters a substituir per un canvi de linia
            ---
            Initialization of the "about" dialog, you need to report:
             - app_name: Title of the dialog
             - app_icon: Icon of the dialog
             - info: Information to show
             Optionally:
             - autoshow: Show the dialog automatically when you create it
             - parent: Specifies the parent window of the dialog
             - new_line: Characters to be replaced by a change of line
            """
        QDialog.__init__(self, parent)
        self.setupUi(self)        
        self.ui = self # Per compatibilitat QGIS2/3

        # Canviem el títol i la icona
        if title:
            self.setWindowTitle(title)
        if layer:
            title = self.windowTitle()
            self.setWindowTitle("%s: %s" % (title, layer.name()))

        # Carreguem la transparència actual
        if transparency:
            self.set_transparency(transparency)
        self.layer = layer
        if self.layer:
            if self.layer.type() == 0:
                transparency = 100 - (self.layer.opacity() * 100)
            else:
                transparency = 100 - (self.layer.renderer().opacity() * 100)
            self.set_transparency(transparency)

        # Mostrem el diàleg
        if autoshow:
            self.show()

    def on_value_changed(self, transparency):
        if self.layer:
            opacity = (100 - transparency) / 100

            if self.layer.type() == 0: # Si es vectorial
               self.layer.setOpacity(opacity)
            else:
                self.layer.renderer().setOpacity(opacity) 
            self.layer.triggerRepaint()

    def get_transparency(self):
        return self.ui.horizontalSlider.value()
    
    def set_transparency(self, transparency):
        if self.get_transparency() != transparency:
            return self.ui.horizontalSlider.setValue(transparency)