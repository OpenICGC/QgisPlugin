# encoding: utf-8
"""
*******************************************************************************
Mòdul amb funcions i classes fer gestionar diàlegs amb progress o working bars
---
Module with functions and classes to manage dialogs with progress or working
bars
                             -------------------
        begin                : 2019-01-18
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

from PyQt5 import QtNetwork
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWidgets import QApplication

import os
from importlib import reload

from . import progressdialog
reload(progressdialog)
from .progressdialog import ProgressDialog


class DownloadManager(object):
    """ Classe per gestionar la descàrregar de fitxers via HTTP
        ---
        Class to manage the download of files via HTTP
        """

    def __init__(self):
        """ Inicialització del gestor de descàrregues i diccionari de peticions
            ---
            Initialization of download manager and request dictionary
            """
        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.__download_finished__)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.__refresh_progressbar_time__)

        self.queries_dict = {}

    def download(self, remote_file, local_pathname, synchronous=True, callback=None, title="Downloading ...", cancel_button_text="Cancel", time_info="Elapsed %s"):
        """ Descarrega un fitxer remote, opcionalment es pot indicar:
            - synchronous: descàrrega síncrona (espera a acabar)
            - callback: funció a executar al acabar la descàrrega (se li passa el path del fitxer descarregat)
            - title: títol del diàleg de progrés
            - cancel_button_text: Text del botó de cancel·lar de diàleg de progrés
            - time_info: Text de la informació del temps, pex: "Elapsed %s"
            ---
            Download a remote file, optionaly you can specify:
            - synchronous: synchronous download (wait to finish)
            - callback: function to execute when download finish (function recive downloaded file pathname)
            - title: progress dialog title
            - cancel_button_text: progress dialog cancel button text
            - time_info: time information text, for example: "Elapsed %s"
            """
        # Reservem recursos per la descàrrega i els guadem en un diccionari
        local_file = open(local_pathname, "wb+")
        progress = ProgressDialog(os.path.basename(local_pathname), 0, title=title, cancel_button_text=cancel_button_text, time_info=time_info)
        self.queries_dict[remote_file] = [None, progress, local_file, callback, True, None, None] # 4:running, 5:status_ok, 6:error_msg

        # Realitzem la petició de descàrraga al servidor
        reply = self.manager.get(QtNetwork.QNetworkRequest(QUrl(remote_file)))
        reply.readyRead.connect(lambda:self.__download_ready__(reply, local_file))
        reply.downloadProgress.connect(lambda read, total, progress=progress: self.__download_progress__(read, total, progress))

        # Guardem la petició de descàrrega al diccionari de gestió de descàrregues
        self.queries_dict[remote_file][0] = reply
        # Inicialitzem el refresc del temps de les progressbar
        self.timer.start()

        # Si la descàrrega és síncrona, esperem a que acabi
        if synchronous:
            while self.is_downloading(remote_file):
                if progress.was_canceled():
                    reply.abort()
            # Recuperem com ha acabat el procés
            status_ok, error_msg = self.get_status(remote_file)
            # Netejem el diccionari de descàrregues
            self.remove(remote_file)
            # Si tenim error, el tornem com una exception
            if not status_ok:
                raise Exception(error_msg)

    def __download_ready__(self, reply, local_file):
        """ Event de dades disponibles que llegeix i escriu les dades en el fitxer de sortida
            ---
            Data ready event that read and write data in output file
            """
        ##print("Ready")
        data = reply.readAll()
        local_file.write(data)

    def __download_progress__(self, read, total, progress):
        """ Event de lectura que actualitza la barra de progrés
            ---
            Read event that update progress bar
            """
        #print("%s / %s" % (read, total))
        progress.set_steps(total)
        progress.set_value(read)

    def __download_finished__(self, reply, debug=True):
        """ Event de descàrrega finalitzada, que allibera recursos
            ---
            Download finished event that free resources
            """
        ##print("Finished!")
        download_key = reply.request().url().url()
        _reply, progress, local_file, callback, running, status_ok, error_msg = self.queries_dict[download_key]
        filename = local_file.name
        status_ok = (reply.error() == QtNetwork.QNetworkReply.NoError)

        # Alliberem recursos
        local_file.close()
        progress.close()
        self.check_stop_timer()

        # Obtenim com ha acabat la descàrrega
        if not status_ok:
            error_msg = reply.errorString()
            # Si és un error, ha quedat guardar un informe HTML en el fitxer que hem guardat
            if os.path.getsize(filename) > 0:
                os.rename(filename, filename + ".html")
                filename += ".html"
                if debug:
                    os.startfile(filename) # $$$ Problemes fora de windows
            # Si hem cancel·lat, el fitxer queda a 0 i no cal guardar-lo
            elif os.path.exists(filename):
                os.remove(filename)
        elif callback:
            callback(filename)

        # Canviem l'estat de la petició
        self.queries_dict[download_key] = (reply, progress, local_file, callback, False, status_ok, error_msg)

    def __refresh_progressbar_time__(self):
        for reply, progress, local_file, callback, running, status_ok, error_msg in self.queries_dict.values():
            if running and progress and progress.is_visible():
                progress.update_time()

    def check_stop_timer(self):
        for reply, progress, local_file, callback, running, status_ok, error_msg in self.queries_dict.values():
            if running and progress and progress.is_visible():
                return
        self.timer.stop()

    def is_downloading(self, remote_file):
        """ Retorna si el fitxer remot s'està descarregant
            ---
            Return if remote file is downloading
            """
        _reply, _progress, _local_file, _callback, running, _status_ok, _error_msg = self.queries_dict[remote_file]
        return running

    def get_status(self, remote_file):
        """ Retorna l'estat (booleà) del fitxer a descarregar i missatge d'error si hi ha
            ---
            Return remote file status (bool) and error message if exist
            """
        _reply, _progress, _local_file, _callback, _running, status_ok, error_msg = self.queries_dict[remote_file]
        return status_ok, error_msg

    def remove(self, remote_file):
        """ Esborrar el registre del fitxer descarregat del diccionari intern
            ---
            Remove remote file download register from internal dictionary
            """
        self.queries_dict.pop(remote_file)

    def clean_history(self):
        """ Esborra els fitxers descarregats del diccionari intern
            ---
            Remove finished downloads from internal dictionary
            """
        remove_list = [remote_file for remote_file, (_reply, _progress, _local_file, _callback, running, _status_ok, _error_msg) in self.queries_dict.items() if not running]
        for remote_file in remove_list:
            self.remove(remote_file)

if __name__ == "__main__":
    pass
