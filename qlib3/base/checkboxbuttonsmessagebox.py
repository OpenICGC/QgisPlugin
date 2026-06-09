# -*- coding: utf-8 -*-

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *


def show_checkboxbuttons_messagebox(icon, title, text, standard_buttons, extra_checkbuttons_title_list, parent, flags = Qt.WindowType.Dialog | Qt.WindowType.MSWindowsFixedSizeDialogHint):
    # Creem un objecte diàleg Yes/No
    # QMessageBox(QMessageBox.Icon, QString, QString, QMessageBox.StandardButtons buttons=QMessageBox.NoButton, QWidget parent=None, Qt.WindowFlags flags=Qt.Dialog|Qt.MSWindowsFixedSizeDialogHint): argument 4 has unexpected type 'list'
    mb = QMessageBox(icon, title, text, standard_buttons, parent, flags)

    # Creem els checks addicionals i els vinculem al diàleg
    cbbs = []
    for cbb_title in extra_checkbuttons_title_list:
        cbb = QCheckBox(cbb_title, mb)
        cbb.blockSignals(True)
        mb.addButton(cbb, QMessageBox.ButtonRole.ActionRole)
        cbbs.append(cbb)

    # Mostrem el diàleg
    dialog_status = mb.exec()

    # Recuperem el valors dels checks
    check_status_list = [cbb.isChecked() for cbb in cbbs]

    return dialog_status, tuple(check_status_list)
