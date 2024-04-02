# -*- coding: utf-8 -*-
"""
*******************************************************************************
Mòdul amb classe diàleg amb multiples input 
---
Module with a dialog class  with multiple input 

                             -------------------
        begin                : 2024-03-13
        author               : David Sanz & Albert Adell
        email                : david.sanz@icgc.cat
*******************************************************************************
"""

from datetime import date, time, datetime

from PyQt5.QtCore import Qt, QTime, QDate, QDateTime
from PyQt5.QtWidgets import QApplication, QLineEdit, QCheckBox, QComboBox, QDialogButtonBox
from PyQt5.QtWidgets import QFormLayout, QDialog, QMessageBox, QLabel, QTimeEdit, QDateEdit, QDateTimeEdit


class MultipleInputDialog(QDialog):
    """ Classe per generar diàlegs dinàmics a partir d'una llista de camps a demanar 

        El paràmetre labels és una llista de valors o tuples de 2 o 3 elements:
            labels = [<label1:str>, <label2:str>, ...]
            labels = [(<label1:str>, <data_type:type>|<value>|<list of values:list>),  ...]
            labels = [(<label1:str>, <data_type:type>|<value>|<list of values:list>, <required:bool>),  ...]
        
        Si s'especifica un tipus (2n valor) es validarà que les dades introduides es corresponguin amb el tipus
        Si s'especifica un valor (2n valor) s'assignarà com valor per defecte i validarà les dades segons el seu tipus
        Si s'especifica una llista (2n valor) validarà les dades segons el seu tipus del primer element
        Si s'especifica valor requerit (3r valors) es validarà que el camp estigui ple
        El tipus de dada per defecte és str. S'accepten tipus / valors: str, int, float, bool, list, time, date, datetime
        Per defecte els camps no són requerits. Els camps requerits es mostraran en negreta
        No es deixarà sortir del diàleg fins que es compleixin tots els criteris o es cancel·li

        Exemples:
            dlg = MultipleInputDialog(labels=[ # (Etiqueta, tipus_valor_llista, requerit)
                ('Text', str, True), 
                ('Text2', "hola", True), 
                ('Int', int, True), 
                ('Int2', 10, True), 
                ('Real', float, True), 
                ('Real2', 1.2, True), 
                ('Check', bool, False), # Requerit a false activa tristate
                ('Check2', True, True),
                ('Llista', [1,2,3], False), # Requerit a false afegeix un element buit al principi
                ('Llista2', [1,2,3], True),
                ('Llista3', [True, False], True),
                ])
            status_ok = dlg.do_moldal()
            if status_ok:
                values_list = dlg.get_values()

            dlg = MultipleInputDialog(labels=[
                ('Passada', str), 
                ('Codi de planificació', [11231,22323,3346]),
                ], title="Planificació de la pasada")
            status_ok = dlg.do_modal()
            if status_ok:
                values_list = dlg.get_values()

            dlg = MultipleInputDialog(labels=[
                'Passada', 
                'Codi de planificació'
                ], title="Planificació de la pasada")
            status_ok = dlg.do_modal()
            if status_ok:
                values_list = dlg.get_values()
        """

    def __init__(self, labels, title="", parent=None):
        """ Constructor """
        super().__init__(parent)
        self.setWindowTitle(title)

        # Obtenim la configuració dels valors a denamar
        self.label_list = self.parse_labels(labels)
        # Preparem una llista de valors resultats i errors tots a None
        self.value_list = [None] * len(self.label_list)
        self.error_list = [None] * len(self.label_list)
        
        # Afegim controls dinàmicament al diàleg
        self.layout, self.item_list = self.create_items(self.label_list)
    
    def parse_labels(self, label_list):
        """ Retorna una llista amb la configuració del items a generar dinàmicament 
            a partir de la llista d'informació de labels que passa l'usuari 
            label_list = [(Label:str, [type_or_value_or_list_of_values, [required:bool]]), ...]
            """
        label_config_list = [] # [(label, label_type, label_default_value, label_list_type, label_required), ...]
        # Recorre la llista de labels que ens passen i depenent del tipus i quantitat de valors
        # obtenim la configuració per cada una de les etiquets
        for label_info in label_list:
            label, label_type, label_default_value, label_list_type, label_required = None, None, None, None, None
            
            # Segons el tipus del label_info, deduim la informació necessària
            if type(label_info) is str:
                label, label_type, label_required = label_info, str, False
            elif type(label_info) is tuple and len(label_info) == 2:
                if type(label_info[0]) is str:
                    label, label_type, label_required = label_info[0], label_info[1], False
            elif type(label_info) is tuple and len(label_info) == 3:
                if type(label_info[0]) is str and type(label_info[2]) is bool:
                    label, label_type, label_required = label_info

            if label:
                # El segon valor pot ser un tipus o un valor per defecte
                if type(label_type) is not type:
                    label_default_value = label_type
                    label_type = type(label_type)
                # Si el segon valor és una llista detectem el tipus dels seus elements
                if label_type is list and label_default_value:
                    label_list_type = type(label_default_value[0])
                # Guardem tota la informació obtinguda en una llista
                label_config_list.append((label, label_type, label_default_value, label_list_type, label_required))
            else:
                # Si no hem pogut deduir la configuració d'un element tornem error
                raise Exception("Definició d'etiqueta desconeguda: %s" % str(label_info))
        
        return label_config_list

    def create_items(self, label_list):
        """ Afegim controls dinàmicament al diàleg segons la llista de labels
            Retorna un layout contenidor i la llista de widgets utilitzats
            """
        item_list = []
        layout = QFormLayout(self)
        for label_text, label_type, label_default_value, label_list_type, label_required in label_list:
            # Creem el widget corresponent al tipus de dades
            if label_type is list:
                item = QComboBox(self)
                item.addItems(([] if label_required else [""]) + [str(v) for v in label_default_value])
            elif label_type is bool:
                item = QCheckBox(self)
                if not label_required:
                    item.setCheckState(Qt.PartiallyChecked)
                if label_default_value is not None:
                    item.setChecked(label_default_value)
            elif label_type is date:
                value = label_default_value if label_default_value else date.today()
                item = QDateEdit(QDate(value), self)
                item.setDisplayFormat("dd/MM/yyyy")
                item.setCalendarPopup(True)
            elif label_type is time:
                value = label_default_value if label_default_value else datetime.now().time()
                item = QTimeEdit(QTime(value), self)
            elif label_type is datetime:
                value = label_default_value if label_default_value else datetime.now()
                item = QDateTimeEdit(QDateTime(value), self)
                item.setDisplayFormat("dd/MM/yyyy hh:mm:ss")
                item.setCalendarPopup(True)
            else:
                item = QLineEdit(self)
                if label_default_value is not None:
                    item.setText(str(label_default_value))
            # Si tenim un camp requerit el pintem en negreta
            if label_required:
                label = QLabel(self)
                label.setText("<b>%s</b>" % label_text)
            else:
                label = label_text
            layout.addRow(label, item)
            # Ens guardem l'item perquè no es destrueixi
            item_list.append(item)
        
        # Afegim els botons d'acceptar/cancel·lar
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttonBox)        
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        return layout, item_list

    def parse_values(self, label_list, item_list, error_pattern="Camp \"%s\" (%s): \"%s\" - %s", \
        format_error="Format incorrecte", required_error="Valor requerit"):
        """ Retorna les llistes de valors i errors segons les dades introduides
            """
        value_list = []
        error_list = []
        for (label, label_type, label_default_value, label_list_type, label_required), item\
            in zip(label_list, item_list):
            
            error = None
            try:
                if label_type is str:
                    value = item.text()
                elif label_type is bool:
                    value = None if item.checkState() == Qt.PartiallyChecked else item.isChecked()
                elif label_type is int:
                    value = item.text()
                    try:
                        value = int(value) if value else None
                    except:
                        raise Exception(format_error)
                elif label_type is float:
                    value = item.text()
                    try:
                        value = float(value) if value else None
                    except:
                        raise Exception(format_error)
                elif label_type is list:
                    value = item.currentText()               
                    if label_list_type is bool:
                        try:
                            value = (value == "True") if value else None
                        except:
                            raise Exception(format_error)
                    elif label_list_type is int:
                        try:
                            value = int(value) if value else None
                        except:
                            raise Exception(format_error)
                    elif label_list_type is float:
                        try:
                            value = float(value) if value else None
                        except:
                            raise Exception(format_error)
                elif label_type is date:
                    value = item.date().toPyDate()
                elif label_type is time:
                    value = item.time().toPyTime()
                elif label_type is datetime:
                    value = item.dateTime().toPyDateTime()
                else:
                    value = None

                if (value is None or value == "") and label_required:
                    raise Exception(required_error)

            except Exception as e:
                label_type_name = str(label_type).replace("<class '", "").replace("'>", "")
                error = error_pattern % (label, label_type_name, value, str(e).strip())

            value_list.append(value)
            error_list.append(error)

        return value_list, error_list

    def accept(self):
        """ Event d'acceptació del diàleg que valida els valors introduits """
        # Carreguem la llista de valors i d'errors
        self.value_list, self.error_list = self.parse_values(self.label_list, self.item_list)
        
        # Detectem errors (error de label diferent de None) i els mostrem
        display_error_list = [error for error in self.error_list if error]
        if display_error_list:
            QMessageBox.warning(self, "Error de dades", "\n\n".join(display_error_list))
        else:
            super().accept()

    def do_modal(self):
        """ Mostra el diàleg i retorna True/False segons s'ha acceptat o cancel·lat """
        self.show()
        return self.exec() == QDialog.Accepted

    def get_values(self):
        """ Retorna una llista amb els valors introduits """
        return self.value_list

    @classmethod
    def get_inputs(cls, parent, title, labels):
        """ Funció estàtica per crear un diàleg multicamp en una linia, retorna 
            tots els paràmetres demanats més un boleà d'acceptació o cancel·lació
            del diàleg """
        dlg = cls(labels, title, parent)
        status_ok = dlg.do_modal()
        values_list = dlg.get_values()
        values_list.append(status_ok)
        return values_list
        