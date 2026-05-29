# -*- coding: utf-8 -*-
"""
Main dialog for Minera Indices GEE plugin.
"""

import os
from datetime import date, timedelta

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog,
    QGroupBox, QCheckBox, QScrollArea, QWidget,
    QProgressBar, QTextEdit, QComboBox, QSpinBox,
    QFrame, QMessageBox, QDateEdit,
)
from qgis.PyQt.QtCore import Qt, QDate
from qgis.PyQt.QtGui import QFont, QColor
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProject, QgsRasterLayer,
)

from .gee_indices import SENSORS
from .aoi_tool import RectangleAOITool


class MineraIndicesGEEDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Minera Indices GEE - Google Earth Engine")
        self.setMinimumSize(820, 700)
        self._aoi_rect = None      # QgsRectangle in map CRS
        self._aoi_tool = None
        self._prev_tool = None
        self._worker = None
        self._checkboxes = {}
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        # Title
        title = QLabel("Minera Indices — Google Earth Engine")
        font = QFont(); font.setPointSize(13); font.setBold(True)
        title.setFont(font)
        root.addWidget(title)
        root.addWidget(QLabel(
            "Server-side mineral indices via GEE  |  "
            "ASTER · Landsat 5/7/8/9 · Sentinel-2"))

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken); root.addWidget(sep)

        # ── GEE Connection ────────────────────────────────────────────────────
        conn_grp = QGroupBox("1. GEE Connection")
        conn_lay = QGridLayout(conn_grp)

        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText(
            "GEE Cloud Project ID (e.g. ee-myproject) — leave blank for legacy")
        self.auth_btn = QPushButton("Authenticate")
        self.auth_btn.clicked.connect(self._authenticate)
        self.connect_btn = QPushButton("Connect / Test")
        self.connect_btn.clicked.connect(self._connect)
        self.conn_status = QLabel("Status: Not connected")
        self.conn_status.setStyleSheet("color: #888;")

        conn_lay.addWidget(QLabel("Project ID:"), 0, 0)
        conn_lay.addWidget(self.project_edit, 0, 1)
        conn_lay.addWidget(self.auth_btn, 0, 2)
        conn_lay.addWidget(self.connect_btn, 0, 3)
        conn_lay.addWidget(self.conn_status, 1, 0, 1, 4)
        root.addWidget(conn_grp)

        # ── Sensor & Dates ────────────────────────────────────────────────────
        sensor_grp = QGroupBox("2. Sensor & Date Range")
        sensor_lay = QGridLayout(sensor_grp)

        self.sensor_combo = QComboBox()
        self.sensor_combo.addItems(list(SENSORS.keys()))
        self.sensor_combo.currentTextChanged.connect(self._update_indices)

        today = QDate.currentDate()
        one_year_ago = today.addDays(-365)

        self.start_date = QDateEdit(one_year_ago)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date = QDateEdit(today)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 1000)
        self.scale_spin.setValue(30)
        self.scale_spin.setSuffix(" m")
        self.scale_spin.setToolTip("Output pixel size (spatial resolution)")

        self.cloud_cb = QCheckBox("Apply cloud masking")
        self.cloud_cb.setChecked(True)

        sensor_lay.addWidget(QLabel("Sensor:"), 0, 0)
        sensor_lay.addWidget(self.sensor_combo, 0, 1)
        sensor_lay.addWidget(QLabel("Scale:"), 0, 2)
        sensor_lay.addWidget(self.scale_spin, 0, 3)
        sensor_lay.addWidget(QLabel("Start:"), 1, 0)
        sensor_lay.addWidget(self.start_date, 1, 1)
        sensor_lay.addWidget(QLabel("End:"), 1, 2)
        sensor_lay.addWidget(self.end_date, 1, 3)
        sensor_lay.addWidget(self.cloud_cb, 2, 0, 1, 2)
        root.addWidget(sensor_grp)

        # ── AOI ───────────────────────────────────────────────────────────────
        aoi_grp = QGroupBox("3. Area of Interest (AOI)")
        aoi_lay = QHBoxLayout(aoi_grp)

        self.draw_btn = QPushButton("Draw Rectangle on Map")
        self.draw_btn.setStyleSheet(
            "QPushButton { background: #1a5276; color: white; "
            "border-radius: 4px; padding: 4px 8px; }"
            "QPushButton:hover { background: #21618c; }")
        self.draw_btn.clicked.connect(self._start_draw)

        self.aoi_label = QLabel("No AOI selected")
        self.aoi_label.setStyleSheet("color: #888;")

        aoi_lay.addWidget(self.draw_btn)
        aoi_lay.addWidget(self.aoi_label, 1)
        root.addWidget(aoi_grp)

        # ── Output ────────────────────────────────────────────────────────────
        out_grp = QGroupBox("4. Output Folder")
        out_lay = QHBoxLayout(out_grp)
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Folder where GeoTIFFs will be saved...")
        btn_out = QPushButton("Browse...")
        btn_out.setFixedWidth(90)
        btn_out.clicked.connect(self._browse_output)
        out_lay.addWidget(self.output_edit)
        out_lay.addWidget(btn_out)
        root.addWidget(out_grp)

        # ── Indices ───────────────────────────────────────────────────────────
        idx_grp = QGroupBox("5. Select Indices")
        idx_lay = QVBoxLayout(idx_grp)

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        btn_all.setFixedWidth(100); btn_none.setFixedWidth(100)
        btn_row.addWidget(btn_all); btn_row.addWidget(btn_none)
        btn_row.addStretch()
        idx_lay.addLayout(btn_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(140)
        self.scroll_content = QWidget()
        self.scroll_layout = QGridLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        idx_lay.addWidget(self.scroll_area)
        root.addWidget(idx_grp)
        self._update_indices(self.sensor_combo.currentText())

        # ── Progress & log ────────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        log_grp = QGroupBox("Log")
        log_lay = QVBoxLayout(log_grp)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        self.log_box.setFont(QFont("Courier", 9))
        log_lay.addWidget(self.log_box)
        root.addWidget(log_grp)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        self.run_btn = QPushButton("Run - Compute & Download Indices")
        self.run_btn.setFixedHeight(36)
        self.run_btn.setStyleSheet(
            "QPushButton { background: #1e8449; color: white; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #239b56; }")
        self.run_btn.clicked.connect(self._run)
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.reject)
        btn_bar.addWidget(self.run_btn)
        btn_bar.addWidget(close_btn)
        root.addLayout(btn_bar)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _authenticate(self):
        from .gee_auth import authenticate
        self._log("Opening GEE authentication browser...")
        ok, msg = authenticate()
        self._log(msg)
        if not ok:
            QMessageBox.warning(self, "GEE Authentication", msg)

    def _connect(self):
        from .gee_auth import initialize
        project = self.project_edit.text().strip() or None
        self._log("Connecting to GEE...")
        ok, msg = initialize(project)
        self._log(msg)
        if ok:
            self.conn_status.setText("Status:  Connected")
            self.conn_status.setStyleSheet("color: #1e8449; font-weight: bold;")
        else:
            self.conn_status.setText("Status:  Connection failed")
            self.conn_status.setStyleSheet("color: #c0392b;")
            QMessageBox.critical(self, "GEE Connection", msg)

    def _update_indices(self, sensor_name):
        self._checkboxes = {}
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        indices = SENSORS.get(sensor_name, {}).get("indices", {})
        row, col = 0, 0
        for name, (_, req, desc) in indices.items():
            cb = QCheckBox(name.replace("_", " "))
            cb.setChecked(True)
            cb.setToolTip(f"{desc}\nBands: {', '.join(req)}")
            self._checkboxes[name] = cb
            self.scroll_layout.addWidget(cb, row, col)
            col += 1
            if col == 2:
                col = 0; row += 1

        # Set recommended scale for sensor
        defaults = {
            "Sentinel-2": 20, "Landsat 8": 30, "Landsat 9": 30,
            "Landsat 7": 30, "Landsat 5": 30, "ASTER": 15,
        }
        self.scale_spin.setValue(defaults.get(sensor_name, 30))

    def _start_draw(self):
        self.hide()
        canvas = self.iface.mapCanvas()
        self._prev_tool = canvas.mapTool()
        self._aoi_tool = RectangleAOITool(canvas)
        self._aoi_tool.rectangleSelected.connect(self._on_aoi_drawn)
        canvas.setMapTool(self._aoi_tool)

    def _on_aoi_drawn(self, rect):
        self._aoi_rect = rect
        # Restore previous tool
        if self._prev_tool:
            self.iface.mapCanvas().setMapTool(self._prev_tool)
        self.show()
        self.raise_()
        self.aoi_label.setText(
            f"AOI: ({rect.xMinimum():.4f}, {rect.yMinimum():.4f}) - "
            f"({rect.xMaximum():.4f}, {rect.yMaximum():.4f})")
        self.aoi_label.setStyleSheet("color: #1e8449; font-weight: bold;")

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_edit.text() or "")
        if folder:
            self.output_edit.setText(folder)

    def _set_all_checks(self, state):
        for cb in self._checkboxes.values():
            cb.setChecked(state)

    def _run(self):
        from .gee_auth import is_initialized
        if not is_initialized():
            QMessageBox.warning(self, "Not Connected",
                                "Please connect to GEE first (step 1).")
            return

        if self._aoi_rect is None:
            QMessageBox.warning(self, "No AOI",
                                "Please draw an AOI on the map (step 3).")
            return

        output_folder = self.output_edit.text().strip()
        if not output_folder:
            QMessageBox.warning(self, "No Output Folder",
                                "Please select an output folder (step 4).")
            return

        selected = [n for n, cb in self._checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "No Indices",
                                "Select at least one index to compute.")
            return

        # Convert AOI rect to WGS84 lon/lat for GEE
        crs_src = self.iface.mapCanvas().mapSettings().destinationCrs()
        crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(
            crs_src, crs_wgs84, QgsProject.instance())

        r = self._aoi_rect
        corners = [
            (r.xMinimum(), r.yMinimum()),
            (r.xMaximum(), r.yMinimum()),
            (r.xMaximum(), r.yMaximum()),
            (r.xMinimum(), r.yMaximum()),
        ]
        from qgis.core import QgsPointXY
        aoi_coords = []
        for x, y in corners:
            pt = transform.transform(QgsPointXY(x, y))
            aoi_coords.append([pt.x(), pt.y()])

        from .export_worker import ExportWorker
        self.run_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self._worker = ExportWorker(
            sensor=self.sensor_combo.currentText(),
            aoi_coords=aoi_coords,
            start_date=self.start_date.date().toString("yyyy-MM-dd"),
            end_date=self.end_date.date().toString("yyyy-MM-dd"),
            selected_indices=selected,
            output_folder=output_folder,
            scale=self.scale_spin.value(),
            cloud_masking=self.cloud_cb.isChecked(),
            project_id=self.project_edit.text().strip() or None,
        )
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.log.connect(self._log)
        self._worker.layer_ready.connect(self._load_layer)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _load_layer(self, name, path):
        """Add exported GeoTIFF to QGIS canvas."""
        layer = QgsRasterLayer(path, name)
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self._log(f"  Added to QGIS: {name}")

    def _on_finished(self, success, message):
        self.run_btn.setEnabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self._log("\n" + message)
        if success:
            QMessageBox.information(self, "Done!", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def _log(self, text):
        self.log_box.append(text)
        self.log_box.ensureCursorVisible()
