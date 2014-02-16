# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        pyradclasses
# Purpose:
#
# Author:      ShafikovIS
#
# Created:     28.10.2013
# Copyright:   (c) ShafikovIS 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from __future__ import print_function
import pyrad, sys
from os import path
from numbers import Real
from inspect import ismethod

#-------------------------------------------------------------------------------

Req = None

def Reload(DSConfig=None):
    """
    Global function that MUST be called before creating and accessing any
    PyRAD classes below. It creates a single PReq object (used for client/server
    data transfer) and assigned it to the global Req variable (which is
    preassigned with None). This variable is then shared by any PyRAD classes
    to make specific requests and get back results.
    """
    #reload(pyrad)
    global Req
    Req = pyrad.PReq('CheckConnection', DSConfig)

#-------------------------------------------------------------------------------

class EPRError(pyrad.EGenericError):
    "Exception class for this module (pyradclasses)"
    pass

#-------------------------------------------------------------------------------

class PRObject(object):
    """
    Base class for all PyRAD classes below.
    Defines some common functionality, such as string representation.
    """
    def __init__(self):
        """
        Before constructed, we check that the global Req variable is assigned.
        We assume that to do that, the global Reload function MUST be called
        before ever accesing any PyRAD classes. If Req is unassigned (=None),
        an exception is raised.
        """
        if Req is None:
            raise EPRError('Request object is not instantiated!\n'
                           'Call Reload before accessing any PRObject classes.')

    def _getlasterror(self, func, *args):
        """
        An 'abstract' method to get the value of 'ErrorMsg' for an object.
        The specific getter function is given in 'func', while any additional
        arguments may be passed in 'args'.
        """
        if args:
            targs = args + ('ErrorMsg',)
            return Req.get_result(func, *targs)
        else:
            return Req.get_result(func, 'ErrorMsg')

    def __str__(self):
        """
        <Typecasting protocol>
        Return this object as a string by retrieving the key-value pairs
        from the internal properties (omitting the 'private' ones - those
        starting with '_').
        """
        pairs = []
        for attr in dir(self):
            val = getattr(self, attr)
            if (attr[:1] != '_') and (not ismethod(val)):
                pairs.append('{k}: {v}'.format(k=attr, v=val))
        return pyrad.tostr('\n'.join(pairs))

#---- PACKAGE

class PRPackage(PRObject):
    """
    Class representing info on a single package in the IDE.
    ------------------------------------------------------------
    Available properties:
        * Index:            (int) index of package in the IDE packages collection
        * FileName:         (Unicode) full path to this package
        * Name:             (Unicode) package short filename (e.g. 'rtl170.bpl')
        * Description:      (Unicode) package description
        * Producer:         (Unicode)
        * Consumer:         (Unicode)
        * SymbolFileName:   (Unicode) package symbolic name (e.g. 'rtl')
        * RuntimeOnly:      (bool) whether this package is runtime-only
        * DesigntimeOnly:   (bool) whether this package is designtime-only
        * IDEPackage:       (bool) whether this package is an IDE package (ToolsAPI etc.)
        * Loaded:           (bool) whether this package is currently loaded in the IDE
        * ContainsList:     (list) list of contained packages
        * RequiresList:     (list) list of required packages
        * ImplicitList:     (list) list of implicitly required packages
        * RequiredByList:   (list) list of packages that require this package
        * ComponentCount:   (int) number of components installed with this package
        * Components:       (list) list of contained components
    ------------------------------------------------------------
    NB!
    * These properties are ONLY available after a successfull execution of the
    __getpkinfo method.
    * The Uninstall and Reload methods may result in deleting most of these
    properties (except Index, ComponentCount, and Components - those are just
    reset). The deletion (implemented in the __clear method) will cause
    these properties to become unavailabe for access. An attempt to access any
    of them after calling __clear will raise runtime exceptions. Call Reload or
    Install to restore these properties (with updated values).
    """
    def __init__(self, index):
        """
        <Constructor>
        Check the 'index' arg passed into it and retrieve
        the package info from the IDE for the corresponding package.
        If 'index' is wrong (not a number between 0 and package count and
        not a valid package filename), an EPRError exception is thrown.
        """
        PRObject.__init__(self)

        if isinstance(index, Real):
            if self.__check_index(index):
                self.Index = index
                self.__getpkinfo()
                return
            else:
                raise EPRError('Wrong package index {0}!'.format(index))

        elif isinstance(index, basestring):
            pknames = Req.get_result('IDE_Packages_getPackagesValue', 'PackageNames')
            for i, pk in enumerate(pknames):
                if path.basename(index).lower()==pk.lower():
                    self.Index = i
                    self.__getpkinfo()
                    return
            else:
                raise EPRError('Cannot find package "{0}"!'.format(index))

        raise EPRError('Wrong index type passed to PRPackage constructor ({0})!'.format(type(index)))

    @property
    def LastError(self):
        return PRObject._getlasterror(self, 'IDE_Packages_getPackageInfoValue', self.Index)

    def Reload(self, index=None):
        """
        If 'index' is set (not None), reset the value of Index and updates
        the package info. Otherwise (if 'index' is None), try to find the
        package among the IDE packages by name and update the info correspondingly.
        If Name is not among the IDE package collection, clear all internal data.
        """
        if not index is None:
            self.Index = index
            self.__getpkinfo()
            return True
        else:
            pknames = Req.get_result('IDE_Packages_getPackagesValue', 'PackageNames')
            for i, pkname in enumerate(pknames):
                if self.Name == pkname:
                    self.Index = i
                    self.__getpkinfo()
                    return True
            else:
                self.__clear()
            return False

    @property
    def ComponentCount(self):
        return Req.get_result('IDE_Packages_getCompCount', self.Index) \
               if self.Index >= 0 else 0

    @property
    def Components(self):
        return [Req.get_result('IDE_Packages_getCompName', self.Index, i) \
                for i in xrange(self.ComponentCount)] \
                if self.Index >= 0 else []

    def SetLoaded(self, bLoaded=True):
        """
        Toggle the Loaded state of the package, updating the value
        of self.Loaded on success.
        """
        res = Req.get_result('IDE_Packages_ToggleLoaded', self.Index, bLoaded)
        if res: self.Loaded = bLoaded
        return res

    def Install(self):
        """
        Try to install the package, passing the full path (FileName) to the IDE method.
        If FileName is not available (e.g. after calling __clear), an exception
        is thrown. Returns the result of the Reload method.
        """
        if 'FileName' in self.__dict__:
            FName = self.FileName
        elif ('_pkinfo' in self.__dict__) and ('FileName' in self._pkinfo):
            FName = self._pkinfo['FileName']
        else:
            raise EPRError('Package filename is not assigned!\nCreate new object or reload from index.')
        res = Req.get_result('IDE_Packages_Install', FName)
        return self.Reload()

    def Uninstall(self):
        """
        Try to uninstall this package from the IDE. If the operation succeeds,
        all the internal properties are cleared.
        """
        res = Req.get_result('IDE_Packages_Uninstall', self.FileName)
        if res: self.__clear()
        return res

    def IsInstalled(self):
        """
        Check if this package is currently installed in the IDE by searching
        the package name among the IDE packages.
        """
        pknames = Req.get_result('IDE_Packages_getPackagesValue', 'PackageNames')
        return (self.Name in pknames)

    def __check_index(self, index):
        """
        Validate the numeric index passed as 'index' (must be >= 0 and < package count).
        """
        if index < 0: return False
        return (index < Req.get_result('IDE_Packages_getCount'))

    def __getpkinfo(self):
        """
        Update the package info for this package. The function first retrieves
        the data into the _pkinfo dictionary, which is then used to update the
        class properties (_pkinfo is not cleared by the __clear method).
        The ComponentCount and Components properties are added / updated separately.
        """
        self._pkinfo = Req.get_result('IDE_Packages_getPackageInfo', self.Index)
        self.__dict__.update(self._pkinfo)

    def __clear(self):
        """
        Clear all the internal properties of this object (those contained in
        _pkinfo, but not _pkinfo itself) and reset the values of Index,
        ComponentCount, and Components.
        """
        if '_pkinfo' in self.__dict__:
            for key in self._pkinfo:
                if (key in self.__dict__) and (key != '_pkinfo'): del self.__dict__[key]
        self.Index = -1

#---- PACKAGES (COLLECTION)


class PRPackages(PRObject):
    """
    Class representing the IDE collection of packages.
    """
    def __init__(self):
        PRObject.__init__(self)
        self.Reload()

    @property
    def LastError(self):
        return PRObject._getlasterror(self, 'IDE_Packages_getPackagesValue')

    def Reload(self):
        self._pkindex = -1

    @property
    def PackageNames(self):
        """
        Get package names as a list.
        """
        return Req.get_result('IDE_Packages_getPackagesValue', 'PackageNames')

    @property
    def Count(self):
        """
        Get number of packages.
        """
        return len(self.PackageNames)

    def GetPackage(self, index):
        return PRPackage(index)

    def Install(self, index):
        res = Req.get_result('IDE_Packages_Install', \
            index if isinstance(index, basestring) else self._getpkname(index))
        self.Reload()
        return res

    def Uninstall(self, index):
        res = Req.get_result('IDE_Packages_Uninstall', \
            index if isinstance(index, basestring) else self._getpkname(index))
        self.Reload()
        return res

    def IsInstalled(self, index):
        return ((path.basename(index) if isinstance(index, basestring) \
            else self._getpkname(index, False)) in self.PackageNames)

    def _getpkindex(self, pkname):
        for i, pk in enumerate(self.PackageNames):
            if path.basename(pkname).lower()==pk.lower():
                return i
        return -1

    def _getpkname(self, index, FullPath=True):
        if (index < 0) or (index >= self.Count):
            raise IndexError('Wrong package index {0}!'.format(index))
        pk = self.GetPackage(index)
        return pk.FileName if FullPath else pk.Name

    def __iter__(self):
        """
        <Iteration protocol>
        Return this object as an iterator.
        """
        return self

    def next(self):
        """
        <Iteration protocol>
        Return a next package in the collection.
        """
        if self._pkindex >= (self.Count - 1):
            raise StopIteration
        self._pkindex += 1
        return self.GetPackage(self._pkindex)

    def __next__(self):
        "<Next> iterator in Python 3.x"
        return self.next()

    def __getitem__(self, index):
        """
        <Indexing protocol: OBJECT[INDEX]>
        Return a package indexed by numerical index.
        Raise IndexError if index is invalid.
        """
        if (index < 0) or (index >= self.Count):
            raise IndexError('Wrong package index {0}!'.format(index))
        return self.GetPackage(index)

    def __contains__(self, pk):
        """
        <Containment check>
        Used in expressions like (if item in collection...).
        """
        try:
            return bool(self.GetPackage(pk))
        except:
            return False

    def __len__(self):
        """
        <Typecasting protocol>
        Used to assert that the object is non-zero (cast to bool):
        return number of packages.
        """
        return self.Count

    def __str__(self):
        """
        <Typecasting protocol>
        Return the PackageNames list as a string.
        """
        return pyrad.tostr(self.PackageNames)


#---- COMMON ACTIONS


class PRCommon(PRObject):
    """
    Class performing miscellaneous IDE operations and containing
    various IDE constants, like common directories, IDE handle, and so on.
    ------------------------------------------------------------
    Available properties:
        * BaseRegistryKey:                  (string)
        * ProductIdentifier:                (string)
        * ParentHandle:                     (int)
        * ActiveDesignerType:               (string)
        * RootDirectory:                    (string)
        * BinDirectory:                     (string)
        * TemplateDirectory:                (string)
        * ApplicationDataDirectory:         (string)
        * LocalApplicationDataDirectory:    (string)
        * IDEPreferredUILanguages:          (string)
        * StartupDirectory:                 (string)
    """
    def __init__(self):
        PRObject.__init__(self)
        self.Reload()

    def Reload(self):
        """
        Retrieve properties from the object on the server
        and add them as attributes to this class instance.
        """
        dResult = Req.get_result('IDE_Common_getEnvironment')
        if isinstance(dResult, dict):
            self.__dict__.update(dResult)
        else:
            raise EPRError('Error loading properties from IDE_Common_getEnvironment!\n'
                           'Returned result = {0}'.format(dResult))

    def IsProject(self, fname, CheckExists=True):
        return (path.isfile(fname) and Req.get_result_bool('IDE_Common_IsProject', fname)) \
                if CheckExists else Req.get_result_bool('IDE_Common_IsProject', fname)

    def IsProjectGroup(self, fname, CheckExists=True):
        return (path.isfile(fname) and Req.get_result_bool('IDE_Common_IsProjectGroup', fname)) \
                if CheckExists else Req.get_result_bool('IDE_Common_IsProjectGroup', fname)

    def ExpandRootMacro(self, rootmacro):
        return Req.get_result('IDE_Common_getExpandRootMacro', rootmacro)

    def OpenFile(self, fname):
        return Req.get_result_bool('IDE_Actions_OpenFile', fname)

    def CloseFile(self, fname, SaveBeforeClose=True):
        if SaveBeforeClose: self.SaveFile(fname)
        return Req.get_result_bool('IDE_Actions_CloseFile', fname)

    def CloseAllFiles(self, SaveBeforeClose=True):
        if SaveBeforeClose: Req.get_result_bool('IDE_MainMenu_ExecuteAction', 'FileSaveAllCommand')
        return Req.get_result_bool('IDE_MainMenu_ExecuteAction', 'FileCloseAllCommand')

    def ReloadFile(self, fname):
        return Req.get_result_bool('IDE_Actions_ReloadFile', fname)

    def SaveFile(self, fname):
        return Req.get_result_bool('IDE_Actions_SaveFile', fname)

    def OpenProject(self, fname, NewProjectGroup=True):
        return Req.get_result_bool('IDE_Actions_OpenProject', fname, NewProjectGroup)


#---- MAIN MENU & IDE ACTIONS


class PRMainMenu(PRObject):
    """
    Class performing operations with the IDE main menu and actions.
    The most common operations are 'ExecuteMenuItem' - the method to
    call a menu item given its 'absolute caption path' (see function description),
    and 'ExecuteAction' - to execute an internal IDE action given its name.
    """
    def __init__(self):
        PRObject.__init__(self)

    @property
    def LastError(self):
        return PRObject._getlasterror(self, 'IDE_MainMenu_getValue')

    def MenuToFile(self, fname):
        """
        Output the IDE menu structure to a text file (creating it if it doesn't
        exist, or overwriting if otherwise). This method is helpful to have
        all the menu captions at hand, ready to be passed to 'ExecuteMenuItem'.
        """
        return Req.get_result_bool('IDE_MainMenu_WriteToFile', fname)

    def MenuToStr(self):
        """
        Same as 'MenuToFile', but outputs to a string rather than a file.
        """
        return pyrad.tostr(Req.get_result('IDE_MainMenu_getValue', 'MainMenuString'))

    def ActionsToFile(self, fname):
        """
        Same as 'MenuToFile', but appends action names to menu item captions,
        so that an action name may be passed to 'ExecuteAction'.
        """
        return Req.get_result_bool('IDE_MainMenu_WriteActionsToFile', fname)

    def ExecuteMenuItem(self, ItemText, Delimiter='|'):
        """
        Executes an item in the IDE menu - just as if that item is clicked.
        The item is passed in 'ItemText' as an 'absolute caption path', i.e.
        the full path of the item in the menu structure comprised of captions
        and delimited by the string given in the 'Delimiter' argument.
        E.g. if Delimiter == '|' (by default), the Replace dialog can be accessed as
        'Search|Replace...'. Ampersand characters ('&') used for keyboard control
        are stripped, so 'ItemText' is passed without these, e.g. 'Reopen' and NOT '&Reopen'.
        """
        return Req.get_result_bool('IDE_MainMenu_ExecuteMenuItem', ItemText, Delimiter)

    def ExecuteAction(self, ActionName):
        """
        Executes an internal IDE action given its name. All the action names
        tied to menu items can be retrieved using the 'ActionsToFile' method.
        """
        return Req.get_result_bool('IDE_MainMenu_ExecuteAction', ActionName)

    def __str__(self):
        """
        <Typecasting protocol>
        Return the IDE main menu as a string.
        """
        return self.MenuToStr()

#-------------------------------------------------------------------------------