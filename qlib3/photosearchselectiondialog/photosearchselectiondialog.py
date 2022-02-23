# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb classe diàleg gestionar les cerques dins la fototeca
---
Module with a dialog class to manage photo library searches

                             -------------------
        begin                : 2021-06-17
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import os

from PyQt5.QtCore import QDateTime
from PyQt5 import uic
from PyQt5.QtGui import QPainter, QPen, QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtWidgets import QDockWidget, QSlider, QApplication, QStyleOptionSlider, QToolTip, QTableWidgetItem, QHeaderView, QStyle

from . import resources_rc

Ui_TimeSeries, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_%s.ui' % os.path.basename(__file__).replace("dialog.py", "")))


class PhotoSearchSelectionDialog(QDockWidget, Ui_TimeSeries):
    """ Dialog class to show results of photo search and filter it """

    photo_layer = None
    time_series_list = []
    photo_list = []

    def __init__(self, photo_layer, time_series_list, current_time,
        update_callback=None, photo_selection_callback=None, show_info_callback=None, preview_callback=None, adjust_callback=None,
        download_callback=None, request_certificate_callback=None, request_scan_callback=None, report_bug_callback=None,
        name_field_name="name", gsd_field_name="gsd", date_field_name="flight_date", image_field_name="image_filename",
        publishable_field_name=None, available_field_name=None, autoshow=True, show_buttons_text=True, parent=None):
        """ Initialize time range and refresh / action callbacks """
        super().__init__(parent)
        self.setupUi(self)

        # Configure layers column names
        self.name_field_name = name_field_name
        self.gsd_field_name = gsd_field_name
        self.date_field_name = date_field_name
        self.image_field_name = image_field_name
        self.publishable_field_name = publishable_field_name
        self.available_field_name = available_field_name

        # Set table widget properties
        self.tableWidget_photos.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # col(0) és autoescalable
        self.tableWidget_photos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tableWidget_photos.setColumnWidth(1, 130)
        self.tableWidget_photos.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tableWidget_photos.setColumnWidth(2, 60)
        self.tableWidget_photos.keyPressEvent  = self.on_table_key_press

        # Map year sliders keypress event
        self.horizontalSlider.keyPressEvent = lambda event:self.on_slider_key_press(event, self.horizontalSlider)
        self.horizontalSlider_range.keyPressEvent = lambda event:self.on_slider_key_press(event, self.horizontalSlider_range)

        # Load button icons
        self.pushButton_report_bug.setIcon(QIcon(":/lib/qlib3/base/images/bug.png"))
        self.pushButton_show_info.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.pushButton_link_preview.setIcon(QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_preview.png"))
        self.pushButton_download_hd.setIcon(QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_download.png"))
        self.pushButton_request_certificate.setIcon(QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_certificate.png"))
        self.pushButton_request_scan.setIcon(QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_scan.png"))
        self.pushButton_adjust_brightness.setIcon(QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_brightness.png"))

        # Translate dialog text
        self.current_value_prefix = self.tr("Year: %s")
        self.checkBox_range.setText(self.tr("Years range"))
        self.label_quality.setText(self.tr("Resolution"))
        self.comboBox_quality.blockSignals(True)
        self.comboBox_quality.clear()
        self.comboBox_quality.addItem(self.tr("All"))
        self.comboBox_quality.addItem(self.tr("Very high (< 15 cm/px)"))
        self.comboBox_quality.addItem(self.tr("High (approx. 25 cm/px)"))
        self.comboBox_quality.addItem(self.tr("Medium (approx. 50 cm/px)"))
        self.comboBox_quality.addItem(self.tr("Low (> 60 cm/px)"))
        self.comboBox_quality.blockSignals(False)
        self.photo_count_prefix = self.tr("Photograms: %s")
        self.tableWidget_photos.horizontalHeaderItem(0).setText(self.tr("Photogram"))
        self.tableWidget_photos.horizontalHeaderItem(1).setText(self.tr("Date"))
        self.tableWidget_photos.horizontalHeaderItem(2).setText(self.tr("m/px"))
        self.label_extra_info.setText(self.tr("Note: Photograms locations are approximate"))
        self.pushButton_report_bug.setText("")
        self.pushButton_report_bug.setToolTip(self.tr("Report photo bug"))
        self.pushButton_show_info.setText((" " + self.tr("Information")) if show_buttons_text else "")
        self.pushButton_show_info.setToolTip(self.tr("Information"))
        self.pushButton_link_preview.setText((" " + self.tr("View")) if show_buttons_text else "")
        self.pushButton_link_preview.setToolTip(self.tr("View"))
        self.pushButton_adjust_brightness.setText((" " + self.tr("Adjust\nbrightness")) if show_buttons_text else "")
        self.pushButton_adjust_brightness.setToolTip(self.tr("Adjust brightness"))
        self.pushButton_download_hd.setText((" " + self.tr("Download")) if show_buttons_text else "")
        self.pushButton_download_hd.setToolTip(self.tr("Download"))
        self.pushButton_request_certificate.setText((" " + self.tr("Request\ncertificate")) if show_buttons_text else "")
        self.pushButton_request_certificate.setToolTip(self.tr("Request certificate"))
        self.pushButton_request_scan.setText((" " + self.tr("Request\nscan")) if show_buttons_text else "")
        self.pushButton_request_scan.setToolTip(self.tr("Request scan"))

        # Configure small help in tooltip
        self.tableWidget_photos.setToolTip(self.tr("""When photograms list is focused you can use\n"""
            """up and down cursor keys to select current photo,\n"""
            """left and right keys to select current year and\n"""
            """enter key to visualize a photo"""))

        # Update time, photo information and callbacks
        self.set_info(photo_layer, time_series_list, current_time,
            update_callback, photo_selection_callback, show_info_callback, preview_callback, adjust_callback,
            download_callback, request_certificate_callback, request_scan_callback, report_bug_callback)

        # Hide second time slider (date range slider)
        self.horizontalSlider_range.setVisible(False)
        self.label_begin_range.setVisible(False)
        self.label_end_range.setVisible(False)
        # Hide resolution filter (not used for the moment)
        self.label_quality.setVisible(False)
        self.comboBox_quality.setVisible(False)

        # Show dialog
        if autoshow:
            self.show()

    def set_info(self, photo_layer, time_series_list, current_time,
            update_callback, photo_selection_callback, show_info_callback, preview_callback, adjust_callback,
            download_callback, request_certificate_callback, request_scan_callback, report_bug_callback):
        """ Store time, photo information and callbacks """
        self.photo_layer = photo_layer
        self.update_callback = update_callback
        self.photo_selection_callback = photo_selection_callback
        self.show_info_callback = show_info_callback
        self.preview_callback = preview_callback
        self.adjust_callback = adjust_callback
        self.download_callback = download_callback
        self.request_certificate_callback = request_certificate_callback
        self.request_scan_callback = request_scan_callback
        self.report_bug_callback = report_bug_callback

        # Update windows title with photo_layer
        self.setWindowTitle(self.photo_layer.name() if self.photo_layer else self.windowTitle().split(":")[0])
        # Update year sliders
        self.set_time_series(time_series_list, current_time)

        # Update photograms list
        features_list = self.photo_layer.getFeatures() if self.photo_layer else []
        self.photo_list = [self.get_photo_info(f) for f in features_list]
        self.photo_list.sort(key=lambda p:p[1])
        self.update_photos()

        # Update buttons
        self.pushButton_report_bug.setVisible(self.report_bug_callback is not None)
        self.pushButton_show_info.setVisible(self.show_info_callback is not None)
        self.pushButton_link_preview.setVisible(self.preview_callback is not None)
        self.pushButton_adjust_brightness.setVisible(self.adjust_callback is not None)
        self.pushButton_download_hd.setVisible(self.download_callback is not None)
        self.pushButton_request_certificate.setVisible(self.request_certificate_callback is not None)
        self.pushButton_request_scan.setVisible(self.request_scan_callback is not None)

    def get_photo_info(self, feature):
        """ Returns tuplue with photo info from layer feature """
        datetime = feature[self.date_field_name]
        if datetime:
            if type(datetime) is QDateTime:
                year, datetime_text = datetime.date().year(), datetime.toString(Qt.SystemLocaleShortDate)
            else:
                year, datetime_text = int(datetime.split("-")[0]), datetime
        else:
            year, datetime_text = None, None
        return feature.id(), feature[self.name_field_name], year, datetime_text, feature[self.gsd_field_name], \
            True if feature[self.image_field_name] else False, \
            feature[self.publishable_field_name] if self.publishable_field_name else True, \
            feature[self.available_field_name] if self.available_field_name else True

    def reset(self, hide=True):
        """ Reset all information, disable controls and hide dialog"""
        # Delete information and disable controls
        self.set_info(photo_layer=None, time_series_list=[], current_time=None,
            update_callback=None, photo_selection_callback=None, show_info_callback=None,
            preview_callback=None, adjust_callback=None, download_callback=None,
            request_certificate_callback=None, request_scan_callback=None, report_bug_callback=None)
        # Hide dialog
        if hide:
            self.hide()

    # Colors for different photo status
    DEFAULT_PHOTO_COLOR = QColor(255, 255, 255)
    UNPUBLISHABLE_PHOTO_COLOR = QColor(220, 220, 220)
    UNSCANNED_PHOTO_COLOR = QColor(255, 255, 200)
    UNAVAILABLE_PHOTO_COLOR = QColor(255, 200, 200)
    # Icons for differents photo status
    DEFAULT_PHOTO_ICON = QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_preview.png")
    UNPUBLISHABLE_PHOTO_ICON = QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_forbidden.png")
    UNSCANNED_PHOTO_ICON = QIcon(":/lib/qlib3/photosearchselectiondialog/images/photo_scan.png")
    UNAVAILABLE_PHOTO_ICON = QIcon(":/lib/qlib3/base/images/bug.png")

    def update_photos(self):
        """ Update tableWidget photo infomation """
        # Get seleted time range and resolution range
        time_range_list = self.get_current_time_range_list()
        min_res, max_res = self.get_current_resolution_range()

        # Update tableWidget with photo_list data
        self.tableWidget_photos.blockSignals(True)
        self.tableWidget_photos.setRowCount(0)
        for id, name, year, flight_datetime_text, gsd, image_available, publishable, available in self.photo_list:
            if year is not None and year in time_range_list and gsd is not None and gsd >= min_res and gsd < max_res:
                if not available:
                    color = self.UNAVAILABLE_PHOTO_COLOR
                    icon = self.UNAVAILABLE_PHOTO_ICON
                    tooltip = self.tr("Unavailable or lost")
                elif not publishable:
                    color = self.UNPUBLISHABLE_PHOTO_COLOR
                    icon = self.UNPUBLISHABLE_PHOTO_ICON
                    tooltip = self.tr("No publishable")
                elif not image_available:
                    color = self.UNSCANNED_PHOTO_COLOR
                    icon = self.UNSCANNED_PHOTO_ICON
                    tooltip = self.tr("Scan required")
                else:
                    color = self.DEFAULT_PHOTO_COLOR
                    icon = self.DEFAULT_PHOTO_ICON
                    tooltip = self.tr("Available")
                row = self.tableWidget_photos.rowCount()
                self.tableWidget_photos.insertRow(row)
                item = QTableWidgetItem(name)
                item.setData(Qt.UserRole, (id, image_available, available, publishable))
                item.setBackground(color)
                item.setToolTip(tooltip)
                item.setIcon(icon)
                self.tableWidget_photos.setItem(row, 0, item)
                item = QTableWidgetItem(flight_datetime_text)
                item.setBackground(color)
                item.setToolTip(tooltip)
                self.tableWidget_photos.setItem(row, 1, item)
                gsd_text = "%.2f" % gsd if gsd else ""
                item = QTableWidgetItem(gsd_text)
                item.setBackground(color)
                item.setToolTip(tooltip)
                self.tableWidget_photos.setItem(row, 2, item)
        self.tableWidget_photos.resizeColumnToContents(0) # Col0 mida fixa ajustada al contingut
        self.tableWidget_photos.resizeRowsToContents()
        self.tableWidget_photos.blockSignals(False)

        # Update photo counter
        self.label_photos.setText(self.photo_count_prefix % self.tableWidget_photos.rowCount())

        # Enable or disable dialog controls no selection dependent
        enable = self.tableWidget_photos.rowCount() > 0
        self.horizontalSlider.setEnabled(enable)
        self.label_begin.setEnabled(enable)
        self.label_end.setEnabled(enable)
        self.checkBox_range.setEnabled(enable)
        self.horizontalSlider_range.setEnabled(enable)
        self.label_begin_range.setEnabled(enable)
        self.label_end_range.setEnabled(enable)
        self.label_current.setEnabled(enable)
        self.tableWidget_photos.setEnabled(enable)

        # Simulate update selection signal (and enable/disable selection dependent buttons)
        self.on_photo_changed()

    def set_time_series(self, time_series_list, current_time):
        """ Update year sliders information """
        # Store years list
        self.time_series_list = time_series_list
        # Set years labels
        self.label_begin.setText(str(time_series_list[0]) if time_series_list else "")
        self.label_end.setText(str(time_series_list[-1]) if time_series_list else "")
        self.label_begin_range.setText(str(time_series_list[0]) if time_series_list else "")
        self.label_end_range.setText(str(time_series_list[-1]) if time_series_list else "")
        self.label_current.setText(self.current_value_prefix % (str(current_time) if current_time else ""))

        # Disable sliders signals to update it
        self.horizontalSlider.blockSignals(True)
        self.horizontalSlider_range.blockSignals(True)
        # Set sliders limits
        self.horizontalSlider.setTickInterval(1)
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(len(time_series_list) - 1)
        self.horizontalSlider_range.setTickInterval(1)
        self.horizontalSlider_range.setMinimum(0)
        self.horizontalSlider_range.setMaximum(len(time_series_list) - 1)
        # Set current time
        self.set_current_time(current_time)
        # Activate sliders signals
        self.horizontalSlider.blockSignals(False)
        self.horizontalSlider_range.blockSignals(False)

    def set_current_time(self, current_time, range_time=None):
        """ Set current sliders years """
        # Change value only when it is different that old value
        new_current_value = self.time_series_list.index(current_time) if current_time else 0
        if new_current_value:
            if self.horizontalSlider.value() != new_current_value:
                self.horizontalSlider.setValue(new_current_value)
        new_range_value = self.time_series_list.index(range_time) if range_time else new_current_value
        if new_range_value:
            if self.horizontalSlider_range.value() != new_range_value:
                self.horizontalSlider_range.setValue(new_range_value)

    def get_current_time_range(self):
        """ Return current selected years range (two years) """
        if not self.time_series_list:
            return None, None
        current_time = self.time_series_list[self.horizontalSlider.value()]
        current_range = self.time_series_list[self.horizontalSlider_range.value()] if self.checkBox_range.isChecked() else None
        min_time = min(current_time, current_range) if current_range else current_time
        max_time = max(current_time, current_range) if current_range else None
        return min_time, max_time

    def get_current_time_range_list(self):
        """ Return current selected years list """
        current_time, current_range = self.get_current_time_range()
        if not current_time:
            return []
        return range(current_time, current_range+1) if current_range else [current_time]

    def get_current_resolution_range(self):
        """ Return current selecte resolution range (two values) """
        all_tuple = (0, 1000000)
        quality_dict = {
            0: all_tuple,
            1: (0, 0.15),
            2: (0.15, 0.35),
            3: (0.35, 0.60),
            4: (0.60, 1000000)
            }
        return quality_dict.get(self.comboBox_quality.currentIndex(), all_tuple)

    def on_range_clicked(self, enabled):
        """ Mapped event to enable or disable second year slider and update photograms list"""
        # Enable or disable second year slider
        self.horizontalSlider_range.setVisible(enabled)
        if enabled:
            self.horizontalSlider_range.setValue(self.horizontalSlider.value())
        self.label_begin_range.setVisible(enabled)
        self.label_end_range.setVisible(enabled)
        # Update filteredd photograms list
        self.update_filter()

    def on_value_changed(self, value=None):
        """ Mapped event to update filtered photograms list when change current year """
        if not self.horizontalSlider.isSliderDown():
            self.update_filter()

    def on_range_value_changed(self, value=None):
        """ Mapped event to update filtered photograms list when change current year range """
        if not self.horizontalSlider_range.isSliderDown():
            self.update_filter()

    def update_filter(self):
        """ Update photograms list applying year and resolution filters """
        # Update current years label
        current_time, current_range = self.get_current_time_range()
        if current_range:
            self.label_current.setText(self.current_value_prefix % ("%s - %s" % (str(current_time), str(current_range))))
        else:
            self.label_current.setText(self.current_value_prefix % str(current_time))

        # Update photograms list
        self.update_photos()

        # Update photo layer visualization
        if self.update_callback and current_time:
            new_layer_name = self.update_callback(current_time, current_range)
            if new_layer_name:
                self.setWindowTitle(new_layer_name)

    def on_quality_changed(self, index):
        """ Mapped event to update filtered photograms list when change selected resolution """
        self.update_photos()

    def get_selected_photo_id(self):
        photo_id, _image_available, _publishable, _available = self.get_selected_photo_info()
        return photo_id

    def get_selected_photo_info(self):
        """ Return current selected photogram id """
        items_list = self.tableWidget_photos.selectedItems()
        if not items_list:
            return None, None, None, None
        row = items_list[0].row()
        item = self.tableWidget_photos.item(row, 0)
        photo_id, image_available, available, publishable = item.data(Qt.UserRole)
        image_available = item.background() not in [self.UNSCANNED_PHOTO_COLOR, self.UNAVAILABLE_PHOTO_COLOR]
        available = item.background() != self.UNAVAILABLE_PHOTO_COLOR
        publishable = item.background() != self.UNPUBLISHABLE_PHOTO_COLOR
        return photo_id, image_available, publishable, available

    def get_selected_photo_name(self):
        """ Return current selected photogram name """
        items_list = self.tableWidget_photos.selectedItems()
        if not items_list:
            return None
        row = items_list[0].row()
        item = self.tableWidget_photos.item(row, 0)
        photo_name = item.text()
        return photo_name

    def select_photo(self, photo_id, year):
        """ Select specified photo in tableWidget """
        # Search photo id in table
        row = None
        if photo_id is not None:
            # Search photo_id row
            for i in range(self.tableWidget_photos.rowCount()):
                photo_id2, _image_available, _publishable, _available = self.tableWidget_photos.item(i, 0).data(Qt.UserRole)
                if  photo_id2 == photo_id:
                    row = i
                    break
        # Select found row (or not)
        if row is not None:
            self.tableWidget_photos.selectRow(row)
        elif year:
            # If we have year, try change year and search again
            self.set_current_time(year)
            self.select_photo(photo_id, year=None)
        else:
            self.tableWidget_photos.clearSelection()

    def on_photo_changed(self):
        """ Mapped event to update photo layer selection when change selected photogram """
        photo_id, image_available, publishable, available = self.get_selected_photo_info()
        if self.photo_selection_callback:
            self.photo_selection_callback(photo_id)

        enable = photo_id is not None
        self.pushButton_report_bug.setEnabled(enable and image_available)
        self.pushButton_show_info.setEnabled(enable)
        self.pushButton_link_preview.setEnabled(enable and image_available)
        self.pushButton_adjust_brightness.setEnabled(enable and image_available)
        self.pushButton_download_hd.setEnabled(enable and image_available and publishable)
        self.pushButton_request_certificate.setEnabled(enable and image_available and publishable)
        self.pushButton_request_scan.setEnabled(enable and not image_available and available)

    def show_info(self):
        """ Mapped event to show photo information when push button """
        photo_id = self.get_selected_photo_id()
        if self.show_info_callback and photo_id:
            self.show_info_callback(photo_id)

    def preview(self):
        """ Mapped event to load photo raster when push button """
        photo_id = self.get_selected_photo_id()
        if self.preview_callback and photo_id:
            self.preview_callback(photo_id)

    def adjust(self):
        photo_id = self.get_selected_photo_id()
        if self.adjust_callback and photo_id:
            self.adjust_callback(photo_id)

    def download_hd(self):
        """ Mapped event to enable download tool when push button """
        photo_id = self.get_selected_photo_id()
        if self.download_callback and photo_id:
            self.download_callback(photo_id)

    def request_certificate(self):
        """ Mapped event to request certificate when push button """
        photo_id = self.get_selected_photo_id()
        if self.request_certificate_callback and photo_id:
            self.request_certificate_callback(photo_id)

    def request_scan(self):
        """ Mapped event to request certificate when push button """
        photo_id = self.get_selected_photo_id()
        if self.request_scan_callback and photo_id:
            self.request_scan_callback(photo_id)

    def report_bug(self):
        """ Mapped event to report bug when push button """
        photo_id = self.get_selected_photo_id()
        if self.report_bug_callback and photo_id:
            self.report_bug_callback(photo_id)

    def on_table_key_press(self, event):
        """ Mapped table keyPress event to change current year with cursors and load preview photo raster """
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.preview()
            self.tableWidget_photos.setFocus()
        elif event.key() == Qt.Key_Left:
            self.horizontalSlider.setValue(self.horizontalSlider.value() - 1)
        elif event.key() == Qt.Key_Right:
            self.horizontalSlider.setValue(self.horizontalSlider.value() + 1)
        else:
            self.tableWidget_photos.__class__.keyPressEvent(self.tableWidget_photos, event)

    def on_slider_key_press(self, event, widget):
        """ Mapped sliders keyPress event to change current selected photogram with cursors"""
        if event.key() == Qt.Key_Up:
            rows_list = self.tableWidget_photos.selectionModel().selectedRows()
            self.tableWidget_photos.selectRow(rows_list[0].row()-1 if rows_list else self.tableWidget_photos.rowCount() - 1)
        elif event.key() == Qt.Key_Down:
            rows_list = self.tableWidget_photos.selectionModel().selectedRows()
            self.tableWidget_photos.selectRow(rows_list[0].row()+1 if rows_list else 0)
        else:
            self.horizontalSlider.__class__.keyPressEvent(widget, event)
