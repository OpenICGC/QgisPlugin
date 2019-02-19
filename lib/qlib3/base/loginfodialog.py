# -*- coding: utf-8 -*-
"""
    Diàleg per mostrar informació multiliniea
"""


import os
import win32clipboard as clipboard
try:    
    import utilities.email
    email_available = True
except:
    email_available = False


from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFontMetrics
from PyQt5.QtWidgets import QStyle, QDialogButtonBox, QDialog, QApplication

ui_loginfo, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_loginfo.ui'))


class LogInfoDialog(QDialog, ui_loginfo):
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

    def __init__(self, info_or_tupleinfolist, title = u"Informació de procés", 
            mode = mode_info, buttons = buttons_ok, 
            default_combo_selection = None, 
            extrainfo_or_tupleextrainfolist = None, extrainfohtml_or_tupleextrainfohtmllist = None,
            email_button_text = None, email_subject = None, email_to = None, email_cc = None,            
            save_button_text = None, copy_clipboard_button_test = None,
            autoshow = True, width = None, height = None, parent = None):
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
        if copy_clipboard_button_test:
            self.ui.pushButton_clipboard.setText(copy_clipboard_button_test)
            self.ui.pushButton_clipboard.setMaximumWidth(QFontMetrics(self.ui.pushButton_save.font()).width(copy_clipboard_button_test) + 20)
            self.ui.pushButton_clipboard.setEnabled(True)
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
        ##self.ui.plainTextEdit.setFont(QFont(self.ui.plainTextEdit.font().rawName(), 11))

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
        if autoshow:
            self.return_value = self.do_modal()

    def update(self, index):
        self.index = index
        self.ui.plainTextEdit.setPlainText(self.tuple_list[index][1])

    def get_report_info(self, html_format = False, crlf = False):        
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
        
        if crlf:
            report_info = report_info.replace('\r\n', '\n').replace('\n', '\r\n')
        return report_info

    def save(self):
        out_file = QDir.toNativeSeparators(QFileDialog.getSaveFileName(None, "Save log info", "log.txt", "Text files (*.txt)"))
        if not out_file:
            return
        ##text = self.ui.plainTextEdit.toPlainText().replace('\n', '\r\n')
        ##print "text", text
        ##try:
        ##    with open(out_file, "w") as fout:
        ##        fout.write(text)
        report_info = self.get_report_info(html_format = False, crlf = True)
        try:
            with open(out_file, 'w') as file:
                file.write(report_info.encode('UTF-8'))
        except Exception as e:
            QMessageBox.warning(None, u"Save error", u"Error saving log\n%s" % e)

    def copy_to_clipboard(self):
        ##message = "\r\n".join(["\t".join([unicode(value) for value in strip_info]) for strip_info in delivery_note_strips_list[1:]])
        # Put string into clipboard (open, clear, set, close)
        clipboard.OpenClipboard()
        clipboard.EmptyClipboard()
        clipboard.SetClipboardText(self.ui.plainTextEdit.toPlainText())
        clipboard.CloseClipboard()

    def send_email(self):
        if not email_available:
            return
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            return self.show_extra_info()

        email_info = self.get_report_info(html_format = True, crlf = False)
        try:
            email_object = utilities.email.eMail(self.email_to, self.email_cc, self.email_subject, htmlbody = email_info, attachment_files = [])
            email_object.open()
        except:
            QMessageBox.warning(None, u"Enviar informe", u"Error no es pot obrir el programa d'email per enviar l'informe")

    def show_extra_info(self):
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
        self.show()
        self.return_value = self.exec_()
        return self.return_value

    def accept(self):
        QDialog.accept(self)

    def reject(self):
        QDialog.reject(self)

    def is_ok(self):
        return self.return_value == 1

    def is_cancel(self):
        return self.return_value == 0

    def is_yes(self):
        return self.return_value == 1

    def is_no(self):
        return self.return_value == 0
