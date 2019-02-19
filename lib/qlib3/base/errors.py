# encoding: utf-8
import os
import traceback
import console # Consola QGIS
import qgis # Accés a QGIS
from importlib import reload
from PyQt5.QtWidgets import QApplication

from . import loginfodialog
reload(loginfodialog)
from .loginfodialog import LogInfoDialog


class ErrorReportManager():
    """ Gestor de missatges d'error per excepcions """

    def __init__(self, dialog_title = u"Error", 
        email_subject = u"Error", email_to ="" , email_cc = "", 
        console_last_lines = 20, 
        width = 350, height = 250):

        self.set_dialog(dialog_title)
        self.set_email(email_subject, email_to, email_cc)
        self.set_size(width, height)
        self.set_console_last_lines(console_last_lines)

    def set_dialog(self, dialog_title, parent = None):
        self.dialog_title = dialog_title
        self.parent = parent

    def set_size(self, width, height):
        self.width = width
        self.height = height

    def set_email(self, email_subject, email_to, email_cc = ""):
        self.email_subject = email_subject
        self.email_to = email_to
        self.email_cc = email_cc

    def set_console_last_lines(self, console_last_lines = 20):
        self.console_last_lines = console_last_lines

    def get_error_info(self):
        # Obtenim el traceback
        traceback_info = traceback.format_exc().strip()
        # Obtenim la consola
        console_info = u"...\n%s" % u"\n".join(console.console._console.console.shellOut.text().split('\n')[-self.console_last_lines:])
        # Obtenim informació de la BBDD
        host = os.environ.get('POSTGIS_HOST', None)
        db = os.environ.get('POSTGIS_DBNAME', None)
        db_info = u"host: %s, db: %s" % (host, db) if host or db else None
        # Obtenim informaicó de la capa activa
        layer = qgis.utils.iface.mapCanvas().currentLayer()
        layer_name = layer.name() if layer else None
        selected_features = (u", ".join([unicode(feature.id()) for feature in layer.selectedFeatures()])) if layer and 'selectedFeatures' in dir(layer) else None
        layer_info = u"layer: %s, selection obj id: %s" % (layer_name, selected_features) if layer else None        

        return traceback_info, console_info, db_info, layer_info

    def manage_exception(self, e):
        msg = str(e)
        #msg = e.message
        #if not msg or type(msg) is not unicode and type(msg) is not str:
        #    msg = unicode(e)
        return self.manage_error(msg)

    def manage_error(self, message):
        # Obtenim informació de l'error
        trace_back_info, console_info, db_info, layer_info = self.get_error_info()
        
        # Preparem un missatge d'error per mostrar a pantalla
        extra_info = "[ERROR:]\n%s\n\n[TRACE:]\n%s\n\n[QGIS CONSOLE:]\n%s" % (message, trace_back_info, console_info.strip())
        if(db_info):
            extra_info += "\n\n[DB:]\n%s" % db_info
        if layer_info:
            extra_info += "\n\n[LAYER:]\n%s" % layer_info
        
        # Preparem un missatge d'error per l'email
        email_info = """
            <B>ERROR:</B><BR/>
            %s<BR/><BR/>
            <B>TRACE:</B><BR/>
            %s<BR/><BR/>
            <B>QGIS CONSOLE:</B><BR/>
            %s""" % (message.replace("\n", "<BR/>"), trace_back_info.replace("\n", "<BR/>"), console_info.replace("\n", "<BR/>"))
        if(db_info):
            email_info += "<BR/><B>DB:</B><BR/>%s<BR/>" % db_info
        if layer_info:
            email_info += "<BR/><B>LAYER:</B><BR/>%s<BR/>" % layer_info
        
        # Mostrem un diàleg amb la informació
        dlg = LogInfoDialog(
            message, extrainfo_or_tupleextrainfolist = extra_info, extrainfohtml_or_tupleextrainfohtmllist = email_info,
            title = self.dialog_title, mode = LogInfoDialog.mode_error, 
            buttons = LogInfoDialog.buttons_ok, save_button_text = u"Guardar",
            email_button_text = u"Reportar", email_subject = self.email_subject, email_to = self.email_to, email_cc = self.email_cc,
            width = self.width, height = self.height, parent = self.parent
            )

error_report_manager = ErrorReportManager()

def generic_handle_error(func):
    """ Funció que decora la gestió d'errors de manera genèrica"""

    def handle_error(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:     
            QApplication.restoreOverrideCursor()       
            #iface = args[0].iface if args and args[0].__dict__.get('iface', None) else None
            error_report_manager.manage_exception(e)

    return handle_error


if __name__ == '__main__':
    ermanager = ErrorReportManager()
    ermanager.set_email("Prova exception manager", "albert.adell@icgc.cat")

    try:
        1/0
    except Exception as e:        
        #message, trace_back_info, console_info = get_exception_info(e)
        #print "Message:", message, "\n"
        #print "Trace:", trace_back_info, "\n"
        #print "Console:", console_info
        ermanager.manage_exception(e)
