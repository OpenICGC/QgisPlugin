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
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QDockWidget, QSlider, QApplication, QStyleOptionSlider, QToolTip

Ui_TimeSeries, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_timeseries.ui'))


#class MySlider(QSlider):
#    def __init__(self, parent=None):
#        super().__init__(parent)
#        self.style = QApplication.style()
#        self.opt = QStyleOptionSlider()
#        self.tip_offset = QPoint(10, 10)
#        self.valueChanged.connect(self.show_tip)
#        #self.enterEvent = self.show_tip
#        #self.mouseReleaseEvent = self.show_tip

#    def paintEvent(self, event):
#        """Paint log scale ticks"""
#        super().paintEvent(event)
#        qp = QPainter(self)
#        pen = QPen()
#        pen.setWidth(2)
#        pen.setColor(Qt.black)

#        qp.setPen(pen)
#        font = QFont('Times', 10)
#        font_y_offset = font.pointSize()/2
#        qp.setFont(font)
#        size = self.size()
#        contents = self.contentsRect()
#        db_val_list =   [10, 5, 0, -5, -10, -20, -30, -40, -50, -60, -90]
#        for val in db_val_list:
#            if val == 10:
#                y_val_fudge = 12
#            elif val == -90:
#                y_val_fudge = -12
#            ##db_scaled = db_to_int(val)
#            db_scaled = int(val)
#            y_val = contents.height() - translate(db_scaled, 0, 1023, 0, contents.height())
#            if val == -90:
#                qp.drawText(contents.x() - font.pointSize(), y_val + font_y_offset + y_val_fudge, '-oo')
#            else:
#                qp.drawText(contents.x() - font.pointSize(), y_val + font_y_offset + y_val_fudge,'{0:2}'.format(val))
#            qp.drawLine(contents.x() + font.pointSize(), y_val + y_val_fudge,  contents.x() + contents.width(), y_val + y_val_fudge)

#    def show_tip(self, _):
#        #self.initStyleOption(self.opt)
#        #rectHandle = self.style.subControlRect(self.style.CC_Slider, self.opt, self.style.SC_SliderHandle, self)
#        rectHandle = self.style.subControlRect(self.style.CC_Slider, None, self.style.SC_SliderHandle, self)
#        pos_local = rectHandle.topLeft() + self.tip_offset
#        pos_global = self.mapToGlobal(pos_local)
#        QToolTip.showText(pos_global, str(self.value()), self)

class TimeSeriesDialog(QDockWidget, Ui_TimeSeries):
    """ Classe diàleg per mostrar informació bàsica del plugin i logo el ICGC
        ---
        Class to display basic information of plugin and ICGC logo
        """

    layer = None
    time_series_list = []

    def __init__(self, time_series_list, current_time, layer_name, update_callback=None, title=None, current_label="", autoshow=True, parent=None):
        """ Inicialització del diàleg "about", cal informar de:
            - title: Títol del diàleg
            - layer: capa a modificar
            - time_series_list: Llista de dates disponibles
            Opcionalment:
            - autoshow: Mostra el diàleg automàticament al crear-lo
            - parent: Especifica la finestra pare del diàleg
            ---
            Initialization of the "about" dialog, you need to report:
             - title: Title of the dialog
             - layer: layer to modify
             - time_series_list: List of available dates
             Optionally:
             - autoshow: Show the dialog automatically when you create it
             - parent: Specifies the parent window of the dialog
            """
        super().__init__(parent)
        self.setupUi(self)

        # Etiqueta opcional pel valors seleccionat
        self.current_value_prefix = current_label

        # Canviem el títol i la icona
        if title:
            self.setWindowTitle(title)
        # Carreguem la sèrie temporal
        self.set_time_series(time_series_list, current_time, layer_name, update_callback)

        # Mostrem el diàleg
        if autoshow:
            self.show()

    def set_time_series(self, time_series_list, current_time, layer_name, update_callback):
        # Ens guardem la funció d'actualització de dades
        self.update_callback = update_callback

        # Actualitzem el títol amb el nom de la capa
        self.set_title(layer_name)

        self.time_series_list = time_series_list
        # Assignem les etiquetes
        self.label_begin.setText(time_series_list[0])
        self.label_end.setText(time_series_list[-1])
        self.label_current.setText(self.current_value_prefix + current_time)
        # Assignem el slider
        ##self.horizontalSlider = MySlider(self.horizontalSlider)
        self.horizontalSlider.setTickInterval(1)
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(len(time_series_list) - 1)
        self.set_current_time(current_time)

    def set_title(self, layer_name):
        title = self.windowTitle().split(":")[0]
        self.setWindowTitle("%s: %s" % (title, layer_name))

    def set_current_time(self, current_time):
        # Canviem el valor quan és diferent de l'actual
        new_value = self.time_series_list.index(current_time)
        if self.horizontalSlider.value() != new_value:
            return self.horizontalSlider.setValue(new_value)

    def get_current_time(self):
        # Retornem el valor actual de la llista de time series
        return self.time_series_list[self.horizontalSlider.value()]

    def on_value_changed(self, value=None):
        # Modifiquem el label de temps actual
        # Si entra per event de soltar slider, no tindrem "value", per això no el faig servir
        self.label_current.setText(self.current_value_prefix + self.get_current_time())

        # Volem detectar només events de click o de soltar el slider
        if not self.horizontalSlider.isSliderDown():
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
