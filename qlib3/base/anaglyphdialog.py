# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb classe diàleg gestionar series temporals de dades
---
Module with a dialog class to manage temporal series

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

from PyQt5 import uic
from PyQt5.QtGui import QPainter, QPen, QFont
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtWidgets import QDockWidget, QSlider, QApplication, QStyleOptionSlider, QToolTip

Ui_Anaglyph, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_anaglyph.ui'))




class AnaglyphDialog(QDockWidget, Ui_Anaglyph):
    """ Classe diàleg per mostrar opcions de visualitzar anaglif
        ---
        Class dialog to show anaglyph visualization options
        """

    def __init__(self, layer_name, update_callback=None, anaglyph_percent=100, inverted_stereo=False, \
        title="", parallax_label="", inverted_stereo_label="", autoshow=True, parent=None):
        """ Inicialització del diàleg "about", cal informar de:
            - layer_name: capa a modificar
            Opcionalment:
            - update_callback: funció a cridar quan s'actualitzen les opcions
            - anaglyph_percent: Valor inicial de l'anaglif
            - inverted_stereo: Valor inicial de l'estèreo invertit
            - title: Títol del diàleg
            - parallax_label: Etiqueta anaglif
            - inverted_stereo_label: Etiqueta estèreo invertit
            - autoshow: Mostra el diàleg automàticament al crear-lo
            - parent: Especifica la finestra pare del diàleg
            ---
            Initialization of the "about" dialog, you need to report:
            - layer_name: layer to modify
            Optionally:
            - update_callback: callback function to call when options are modified
            - anaglyph_percent: Anaglyph initial value
            - inverted_stereo: Inverted stereo initial value
            - title: Title of the dialog
            - parallax_label: Anaglyph label
            - inverted_stereo_label: Inverted stereo label
            - autoshow: Show the dialog automatically when you create it
            - parent: Specifies the parent window of the dialog
            """
        super().__init__(parent)
        self.setupUi(self)

        # Ens guardem la funció de callback si executar algun procés extern
        self.update_callback = update_callback
        # Configurem un temporizador per fer un refresc retardat a l'utilitzar el slider
        self.parallax_timer = QTimer()
        self.parallax_timer.timeout.connect(lambda:self.on_parallax_changed(delayed=0))

        # Canviem el títol
        if title:
            self.setWindowTitle(title)
        if layer_name:
            self.update_title(layer_name)
        # Canviem etiquetes si cal
        if parallax_label:
            self.update_parallax_label(anaglyph_percent, parallax_label)
        if inverted_stereo_label:
            self.checkBox_inverted_stereo.setText(inverted_stereo_label)
        if inverted_stereo:
            self.checkBox_inverted_stereo.setChecked(Qt.Checked if inverted_stereo else Qt.Unchecked)

        # Mostrem el diàleg
        if autoshow:
            self.show()

    def update_title(self, layer_name):
        """ Actualitze el títol del diàleg amb el nom de la capa relacionada """
        title = self.windowTitle().split(":")[0]
        self.setWindowTitle("%s: %s" % (title, layer_name))

    def update_parallax_label(self, value=None, label=None):
        """ Actualitza el valor de la etiqueta de paral·laxi """
        label_parts = self.label_parallax.text().split(": ")
        if not label:
            label = label_parts[0]
        percent = ("%+d%%" % (value - 100)) if value is not None else label_parts[1]
        self.label_parallax.setText("%s: %s" % (label, percent))

    def set_callback(self, update_callback):
        """ Actualitza la crida de refresc extern """
        self.update_callback = update_callback

    def set_enabled(self, enable=True):
        """ Activa o desactiva tots els controls del diàleg """
        self.label_parallax.setEnabled(enable)
        self.horizontalSlider_parallax.setEnabled(enable)
        self.checkBox_inverted_stereo.setEnabled(enable)
        self.label_begin.setEnabled(enable)
        self.label_end.setEnabled(enable)
        # Canviem el color de la barra del slider i el títol del diàleg quan està desactivat
        self.horizontalSlider_parallax.setStyleSheet("" if enable else "selection-background-color: gray")
        self.setStyleSheet("" if enable else "color: gray")

    def set_anaglyph(self, parallax, inverted_stereo):
        """ Assigna valors a les opcions del diàleg """
        self.horizontalSlider_parallax.setValue((parallax - 80) / 4)
        self.checkBox_inverted_stereo.setChecked(Qt.Checked if inverted_stereo else Qt.Unchecked)

    def get_parallax(self):
        """ Retornem el valor de parallax enter entre 80 i 120 (tant per cent)"""
        return self.horizontalSlider_parallax.value() * 4 + 80

    def is_inverted_stereo(self):
        """ Retornem el valor d'estèreo invertid """
        return self.checkBox_inverted_stereo.checkState() == Qt.Checked

    def on_inverted_stereo(self, inverted):
        if self.update_callback:
            self.update_callback(self.get_parallax(), inverted)

    def on_parallax_changed(self, value=None, delayed=1000):
        parallax = self.get_parallax()
        self.update_parallax_label(parallax)
        # Refresh visualization delayed (to avoid excessive refresh events)
        if self.update_callback:
            if delayed:
                self.parallax_timer.start(delayed)
            else:
                self.parallax_timer.stop()
                self.update_callback(parallax, self.is_inverted_stereo())
