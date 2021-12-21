# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb una classe diàleg per mostrar informació multilinia
---
Module with a dialog class to display multi-line information

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""


import os
try:
    import win32clipboard as clipboard
    clipboard_available = True
except:
    clipboard_available = False
try:
    import utilities.email
    email_available = True
except:
    email_available = False

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFontMetrics, QFont
from PyQt5.QtWidgets import QStyle, QDialogButtonBox, QDialog, QApplication, QFrame, QFileDialog, QMessageBox

ui_loginfo, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_loginfo.ui'))


class LogInfoDialog(QDialog, ui_loginfo):
    """ Classe diàleg per mostrar informació multilinia
        ---
        Dialog class to display multi-line information
        """

    mode_info = 0
    mode_warning = 1
    mode_error = 2

    buttons_none = 0
    buttons_ok = 1
    buttons_cancel = 2
    buttons_defcancel = 4
    buttons_okcancel = (buttons_ok | buttons_cancel)
    buttons_okcancel_defcancel = (buttons_ok | buttons_cancel | buttons_defcancel)
    buttons_yes = 8
    buttons_no = 16
    buttons_defno = 32
    buttons_yesno = (buttons_yes | buttons_no)
    buttons_yesno_defno = (buttons_yes | buttons_no | buttons_defno)

    def __init__(self, info_or_tupleinfolist,
            title=u"Informació de procés", mode=mode_info, buttons=buttons_ok,
            default_combo_selection=None,
            extrainfo_or_tupleextrainfolist=None, extrainfohtml_or_tupleextrainfohtmllist=None,
            email_button_text=None, email_subject=None, email_to=None, email_cc=None,
            save_button_text=None, copy_clipboard_button_text=None,
            autoshow=True, width=None, height=None, font_size=10, border=False, parent=None):
        """ Inicialització del diàleg, cal especificar paràmetre amb un text d'informació o amb una
            llista de tuples amb la informació. Opcionalment es pot especificar:
            - title: Títol del diàleg
            - mode: Mode del diàleg que canvia la icona a mostrar (mode_info, mode_warning, mode_error)
            - buttons: Màscara de botons a mostrar (buttons_ok, buttons_cancel, buttons_yes ...)
            - default_combo_selection: En cas de tenir una llista d'informacions, valor de la llista a mostrar per defecte
            - extrainfo_or_tupleextrainfolist: Informació addicional a mostrar (botó email + shift)
            - extrainfohtml_or_tupleextrainfohtmllist: Informació HTML addicional a mostrar (en emails)
            - email_button_text: Text del botó que serveix per enviar informes per email
            - email_subject: Asumpte del informes per email
            - email_to: Destinataris dels informes per email
            - email_cc: Destinataris en copia dels informes per email
            - save_button_text: Text del botó de guardar informació a fitxer
            - copy_clipboard_button_text: Text del botó per guardar informació al porta papers
            - autoshow: Mostra automàticament el diàleg al crear-lo
            - width: Amplada del diàleg
            - height: Alçada del diàleg
            - parent: Finestra pare del diàleg
            ---
            Initialization of the dialog, you need to specify a parameter with an information text or with a
            list of tuples with information. Optionally you can specify:
            - title: Dialog title
            - mode: Dialog mode that switches the icon to display (mode_info, mode_warning, mode_error)
            - buttons: Mask of buttons to show (buttons_ok, buttons_cancel, buttons_yes ...)
            - default_combo_selection: If you have a list of information, value of the list to be displayed by default
            - extrainfo_or_tupleextrainfolist: Additional information to show (email button + shift)
            - extrainfohtml_or_tupleextrainfohtmllist: Additional HTML information to show (in emails)
            - email_button_text: Text of the button used to send reports by email
            - email_subject: Subject of the reports by email
            - email_to: Receivers of the reports by email
            - email_cc: Receivers in copy of the reports by email
            - save_button_text: Text of the button to save information to file
            - copy_clipboard_button_text: Text of the button to save information to clipboard
            - autoshow: Automatically show the dialog when creating it
            - width: Dialog width
            - height: Dialog height
            - parent: Parent window of the dialog
            """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.ui = self # Per compatibilitat QGIS2/3

        # Canviem el títol i la icona
        self.setWindowTitle(title)
        if mode == self.mode_error:
            icon = QStyle.SP_MessageBoxCritical
        elif mode == self.mode_warning:
            icon = QStyle.SP_MessageBoxWarning
        else:
            icon = QStyle.SP_MessageBoxInformation
        self.setWindowIcon(self.style().standardIcon(icon))

        # Canviem la mida
        if height or width:
            if not height:
                height = self.geometry().height()
            if not width:
                width = self.geometry().width()
            self.resize(width, height)

        # Canviem els botons que mostrem
        qt_buttons = 0
        if buttons & self.buttons_ok:
            qt_buttons |= QDialogButtonBox.Ok
        if buttons & self.buttons_cancel:
            qt_buttons |= QDialogButtonBox.Cancel
        if buttons & self.buttons_yes:
            qt_buttons |= QDialogButtonBox.Yes
        if buttons & self.buttons_no:
            qt_buttons |= QDialogButtonBox.No
        self.ui.buttonBox.setStandardButtons(qt_buttons)
        if buttons & self.buttons_defcancel:
            self.ui.buttonBox.button(QDialogButtonBox.Cancel).setDefault(True)
        if buttons & self.buttons_defno:
            self.ui.buttonBox.button(QDialogButtonBox.No).setDefault(True)

        # Mostrem o no el botó de Save
        if save_button_text:
            self.ui.pushButton_save.setText(save_button_text)
            self.ui.pushButton_save.setMaximumWidth(QFontMetrics(self.ui.pushButton_save.font()).width(save_button_text) + 20)
            self.ui.pushButton_save.setEnabled(True)
            self.ui.pushButton_save.setVisible(True)
        else:
            self.ui.pushButton_save.setEnabled(False)
            self.ui.pushButton_save.setVisible(False)

        # Motrem el botó de copiar al portapapers
        if copy_clipboard_button_text:
            self.ui.pushButton_clipboard.setText(copy_clipboard_button_text)
            self.ui.pushButton_clipboard.setMaximumWidth(QFontMetrics(self.ui.pushButton_save.font()).width(copy_clipboard_button_text) + 20)
            self.ui.pushButton_clipboard.setEnabled(clipboard_available)
            self.ui.pushButton_clipboard.setVisible(True)
        else:
            self.ui.pushButton_clipboard.setEnabled(False)
            self.ui.pushButton_clipboard.setVisible(False)

        # Botó d'email
        if email_button_text:
            self.ui.pushButton_email.setText(email_button_text)
            self.ui.pushButton_email.setMaximumWidth(QFontMetrics(self.ui.pushButton_email.font()).width(email_button_text) + 20)
            self.ui.pushButton_email.setEnabled(email_available)
            self.ui.pushButton_email.setVisible(True)
        else:
            self.ui.pushButton_email.setEnabled(False)
            self.ui.pushButton_email.setVisible(False)
        self.email_subject = email_subject
        self.email_to = email_to
        self.email_cc = email_cc

        # Canviem el color i mida de la font de l'edit
        palette = self.ui.plainTextEdit.palette()
        palette.setColor(QPalette.Base, QColor('transparent'))
        self.ui.plainTextEdit.setPalette(palette)
        self.ui.plainTextEdit.setFont(QFont(self.ui.plainTextEdit.font().rawName(), font_size))
        if not border:
            self.ui.plainTextEdit.setFrameStyle(QFrame.NoFrame)

        # Carreguem les dades
        self.info_or_tupleinfolist = info_or_tupleinfolist
        self.extrainfo_or_tupleextrainfolist = extrainfo_or_tupleextrainfolist
        self.extrainfohtml_or_tupleextrainfohtmllist = extrainfohtml_or_tupleextrainfohtmllist
        if type(info_or_tupleinfolist) is list:
            self.index = 0
            self.tuple_list = info_or_tupleinfolist
            self.ui.comboBox.setVisible(True)
            self.ui.comboBox.setEnabled(len(info_or_tupleinfolist) > 1)
            if len(info_or_tupleinfolist) > 0 and len(info_or_tupleinfolist[0]) > 1:
                self.ui.comboBox.addItems([pair[0] for pair in info_or_tupleinfolist])
                combo_index = max(0, self.ui.comboBox.findText(default_combo_selection)) if default_combo_selection else 0
                self.ui.comboBox.setCurrentIndex(combo_index)
                self.ui.plainTextEdit.setPlainText(info_or_tupleinfolist[combo_index][1])
        elif type(info_or_tupleinfolist) is tuple:
            self.index = 0
            self.tuple_list = [info_or_tupleinfolist]
            self.ui.comboBox.setVisible(True)
            self.ui.comboBox.setEnabled(False)
            if len(info_or_tupleinfolist) > 0:
                self.ui.comboBox.addItem(info_or_tupleinfolist[0])
                self.ui.plainTextEdit.setPlainText(info_or_tupleinfolist[1])
        else:
            self.index = None
            self.tuple_list = None
            self.ui.comboBox.setVisible(False)
            self.ui.plainTextEdit.setPlainText(info_or_tupleinfolist)

        # Mostrem el diàleg
        self.setSizeGripEnabled(True) # Mostra la marca de resize (abaix a la dreta)
        if autoshow:
            self.return_value = self.do_modal()

    def update(self, index):
        """ En cas de tenir una llista d'informacions, mostra la informació associada a "index"
            ---
            In case you have a list of information, show the information associated with "index"
            """
        self.index = index
        self.ui.plainTextEdit.setPlainText(self.tuple_list[index][1])

    def get_report_info(self, html_format=False):
        """ Retorna un text amb la informació mostrada en el diàleg, pot ser en format
            text pla, HTML i es pot configurar els canvis de linia
            ---
            Returns a text with the information displayed in the dialog, it can be in
            plain text format, HTML, and you can configure line changes format
            """
        if self.index:
            if html_format and self.extrainfohtml_or_tupleextrainfohtmllist:
                report_info = self.extrainfohtml_or_tupleextrainfohtmllist[self.index][1]
            elif self.extrainfo_or_tupleextrainfolist:
                report_info = self.extrainfo_or_tupleextrainfolist[self.index][1]
            else:
                report_info = self.info_or_tupleinfolist[self.index][1]
        else:
            if html_format and self.extrainfohtml_or_tupleextrainfohtmllist:
                report_info = self.extrainfohtml_or_tupleextrainfohtmllist
            elif self.extrainfo_or_tupleextrainfolist:
                report_info = self.extrainfo_or_tupleextrainfolist
            else:
                report_info = self.info_or_tupleinfolist

        return report_info

    def save(self):
        """ Guarda la informació del diàleg en un fitxer
            ---
            Saves dialog information into a file
            """
        out_file, _file_type = QFileDialog.getSaveFileName(None, "Save log info", "log.txt", "Text files (*.txt)")
        if not out_file:
            return
        report_info = self.get_report_info(html_format=False)
        try:
            with open(out_file, 'w', encoding='utf-8') as file:
                file.write(report_info)
        except Exception as e:
            QMessageBox.warning(None, u"Save error", u"Error saving log\n%s" % e)

    def copy_to_clipboard(self):
        """ Guarda la informació del diàleg en el portapapers
            ---
            Saves dialog information into clipboard
            """
        if not clipboard_available:
            return
        clipboard.OpenClipboard()
        clipboard.EmptyClipboard()
        clipboard.SetClipboardText(self.ui.plainTextEdit.toPlainText())
        clipboard.CloseClipboard()

    def send_email(self):
        """ Envia la informació del diàleg per email
            ---
            Send dialog information by email
            """
        if not email_available:
            return
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            return self.show_extra_info()

        email_info = self.get_report_info(html_format=True)
        try:
            email_object = utilities.email.eMail(self.email_to, self.email_cc, self.email_subject, htmlbody = email_info, attachment_files = [])
            email_object.open()
        except:
            QMessageBox.warning(None, u"Enviar informe", u"Error no es pot obrir el programa d'email per enviar l'informe")

    def show_extra_info(self):
        """ Mostra la informació addicional en el diàleg
            ---
            Show extra information on dialog
            """
        # Mostrem la informació extesa al diàleg
        extra_info = self.get_report_info()
        self.ui.plainTextEdit.clear();
        self.ui.plainTextEdit.appendPlainText(extra_info);
        # Fem el diàleg més gran
        extra_width = 400
        extra_height = 400
        self.resize(self.geometry().width() + extra_width, self.geometry().height() + extra_height)
        self.move(self.x() - extra_width / 2, self.y() - extra_height / 2)

    def do_modal(self):
        """ Mostra el diàleg en mode modal
            ---
            Show modal dialog
            """
        self.show()
        self.return_value = self.exec_()
        return self.return_value

    def accept(self):
        QDialog.accept(self)

    def reject(self):
        QDialog.reject(self)

    def is_ok(self):
        """ Retorna si s'ha premut el botó ok
            ---
            Return if ok button has been pressed
            """
        return self.return_value == 1

    def is_cancel(self):
        """ Retorna si s'ha premut el botó cancelar
            ---
            Return if cancel button has been pressed
            """
        return self.return_value == 0

    def is_yes(self):
        """ Retorna si s'ha premut el botó yes
            ---
            Return if yes button has been pressed
            """
        return self.return_value == 1

    def is_no(self):
        """ Retorna si s'ha premut el botó no
            ---
            Return if no button has been pressed
            """
        return self.return_value == 0
