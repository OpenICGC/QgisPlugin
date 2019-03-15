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

*******************************************************************************
"""

import re
from importlib import reload

# Add a additional library folder to pythonpath
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Support to SOAP connections
import suds
from suds import null
from suds.client import Client
from suds.wsse import Security
# Support to connections with password digest token
from . import wsse
reload(wsse)
from .wsse import UsernameDigestToken

# Import QGIS libraries
from qgis.core import QgsRasterLayer, QgsVectorLayer
# Import the PyQt and QGIS libraries
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QApplication, QComboBox, QMessageBox
# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Add basic plugin functionalities
import qlib3.base.pluginbase
reload(qlib3.base.pluginbase)
from qlib3.base.pluginbase import PluginBase

# Add generic aboug dialog
import qlib3.base.aboutdialog
reload(qlib3.base.aboutdialog)
from qlib3.base.aboutdialog import AboutDialog

# Add geofinder dialog
from . import geofinderdialog
reload(geofinderdialog)
from .geofinderdialog import GeoFinderDialog


class OpenICGC(PluginBase):
    """ Plugin for accessing open data published by ICGC """

    ###########################################################################
    # Plugin constants
    
    # We prepare a toponym mapping with the icon to show
    TOPOICONS_DICT = {
        1:'town.png', 2:'town.png', #Cap municipi, municipi
        3:'flag.png', 17:'flag.png', #Entitat de població, comarca
        4:'build.png', #Edifici
        20:'history.png', #Edifici històric
        21:'house.png', 16:'house.png', #Nucli, barri
        18:'crossroad.png', 19:'crossroad.png', 22:'crossroad.png', 99:'crossroad.png', #diss., diss., e.m.d., llogaret carrerer
        6:'mountain.png', 7:'mountain.png', 8:'mountain.png', 9:'mountain.png', 10:'mountain.png', #Serra, orografia, cim, coll, litoral
        11:'pin.png', #Indret
        12:'equipment.png', #Equipaments
        13:'communications.png', #Comunicacions
        14:'river.png', 15:'river.png' #Curs fluvial, hidrografia
        }



    ###########################################################################
    # Web service management
    
    ## Web Service Cadastre (alternative)
    #cadastral_streets_client = None
    #def get_cadastral_streets_client(self):
    #    if not self.cadastral_streets_client:
    #        # SOAP client configuration
    #        # Available functions: [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #        self.cadastral_streets_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?wsdl") # [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #    return self.cadastral_streets_client    
    
    # Web Service Cadastre. Available functions to call: client.wsdl.services[0].ports[0].methods.keys()
    cadastral_coordinates_client = None 
    def get_cadastral_coordinates_client(self):
        if not self.cadastral_coordinates_client:
            # SOAP client configuration
            # Available functions: [Consulta_CPMRC, Consulta_RCCOOR_Distancia, Consulta_RCCOOR]
            self.cadastral_coordinates_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx?wsdl")
        return self.cadastral_coordinates_client    
    
    # ICGC Web Service. ICGC Web service requires a md5 / base64 encoded security header
    icgc_geoencoder_client = None
    def get_icgc_geoencoder_client(self):
        if not self.icgc_geoencoder_client:
            # Configure connection security 
            wsse_security = Security()
            username_digest_token = UsernameDigestToken('QGIS', 'QGIS')
            wsse_security.tokens.append(username_digest_token)
            # SOAP client configuration with Password Digest 
            # Available functions: [localitzaAdreca, obtenirInfoPunt, localitzaToponim, cercaCaixaUnica, localitzaCruilla, localitzaPK, geocodificacioInversa]
            self.icgc_geoencoder_client = Client(url="http://www.icc.cat/geocodificador/ws/wss_1.0?wsdl", wsse=wsse_security) 
        return self.icgc_geoencoder_client


    ###########################################################################
    # Plugin initialization

    def __init__(self, iface):
        """ Plugin variables initialization """
        
        # Save reference to the QGIS interface
        super().__init__(iface, __file__)

        # This is a constant but I declare it here to be able to use the tr() function
        self.TOOLTIP_HELP = self.tr("""Find:
            Address: municipality, street number or vice versa
                Barcelona, Aribau 86
                Aribau 86, Barcelona
                Barcelona, C/ Aribau 86

            Crossing: municipality, street, street
                Barcelona, Mallorca, Aribau

            Road: road, km
                C32 km 10
                C32, 10

            Toponym: free text
                Barcelona
                Collserola
                Institut Cartografic

            Coordinate: x and EPSG: code (by default coordinate system of the project)
                429394.751 4580170.875
                429394,751 4580170,875
                429394.751 4580170.875 EPSG:25831
                EPSG:4326 1.9767050 41.3297270

            Rectangle: north east southeast EPSG: code (by default system coordinates of the project)
                427708.277 4582385.829 429708.277 4580385.829
                427708,277 4582385,829 429708,277 4580385,829
                427708.277 4582385.829 429708.277 4580385.829 EPSG:25831
                EPSG:25831 427708.277 4582385.829 429708.277 4580385.829

            Cadastral reference: ref (also works with the first 14 digits)
                9872023 VH5797S 0001 WX
                13 077 A 018 00039 0000 FP
                13077A018000390000FP""")

    def initGui(self, debug=False):
        """ GUI initializacion """
        # Plugin registration in the plugin manager
        self.gui.configure_plugin(self.metadata.get_name(), self.about, QIcon(":/plugins/openicgc/icon.png"))
                       
        # About dialog configuration
        self.about_dlg = AboutDialog(self.metadata.get_name(), self.metadata.get_info(), QIcon(":/plugins/openicgc/icon.png"), 
            self.tr("About"), False, parent=self.iface.mainWindow())

        # Add combobox to search
        self.combobox = QComboBox()
        self.combobox.setFixedSize(QSize(250,24))
        self.combobox.setEditable(True)              
        self.combobox.setToolTip(self.TOOLTIP_HELP)
        self.combobox.activated.connect(self.run) # Press intro and select combo value
        # Add new toolbar with plugin options (using pluginbase functions)
        self.toolbar = self.gui.configure_toolbar(self.tr("Spatial search"), [
            self.tr("Find"), # Label text
            self.combobox, # Editable combobox
            (self.tr("Find"), self.run, QIcon(":/plugins/openicgc/images/geofinder.png")), # Action button
            ])
        # Add a new button with access to ICGS WMS layers
        self.tools.add_tool_WMS_background_maps_lite(self.tr("Spatial search"), 
            self.tr("Background maps"), self.tr("Delete background maps"), self.tr("Background maps"))
        # Add style options
        self.gui.add_to_toolbar(self.toolbar, [
            (self.tr("Paint styles"), None, QIcon(":/plugins/openicgc/images/style.png"), [
                (self.tr("Transparence"),
                    lambda:self.tools.show_transparency_dialog(self.tr("Transparence"), self.iface.mapCanvas().currentLayer()) if type(self.iface.mapCanvas().currentLayer()) in [QgsRasterLayer, QgsVectorLayer] else None, 
                    QIcon(":/plugins/openicgc/images/transparency.png")),
                (self.tr("Desaturate selected raster layer"), 
                    lambda:self.layers.set_saturation(self.iface.mapCanvas().currentLayer(), -100, True) if type(self.iface.mapCanvas().currentLayer()) is QgsRasterLayer else None,
                    QIcon(":/plugins/openicgc/images/desaturate.png")),
                ])
            ])
        # Add plugin reload button (debug purpose)
        if debug:
            self.gui.add_to_toolbar(self.toolbar, [
                "---",
                (self.tr("Reload Open ICGC"), self.reload_plugin, QIcon(":/lib/qlib3/base/images/python.png")),
                ])

    def unload(self):
        """ Release of resources """
        # Parent PluginBase class release all GUI resources created with their functions
        super().unload()

    def run(self, checked): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Basic plugin call, which reads the text of the combobox and the search for the different web services available """
        self.find(self.combobox.currentText())

    def about(self, checked): # I add checked param, because the mapping of the signal triggered passes a parameter
        """ Show plugin information (about dialog) """
        self.about_dlg.do_modal()


    ###########################################################################
    # Search implementation

    def find(self, user_text):
        """ Find the text indicated in the different web services available.
            Show results in a dialog and center the map on the item selected by the user """

        print(u"Find: %s" % user_text)
        
        # Find text and return a list of dictionaries with results
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        dict_list = self.find_data(user_text)
        print(u"Found %d: %s %s" % (len(dict_list), ", ".join([data_dict['nom'] for data_dict in dict_list[:10]]), "..." if len(dict_list) > 10 else ""))
        QApplication.restoreOverrideCursor()

        # If we have a rectangle, we do not have to do anything, we get the coordinates and access
        if len(dict_list) == 1 and dict_list[0]['nom'].startswith("Rectangle"):
            # Get rectangle coordinates
            west = dict_list[0]['west']
            north = dict_list[0]['north']
            east = dict_list[0]['east']
            south = dict_list[0]['south']
            epsg = dict_list[0]['epsg']
            # We resituate the map (implemented in parent PluginBase)
            self.set_map_rectangle(west, north, east, south, epsg)
        
        else:
            # We show the found places in a dialog
            dlg = GeoFinderDialog(dict_list, self.TOPOICONS_DICT)
            selection = dlg.get_selection_index()
            if selection < 0:
                return
            print("Selected: %s" % dict_list[selection]['nom'])

            # We get point coordinates
            epsg = dict_list[selection]['epsg']
            x = dict_list[selection]['x']
            y = dict_list[selection]['y']
            if not x or not y:
                print("Error, no coordinates found")
                QMessageBox.warning(self.iface.mainWindow(), self.tr("Spatial search"),    
                    self.tr("Error, location without coordinates"))
                return

            # We resituate the map (implemented in parent PluginBase)
            self.set_map_point(x, y, epsg)

        print(u"")

    def find_data(self, text, find_all=False, recursive=True):
        """ Returns a list of dictionaries with the sites found from the indicated text """

        # Let's see if we pass a ground rectangle 
        west, north, east, south, epsg = self.get_rectangle(text)
        if west and north and east and south: 
            return self.find_rectangle(west, north, east, south, epsg)

        # We detect if we pass a ground coordinate
        x, y, epsg = self.get_coordinate(text)
        if x and y: 
            return self.find_coordinate(x, y, epsg)

        # Let's see if we pass a road
        road, km = self.get_road(text)
        if road and km:
            return self.find_road(road, km)

        # Let's see if we pass a crossroads
        municipality, type1, name1, type2, name2 = self.get_crossing(text)
        if municipality and name1 and name2:
            return self.find_crossing(municipality, type1, name1, type2, name2, find_all)

	    # Let's see if we pass an address
        municipality, type, name, number = self.get_address(text)
        if municipality and name and number:
            return self.find_adress(municipality, type, name, number, find_all, recursive)

	    # We detect if we pass a cadastral reference
        cadastral_ref = self.get_cadastral_ref(text)
        if cadastral_ref:
            return self.find_cadastral_ref(cadastral_ref);

        # If you do not meet any of the above, we are looking for a place name
        return self.find_placename(text)

    def get_rectangle(self, text):
        """ Detects a coordinate rectangle from the text
            Accept texts with 4 reals and optionally an epsg code        
            For example: 1.0 2.0 3.0 4.0 EPSG:0
                         EPSG:0 1.0 2.0 3.0 4.0 
                         1.0 2.0 3.0 4.0 
            Return west, north, east, south, epsg """        

        # We detect 4 reals (and EPSG code) with a regular expression
        # [EPSG:<int>] <real> <real> <real> <real> [EPSG:<int>]
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s([+-]?[0-9]*[.,]?[0-9]+)\s*(?:\s+EPSG:(\d+))?\s*$" 
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            epsg1, west, north, east, south, epsg2 = found.groups()
            west = float(west.replace(',', '.'))
            north = float(north.replace(',', '.'))
            east = float(east.replace(',', '.'))
            south = float(south.replace(',', '.'))
            epsg = epsg1 if epsg1 else epsg2

        else:
            west, north, east, south, epsg = None, None, None, None, None

        return west, north, east, south, epsg

    def get_coordinate(self, text):
        """ Detects a coordinate from the text
            Accepts texts with 2 reals and optionally an epsg code
            For example: 1.0 2.0 EPSG:0
                         EPSG:0 1.0 2.0 EPSG:0
                         1.0 2.0
            return x, y, epsg """

        # We detect 2 reals (and EPSG code) with a regular expression
        # [EPSG:<int>] <real> <real> [EPSG:<int>]
        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s*([+-]?[0-9]*[.,]?[0-9]+)(?:\s+EPSG:(\d+))?\s*$" 
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            epsg1, x, y, epsg2 = found.groups()
            epsg = int(epsg1) if epsg1 else int(epsg2) if epsg2 else None
            x = float(x.replace(',', '.'))
            y = float(y.replace(',', '.'))
        else:
            x, y, epsg = None, None, None

        return x, y, epsg

    def get_road(self, text):
        """ Detects a road from the text
            Accept road / km
            For example: C32 km 10
                         C32, 10
            return road, km """

        # We use regular expression
        # <road> [km|,] <int>
        expression = r'^\s*(\w+)\s*(?:(?:km)|,)\s*(\d+)\s*$'
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            road, km = found.groups()
        else:
            road, km = None, None

        return road, km

    def get_crossing(self, text):
        """ Detects a crossword from the text
            Accept information of crossroads (municipality, street, street)
            For example: Barcelona, Muntaner, C/ Aragó 
            return municipality, type1, name1, type2, name2 """

        # We use regular expression
        # <municipality>, [street_type] <street>, [street_type] <street>
        expression = r"\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*"
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            municipality, type1, street1, type2, street2 = found.groups()        
        else:
            municipality, type1, street1, type2, street2 = None, None, None, None, None
        
        return municipality, type1, street1, type2, street2

    def get_address(self, text):
        """ Detects an adress from the text
            Accept information about the address of a municipality
            For example: Barcelona, Aribau 86
                         Aribau 86, Barcelona
                         Barcelona, C/ Aribau nº 86
                         Barcelona, Avd. Diagonal nº 86
                         Barcelona, C/ Aragó 1-5
            return municipality, type, name, number """

        # We use regular expression
        # [<municipality>, [street_type] <street> [nº] <number> | [street_type] <street> [nº] <number>, <municipality>]
        # To accept accents I use the range: \ u00C0- \ u017F
        expression = r"^\s*(?:([\D\s]+)\s*,)?\s*([\w]+[./])?\s*([\D\s]+)\s+(?:nº)?\s*,*([\d-]+)\s*(?:[,.]\s*([\D\s]+[\D]))?\s*$" # [ciutat,] [C/] <carrer> <numero> [, ciutat]
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            municipality1, type, street, number, municipality2 = found.groups()
            municipality = municipality1 if municipality1 else municipality2
        else:
            municipality, type, street, number = None, None, None, None

        return municipality, type, street, number

    def get_cadastral_ref(self, text):
        """ Detects a cadastral reference from the text
            Accept a cadastral reference code in the 3 official formats
            For example: 9872023 VH5797S 0001 WX
                 13 077 A 018 00039 0000 FP
                 13077A018000390000FP (also works with the first 14 digits)
            return cadastra_ref """
        
        # No spaces should occupy 14 or 20 alphanumeric characters
        cleaned_text = text.replace(' ', '')        
        if len(cleaned_text) not in (14, 20):
            return None
        # Validate that it do not have symbols with a regular expression
        expression = r'(\w+)'
        found = re.search(expression, cleaned_text, re.IGNORECASE)  
        if found:           
            cadastral_ref = found.groups()[0]
        else:
            cadastral_ref = None
        
        return cadastral_ref

    def find_rectangle(self, west, north, east, south, epsg):
        """ Returns a list with a dictionary with the coordinates of the rectangle """

        if not epsg:
            epsg = int(self.project.get_epsg())
        print(u"Rectangle: %s %s %s %s EPSG:%s" % (west, north, east, south, epsg))
        dicts_list = [{
            'nom':'Rectangle (%s %s %s %s)' % (west, north, east, south),
            'west': float(west),
            'north': float(north),
            'east': float(east),
            'south': float(south),
            'epsg': int(epsg)
            }]
        return dicts_list

    def find_coordinate(self, x, y, epsg):
        """ Returns a list of dictionaries with the sites found at the indicated point """

        if not epsg:
            epsg = int(self.project.get_epsg())
        print(u"Coordinate: %s %s EPSG:%s" % (x, y, epsg))

        # We convert the coordinates to ETRS89 UTM31N to do the query
        nom = "Point: %s %s (EPSG:%s)" % (x, y, epsg), 
        query_x, query_y = self.crs.transform_point(x, y, epsg, 25831)

        # We execute the query
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_tuple_list = self.get_icgc_geoencoder_client().service.geocodificacioInversa(
                puntUTMETRS89 = {'X': query_x, 'Y': query_y}
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        
        # We convert the result to a unique format
        dicts_list = [{
            'nom': ("%s (%s)" % (res_dict['Descripcio'], nom)) if 'Descripcio' in res_dict else ("%s, %s %s %s-%s" % (res_dict['municipi']['nom'], res_dict['via']['Tipus'], res_dict['via']['Nom'], res_dict['portalParell'], res_dict['portalSenar'])) if 'portalParell' in res_dict else ("%s, %s %s" % (res_dict['municipi']['nom'], res_dict['via']['Tipus'], res_dict['via']['Nom'])),
            'idTipus': u'', 
            'nomTipus': u'Adreça', 
            'nomMunicipi': res_dict['municipi']['nom'],
            'nomComarca': res_dict['comarca']['nom'],
            'x': x, 
            'y': y,
            'epsg': epsg
            } for (label_adrecaInversa, res_dict) in res_tuple_list]
        return dicts_list

    def find_road(self, road, km):
        """ Returns a list of dictionaries with the roads found with the indicated nomenclature """

        print(u"Road: %s %s" % (road, km))

        # We execute the query
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaPK(
                nomCarretera = road, 
                KM = km
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        
        # We convert the result to a unique format
        dicts_list = [{
            'nom': "%s" % res_dict['PkXY'],
            'idTipus': '', 
            'nomTipus': u'Via', 
            'nomMunicipi': u'', 
            'nomComarca': u'', 
            'x': float(res_dict['coordenadesETRS89UTM']['X']) if 'coordenadesETRS89UTM' in res_dict else None, 
            'y': float(res_dict['coordenadesETRS89UTM']['Y']) if 'coordenadesETRS89UTM' in res_dict else None,
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    def find_crossing(self, municipality, type1, street1, type2, street2, find_all):
        """ Returns a list of dictionaries with crossings found with the indicated nomenclature """

        print(u"Crossing %s, %s %s / %s %s" % (municipality, type1, street1, type2, street2))

        # We execute the query
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaCruilla(
                Poblacio = municipality, 
                Vies = [{'Tipus':type1, 'Nom':street1}, 
                {'Tipus':type2, 'Nom':street2}],
                TrobaTots = ("SI" if find_all else "NO"))
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        
        # We convert the result to a unique format
        dicts_list = [{
            'nom': "%s" % res_dict['CruillaXY'],
            'idTipus': '', 
            'nomTipus': u'Cruilla', 
            'nomMunicipi': res_dict['Cruilla']['Poblacio'], 
            'nomComarca': res_dict['Cruilla']['Comarca']['nom'], 
            'x': float(res_dict['CoordenadesETRS89UTM'][0]['X']) if 'CoordenadesETRS89UTM' in res_dict else None, 
            'y': float(res_dict['CoordenadesETRS89UTM'][0]['Y']) if 'CoordenadesETRS89UTM' in res_dict else None,
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    def find_adress(self, municipality, type, street, number, find_all, recursive):
        """ Returns a list of dictionaries with the addresses found with the indicated nomenclature """

        print(u"Adress: %s, %s %s %s" % (municipality, type, street, number))

        # We execute the query
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaAdreca(
                Poblacio = municipality, 
                Via = {'Tipus':type, 'Nom':street}, 
                Portal = null(), 
                CodiPostal = "NO", 
                Llogaret = null(), 
                Comarca = null(), 
                InePoblacio = null(), 
                TrobaTots = ("SI" if find_all else "NO"), 
                PortalTextual = number)
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        
        # We convert the result to a unique format
        dicts_list = [{
            'nom': "%s" % res_dict['AdrecaXY'],
            'idTipus': '', 
            'nomTipus': 'Adreça', 
            'nomMunicipi': res_dict['Adreca']['Poblacio'], 
            'nomComarca': res_dict['Adreca']['Comarca']['nom'], 
            'x': float(res_dict['CoordenadesETRS89UTM']['X']) if 'CoordenadesETRS89UTM' in res_dict else None, 
            'y': float(res_dict['CoordenadesETRS89UTM']['Y']) if 'CoordenadesETRS89UTM' in res_dict else None,
            'epsg': 25831
            } for res_dict in res_dicts_list]

        # We detect locations without coordinates and try to obtain the coordinate by doing the search on the name
        # returned in the initial request
        if recursive:
            for res_dict in dicts_list:
                if not res_dict['x'] or not res_dict['y']:
                    alternative_res_dict_list = self.find_data(res_dict['nom'], recursive=False)
                    if alternative_res_dict_list:
                        alternative_res_dict = alternative_res_dict_list[0]
                        res_dict['x'] = alternative_res_dict['x']
                        res_dict['y'] = alternative_res_dict['y']
        return dicts_list
        
    def find_cadastral_ref(self, cadastral_ref):
        """ Returns a list with a dictionary with the indicated cadastral reference """

        print(u"Cadastral ref: %s" % cadastral_ref)
        # Examples of cadastral reference:
        # 9872023 VH5797S 0001 WX
        # 13 077 A 018 00039 0000 FP
        # 13077A018000390000FP

        # We execute the query
        print(u"URL: %s" % self.get_cadastral_coordinates_client().wsdl.url)
        clean_cadastra_ref = cadastral_ref.replace(' ', '')[:14]
        try:
            res_dict = self.get_cadastral_coordinates_client().service.Consulta_CPMRC(
                Provincia = "", 
                Municipio = "", 
                SRS = "EPSG:%s" % 25831, 
                RefCat = clean_cadastra_ref) ##Provincia, municipio, srs, ref catastral
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_cadastral_coordinates_client().last_sent()))
            raise e
        if res_dict['control']['cuerr'] != '0':
            raise Exception(str(res_dict['lerr']['err']['des']))

        # We evaluate the result
        # If we have found a match int the response, we separate the street, municipality and district
        adress = res_dict['coordenadas']['coord']['ldt']
        expression = r"([\D]+ \d+) ([\D]+) \(([\D]+)\)"
        found = re.search(expression, adress, re.IGNORECASE)
        if not found:
            expression = r"(.+)\.([\D]+) \(([\D]+)\)"
            found = re.search(expression, adress, re.IGNORECASE)
        if not found:
            expression = r"(.+)()\(([\D]+)\)"
            found = re.search(expression, adress, re.IGNORECASE)        
        if found:
            street, municipality1, municipality2 = found.groups()
        else:
            street = adress
            municipality1 = u''
            municipality2 = u''

        # We convert the result to a unique format
        dicts_list = [{
            'nom': "%s%s (%s)" % (res_dict['coordenadas']['coord']['pc']['pc1'], res_dict['coordenadas']['coord']['pc']['pc2'], street), 
            'idTipus': '', 
            'nomTipus': u'Referència Cadastral', 
            'nomMunicipi': municipality1, 
            'nomComarca': municipality2, 
            'x': float(res_dict['coordenadas']['coord']['geo']['xcen']), 
            'y': float(res_dict['coordenadas']['coord']['geo']['ycen']),
            'epsg': int(res_dict['coordenadas']['coord']['geo']['srs'].replace('EPSG:', ''))
            }]        
        return dicts_list
   
    def find_placename(self, text):
        """ Returns a list of dictionaries with the toponyms found with the indicated nomenclature """

        print(u"Placement: %s" % text)

        # We execute the query
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaToponim(
                text
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        
        # We convert the result to a unique format
        dicts_list = [{
            'nom': res_dict['Nom'],
            'idTipus': int(res_dict['IdTipus']), 
            'nomTipus': res_dict['NomTipus'], 
            'nomMunicipi': res_dict['NomMunicipi'] if 'NomMunicipi' in res_dict else u'', 
            'nomComarca': res_dict['NomComarca']if 'NomComarca' in res_dict else u'', 
            'x': float(res_dict['CoordenadesETRS89UTM']['X']) if 'CoordenadesETRS89UTM' in res_dict else None, 
            'y': float(res_dict['CoordenadesETRS89UTM']['Y']) if 'CoordenadesETRS89UTM' in res_dict else None,
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    ### Alternative implementation not used ...
    ##def find_placename_json(self, text):
    ##    print(u"Placement: %s" % text)
    ##    # We send a request for a place name and read the coordinates
    ##    ##url = "http://www.icc.cat/vissir2/php/getToponim.php?nom=%s" % urllib2.quote(text.toLatin1())
    ##    ##url = "http://www.icc.cat/web/content/php/getToponim/getToponim.php?nom=%s" % urllib2.quote(text.toLatin1())
    ##    url = "http://www.icc.cat/web/content/php/getToponim/getToponim.php?nom=%s" % urllib2.quote(text.encode('latin1'))
    ##    print(u"URL: %s" % url)
    ##    try:
    ##        response_data = None
    ##        response = urllib2.urlopen(url)
    ##        response_data = response.read()
    ##        response_data = response_data.decode('utf-8').replace('":"', '":u"').replace('null', '""')
    ##        topo_list = eval(response_data)
    ##    except Exception as e:
    ##        print(u"Error %s %s" % (response_data, e))
    ##        return
    ##    #print(u"Return: %s" % topo_list)
    ##
    ##    # Let's parse the answer (for example: Barcelona)
    ##    # [{"nom":"Barcelona","x":"431300","y":"4581740","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"1","nomTipus":"Cap de municipi","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Can Barcelona","x":"483074","y":"4628657","idMunicipi":"172137","nomMunicipi":"Vidreres","idComarca":"34","nomComarca":"Selva","idTipus":"4","nomTipus":"Edificació","municipis":{"172137":"Vidreres","170335":"Caldes de Malavella"},"comarques":{"34":"Selva"}},
    ##    #  {"nom":"Fira Barcelona","x":"429059","y":"4580842","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Mas de Barcelona","x":"266901","y":"4555198","idMunicipi":"430228","nomMunicipi":"Batea","idComarca":"37","nomComarca":"Terra Alta","idTipus":"4","nomTipus":"Edificació","municipis":{"430228":"Batea"},"comarques":{"37":"Terra Alta"}},
    ##    #  {"nom":"Mas de Barcelona","x":"305887","y":"4549934","idMunicipi":"431508","nomMunicipi":"Tivissa","idComarca":"30","nomComarca":"Ribera d'Ebre","idTipus":"4","nomTipus":"Edificació","municipis":{"431508":"Tivissa"},"comarques":{"30":"Ribera d'Ebre"}},
    ##    #  {"nom":"Càmping Barcelona","x":"456909","y":"4600328","idMunicipi":"081213","nomMunicipi":"Mataró","idComarca":"21","nomComarca":"Maresme","idTipus":"12","nomTipus":"Equipament","municipis":{"081213":"Mataró"},"comarques":{"21":"Maresme"}},
    ##    #  {"nom":"Clot de Barcelona","x":"420705","y":"4649943","idMunicipi":"081496","nomMunicipi":"Olost","idComarca":"24","nomComarca":"Osona","idTipus":"7","nomTipus":"Orografia","municipis":{"081496":"Olost","081712":"Prats de Lluçanès"},"comarques":{"24":"Osona"}},
    ##    #  {"nom":"Ecoparc Barcelona","x":"427925","y":"4575521","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Moll de Barcelona","x":"431720","y":"4580459","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"13","nomTipus":"Comunicacions","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Port de Barcelona","x":"429782","y":"4577562","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"13","nomTipus":"Comunicacions","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Duana de Barcelona","x":"431325","y":"4580945","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"13","nomTipus":"Comunicacions","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Raval de Barcelona","x":"433206","y":"4672335","idMunicipi":"171479","nomMunicipi":"Ripoll","idComarca":"31","nomComarca":"Ripollès","idTipus":"16","nomTipus":"Barri","municipis":{"171479":"Ripoll"},"comarques":{"31":"Ripollès"}},
    ##    #  {"nom":"Torre de Barcelona","x":"469715","y":"4621796","idMunicipi":"170834","nomMunicipi":"Hostalric","idComarca":"34","nomComarca":"Selva","idTipus":"20","nomTipus":"Edificació Històrica","municipis":{"170834":"Hostalric"},"comarques":{"34":"Selva"}},
    ##    #  {"nom":"Cal Viudo Barcelona","x":"481936","y":"4627279","idMunicipi":"172137","nomMunicipi":"Vidreres","idComarca":"34","nomComarca":"Selva","idTipus":"4","nomTipus":"Edificació","municipis":{"172137":"Vidreres"},"comarques":{"34":"Selva"}},
    ##    #  {"nom":"Hotel Arts Barcelona","x":"432894","y":"4582218","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Aeroport de Barcelona","x":"423753","y":"4571988","idMunicipi":"081691","nomMunicipi":"el Prat de Llobregat","idComarca":"11","nomComarca":"Baix Llobregat","idTipus":"13","nomTipus":"Comunicacions","municipis":{"081691":"el Prat de Llobregat"},"comarques":{"11":"Baix Llobregat"}},
    ##    #  {"nom":"Auditori de Barcelona","x":"431954","y":"4583542","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Futbol Club Barcelona","x":"426720","y":"4581609","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Hospital de Barcelona","x":"427356","y":"4582587","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}},
    ##    #  {"nom":"Hotel Melià Barcelona","x":"428331","y":"4582727","idMunicipi":"080193","nomMunicipi":"Barcelona","idComarca":"13","nomComarca":"Barcelonès","idTipus":"12","nomTipus":"Equipament","municipis":{"080193":"Barcelona"},"comarques":{"13":"Barcelonès"}}
    ##    # ]

    ##    # We convert the coordinates to float and keep the epsg
    ##    for topo_dict in topo_list:
    ##        topo_dict['x'] = float(topo_dict['x'])
    ##        topo_dict['y'] = float(topo_dict['y'])
    ##        topo_dict['epsg'] = 23031
    ##    return topo_list
