# encoding: utf-8
"""
*******************************************************************************
Mòdul amb funcions de gestió de logs de plugin
---
Module with management of plugin logs

                             -------------------
        begin                : 2022-08-31
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os
import html
import logging
import sys
import traceback
from qgis.core import QgsApplication, Qgis
from PyQt5.QtWidgets import QDockWidget, QDialog, QTabWidget, QTabBar, QStackedWidget


class QGISHandler(logging.Handler):
    """ Classe per connextar el logger de QGIS amb el sistema de logging estàndar de python 
        --- 
        Class to connext QGIS logger with standard python logging system
        """
    level_dict = {
        logging.NOTSET: Qgis.Info,
        logging.DEBUG: Qgis.Info,
        logging.INFO: Qgis.Info,
        logging.WARNING: Qgis.Warning,
        logging.ERROR: Qgis.Critical,
        logging.CRITICAL: Qgis.Critical,
        }

    def __init__(self, log_name):                
        super().__init__()
        self.log_name = log_name
        self.message_logger = QgsApplication.instance().messageLog()
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        message_text = html.escape(self.format(record))
        level = self.level_dict[record.levelno]
        self.message_logger.logMessage(message_text, self.log_name, level)


class PluginLogger():
    """ Classe de gestió de missatges de log
        ---
        Log message manager class
        """
    def __init__(self, plugin):
        """ Initialize logger class with two logger handlers, first for show messages on QGIS log window and other
            to store log messages in a file """
        self.plugin = plugin

        # Configurem el logger de QGIS per utilitzar una subfinestra amb el nom del plugin
        self.logger = logging.getLogger(self.plugin.plugin_id)

        # Configurem logs per mostrar en la fistra de log de QGIS i per guardar en un fitxer "<nom_plugin>.log"
        # en el path del plugin
        self.qgis_handler = QGISHandler(self.plugin.metadata.get_name())
        self.logger.addHandler(self.qgis_handler)
        # Intentem crear el fitxer de log en la carpeta del plugin i si no el la carpeta per defecte de plugins de QGIS
        log_path_list = [self.plugin.plugin_path, 
            os.path.join(QgsApplication.instance().qgisSettingsDirPath(), "python", "plugins")]
        for log_path in log_path_list:    
            self.log_filename = os.path.join(log_path, "%s.log" % self.plugin.plugin_id)
            try:
                self.file_handler = logging.FileHandler(self.log_filename, mode='w')
                self.logger.addHandler(self.file_handler)
                break
            except:
                self.log_filename = None
                self.file_handler = None
        
        # Configurem el format dels logs a dist i el nivell de log en general
        self.setFormat()
        self.setLevel()

    def setFormat(self, format="%(asctime)s\t%(levelname)s\t%(message)s"): #\t%(pathname)s line:%(lineno)d %(funcName)s"):
        """ Configure log file info format """
        if self.file_handler:
           self.file_handler.setFormatter(logging.Formatter(format))

    def setLevel(self, level=logging.WARNING):
        """ Configure level of message to register
            Uses standard python logging levels:
            logging.CRITICAL
            logging.ERROR
            logging.WARNING
            logging.INFO
            logging.DEBUG
            logging.NOTSET """
        if self.logger:
            self.logger.setLevel(level)
        if self.file_handler:
            self.file_handler.setLevel(level)
        if self.qgis_handler:
            self.qgis_handler.setLevel(level)
    
    def debug(self, message, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, stack_trace=True, **kwargs):
        if stack_trace:
            message += "\n" + "".join(traceback.format_stack()[:-1]).strip()
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, stack_trace=True, **kwargs):
        if stack_trace:
            message += "\n" + "".join(traceback.format_stack()[:-1]).strip()
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        self.logger.exception(message, *args, **kwargs)

    def getLogText(self, file_not_qgis=True):
        """ Gets log messages text from QGIS log or log file """
        if file_not_qgis:
            if self.log_filename:
                with open(self.log_filename, "r") as file_handler:
                    log_text = file_handler.read()
            else:
                log_text = ""
        else:
            if self.qgis_handler:
                dw = self.plugin.iface.mainWindow().findChild(QDockWidget, "MessageLog")
                d = dw.findChild(QDialog, "QgsMessageLogViewer")
                tw = d.findChild(QTabWidget, "tabWidget")
                tb = tw.findChild(QTabBar, 'qt_tabwidget_tabbar')
                plugin_index = [tb.tabText(i) for i in range(tb.count())].index(self.qgis_handler.log_name)
                sw = tw.findChild(QStackedWidget, 'qt_tabwidget_stackedwidget')
                pt = sw.widget(plugin_index)
                log_text = pt.toPlainText()
            else:
                log_text = ""
        return log_text

    def getLogFilename(self):
        """ Return log filename """
        return self.log_filename
    
    def remove(self):
        """ Remove handlers """
        if self.file_handler:
            self.file_handler.close()
        self.logger.handlers.clear()
        self.logger = None


if __name__ == '__main__':
    pass
