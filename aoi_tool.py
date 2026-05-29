# -*- coding: utf-8 -*-
"""
QGIS rubber-band rectangle draw tool for AOI selection.
"""

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsRectangle, QgsPointXY


class RectangleAOITool(QgsMapTool):
    """
    Click-drag tool that lets the user draw a rectangle on the QGIS canvas.
    Emits rectangleSelected(QgsRectangle) when the user releases the mouse.
    """
    rectangleSelected = pyqtSignal(object)  # QgsRectangle

    def __init__(self, canvas):
        super().__init__(canvas)
        self._canvas = canvas
        self._rubber_band = None
        self._start_point = None
        self._dragging = False
        self.setCursor(Qt.CrossCursor)

    def _init_rubber_band(self):
        self._rubber_band = QgsRubberBand(
            self._canvas, QgsWkbTypes.PolygonGeometry)
        self._rubber_band.setColor(QColor(255, 80, 0, 100))
        self._rubber_band.setStrokeColor(QColor(255, 80, 0, 200))
        self._rubber_band.setWidth(2)

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_point = self.toMapCoordinates(event.pos())
            self._dragging = True
            self._init_rubber_band()

    def canvasMoveEvent(self, event):
        if not self._dragging or self._rubber_band is None:
            return
        end_point = self.toMapCoordinates(event.pos())
        self._update_rubber_band(end_point)

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._dragging:
            return
        self._dragging = False
        end_point = self.toMapCoordinates(event.pos())
        self._update_rubber_band(end_point)

        rect = QgsRectangle(self._start_point, end_point)
        rect.normalize()

        if self._rubber_band:
            self._rubber_band.reset()
        self.rectangleSelected.emit(rect)

    def _update_rubber_band(self, end_point):
        rect = QgsRectangle(self._start_point, end_point)
        rect.normalize()
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self._rubber_band.addPoint(QgsPointXY(rect.xMinimum(), rect.yMinimum()))
        self._rubber_band.addPoint(QgsPointXY(rect.xMaximum(), rect.yMinimum()))
        self._rubber_band.addPoint(QgsPointXY(rect.xMaximum(), rect.yMaximum()))
        self._rubber_band.addPoint(QgsPointXY(rect.xMinimum(), rect.yMaximum()))
        self._rubber_band.closePoints()

    def deactivate(self):
        if self._rubber_band:
            self._rubber_band.reset()
        super().deactivate()
