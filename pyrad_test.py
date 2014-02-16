# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        pyrad_test
# Purpose:
#
# Author:      ShafikovIS
#
# Created:     28.10.2013
# Copyright:   (c) ShafikovIS 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from __future__ import print_function
import pyradclasses as PyRAD
import pickle

def main():
    # settings dict
    DSConfig = {'Hostname': 'localhost', 'Port': 5555,
    'URL': 'datasnap/rest/TServerClass',
    'Login': 'dsclient', 'Password': 'Ds_1234'}

    # Commandline args:
    # "localhost" "5555" "datasnap/rest/TServerClass" "dsclient" "Ds_1234"

    # Save DSConfig to pickle file:
    # pickle.dump(DSConfig, open('D:\DSConfig.pkl', 'wb'))
    # return

    # create engine with settings
    PyRAD.Reload(DSConfig) # to use command line, pass no arguments

    # display info on a package
    Pk = PyRAD.PRPackage('dclfmxstd170.bpl')
    print(Pk)

    # get all IDE packages
    Packages = PyRAD.PRPackages()
    # display package count
    print(Packages.Count)
    # display brief info on each package
    for i, Pk in enumerate(Packages):
        print('{0}: {1}: {2} - {3}'.format(i, Pk.Name, Pk.FileName, Pk.ComponentCount))
    # display the Loaded status of each package
    print(['{0}: {1}'.format(pk.Name, pk.Loaded) for pk in Packages])
    # get package by filename
    Pk = Packages.GetPackage('c:\\program files (x86)\\embarcadero\\rad studio\\10.0\\bin\\dclfmxstd170.bpl')
    # display its name and components
    print('{0}: {1}'.format(Pk.Name, Pk.Components))

    # get IDE main menu object
    pActions = PyRAD.PRMainMenu()
    # display main menu structure
    print(pActions)
    # bring up the Options dialog
    pActions.ExecuteMenuItem('Tools|Options...')

if __name__ == '__main__':
    main()
