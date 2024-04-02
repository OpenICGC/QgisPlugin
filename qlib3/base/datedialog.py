# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QDateTimeEdit, QDateEdit, QLabel
from PyQt5.QtCore import Qt, QDateTime


class DateDialog(QDialog):
    """ Classe diàleg per preguntar una data o data/hora """
    def __init__(self, description=None, title=None, parent=None, datetime_not_date=True):
        super(DateDialog, self).__init__(parent)

        # set title:
        if title:
            self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        # add label with description
        if description:
            self.label = QLabel(description)
            layout.addWidget(self.label)
        # nice widget for editing the date
        self.datetime = QDateTimeEdit(self) if datetime_not_date else QDateEdit(self)
        self.datetime.setCalendarPopup(True)
        self.datetime.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.datetime)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # get current date and time from the dialog
    def dateTime(self):
        return self.datetime.dateTime().toPyDateTime()

    def date(self):
        return self.datetime.dateTime().date().toPyDate()

    def time(self):
        return self.datetime.dateTime().time().toPyTime()

    # static method to create the dialog and return (date, time, accepted)
    @staticmethod
    def getDateTime(description=None, title=None, parent=None):
        dialog = DateDialog(description, title, parent)
        status_ok = (dialog.exec_() == QDialog.Accepted)
        return (dialog.date() if status_ok else None, dialog.time() if status_ok else None, status_ok)

    @staticmethod
    def getDateTimeInOne(description=None, title=None, parent=None):
        dialog = DateDialog(description, title, parent)
        status_ok = (dialog.exec_() == QDialog.Accepted)
        return (dialog.dateTime() if status_ok else None, status_ok)

    @staticmethod
    def getDate(description=None, title=None, parent=None):
        dialog = DateDialog(description, title, parent, False)
        status_ok = (dialog.exec_() == QDialog.Accepted)
        return (dialog.date() if status_ok else None, status_ok)