# encoding: utf-8
"""
*******************************************************************************
Mòdul amb funcions i classes fer gestionar diàlegs amb progress o working bars
---
Module with functions and classes to manage dialogs with progress or working
bars
                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import datetime
import time
import threading
import operator

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog, QProgressBar, QApplication


def get_main_window():
    """ Retorna una referència a la finestra principal de QGIS
        ---
        Returns a reference to the main QGIS window
        """
    # QGIS té MÉS D'UNA MAINWINDOW (La finestra principal i els reports de mapes...)
    # Per distinguir-los, de moment utilitzo el nombre de fills que té cada un i ens quedem amb el que en té més (la finestra principal...)
    main_window = max([(w, len(w.children())) for w in QApplication.instance().topLevelWidgets() if w.inherits("QMainWindow")] , key=operator.itemgetter(1))[0]
    return main_window

def process_events():
    QApplication.instance().processEvents()

class ProgressDialog(object):
    """ Classe diàleg amb progressbar, % i estimació de temps de finalització
        ---
        Dialog class with progressbar, % and end time estimate
        """

    def __init__(self, label, num_steps, title="Processing...", cancel_button_text=None, autoclose=True, time_info="Elapsed %s. Remaining %s", parent=None):
        """ Inicialitza un diàleg amb una progressbar a dins, cal indicar etiqueta a mostrar i nombre de passos de la barra.
            Opcionalment es pot especificar:
            - title: Títol del diàleg
            - cancel_button_text: Afegeix un botó de cancelació amb el text indicat
            - autoclose: indica si es tanca automàticament a l'arribar al 100% (activeu-lo per fer que la barra es mantingui plena quan arriba al 100%)
            - time_info: plantilla text amb la informació de temps transcorregut i restant (ha de portar 2 %s)
            - parent: finestra pare del diàleg
            ---
            Initializes a dialog with a progressbar inside, you must indicate the label to show and the number of steps in the bar.
            Optionally you can specify:
            - title: dialog title
            - cancel_button_text: add a cancellation button with the indicated text
            - autoclose: indicates if it is automatically closed when reaching 100% (set autoclose=True to ensure a full progress bar at 100%)
            - time_info: text template with the elapsed and remaining time information (requires 2 %s)
            - parent: parent window of the dialog
            """
        self.time_info = time_info
        self.app = QApplication.instance()
        self.parent = parent if parent else get_main_window()
        self.parent_was_enabled = self.parent.isEnabled() if self.parent else True
        self.autoclose = autoclose

        class MyQProgressDialog(QProgressDialog):
            def changeEvent(self, event):
                if event.type() == event.WindowStateChange:
                    parent = self.parent()
                    if not parent:
                        parent = get_main_window()
                    if self.isMinimized():
                        ##print("minimize")
                        parent.setWindowState(Qt.WindowMinimized)
                    else:
                        ##print("restore")
                        parent.setWindowState(Qt.WindowNoState)
            #    elif event.type() == event.Close:
            #        ##print("close")
            #        pass
            #    elif event.type() == event.Hide:
            #        ##print("hide")
            #        pass
            #def closeEvent(self, event):
            #    ##print("close2")
            #    pass
            #def reject(self):
            #    ##print("reject")
            #    pass
            #def cancel(self):
            #    ##print("cancel")
            #    pass
            #def canceled(self):
            #    ##print("canceled")
            #    pass
        self.dlg = MyQProgressDialog(label + "\n", cancel_button_text, 0, num_steps, self.parent, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint)

        # Configurem el diàleg
        self.dlg.setWindowState(Qt.WindowNoState if self.parent != None and not self.parent.isMinimized() else Qt.WindowMinimized)
        self.dlg.setWindowModality(Qt.WindowModal)
        self.dlg.setWindowTitle(title)
        self.dlg.setAutoClose(autoclose)
        #self.dlg.setValue(0)

        # Obtinc un apuntador a la barra de progres
        self.bar = [c for c in self.dlg.children() if type(c) == QProgressBar][0]

        # Inicialitza el progrés
        self.time_begin = datetime.datetime.now()
        self.time_prev = self.time_begin
        self.time_last = self.time_begin
        self.time_average = datetime.timedelta(0)
        self.set_value(0)

        # Mostrem el diàleg
        self.show()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def show(self):
        """ Mostra el diàleg i desactiva la finestra pare si cal
            ---
            Show the dialog and deactivate the parent window if necessary
            """
        if self.parent_was_enabled:
            self.parent.setEnabled(False)
            ##print "Disabled!", self.parent, self.parent.windowTitle()
        self.dlg.resize(400, self.dlg.height())
        self.dlg.setEnabled(True)
        self.dlg.show()
        self.app.processEvents()

    def close(self):
        """ Tanca el diàleg
            ---
            Close the dialog
            """
        self.app.processEvents()
        self.dlg.hide()
        self.dlg.close()
        self.__post_close__()

    def __post_close__(self):
        """ Desbloqueja la finestra pare
            ---
            Unlock parent window
            """
        if self.parent_was_enabled:
            self.parent.setEnabled(True)
            ##print "Enabled!", self.parent, self.parent.windowTitle()
        self.app.processEvents()

    def set_steps(self, num_steps):
        """ Especifica el nombre de passos de la progress bar
            ---
            Specify the passos name of the progress bar
            """
        self.dlg.setMaximum(num_steps)

    def set_value(self, value):
        """ Especifica la posició actual de progress bar
            ---
            Specify the current position of progress bar
            """
        self.dlg.setValue(value)
        self.update_time()
        self.app.processEvents()
        # Quan es tanca sol el diàleg de progress ens podem deixar el programa bloquejat, això ho evitarà
        if self.autoclose:
            if not self.dlg.isVisible():
                self.__post_close__()
            #if self.dlg.value() == self.dlg.maximum():
            #  self.close()

    def get_value(self):
        """ Retorna la posició actual de progress bar
            ---
            Get current position of progress bar
            """
        value = self.dlg.value()
        # Quan arriba al màxim, QProgressDialog reseteja el valor a -1. Ho arreglo
        return self.dlg.maximum() if value < 0 else value

    def step_it(self, steps=1):
        """ Avança la posició de la progressbar "steps" vegades
            ---
            Move progressbar position "steps" times
            """
        self.set_value(min(self.get_value() + steps, self.dlg.maximum()))

    def set_label(self, label):
        """ Canvia la etiqueta informativa del diàleg
            ---
            Change informative dialog label
            """
        self.dlg.setLabelText("%s\n%s %s" % (label, self.get_position_info(), self.get_time_info()))
        self.app.processEvents()

    def get_position_info(self):
        """ Retorna informació de la poció de la progresbar ens trobem
            ---
            Return progressbar position info
            """
        return ("(%d/%d) " % (self.get_value(), self.dlg.maximum())) if self.dlg.maximum() else ""

    def get_label(self):
        """ Retorna la etiqueta informativa del diàleg
            ---
            Get informative dialog label text
            """
        full_label = self.dlg.labelText()
        return full_label[:full_label.rfind('\n')]

    def was_canceled(self):
        """ Retorna si s'ha apretat el botó de cancelar
            ---
            Returns if the cancel button has been pressed
            """
        self.app.processEvents()
        return self.dlg.wasCanceled()

    def update_time(self):
        """ Actualitza l'estimació de temps per acabat i temps transcorregut cada 0.1 segons
            ---
            Update estimated time to finish and elapsed time every 0.1 seconds
            """
        self.time_last = datetime.datetime.now()
        if (self.time_last - self.time_prev) > datetime.timedelta(microseconds=100000):
            self.time_prev = self.time_last
            self.set_label(self.get_label()) # Força actualitzar el temps

    def get_begin_time(self):
        """ Retorna el temps d'inici de procés
            ---
            Returns the start time of the process
            """
        return self.time_begin

    def get_last_time(self):
        """ Retorna la última marca de temps registrada
            ---
            Returns the last recorded time
            """
        return self.time_last

    def get_elapsed_time(self):
        """ Retorna el temps transcorregut des de l'inici de procés
            ---
            Returns the time elapsed since the beginning of the process
            """
        return self.time_last - self.time_begin

    def get_average_time(self):
        """ Retorna el temps mig de procés per pas
            ---
            Returns the average time of process per step
            """
        values = self.get_value()
        elapsed = self.get_elapsed_time()
        if not elapsed or not values:
            return datetime.timedelta(0)
        return elapsed / values

    def get_remaining_time(self):
        """ Retorna el temps estima de finalització
            ---
            Returns estimated end time
            """
        return self.get_average_time() * (self.dlg.maximum() - self.get_value())

    def get_time_info(self):
        """ Retorna informació del temps transcorregut i temps restant
            ---
            Returns information about the time elapsed and the remaining time
            """
        if self.dlg.maximum():
            return self.time_info % (self.get_delta_info(self.get_elapsed_time()), self.get_delta_info(self.get_remaining_time()))
        else:
            # Ens assegurem de que només tenim un %s
            return self.time_info.split("%s")[0]+"%s" % (self.get_delta_info(self.get_elapsed_time()))

    def get_delta_info(self, delta):
        """ Formateja una diferència de temps
            ---
            Format a time difference
            """
        # Obtenim el temps
        h, remaining = divmod(delta.seconds, 3600)
        m, s = divmod(remaining, 60)
        # Construim un string amb el temps
        info = []
        if h:
            info.append(str(h))
        if m:
            info.append("%2d" % m if h else str(m))
        info.append("%2d" %s if m else str(s))
        # Obtenim les unitats
        ##if h:
        ##    suffix = "h"
        ##elif m:
        ##    suffix = "min"
        ##else:
        suffix = "s"
        # Retornem el temps am unitats
        return ":".join(info) + suffix

    def is_visible(self):
        """ Retorna si el diàleg és visible
            ---
            Returns that dialog is visible
            """
        return self.dlg and self.dlg.isVisible()


class WorkingDialog(ProgressDialog):
    """ Classe diàleg amb workingbar i informació de temps transcorregut
        ---
        Dialog class with workingbar and elapsed time information
        """

    def __init__(self, label, title="Processing...", cancel_button_text=None, autoclose=True, time_info="Elapsed %s", parent=None):
        """ Inicialitza un diàleg amb una workingbar a dins, cal indicar etiqueta a mostrar.
            Opcionalment es pot especificar:
            - title: Títol del diàleg
            - cancel_button_text: Afegeix un botó de cancelació amb el text indicat
            - autoclose: indica si es tanca automàticament a l'arribar al 100%
            - time_info: plantilla text amb la informació de temps transcorregut i restant (ha de portar 1 %s)
            - parent: finestra pare del diàleg
            ---
            Initializes a dialog with a progressbar inside, you must indicate the label to show and the number of steps in the bar.
            Optionally you can specify:
            - title: dialog title
            - cancel_button_text: add a cancellation button with the indicated text
            - Autoclose: indicates if it is automatically closed when reaching 100%
            - time_info: text template with the elapsed and remaining time information (requires 1 %s)
            - parent: parent window of the dialog
            """
        # Creem un progressdialog amb nombre de passos 0
        super(self.__class__, self).__init__(label, 0, title, cancel_button_text, autoclose, time_info, parent )
        # Amaguem el percentatge de la progressbar
        self.bar.setTextVisible(False)

def execute_fx_with_workingbar(fx, label, title = u"Processant...", cancel_button_text = None):
    """ Executa una funció obrint prèviament un working dialog i tancant-lo al finalitzar
        ---
        Run a function by opening a working dialog and closing it at the end
        """
    class FxReturn:
        return_value = None
        def run(self):
            self.return_value = fx() # Afaga fx com a global a la subfunció
    fx_return = FxReturn()

    with WorkingDialog(label, title, cancel_button_text) as progress:
        t1 = threading.Thread(target = fx_return.run)
        t1.start()
        while t1.is_alive() and not progress.was_canceled():
            progress.step_it()
            time.sleep(0.05)

    return fx_return.return_value


if __name__ == "__main__":
    pass
