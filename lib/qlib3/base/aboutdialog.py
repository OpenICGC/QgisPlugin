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
import sys

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFontMetrics, QPixmap
from PyQt5.QtWidgets import QStyle, QDialogButtonBox, QDialog, QApplication

ui_about, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_about.ui'))


class AboutDialog(QDialog, ui_about):
    """ Classe diàleg per mostrar informació bàsica del plugin i logo el ICGC
        ---
        Class to display basic information of plugin and ICGC logo
        """

    def __init__(self, app_name, app_info, app_icon=None, title="Sobre", autoshow=True, new_line="  ", parent=None):
        """ Inicialització del diàleg "about", cal informar de:
            - app_name: Títol del diàleg
            - app_icon: Icona del diàleg
            - app_info: Informació a mostrar
            - title: Títol de la finestra
            Opcionalment:
            - autoshow: Mostra el diàleg automàticament al crear-lo
            - new_line: Caràcters a substituir per un canvi de linia
            - parent: Especifica la finestra pare del diàleg
            ---
            Initialization of the "about" dialog, you need to report:
             - app_name: Title of the dialog
             - app_icon: Icon of the dialog
             - app_info: Information to show
             - title: Window title
             Optionally:
             - autoshow: Show the dialog automatically when you create it
             - new_line: Characters to be replaced by a change of line
             - parent: Specifies the parent window of the dialog
            """
        QDialog.__init__(self, parent)
        self.setupUi(self)        
        self.ui = self # Per compatibilitat QGIS2/3

        # Canviem el títol i la icona
        if not title:
            title = self.windowTitle()
        self.setWindowTitle("%s %s" % (title, app_name))
        if app_icon and sys.platform == "win32":
            self.setWindowIcon(app_icon)

        # Escalem la imatge de logo mantenint proporcions
        self.label_banner.setScaledContents(False)
        self.label_banner.setAlignment(Qt.AlignCenter)
        self.pixmap_banner = QPixmap(self.label_banner.pixmap())
        self.resize_banner()

        # Carreguem la informació
        self.label_info.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.label_info.setWordWrap(True);
        self.label_info.setText("\n" + app_info.replace(new_line, "\n"))

        # Mostrem el diàleg
        if autoshow:
            self.return_value = self.do_modal()

    def resizeEvent(self, newSize):
        """ Mapeja l'event de canvi de mida del diàlog
            ---
            Map dialog size change event
            """
        self.resize_banner()

    def resize_banner(self):
        """ Reescala el "banner" (logo ICGC) a la mida del diàleg
            ---
            Resize banner (logo ICGC) to dialog size
            """
        self.label_banner.setPixmap(self.pixmap_banner.scaled(self.label_banner.width(), self.label_banner.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def do_modal(self):
        """ Mostra el diàleg en mode modal
            ---
            Show dialog on modal mode
            """
        self.show()
        self.return_value = self.exec_()
        return self.return_value
