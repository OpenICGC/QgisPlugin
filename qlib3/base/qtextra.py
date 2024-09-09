# -*- coding: utf-8 -*-
"""
Module with extra QT functionalies 
"""

from PyQt5.QtWidgets import QApplication, QStyleFactory, QCommonStyle


class QtExtra:
    @staticmethod
    def changeStyle(widget, style_or_style_list): #, overwrite_style=None):
        """ Change style widget from style name o style name list. overwrite_style filter current style to do change """
        # Gets desired style 
        desired_style_list = style_or_style_list if type(style_or_style_list) is list else [style_or_style_list]
        
        # ATENCIÓ SI INTENTO OBTENIR L'ESTIL ACTIU SI ALGÚ ACTIVA EL "MODE FOSC" DE QGIS LA CRIDa  app.style().baseStyle().objectName() PETA!!
        # Gets current style (Gets widget style or default app style)
        #app = QApplication.instance()
        #app_default_style = app.style().objectName() if type(app.style()) is QCommonStyle else app.style().baseStyle().objectName()
        #widget_style = widget.style().objectName()        
        #current_style = widget_style or app_default_style            
        # if not overwrite_style or current_style == overwrite_style.lower():
        
        # Apply new style if it is available
        available_styles_list = QStyleFactory.keys()
        for desired_style in desired_style_list:
            if desired_style in available_styles_list:
                widget.setStyle(QStyleFactory.create(desired_style))
                return True
        return False

    @staticmethod
    def forceQSliderArrowStyle(slider):
        return QtExtra.changeStyle(slider, ["windowsvista", "Windows"]) #, "Fusion")
