# -*- coding: utf-8 -*-

"""
/***************************************************************************
 GeoFinder
                                 A QGIS plugin
 Cerca zones geogràfiques per toponim, carrer, referència cadastral
 o coordenades
                             -------------------
        begin                : 2019-01-18
        copyright            : (C) 2019 by ICGC
        email                : albert.adell@icgc.cat
 ***************************************************************************/
"""

import re
from importlib import reload

# Afegim llibreries addicionales del plugin al pythonpath
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# Import per connexions SOAP
import suds
from suds import null
from suds.client import Client
from suds.wsse import Security
# Import connexió amb password DigestToken
from . import wsse
reload(wsse)
from .wsse import UsernameDigestToken

# Import the PyQt and QGIS libraries
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import QApplication, QComboBox
# Initialize Qt resources from file resources_rc.py
from . import resources_rc

# Import plugin base
import qlib3.base.pluginbase
reload(qlib3.base.pluginbase)
from qlib3.base.pluginbase import PluginBase

# Import About
import qlib3.base.aboutdialog
reload(qlib3.base.aboutdialog)
from qlib3.base.aboutdialog import AboutDialog

# Import error manager
import qlib3.base.errors
reload(qlib3.base.errors)
from qlib3.base.errors import generic_handle_error, error_report_manager

# Import the code for the dialog
from . import geofinderdialog
reload(geofinderdialog)
from .geofinderdialog import GeoFinderDialog


class OpenICGC(PluginBase):     
    ###########################################################################
    # Definim constants del plugin
    
    # Preparem un mapeig de tipus de topònim amb la icona a mostrar
    TOPOICONS_DICT = {
        '1':'icon.png', '2':'icon.png', '3':'icon.png', '17':'icon.png', #Cap municipi, municipi, entitat de població, comarca
        '4':'house.png', #Edifici
        '20':'history.png', #Edifici històric
        '21':'build.png', '16':'build.png', #Nucli, barri
        '18':'crossroad.png', '19':'crossroad.png', '22':'crossroad.png', '99':'crossroad.png', #diss., diss., e.m.d., llogaret carrerer
        '6':'mountain.png', '7':'mountain.png', '8':'mountain.png', '9':'mountain.png', '10':'mountain.png', #Serra, orografia, cim, coll, litoral
        '11':'pin.png', #Indret
        '12':'equipment.png', #Equipaments
        '13':'communications.png', #Comunicacions
        '14':'river.png', '15':'river.png' #Curs fluvial, hidrografia
        }


    ###########################################################################
    # Gestió dels serveis web a utilitzar
    
    ## Web Service Cadastre
    #cadastral_streets_client = None # [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #def get_cadastral_streets_client(self):
    #    if not self.cadastral_streets_client:
    #        self.cadastral_streets_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCallejero.asmx?wsdl") # [Consulta_DNPPP, ObtenerNumerero, ObtenerMunicipios, Consulta_DNPLOC, ObtenerCallejero, Consulta_DNPRC, ObtenerProvincias]
    #    return self.cadastral_streets_client    
    
    # Web Service Cadastre. Per consultar crides disponibles fer: client.wsdl.services[0].ports[0].methods.keys()
    cadastral_coordinates_client = None # [Consulta_CPMRC, Consulta_RCCOOR_Distancia, Consulta_RCCOOR]
    def get_cadastral_coordinates_client(self):
        # Configurem el client SOAP
        if not self.cadastral_coordinates_client:
            self.cadastral_coordinates_client = Client("http://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/OVCCoordenadas.asmx?wsdl") # [Consulta_CPMRC, Consulta_RCCOOR_Distancia, Consulta_RCCOOR]
        return self.cadastral_coordinates_client    
    
    # Web Service ICGC. Per el WS de l'ICC cal afegir capçalera de seguretat codificada md5 / base64
    icgc_geoencoder_client = None # [localitzaAdreca, obtenirInfoPunt, localitzaToponim, cercaCaixaUnica, localitzaCruilla, localitzaPK, geocodificacioInversa]
    def get_icgc_geoencoder_client(self):
        # Configurem la seguretat de la connexió
        wsse_security = Security()
        username_digest_token = UsernameDigestToken('QGIS', 'QGIS')
        wsse_security.tokens.append(username_digest_token)
        # Configurem el client SOAP amb Password Digest
        if not self.icgc_geoencoder_client:
            self.icgc_geoencoder_client = Client(url="http://www.icc.cat/geocodificador/ws/wss_1.0?wsdl", wsse=wsse_security) # [localitzaAdreca, obtenirInfoPunt, localitzaToponim, cercaCaixaUnica, localitzaCruilla, localitzaPK, geocodificacioInversa]
        return self.icgc_geoencoder_client


    ###########################################################################
    # Inicialització del plugin

    def __init__(self, iface):
        """ Inicialització de variables i serveis del plugin """        
        # Save reference to the QGIS interface
        super().__init__(iface, __file__)

        # Inicialitzem el diccionari de traduccions
        self.initLanguages()

    def initLanguages(self):
        # Català
        self.translation.set_text(self.translation.LANG_CA, "FIND", "Cerca espacial")
        self.translation.set_text(self.translation.LANG_CA, "FIND_LABEL", "Cercar")
        self.translation.set_text(self.translation.LANG_CA, "ABOUT", "Sobre Open ICGC")
        self.translation.set_text(self.translation.LANG_CA, "RELOAD", "Recarregar Open ICGC")
        self.translation.set_text(self.translation.LANG_CA, "BACKGROUND_MAPS", "Mapes de fons")
        self.translation.set_text(self.translation.LANG_CA, "BAGROUND_MAPS_DELETE", "Esborrar mapes de fons")
        self.translation.set_text(self.translation.LANG_CA, "TOOLTIP_HELP", """Cercar:
            Adreça: municipi, carrer número o al revés
               Barcelona, Aribau 86
               Aribau 86, Barcelona
               Barcelona, C/ Aribau 86

            Cruilla: municipi, carrer, carrer
               Barcelona, Mallorca, Aribau

            Carretera: carretera, km
               C32 km 10
               C32, 10

            Topònim: text lliure
               Barcelona
               Collserola
               Institut Cartogràfic

            Coordenada: x y EPSG:codi (per defecte sistema de coordenades del projecte)
               429394.751 4580170.875
               429394,751 4580170,875
               429394.751 4580170.875 EPSG:25831
               EPSG:4326 1.9767050 41.3297270

            Rectangle: oest nord est sud EPSG:codi (per defecte sistema coordenades del projecte)
               427708.277 4582385.829 429708.277 4580385.829
               427708,277 4582385,829 429708,277 4580385,829
               427708.277 4582385.829 429708.277 4580385.829 EPSG:25831
               EPSG:25831 427708.277 4582385.829 429708.277 4580385.829

            Referència cadastral: ref (també funciona amb els 14 primers dígits)
               9872023 VH5797S 0001 WX
               13 077 A 018 00039 0000 FP
               13077A018000390000FP           
            """)
        self.translation.set_text(self.translation.LANG_CA, "TOPO_HEADER", ["Nom", "Tipus", "Municipi", "Comarca"])

        # Castellà
        self.translation.set_text(self.translation.LANG_ES, "FIND", "Búsqueda espacial")
        self.translation.set_text(self.translation.LANG_ES, "FIND_LABEL", "Buscar")
        self.translation.set_text(self.translation.LANG_ES, "ABOUT", "Acerca de Open ICGC")
        self.translation.set_text(self.translation.LANG_ES, "RELOAD", "Recargar Open ICGC") 
        self.translation.set_text(self.translation.LANG_ES, "BACKGROUND_MAPS", "Mapas de fondo")
        self.translation.set_text(self.translation.LANG_ES, "BAGROUND_MAPS_DELETE", "Borrar mapas de fondo")
        self.translation.set_text(self.translation.LANG_ES, "TOOLTIP_HELP", """Buscar:
            Dirección: municipio, calle número o al reves
               Barcelona, Aribau 86
               Aribau 86, Barcelona
               Barcelona, C/ Aribau 86

            Cruce: municipio, calle, calle
               Barcelona, Mallorca, Aribau

            Carretera: carretera, km
               C32 km 10
               C32, 10

            Topónimo: texto libre
               Barcelona
               Collserola
               Institut Cartogràfic

            Coordenada: x y EPSG:codigo (por defecto sistema de coordenades del proyecto)
               429394.751 4580170.875
               429394,751 4580170,875
               429394.751 4580170.875 EPSG:25831
               EPSG:4326 1.9767050 41.3297270

            Rectángulo: oeste norte este sur EPSG:codi (por defecto sistema de coordenades del proyecto)
               427708.277 4582385.829 429708.277 4580385.829
               427708,277 4582385,829 429708,277 4580385,829
               427708.277 4582385.829 429708.277 4580385.829 EPSG:25831
               EPSG:25831 427708.277 4582385.829 429708.277 4580385.829

            Referencia catastral: ref (también funciona con los primeros 14 dígitos)
               9872023 VH5797S 0001 WX
               13 077 A 018 00039 0000 FP
               13077A018000390000FP           
            """)
        self.translation.set_text(self.translation.LANG_ES, "TOPO_HEADER", ["Nombre", "Tipo", "Municipio", "Comarca"])

        # Anglès
        self.translation.set_text(self.translation.LANG_EN, "FIND", "Spatial search")
        self.translation.set_text(self.translation.LANG_EN, "FIND_LABEL", "Find")
        self.translation.set_text(self.translation.LANG_EN, "ABOUT", "About Open ICGC")
        self.translation.set_text(self.translation.LANG_EN, "RELOAD", "Reload Open ICGC")
        self.translation.set_text(self.translation.LANG_EN, "BACKGROUND_MAPS", "Background maps")
        self.translation.set_text(self.translation.LANG_EN, "BAGROUND_MAPS_DELETE", "Delete background maps")
        self.translation.set_text(self.translation.LANG_EN, "TOOLTIP_HELP", """Find:
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
               Institut Cartogràfic

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
               13077A018000390000FP           
            """)
        self.translation.set_text(self.translation.LANG_EN, "TOPO_HEADER", ["Name", "Type", "Municipality", "Region"])

    def initGui(self):
        """ Inicialització de la part gràfica del plugin """
        # Registra el plugin
        self.gui.configure_plugin(self.metadata.get_name(), self.about, QIcon(":/plugins/openicgc/icon.png"))

        ## Configurem el gestor d'errors
        error_report_manager.set_dialog("%s error" % self.metadata.get_name())
        error_report_manager.set_email("%s error" % self.metadata.get_name(), self.metadata.get_email())
                       
        # Inicialitzem el diàleg About
        self.about_dlg = AboutDialog(self.metadata.get_name(), QIcon(":/plugins/openicgc/icon.png"), self.metadata.get_info(), False, self.iface.mainWindow())

        # Preparem un combobox per llegir la cerca
        self.combobox = QComboBox()
        self.combobox.setFixedSize(QSize(250,24))
        self.combobox.setEditable(True)              
        self.combobox.setToolTip(self.translation.get_text("TOOLTIP_HELP"))
        self.combobox.activated.connect(self.run) # Apretar intro i seleccionar valor del combo
        # Afegim la eina a la toolbar
        self.toolbar = self.gui.configure_toolbar(self.translation.get_text("FIND"), [
            self.translation.get_text("FIND_LABEL"),
            self.combobox,
            (self.translation.get_text("FIND"), self.run, QIcon(":/plugins/geofinder/geofinder.png")),
            ])
        # Afegim un menú amb les capes WMS de l'ICGC
        self.tools.add_tool_WMS_background_maps_lite(self.translation.get_text("FIND"), self.translation.get_text('BACKGROUND_MAPS'), self.translation.get_text('BAGROUND_MAPS_DELETE'))
        # Afegim reload per debug
        #self.gui.add_to_toolbar(self.toolbar, [
        #    "---",
        #    (self.translation.get_text("RELOAD"), self.reload_plugin, QIcon(":/lib/qlib3/base/python.png")),
        #    ])

    def unload(self):
        """ Alliberament de recursos """
        super().unload()

    @generic_handle_error
    def run(self, checked): # Afegeixo checked, perquè el mapeig del signal triggered passa un paràmetre
        """ Crida bàsica del plugin, que llegeix el text del combobox i el cerca als diferentes serveis web disponibles """
        self.find(self.combobox.currentText())

    @generic_handle_error
    def about(self, checked): # Afegeixo checked, perquè el mapeig del signal triggered passa un paràmetre
        """ Mostra informació sobre l'aplicació """
        self.about_dlg.do_modal()


    ###########################################################################
    # Implementació de les cerques

    def find(self, user_text):
        """ Cerca del text indicat en el diferentes serveis web disponibles. 
            Mostra els resultats en un diàleg i centra el mapa en l'element seleccionat per usuari """

        print(u"Find: %s" % user_text)
        
        # Cerquem el text i obtenim una llista de diccionaris amb els resultats
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        dict_list = self.find_data(user_text)
        print(u"Found %d: %s %s" % (len(dict_list), ", ".join([data_dict['nom'] for data_dict in dict_list[:10]]), "..." if len(dict_list) > 10 else ""))
        QApplication.restoreOverrideCursor()

        # Si tenim un rectangle, no cal mostrar res, accedim i ja està
        if len(dict_list) == 1 and dict_list[0]['nom'].startswith("Rectangle"):
            # Obtenim les coordenades del rectangle
            west = dict_list[0]['west']
            north = dict_list[0]['north']
            east = dict_list[0]['east']
            south = dict_list[0]['south']
            epsg = dict_list[0]['epsg']
            # Resituem el mapa
            self.set_map_rectangle(west, north, east, south, epsg)
        
        else:
            # Mostrem els indrets trobats
            dlg = GeoFinderDialog(self.translation.get_text("FIND"), self.translation.get_text("TOPO_HEADER", []), dict_list, self.TOPOICONS_DICT)
            selection = dlg.get_selection_index()
            if selection < 0:
                return
            print(u"Selected: %s" % dict_list[selection]['nom'])

            # Obtenim les coordenades del punt
            x = dict_list[selection]['x']
            y = dict_list[selection]['y']
            epsg = dict_list[selection]['epsg']
            # Resituem el mapa
            self.set_map_point(x, y, epsg)

        print(u"")

    def find_data(self, text, find_all = False):
        """ Retorna una llista de diccionaris amb els llocs trobats a partir del text indicat 
        """
        # Detectem si ens passen un rectangle terra
        west, north, east, south, epsg = self.get_rectangle(text)
        if west and north and east and south: 
            return self.find_rectangle(west, north, east, south, epsg)

        # Detectem si ens passen una coordenada terra
        x, y, epsg = self.get_coordinate(text)
        if x and y: 
            return self.find_coordinate(x, y, epsg)

        # Detectem si ens passen una carretera
        road, km = self.get_road(text)
        if road and km:
            return self.find_road(road, km)

        # Detectem si ens passen una cruilla
        municipality, type1, name1, type2, name2 = self.get_crossing(text)
        if municipality and name1 and name2:
            return self.find_crossing(municipality, type1, name1, type2, name2, find_all)

	                # Detectem si ens demanen una adreça
        municipality, type, name, number = self.get_address(text)
        if municipality and name and number:
            return self.find_adress(municipality, type, name, number, find_all)

	    # Detectem si ens demanen una referència catastral
        cadastral_ref = self.get_cadastral_ref(text)
        if cadastral_ref:
            return self.find_cadastral_ref(cadastral_ref);

	    # Si cap de les anteriors cerquem un topónim
        return self.find_placename(text)

    def get_rectangle(self, text):
        """ Detecta un rectangle de coordenades a partir del text
            Accepta textos amb 4 reals i opcionalment un codi epsg
            pex: 1.0 2.0 3.0 4.0 EPSG:0
                 EPSG:0 1.0 2.0 3.0 4.0 
                 1.0 2.0 3.0 4.0 
            return west, north, east, south, epsg """        

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
        """ Detecta una coordenada a partir del text
            Accepta textos amb 2 reals i opcionalment un codi epsg
            Pex: 1.0 2.0 EPSG:0
                 EPSG:0 1.0 2.0 EPSG:0
                 1.0 2.0
            return x, y, epsg """

        expression = r"^\s*(?:EPSG:(\d+)\s+)?([+-]?[0-9]*[.,]?[0-9]+)\s*([+-]?[0-9]*[.,]?[0-9]+)(?:\s+EPSG:(\d+))?\s*$" # <real> <real> [EPSG:<int>]
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
        """ Detecta una carretera a partir del text
            Accepta informació de carretera / km
            Pex: C32 km 10
                 C32, 10
            return road, km """

        ##expression = r'^\s*([\w]+)?\s*(?:km)?\s*([\d]+)?\s*$'
        expression = r'^\s*(\w+)\s*(?:(?:km)|,)\s*(\d+)\s*$'
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            road, km = found.groups()
        else:
            road, km = None, None

        return road, km

    def get_crossing(self, text):
        """ Detecta una cruilla a partir del text
            Accepta informació d'una cruilla (municipi, carrer, carrer)
            Pex: Barcelona, Muntaner, C/ Aragó 
            return municipality, type1, name1, type2, name2 """

        expression = r"\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*,\s*([\w]+[./])?\s*(\D+)\s*"
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            municipality, type1, street1, type2, street2 = found.groups()        
        else:
            municipality, type1, street1, type2, street2 = None, None, None, None, None
        
        return municipality, type1, street1, type2, street2

    def get_address(self, text):
        """ Detecta una adreça a partri del text
            Accepta informació d'adreça d'un municipi 
            Pex: Barcelona, Aribau 86
                 Aribau 86, Barcelona
                 Barcelona, C/ Aribau nº 86
                 Barcelona, Avd. Diagonal nº 86
            return municipality, type, name, number """

        # Per acceptar accents utilitzo el rang: \u00C0-\u017F
        expression = r"^\s*(?:([\D\s]+)\s*,)?\s*([\w]+[./])?\s*([\D\s]+)\s+(?:nº)?\s*(\d+)\s*(?:,\s*([\D\s]+[\D]))?\s*$" # [ciutat,] [C/] <carrer> <numero> [, ciutat]
        found = re.search(expression, text, re.IGNORECASE)
        if found:
            municipality1, type, street, number, municipality2 = found.groups()
            municipality = municipality1 if municipality1 else municipality2
        else:
            municipality, type, street, number = None, None, None, None

        return municipality, type, street, number

    def get_cadastral_ref(self, text):
        """ Detecta una referència cadastral a partir del text
            Accepta un codi de referència cadastral en els 3 formats oficials
            Pex: 9872023 VH5797S 0001 WX
                 13 077 A 018 00039 0000 FP
                 13077A018000390000FP (també funciona amb els 14 primers dígites)
            return cadastra_ref """
        
        # Sense espais ha d'ocupar 14 o 20 caràcters alfanumèrics
        cleaned_text = text.replace(' ', '')        
        if len(cleaned_text) not in (14, 20):
            return None
        # Validem que no tingui simbols
        expression = r'(\w+)'
        found = re.search(expression, cleaned_text, re.IGNORECASE)  
        if found:           
            cadastral_ref = found.groups()[0]
        else:
            cadastral_ref = None
        
        return cadastral_ref

    def find_rectangle(self, west, north, east, south, epsg):
        """ Retorna una llista amb un diccionari amb les coordenades del rectangle """

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
        """ Retorna una llista de diccionaris amb els llocs trobats al punt indicat """

        if not epsg:
            epsg = int(self.project.get_epsg())
        print(u"Coordinate: %s %s EPSG:%s" % (x, y, epsg))

        # Convertim les coordenades a ETRS89 UTM31N per fer la consulta        
        nom = "Punt: %s %s (EPSG:%s)" % (x, y, epsg), 
        query_x, query_y = self.crs.transform_point(x, y, epsg, 25831)

        # Fem la consulta
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_tuple_list = self.get_icgc_geoencoder_client().service.geocodificacioInversa(
                puntUTMETRS89 = {'X': query_x, 'Y': query_y}
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        #print(u"Return: %s%s" % (res_tuple_list[:3], "..." if len(res_tuple_list) > 3 else ""))
        
        # Convertim el resultat a format únic
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
        """ Retorna una llista de diccionaris amb les carreteres trobades amb la nomenclatura indicada """

        print(u"Road: %s %s" % (road, km))
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaPK(
                nomCarretera = road, 
                KM = km
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        #print(u"Return: %s%s" % (res_dicts_list[:3], "..." if len(res_dicts_list) > 3 else ""))
        
        # Convertim el resultat a format únic
        dicts_list = [{
            'nom': "%s" % res_dict['PkXY'],
            'idTipus': '', 
            'nomTipus': u'Via', 
            'nomMunicipi': u'', 
            'nomComarca': u'', 
            'x': float(res_dict['coordenadesETRS89UTM']['X']), 
            'y': float(res_dict['coordenadesETRS89UTM']['Y']),
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    def find_crossing(self, municipality, type1, street1, type2, street2, find_all):
        """ Retorna una llista de diccionaris amb les cruilles trobades amb la nomenclatura indicada """

        print(u"Crossing %s, %s %s / %s %s" % (municipality, type1, street1, type2, street2))
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
        #print(u"Return: %s%s" % (res_dicts_list[:3], "..." if len(res_dicts_list) > 3 else ""))
        
        # Convertim el resultat a format únic
        dicts_list = [{
            'nom': "%s" % res_dict['CruillaXY'],
            'idTipus': '', 
            'nomTipus': u'Cruilla', 
            'nomMunicipi': res_dict['Cruilla']['Poblacio'], 
            'nomComarca': res_dict['Cruilla']['Comarca']['nom'], 
            'x': float(res_dict['CoordenadesETRS89UTM'][0]['X']), 
            'y': float(res_dict['CoordenadesETRS89UTM'][0]['Y']),
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    def find_adress(self, municipality, type, street, number, find_all):
        """ Retorna una llista de diccionaris amb les adreces trobades amb la nomenclatura indicada """

        print(u"Adress: %s, %s %s %s" % (municipality, type, street, number))
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
        #print(u"Return: %s%s" % (res_dicts_list[:3], "..." if len(res_dicts_list) > 3 else ""))
        
        # Convertim el resultat a format únic
        dicts_list = [{
            'nom': "%s" % res_dict['AdrecaXY'],
            'idTipus': '', 
            'nomTipus': u'Adreça', 
            'nomMunicipi': res_dict['Adreca']['Poblacio'], 
            'nomComarca': res_dict['Adreca']['Comarca']['nom'], 
            'x': float(res_dict['CoordenadesETRS89UTM']['X']), 
            'y': float(res_dict['CoordenadesETRS89UTM']['Y']),
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list
        
    def find_cadastral_ref(self, cadastral_ref):
        """ Retorna una llista amb un diccionari amb la referència cadastral indicada """

        print(u"Cadastral ref: %s" % cadastral_ref)
        print(u"URL: %s" % self.get_cadastral_coordinates_client().wsdl.url)
        clean_cadastra_ref = cadastral_ref.replace(' ', '')[:14]
        # Exemples de RefCat:
        # 9872023 VH5797S 0001 WX
        # 13 077 A 018 00039 0000 FP
        # 13077A018000390000FP
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
        #print(u"Return: %s" % res_dict)

        adress = res_dict['coordenadas']['coord']['ldt']
        expression = r"([\D]+ \d+) ([\D]+) \(([\D]+)\)"
        found = re.search(expression, adress, re.IGNORECASE)
        if not found:
            expression = r"(.+)\.([\D]+) \(([\D]+)\)"
            found = re.search(expression, adress, re.IGNORECASE)
        if not found:
            expression = r"(.+)()\(([\D]+)\)"
            found = re.search(expression, adress, re.IGNORECASE)        
        # Si hem trobat un coincidencia separem carrer, municipi i comarca
        if found:
            street, municipality1, municipality2 = found.groups()
        else:
            street = adress
            municipality1 = u''
            municipality2 = u''

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
        """ Retorna una llista de diccionaris amb els topònims trobats amb la nomenclatura indicada """

        print(u"Placement: %s" % text)
        print(u"URL: %s" % self.get_icgc_geoencoder_client().wsdl.url)
        try:
            res_dicts_list = self.get_icgc_geoencoder_client().service.localitzaToponim(
                text
                )
        except Exception as e:
            print(u"Error: %s SOAP Request: %s" % (e, self.get_icgc_geoencoder_client().last_sent()))
            raise e
        #print(u"Return: %s%s" % (res_dicts_list[:3], "..." if len(res_dicts_list) > 3 else ""))
        
        # Convertim les coordenades a float i guardem l epsg
        dicts_list = [{
            'nom': res_dict['Nom'],
            'idTipus': int(res_dict['IdTipus']), 
            'nomTipus': res_dict['NomTipus'], 
            'nomMunicipi': res_dict['NomMunicipi'] if 'NomMunicipi' in res_dict else u'', 
            'nomComarca': res_dict['NomComarca']if 'NomComarca' in res_dict else u'', 
            'x': float(res_dict['CoordenadesETRS89UTM']['X']), 
            'y': float(res_dict['CoordenadesETRS89UTM']['Y']),
            'epsg': 25831
            } for res_dict in res_dicts_list]
        return dicts_list

    ### Implementació alternativa no utilitzada...
    ##def find_placename_json(self, text):
    ##    print(u"Placement: %s" % text)
    ##    # Enviem la petició de topònim i llegim les coordeandes
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
    ##    # Parsejem la resposta (pex: Barcelona)
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

    ##    # Convertim les coordenades a float i guardem el epsg
    ##    for topo_dict in topo_list:
    ##        topo_dict['x'] = float(topo_dict['x'])
    ##        topo_dict['y'] = float(topo_dict['y'])
    ##        topo_dict['epsg'] = 23031
    ##    return topo_list


    ###########################################################################
    # Crides auxiliars de resituació al mapa i reprojecció

    