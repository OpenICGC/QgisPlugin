# encoding: utf-8
"""
*******************************************************************************
Mòdul amb funcions de gestió i informe d'errors
---
Module with management functions and reports of errors

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os
import traceback
import functools
import console # Consola QGIS
import qgis # Accés a QGIS
from qgis.core import Qgis, QgsMessageLog
from importlib import reload

from PyQt5.QtWidgets import QApplication, QPushButton

from . import loginfodialog
reload(loginfodialog)
from .loginfodialog import LogInfoDialog


class ErrorReportManager():
    """ Classe Gestor de missatges d'error per excepcions
        ---
        Error message manager class for exceptions
        """

    def __init__(self, dialog_title=u"Error",
        email_subject=u"Error", email_to="", email_cc="",
        console_last_lines=20,
        width=350, height=250, parent=None):
        """ Inicialització de la classe de gestió d'errors, cal especificar com serà el diàleg
            d'errors i si es permet enviar emails i a qui.
            - dialog_title: Títol del diàleg d'errors
            - email_subject: Títol dels emails d'informe d'errors
            - email_to: destinataris dels informes d'errors
            - email_cc: destinataris en copia dels informes d'errors
            - console_last_lines: Línies a capturar de la consola a l'enviar un informe d'errors
            - width & height: Mida del diàleg d'errors
            - parent: Finestra pare del diàleg d'errors
            ---
            Initialization of the class of management of errors, it is necessary to specify how will be the dialog
            of errors and if it is allowed to send emails and to whom.
            - dialog_title: Title of the error dialog
            - email_subject: Title of error reporting emails
            - email_to: recipients of error reports
            - email_cc: recipients in copy of bug reports
            - Console_last_lines: Lines to capture from the console when sending a bug report
            - width & height: Error dialog size
            - parent: dialog parent window
            """
        self.set_dialog(dialog_title, parent)
        self.set_email(email_subject, email_to, email_cc)
        self.set_size(width, height)
        self.set_console_last_lines(console_last_lines)

    def set_dialog(self, dialog_title, parent=None):
        """ Configura el títol i pare del diàleg d'errors
            ---
            Configure title and dialog parent window
            """
        self.dialog_title = dialog_title
        self.parent = parent

    def set_parent(self, parent=None):
        """ Configura el pare del diàleg d'errors
            ---
            Configure dialog parent window
            """
        self.parent = parent

    def set_size(self, width, height):
        """ Configura la mida del diàleg
            ---
            Configure dialog size
            """
        self.width = width
        self.height = height

    def set_email(self, email_subject, email_to, email_cc = ""):
        """ Configura els emails d'informe d'errors
            ---
            Configure error report emails
            """
        self.email_subject = email_subject
        self.email_to = email_to
        self.email_cc = email_cc

    def set_console_last_lines(self, console_last_lines = 20):
        """ Configura el nombre de linies de la consola a capturar en els informes d'errors
            ---
            Configure the number of console lines to capture in the bug reports
            """
        self.console_last_lines = console_last_lines

    def get_error_info(self):
        """ Obté informació de l'error. Captura informació de traceback, consola QGIS, accés a BBDD i capa seleccionada
            ---
            Obtain error information. Capture traceback information, QGIS console, db access and selected layer
            """
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
        """ Obté informació de l'excepció produïda i mostra un diàleg amb les dades de l'error
            ---
            Gets information about the exception produced and displays a dialog with the error data
            """
        msg = str(e)
        #msg = e.message
        #if not msg or type(msg) is not unicode and type(msg) is not str:
        #    msg = unicode(e)
        return self.manage_error(msg)

    def manage_error(self, message):
        """ Mostra un diàleg amb les dades de l'error, amb la possibilitat d'enviar informes per email
            ---
            Shows a dialog with the error data, with the possibility to send reports by email
            """
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

    def generic_handle_error(self, func):
        """ Funció que decora la gestió d'errors de manera genèrica
            ---
            Function that decorates error management in a generic way
            """
        def handle_error(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                QApplication.restoreOverrideCursor()
                self.manage_exception(e)
        return handle_error


###############################################################################
# Gestió d'error global, si es fan servir en dos plugins potser que
# matxaquin les adreces d'email o el destinatari del emails

error_report_manager = ErrorReportManager()

def generic_handle_error(func):
    """ Funció que decora la gestió d'errors de manera genèrica
        ---
        Function that decorates error management in a generic way
        """

    def handle_error(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            #iface = args[0].iface if args and args[0].__dict__.get('iface', None) else None
            error_report_manager.manage_exception(e)

    return handle_error


###############################################################################
# Gestió d'errors específica per QGIS
# Mostra la informació als panells de QGIS (MessageBar, StatusBar i MessageLog)

class QgisError(Exception):
    """ Classe d'error predefinida per mostrar missatge al MessageBar de QGIS
            message: missatge explicant la causa de l'error
            level: segons la gravetat (Qgis.Info, Qgis.Warning, Qgis.Critical)
            duration: temps que es mostra el missatge en segons. Per defecte no expira (0)
    """
    def __init__(self, message, level=Qgis.Critical, duration=0):
        self._message = message
        self._level = level
        self._duration = duration
    
    @property
    def message(self):
        return self._message
    
    @property
    def level(self):
        return self._level
    
    @property
    def duration(self):
        return self._duration
    

class CancelError(QgisError):
    """ L'usuari ha abortat intencionadament """
    def __init__(self, message="Operació cancel·lada per l'usuari."):
        super().__init__(message, level=Qgis.Info, duration=2)
    
class InputError(QgisError):
    """ L'usuari ha entrat dades invàlides """
    def __init__(self, message="Error de les dades d'entrada."):
        super().__init__(message, level=Qgis.Warning, duration=5)
    
class ProcessError(QgisError):
    """ Algun procés ha acabat malament (scripts gdal, qgis processing, subprocess...)"""
    def __init__(self, message="Error de procés."):
        super().__init__(message, level=Qgis.Critical, duration=0)

class DatabaseError(QgisError):
    """ Error llegint/escrivint a base de dades """
    def __init__(self, message="Error de base de dades."):
        super().__init__(message, level=Qgis.Critical, duration=0)


def qgis_show_traceback(parent, function, error_message, traceback_info):
    """ Mostra un missatge d'error no controlat al MessageBar.
        Afegeix un botó per si l'usuari vol printar el traceback a la consola
    """
    def on_button_pressed():
        """ Callback que printa el traceback a la consola de QGIS """
        parent.debug.show_console()
        print(traceback_info)
        
    # Crea la barra amb el missatge d'error
    widget = parent.iface.messageBar().createMessage(function, error_message)
    
    # Afegeix un botó a la barra per cridar el callback
    button = QPushButton(widget)
    button.setText("Vull veure més informació!")
    button.pressed.connect(on_button_pressed)
    widget.layout().addWidget(button)
    
    # Mostra la barra
    parent.iface.messageBar().pushWidget(widget, Qgis.Critical)
    
    
def qgis_handle_error(function):
    """ Decorador per gestionar excepcions d'un plugin de QGIS i informar de l'inici/final
    """
    @functools.wraps(function)
    def handle_error(*args, **kwargs):
        try:
            QgsMessageLog.logMessage(f"Procés '{function.__name__}' iniciat", 'Missatges', level=Qgis.Info)
            function(*args, **kwargs)
            status_message = f"Procés '{function.__name__}' finalitzat amb èxit."
        except QgisError as e:
            # Error controlat (InputError, ProcessError...)
            title = 'Info' if e.level==Qgis.Info else ('Atenció' if e.level==Qgis.Warning else 'Error')
            args[0].iface.messageBar().pushMessage(title, e.message, level=e.level, duration=e.duration)
            status_message = e.message
        except Exception as e:
            # Error inesperat (amb l'opció d'imprimir el traceback a posteriori)
            qgis_show_traceback(args[0], function.__name__, f"{type(e).__name__}: {e}", traceback.format_exc())
            status_message = f"Error inesperat a: '{function.__name__}'"
        finally:
            # Informem que el procés ha acabat
            args[0].iface.statusBarIface().showMessage(f"AtQ: {status_message}")
            QgsMessageLog.logMessage(f"Procés '{function.__name__}' finalitzat", 'Missatges', level=Qgis.Info)
        
    return handle_error
    


if __name__ == '__main__':
    # Test
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
