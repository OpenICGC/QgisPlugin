# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb una classe diàleg per mostrar una pàgina web
---
                             -------------------
        begin                : 2021-03-02
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

from PyQt5.QtCore import QUrl
from PyQt5.QtWebKitWidgets import QWebView, QWebPage
from PyQt5.QtWebKit import QWebSettings

class MiniWebBrowser(QWebView):
    def __init__(self):
        # QWebView
        self.view = QWebView.__init__(self)
        self.setWindowTitle('Loading...')
        self.titleChanged.connect(self.adjustTitle)

    def adjustTitle(self):
        self.setWindowTitle(self.title())

    def disableJS(self):
        settings = QWebSettings.globalSettings()
        settings.setAttribute(QWebSettings.JavascriptEnabled, False)

    def load(self, url, show=True):
        self.setUrl(QUrl(url))
        if show:
            self.activateWindow()
            self.show()
