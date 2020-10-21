# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb classe diàleg per gestionar la transparencia d'una capa
---
Module with a dialog class to manage layer transparency

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

from PyQt5 import uic
from PyQt5.QtWidgets import QDockWidget

Ui_Transparency, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_transparency.ui'))


class TransparencyDialog(QDockWidget, Ui_Transparency):
    """ Classe diàleg per gestionar la transparencia d'una capa
        ---
        Class to manage layer transparency
        """

    layer = None

    def __init__(self, title=None, layer=None, transparency=None, autoshow=True, parent=None):
        """ Inicialització del diàleg "transparència", cal informar de:
            - title: Títol del diàleg
            - layer: Capa a modificar
            - tranparency: valor de transparència actual
            Opcionalment:
            - autoshow: Mostra el diàleg automàticament al crear-lo
            - parent: Especifica la finestra pare del diàleg
            ---
            Initialization of the "transparency" dialog, you need to report:
             - title: Title of the dialog
             - layer: layer to modify
             - transparency: current transparency layer value
             Optionally:
             - autoshow: Show the dialog automatically when you create it
             - parent: Specifies the parent window of the dialog
            """
        super().__init__(parent)
        self.setupUi(self)        

        # Canviem el títol
        if title:
            self.setWindowTitle(title)
        # Carreguem la transparència actual
        if transparency:
            self.set_transparency(transparency)
        # Assignem la capa
        if layer:
            self.set_layer(layer)

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
        return self.horizontalSlider.value()
    
    def set_transparency(self, transparency):
        if self.get_transparency() != transparency:
            return self.horizontalSlider.setValue(transparency)

    def set_layer(self, layer):
        self.layer = layer

        title = self.windowTitle().split(":")[0]
        self.setWindowTitle("%s: %s" % (title, layer.name()))

        if self.layer.type() == 0:
            transparency = 100 - (self.layer.opacity() * 100)
        else:
            transparency = 100 - (self.layer.renderer().opacity() * 100)
        self.set_transparency(transparency)

