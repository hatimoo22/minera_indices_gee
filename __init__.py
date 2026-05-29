# -*- coding: utf-8 -*-
"""
Minera Indices GEE - QGIS Plugin
Mineral spectral indices via Google Earth Engine.
"""


def classFactory(iface):
    from .mineral_indices_gee import MineraIndicesGEEPlugin
    return MineraIndicesGEEPlugin(iface)
