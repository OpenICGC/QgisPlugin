# -*- coding: utf-8 -*-
"""
Module with extra QT functionalies 
"""

from PyQt5.QtWidgets import QApplication, QStyleFactory


class QtExtra:
    @staticmethod
    def changeStyle(widget, style_or_style_list, overwrite_style=None):
        """ Change style widget from style name o style name list. overwrite_style filter current style to do change """
        desired_styles_list = style_or_style_list if type(style_or_style_list) is list else [style_or_style_list]
        current_style = widget.style().objectName() or QApplication.instance().style().baseStyle().objectName()
        if not overwrite_style or current_style == overwrite_style.lower():
            available_styles_list = QStyleFactory.keys()
            for desired_style in desired_styles_list:
                if desired_style in available_styles_list:
                    widget.setStyle(QStyleFactory.create(desired_style))
                    return True
        return False

    @staticmethod
    def forceQSliderArrowStyle(slider):
        return QtExtra.changeStyle(slider, ["windowsvista", "Windows"], "Fusion")
