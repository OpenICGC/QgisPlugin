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

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QDockWidget

from .qtextra import QtExtra

Ui_TimeSeries, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_timeseries.ui'))


class TimeSeriesDialog(QDockWidget, Ui_TimeSeries):
    """ Classe diàleg per mostrar opcions de sèries temporals
        ---
        Class dialog to display temporal series options
        """

    layer = None
    time_series_list = []

    def __init__(self, time_series_list, current_time, layer_name, simplify_begin_end=False,
        update_callback=None, title_prefix=None, current_prefix="", parent=None, autoshow=True):
        """ Inicialització del diàleg "about", cal informar de:
            - title: Títol del diàleg
            - layer: capa a modificar
            - time_series_list: Llista de dates disponibles
            Opcionalment:
            - parent: Especifica la finestra pare del diàleg
            - autoshow: Mostra el diàleg automàticament al crear-lo
            ---
            Initialization of the "about" dialog, you need to report:
             - title: Title of the dialog
             - layer: layer to modify
             - time_series_list: List of available dates
            Optionally:
             - parent: Specifies the parent window of the dialog
             - autoshow: Show the dialog automatically when you create it
            """
        super().__init__(parent)
        self.setupUi(self)
        # Canviem l'estil del QSlider per fer que surti la "fletxeta"
        QtExtra.forceQSliderArrowStyle(self.horizontalSlider)

        # Canviem el títol i la icona
        self.set_title_prefix(title_prefix)

        # Etiqueta opcional pel valors seleccionat
        self.set_current_prefix(current_prefix)

        # Configurem un timer per fer les actualitzacions amb retard (i evitar events molt seguits)
        self.timer_delay = 500
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)

        # Configurem els botons anterior i següent
        self.toolButton_previous.clicked.connect(self.previous)
        self.toolButton_next.clicked.connect(self.next)

        # Carreguem la sèrie temporal
        self.blockSignals(True)
        self.set_time_series(time_series_list, current_time, layer_name, simplify_begin_end, update_callback)
        self.blockSignals(False)

        # Mostrem el diàleg
        if autoshow:
            self.show()

    def set_title_prefix(self, title):
        self.title = title
        if title:
            self.setWindowTitle(title)

    def set_current_prefix(self, current_prefix):
        self.current_value_prefix = current_prefix
        self.label_current.setText(self.current_value_prefix)

    def set_time_series(self, time_series_list, current_time, layer_name, simplify_begin_end, update_callback, separator="-"):
        # Ens guardem la funció d'actualització de dades
        self.update_callback = update_callback

        # Actualitzem el títol amb el nom de la capa
        self.set_title(layer_name)

        # Ens guardem les sèries temporals disponibles
        self.time_series_list = time_series_list

        # Assignem les etiquetes inici i fi
        if simplify_begin_end:
            begin_parts = time_series_list[0].split(separator)
            for value in begin_parts:
                if value.isdigit():
                    self.label_begin.setText(value)
                    break
            end_parts = time_series_list[-1].split(separator)[::-1]
            for value in end_parts:
                if value.isdigit():
                    self.label_end.setText(value)
                    break
        else:
            self.label_begin.setText(time_series_list[0])
            self.label_end.setText(time_series_list[-1])
        # Assignem el valor actual al label
        self.label_current.setText(self.current_value_prefix + current_time)

        # Assignem el slider
        self.horizontalSlider.setTickInterval(1)
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(len(time_series_list) - 1)
        self.set_current_time(current_time)

    def set_title(self, layer_name):
        self.setWindowTitle("%s: %s" % (self.title, layer_name))

    def set_current_time(self, current_time):
        # Canviem el valor quan és diferent de l'actual
        new_value = self.time_series_list.index(current_time)
        if self.horizontalSlider.value() != new_value:
            return self.horizontalSlider.setValue(new_value)

    def get_current_time(self):
        # Retornem el valor actual de la llista de time series
        return self.time_series_list[self.horizontalSlider.value()]

    def on_value_changed(self, value=None):
        # Si entra per event de soltar slider, no tindrem "value", per això no el faig servir
        # Modifiquem el label de temps actual
        self.label_current.setText(self.current_value_prefix + self.get_current_time())

        # Volem detectar només events de click o de soltar el slider
        if not self.horizontalSlider.isSliderDown():
            # Activem el refresc retardat
            self.timer.start(self.timer_delay)

    def previous(self):
        current_index = self.horizontalSlider.value()
        if current_index > 0:
            self.set_current_time(self.time_series_list[current_index - 1])

    def next(self):
        current_index = self.horizontalSlider.value()
        if current_index < len(self.time_series_list) - 1:
            self.set_current_time(self.time_series_list[current_index + 1])

    def update(self):
        # Aturem el temporitzador de refresc retardat
        self.timer.stop()
        # Modifiquem la capa referenciada
        if self.update_callback:
            new_layer_name = self.update_callback(self.get_current_time())
            if new_layer_name:
                self.set_title(new_layer_name)

    def set_enabled(self, enable=True):
        # Activa o desactiva la barra temporal
        self.horizontalSlider.setEnabled(enable)
        self.label_begin.setEnabled(enable)
        self.label_end.setEnabled(enable)
        self.label_current.setEnabled(enable)
        # Canviem el color de la barra del slider i el títol del diàleg quan està desactivat
        self.horizontalSlider.setStyleSheet("" if enable else "selection-background-color: gray")
        self.setStyleSheet("" if enable else "color: gray")
