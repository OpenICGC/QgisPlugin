# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with the implementation of the dialog that allows to show the results
of the spatial searches
                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

# Import the PyQt libraries
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

# Load a .ui file without pre-compiling it
ui_download, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_download.ui'))


class DownloadDialog(QDialog, ui_download):
    """ Dialog class that allows to show product download options """

    def __init__(self, data_dict, auto_show=False, parent=None):
        """ Dialog initialization with data format:
            data_dict = {
                <year_1>: {
                    <gsd_1>: [
                        <download_type_1>...<download_type_n>
                        ]
                     ...
                    <gsd_n>: ...
                    }
                ...
                <year_n>: ...
                }
            Note:
            <year> can be None
            <gsd> can be None
            <download_type> list is required
            """
        QDialog.__init__(self, parent)
        
        # Set up the user interface from Designer.
        super().setupUi(self)

        # Translate dialog
        self.setWindowTitle(self.tr("Downloads"))
        self.label_info.setText(self.tr("Select the type of download and then use the download tool to mark a point or area of interest, enter a rectangle coordinates or select a polygons layer"))
        self.label_year.setText(self.tr("Year:"))
        self.label_gsd.setText(self.tr("Resolution (m):"))
        self.label_download_type.setText(self.tr("Download type:"))

        # Set up values
        self.updating = False
        self.set_data(data_dict)

        # We show the dialog automatically if necessary
        self.status = False
        if auto_show:
            self.do_modal()

    def set_data(self, data_dict):
        """ Setup the components that form the dialog """
        self.data_dict = data_dict
        self.year_list = []
        self.current_year = None
        self.gsd_list = []
        self.current_gsd = None
        self.download_type_list = []
        self.current_download_type = None
        
        # Get initial value lists
        self.year_list = [] if None in self.data_dict.keys() \
            and len(self.data_dict.keys()) == 1 else list(self.data_dict.keys()) 
        self.current_year = self.year_list[-1] if self.year_list else None
        gsd_dict = self.data_dict[self.current_year]
        self.gsd_list = [] if None in gsd_dict.keys() \
            and len(gsd_dict.keys()) == 1 else list(gsd_dict.keys())
        self.current_gsd = self.gsd_list[0] if self.gsd_list else None
        download_type_dict = gsd_dict[self.current_gsd]
        self.download_type_list = [] if None in download_type_dict.keys() \
            and len(download_type_dict.keys()) == 1 else list(download_type_dict.keys())
        self.current_download_type = self.download_type_list[0] if self.download_type_list else None

        # Update dialog controls
        self.update_controls()

    def update_controls(self, update_year=True, update_gsd=True, update_download_type=True):
        """ Load current values into dialog controls """
        if self.updating:
            return
        self.updating = True
        if update_year:
            show_year = True if self.year_list else False
            enable_year = show_year
            self.label_year.setVisible(show_year)
            self.label_begin_year.setVisible(show_year)
            self.label_end_year.setVisible(show_year)
            if self.year_list:
                self.label_begin_year.setText(str(self.year_list[0]))
                self.label_end_year.setText(str(self.year_list[-1]))
            self.horizontalSlider_year.setVisible(show_year)
            self.horizontalSlider_year.setEnabled(enable_year)
            self.horizontalSlider_year.setRange(0, len(self.year_list) - 1)
            self.horizontalSlider_year.setValue(len(self.year_list) - 1)
        
        if update_gsd:
            if self.current_year:
                self.label_year.setText("%s: %s" % (self.label_year.text().split(":")[0], str(self.current_year)))

            show_gsd = True if self.gsd_list else False #or self.year_list  else False
            enable_gsd = True if self.gsd_list else False
            self.label_gsd.setVisible(show_gsd)
            self.comboBox_gsd.setVisible(show_gsd)
            self.comboBox_gsd.setEnabled(enable_gsd)
            current_text = self.comboBox_gsd.currentText()
            self.comboBox_gsd.clear()
            self.comboBox_gsd.addItems([str(v) for v in self.gsd_list])
            self.comboBox_gsd.setCurrentText(current_text)
        
        if update_download_type:
            show_download_type = True if self.year_list or self.gsd_list or self.download_type_list else False
            enable_download_type = True if self.download_type_list else False
            self.label_download_type.setVisible(show_download_type)
            self.comboBox_download_type.setVisible(show_download_type)
            self.comboBox_download_type.setEnabled(enable_download_type)
            current_text = self.comboBox_download_type.currentText()
            self.comboBox_download_type.clear()
            self.comboBox_download_type.addItems([str(v) for v in self.download_type_list])
            self.comboBox_download_type.setCurrentText(current_text)

        self.updating = False

    def on_year_changed(self, current_year_index=None):
        """ Get current year value and update related values """
        if not self.year_list or current_year_index < 0:
            self.current_year = None
            return
        # Get current year value
        self.current_year = self.year_list[current_year_index]
        self.gsd_list = [] if None in self.data_dict[self.current_year].keys() \
            and len(self.data_dict[self.current_year].keys()) == 1 else list(self.data_dict[self.current_year].keys())
        # Update dialog controls
        self.update_controls(update_year=False)

    def on_gsd_changed(self, current_gsd_index=None):
        """ Get current GSD value and update related values """
        if not self.gsd_list or current_gsd_index < 0:
            self.current_gsd = None
            return
        # Get current GSD value
        self.current_gsd = self.gsd_list[current_gsd_index]
        self.download_type_list = list(self.data_dict[self.current_year][self.current_gsd].keys())
        # Update dialog controls
        self.update_controls(update_year=False, update_gsd=False)

    def on_download_type_changed(self, current_download_type_index=None):
        """ Get current download type """
        if not self.download_type_list or current_download_type_index < 0:
            self.current_download_type = None
            return
        self.current_download_type = self.download_type_list[current_download_type_index]

    def do_modal(self):
        """ Show GeoFinder dialog and makes it modal """
        self.show()
        self.adjustSize() # Adjust dialog size to visible children
        self.status = self.exec_()
        return self.status

    def get_year(self):
        """ Return selected download year """
        return self.current_year

    def get_gsd(self):
        """ Return selected download resolution """
        return self.current_gsd

    def get_download_type(self):
        """ Return selected download type """
        return self.data_dict[self.current_year][self.current_gsd][self.current_download_type]

