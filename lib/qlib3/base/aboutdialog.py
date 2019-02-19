# -*- coding: utf-8 -*-
"""
    Diàleg per mostrar informació multiliniea
"""


import os
import win32clipboard as clipboard
import utilities.email

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFontMetrics, QPixmap
from PyQt5.QtWidgets import QStyle, QDialogButtonBox, QDialog, QApplication

ui_about, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_about.ui'))


class AboutDialog(QDialog, ui_about):
    def __init__(self, app_name, app_icon, info, autoshow=True, parent=None, new_line="  "):
        QDialog.__init__(self, parent)
        self.setupUi(self)        
        self.ui = self # Per compatibilitat QGIS2/3

        # Canviem el títol i la icona
        title = self.windowTitle()
        self.setWindowTitle(title % app_name)
        self.setWindowIcon(app_icon)

        # Escalem la imatge de logo mantenint proporcions
        self.label_banner.setScaledContents(False)
        self.label_banner.setAlignment(Qt.AlignCenter)
        self.pixmap_banner = QPixmap(self.label_banner.pixmap())
        self.resize_banner()

        # Carreguem la informació
        self.label_info.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.label_info.setWordWrap(True);
        self.label_info.setText("\n" + info.replace("  ", "\n"))

        # Mostrem el diàleg
        if autoshow:
            self.return_value = self.do_modal()

    def resizeEvent(self, newSize):
        self.resize_banner()

    def resize_banner(self):
        self.label_banner.setPixmap(self.pixmap_banner.scaled(self.label_banner.width(), self.label_banner.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def do_modal(self):
        self.show()
        self.return_value = self.exec_()
        return self.return_value
