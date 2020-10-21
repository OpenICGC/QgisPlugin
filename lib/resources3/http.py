# -*- coding: utf-8 -*-
"""
*******************************************************************************
Module with functions to recover data to make WMS connections to ICGC resources

                             -------------------
        begin                : 2019-03-27
        author               : Albert Adell
        email                : albert.adell@icgc.cat
*******************************************************************************
"""

import urllib
import urllib.request
import html
import socket
import re


sheets_urlbase = "https://datacloud.icgc.cat/datacloud/talls_ETRS89/json_unzip"
delimitations_urlbase = "https://datacloud.icgc.cat/datacloud/bm5m_ETRS89/json_unzip/"
dtm_urlbase_list = [
    ("2m", "https://datacloud.icgc.cat/datacloud/met2_ETRS89/mosaic"),
    ("5m", "https://datacloud.icgc.cat/datacloud/met5_ETRS89/mosaic")
    ]

def get_dtms(timeout_seconds=0.5, retries=3, dtm_http_file_pattern = r'<A HREF=["\/\w]*[\/"](\w+\.\w+)">'):
    """ Obté les URLs dels arxius de MET disponibles de l'ICGC
        Retorna: [(dtm_name, dtm_url)]
        ---
        Gets ICGC's available DTM urls
        Returns: [(dtm_name, dtm_url)]
        """
    dtm_list = []
    for dtm_name, dtm_urlbase in dtm_urlbase_list:
        # Llegeixo la pàgina HTTP que informa dels arxius disponibles
        remaining_retries = retries
        while remaining_retries:
            try:
                response = None
                response = urllib.request.urlopen(dtm_urlbase, timeout=timeout_seconds)
                remaining_retries = 0
            except socket.timeout:
                remaining_retries -= 1
                print("retries", remaining_retries)
        if response:
            response_data = response.read()
            response_data = response_data.decode('utf-8')
        else:
            response_data = ""
        if not response_data:
            continue

        # Cerquem links a arxius MET i ens quedem el més recent
        files_list = re.findall(dtm_http_file_pattern, response_data)
        if not files_list:
            continue
        dtm_file = sorted(files_list, reverse=True)[0]
        dtm_url = "%s/%s" % (dtm_urlbase, dtm_file)
        dtm_list.append((dtm_name, dtm_url))

    return dtm_list

def get_sheets(timeout_seconds=0.5, retries=3, sheet_http_file_pattern = r'<A HREF=["\/\w]*[\/"](tall(\w+)etrs\w+\.json)"'):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    sheets_list = []
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    remaining_retries = retries
    while remaining_retries:
        try:
            response = None
            response = urllib.request.urlopen(sheets_urlbase, timeout=timeout_seconds)
            remaining_retries = 0
        except socket.timeout:
            remaining_retries -= 1
            print("retries", remaining_retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""
    if not response_data:
        return []

    # Cerquem links a arxius json
    sheets_info_list = re.findall(sheet_http_file_pattern, response_data)
    sheets_info_list.sort(key=lambda sheet_infoi:int(sheet_infoi[1][:-1]) if sheet_infoi[1][:-1].isdigit() and sheet_infoi[1][-1] == "m" else 9999999)
    for sheet_file, sheet_name in sheets_info_list:
        if sheet_name[:-1].isdigit() and sheet_name[-1] == 'm':
            sheet_name = sheet_name.replace("m", ".000")
        sheet_url = "%s/%s" % (sheets_urlbase, sheet_file)
        sheets_list.append((sheet_name, sheet_url))
        
    return sheets_list

def get_delimitations(timeout_seconds=0.5, retries=3, delimitation_http_file_pattern=r'<A HREF=["\/\w]*[\/"](bm5mv\d+js\dt[cp][cmp][\d_]+\.json)"', 
    delimitation_type_patterns_list=[("Caps de Municipi", "bm5mv\d+js\dtcm[\d_]+\.json"), ("Municipis", "bm5mv\d+js\dtpm[\d_]+\.json"), 
    ("Comarques", "bm5mv\d+js\dtpc[\d_]+\.json"), ("Províncies", "bm5mv\d+js\dtpp[\d_]+\.json")]):
    """ Obté les URLs dels arxius de talls disponibles de l'ICGC
        Retorna: [(sheet_name, sheet_url)]
        ---
        Gets ICGC's available sheets urls
        Returns: [(sheet_name, sheet_url)]
        """
    delimitations_list = []
    # Llegeixo la pàgina HTTP que informa dels arxius disponibles
    remaining_retries = retries
    while remaining_retries:
        try:
            response = None
            response = urllib.request.urlopen(delimitations_urlbase, timeout=timeout_seconds)
            remaining_retries = 0
        except socket.timeout:
            remaining_retries -= 1
            print("retries", remaining_retries)
    if response:
        response_data = response.read()
        response_data = response_data.decode('utf-8')
    else:
        response_data = ""
    if not response_data:
        return []

    # Cerquem links a arxius json
    delimitations_info_list = re.findall(delimitation_http_file_pattern, response_data)
    for delimitation_name, delimitation_type_pattern in delimitation_type_patterns_list:
        for delimitation_file in delimitations_info_list:    
            # Cerquem el fitxer que quadri amb cada plantilla de tipus
            if re.match(delimitation_type_pattern, delimitation_file):
                delimitation_url = "%s/%s" % (delimitations_urlbase, delimitation_file)
                delimitations_list.append((delimitation_name, delimitation_url))
                break
                
    return delimitations_list