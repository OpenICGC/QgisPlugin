# -*- coding: utf-8 -*-
"""
*******************************************************************************
OpenICGC
                                 A QGIS plugin

Plugin for accessing open data published by the Cartographic and Geological 
Institute of Catalonia (Catalan mapping agency).
Includes spatial toponymic searches, streets, roads, coordinates in different 
reference systems and load of WMS base layers of Catalonia.

                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat

This script initializes the plugin, making it known to QGIS.

*******************************************************************************
"""

# pylint: disable=C0103
# noinspection PyPep8Naming
def classFactory(iface):
    """Load OpenICGC plugin class from file OpenICGC.
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .openicgc import OpenICGC
    return OpenICGC(iface)
# pylint: enable=C0103