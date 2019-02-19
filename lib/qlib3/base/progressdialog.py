# encoding: utf-8
"""
MODULE: progressdialog.py
Funcions per fer progress o working bars en diàlegs
"""


import datetime
import time
import threading
import operator

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog, QProgressBar, QApplication


def get_main_window():
    # QGIS té MÉS D'UNA MAINWINDOW (La finestra principal i els reports de mapes...)
    # Per distinguir-los, de moment utilitzo el nombre de fills que té cada un i ens quedem amb el que en té més (la finestra principal...)
    main_window = max([(w, len(w.children())) for w in QApplication.instance().topLevelWidgets() if w.inherits("QMainWindow")] , key=operator.itemgetter(1))[0]
    return main_window

def process_events():
    QApplication.instance().processEvents()

class ProgressDialog(object):
    def __init__(self, label, num_steps, title = "Processing...", cancel_button_text = None, autoclose = True, time_info = "Elapsed %s. Remaining %s", parent = None):
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
                        ##print "minimize"
                        parent.setWindowState(Qt.WindowMinimized)
                    else:
                        ##print "restore"
                        parent.setWindowState(Qt.WindowNoState)
                elif event.type() == event.Close:
                    ##print "close"
                    pass
                elif event.type() == event.Hide:
                    ##print "hide"
                    pass
            def closeEvent(self, event):
                ##print "close2"
                pass
            def reject(self):
                ##print "reject"
                pass
            def cancel(self):
                ##print "cancel"
                pass
            def canceled(self):
                ##print "canceled"
                pass
        self.dlg = MyQProgressDialog(label + "\n", cancel_button_text, 0, num_steps, self.parent, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowMinimizeButtonHint)

        # Configurem el diàleg
        self.dlg.setWindowState(Qt.WindowNoState if self.parent != None and not self.parent.isMinimized() else Qt.WindowMinimized)
        self.dlg.setWindowModality(Qt.WindowModal)
        self.dlg.setWindowTitle(title)
        self.dlg.setAutoClose(autoclose)
        self.dlg.setValue(0)

        # Obtinc un apuntador a la barra de progres
        self.bar = [c for c in self.dlg.children() if type(c) == QProgressBar][0]

        # Mostrem el di``aleg
        self.show();

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def show(self):
        self.time_begin = datetime.datetime.now()
        self.time_last = self.time_begin
        self.time_average = datetime.timedelta(0)
        if self.parent_was_enabled:
            self.parent.setEnabled(False)
            ##print "Disabled!", self.parent, self.parent.windowTitle()
        self.dlg.setEnabled(True)
        self.dlg.show()
        self.app.processEvents()

    def close(self):
        self.app.processEvents()
        self.dlg.hide()
        self.dlg.close()
        self.__post_close__()

    def __post_close__(self):
        if self.parent_was_enabled:
            self.parent.setEnabled(True)
            ##print "Enabled!", self.parent, self.parent.windowTitle()
        self.app.processEvents()

    def set_steps(self, num_steps):
        self.dlg.setMaximum(num_steps)

    def set_value(self, value):
        self.dlg.setValue(value)
        self.update_time()
        self.app.processEvents()
        # Quan es tanca sol el diàleg de progress ens podem deixar el programa bloquejat, això ho eivtarà
        if self.autoclose and not self.dlg.isVisible():
            self.__post_close__()

    def get_value(self):
        return self.dlg.value()

    def step_it(self, steps = 1):
        self.set_value(self.get_value() + steps)

    def set_label(self, label):
        self.dlg.setLabelText("%s\n%s" % (label, self.get_time_info()))
        self.app.processEvents()

    def get_label(self):
        full_label = self.dlg.labelText()
        return full_label[:full_label.rfind('\n')]
        ##label_parts = self.dlg.labelText().split('\n')
        ##return "\n".join(label_parts[0:len(label_parts) - 1] if len(label_parts) > 1 else label_parts)

    def was_canceled(self):
        self.app.processEvents()
        return self.dlg.wasCanceled()

    def update_time(self):
        self.time_last = datetime.datetime.now()
        self.set_label(self.get_label()) # Força actualitzar el temps

    def get_begin_time(self):
        return self.time_begin

    def get_last_time(self):
        return self.time_last

    def get_elapsed_time(self):
        return self.time_last - self.time_begin

    def get_average_time(self):
        values = self.get_value()
        if values < 0:
            values = self.dlg.maximum()
        elapsed = self.get_elapsed_time()
        if not elapsed or not values:
            return datetime.timedelta(0)
        return elapsed / values

    def get_time_info(self):
        if self.dlg.maximum():
            return self.time_info % (self.get_delta_info(self.get_elapsed_time()), self.get_delta_info(self.get_remaining_time()))
        else:
            return self.time_info % (self.get_delta_info(self.get_elapsed_time()))

    def get_delta_info(self, delta):
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

    def get_remaining_time(self):
        return self.get_average_time() * (self.dlg.maximum() - self.get_value())

class WorkingDialog(ProgressDialog):
    def __init__(self, label, title = "Processing...", cancel_button_text = None, autoclose = True, time_info = "Elapsed %s"):
        # Creem un progressdialog amb nombre de passos 0
        super(self.__class__, self).__init__(label, 0, title, cancel_button_text, autoclose, time_info)
        # Amaguem el percentatge de la progressbar
        self.bar.setTextVisible(False)

def execute_fx_with_workingbar(fx, label, title = u"Processant...", cancel_button_text = None):
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
