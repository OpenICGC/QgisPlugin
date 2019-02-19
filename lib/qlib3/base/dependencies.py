# encoding: utf-8
import os
import sys
import subprocess


def install(package):
    print("install")
    python_path = os.path.join(os.getcwd(), "python3.exe")
    cmd_list = [python_path, "-m", "pip", "install", package]
        
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags = 0x01
    startupinfo.wShowWindow = 0
    status = subprocess.call(cmd_list, shell=False, startupinfo=startupinfo)        
    print("%s (status: %s)" % (" ".join(cmd_list), status))

def is_installed(module_name):
    return module_name in sys.modules.keys()

def add_lib_folder(lib_folder):
    sys.path.append(lib_folder)

def add_plugin_lib_folder(plugin_folder, lib_subfolder="lib"):
    add_lib_folder(os.path.join(os.path.dirname(plugin_folder), lib_subfolder))
    

if __name__ == '__main__':
    pass
