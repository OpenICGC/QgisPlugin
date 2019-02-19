# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OpenICGC
                                 A QGIS plugin
 Cerca zones geogràfiques per toponim, carrer, referència cadastra o coordenades
                             -------------------
        begin                : 2019-01-18
        copyright            : (C) 2019 by ICGC
        email                : joan.arnaldich@icgc.cat
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""

# pylint: disable=C0103
# noinspection PyPep8Naming
def classFactory(iface):
    """Load OpenICGCPlugin class from file OpenICGC.
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .openicgc import OpenICGC
    return OpenICGC(iface)
# pylint: enable=C0103