# -*- coding: utf-8 -*-
"""
Minera Indices GEE — QGIS 3.x Plugin
Main plugin class.
"""

import os

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon


class MineraIndicesGEEPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()

        self.action = QAction(
            icon, "Minera Indices GEE", self.iface.mainWindow())
        self.action.setToolTip(
            "Compute mineral spectral indices via Google Earth Engine")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToRasterMenu("Minera Indices GEE", self.action)

    def unload(self):
        self.iface.removePluginRasterMenu("Minera Indices GEE", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.action:
            self.action.deleteLater()

    def run(self):
        # Check earthengine-api before opening dialog
        from .gee_auth import check_ee_installed
        from qgis.PyQt.QtWidgets import QMessageBox
        ok, msg = check_ee_installed()
        if not ok:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "earthengine-api not found", msg)
            return

        from .mineral_indices_gee_dialog import MineraIndicesGEEDialog
        if self.dialog is None:
            self.dialog = MineraIndicesGEEDialog(
                self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
