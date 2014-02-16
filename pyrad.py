# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        pyrad
# Purpose:
#
# Author:      shafikovis
#
# Created:     08.11.2013
# Copyright:   (c) shafikovis 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from __future__ import print_function
import sys, requests, json, pickle

#-------------------------------------------------------------------------------

STR_ENCODING = 'utf-8'          # default encoding

def tostr(what):
    "Portable (Py 2/3) function to convert anything to a unicode string"
    if sys.version_info[0] < 3: return unicode(what)
    else: return str(what)

class EGenericError(Exception):
    "Base exception type to use in this library."
    def __init__(self, value):
        self.value = value
    def __str__(self):
        try:
            return tostr(self.value)
        except:
            return repr(self.value)

#-------------------------------------------------------------------------------

class PReq(object):
    """
    Class for raw client-server communication.
    Exposes the 'get_result' method that returns the actual result of
    executing a server method.
    """

    UsageHelp = \
    """
    *** USAGE (one of the following):

    1) <main.py> pickle-filename
    * pickle-filename - pickle binary file to load settings from
    2) <main.py> hostname port URL [login password]
    * hostname - machine hostname where the server is running, e.g. 'localhost'
    * port - server port number, e.g. 8180
    * URL - DataSnap URL, e.g. 'datasnap/rest/TServerClass'
    * login - DataSnap authorization login, if present (optional)
    * password - DataSnap authorization password, if present (optional)
    """

    def __init__(self, check_connection_method='', DSConfig=None):
        """
        <Constructor>
        Assign the DataSnap server URL (including hostname & port)
        and the client login/password either from the commandline parameters
        or optionally from a dictionary argument.
        """
        # if DSConfig is None, use commandline params
        if DSConfig is None:
            # there must be either 2 or 6 params (argv[0] = script path)
            if len(sys.argv) == 2:
                # argv[1] = pickle binary file to load DSConfig from
                try:
                    DSConfig = pickle.load(open(sys.argv[1], 'rb'))
                    self.__init__(check_connection_method, DSConfig)
                except:
                    raise EGenericError('Error loading (DSConfig) dictionary!\n' + self.UsageHelp)
            elif len(sys.argv) < 4:
                raise EGenericError(self.UsageHelp)
            else:
                # construct from commandline params
                self.Hostname = sys.argv[1]
                self.Port = int(sys.argv[2])
                self.URL = sys.argv[3]
                self.Dserver = 'http://{0}:{1}/{2}/'.format(*sys.argv[1:4])
                self.Auth = (sys.argv[4], sys.argv[5]) if len(sys.argv) >= 6 else None
        # otherwise, use DSConfig
        else:
            # check DSConfig (must be a dictionary and contain at least 3 keys)
            if isinstance(DSConfig, dict):
                # construct from DSConfig values
                if ('Hostname' in DSConfig) and ('Port' in DSConfig) and ('URL' in DSConfig):
                    self.Hostname = DSConfig['Hostname']
                    self.Port = int(DSConfig['Port'])
                    self.URL = DSConfig['URL']
                    self.Dserver = 'http://{Hostname}:{Port}/{URL}/'.format(**DSConfig)
                else:
                    raise EGenericError('DSConfig must contain the following keys: Hostname, Port, URL!')
                if ('Login' in DSConfig) and ('Password' in DSConfig):
                    self.Auth = (DSConfig['Login'], DSConfig['Password'])
                else:
                    self.Auth = None
            else:
                raise EGenericError('Wrong parameter (DSConfig) passed to (Req) class constructor!')
        # check connection, raise an error on failure
        if not self.check_connection(check_connection_method):
            raise EGenericError('Failed to connect to the DataSnap server!')

    def __del__(self):
        """
        <Destructor>
        Leave unassigned, so it can be overridden by subclasses.
        """
        pass

    #------------------ PUBLIC METHODS ----------------------#

    def check_connection(self, check_connection_method=''):
        """
        Execute the 'CheckConnection' method on the server that returns true.
        If this method raises no errors and returns true, it means that the
        client-server connection is established properly.
        """
        return self.get_result_bool(check_connection_method) \
            if check_connection_method else True

    def get_result(self, func_name, *args, **kwargs):
        """
        Execute a server-side function with the name given by func_name
        and the optional arguments passed as args.
        If no errors occur, returns a formatted result that may be of any
        type.
        """
        try:
            # extract the 'quotemethod' and 'requesttype' params from kwargs
            quotemethod = kwargs.pop('quotemethod', True)
            requesttype = kwargs.pop('requesttype', 'post')
            # make RESTful url from hostname, port, server url, the function name and arguments
            surl = self.Dserver + self.__get_funcstring(func_name, quotemethod, *args)
            # add request URL, authorization data (if present), and headers
            kwargs['url'] = surl
            if self.Auth: kwargs['auth'] = self.Auth
            kwargs['headers'] = {'Accept': 'application/json',
                'Content-Type': 'text/plain;charset=UTF-8'}

            #print('Request string = {0}'.format(str(kwargs)))

            # post/get request with all additional data
            if requesttype.lower() == 'post': req = requests.post(**kwargs)
            elif requesttype.lower() == 'get': req = requests.get(**kwargs)
            else: raise EGenericError('Wrong request type!')

        except EGenericError:
            # re-raise all EGenericError exceptions
            raise

        except requests.exceptions.RequestException as err:
            # internal Requests exception
            # (see RequestException in requests.exceptions)
            raise EGenericError(err.__class__.__doc__)

        except Exception as err:
            # some other exception
            raise EGenericError(err)

        else:
            # if no exceptions have been raised...
            # get result as a Unicode string
            sRes = self.__format_result_text(req.text)
            try:
                # parse result into a dictionary and return formatted data
                Res = self.__format_result(json.loads(sRes, encoding=STR_ENCODING)) \
                    if sRes.startswith('{') and sRes.endswith('}') and (':' in sRes) \
                    else sRes
                return Res
            except Exception as err:
                # we get here if json.loads has raised an exception
                raise EGenericError('Error: {0}\nRaw result: {1}'.format(tostr(err), sRes))

    def get_result_bool(self, func_name, *args, **kwargs):
        """
        Wrapper method for Boolean results.
        Perform an additional type check (result must be Boolean).
        """
        bRes = self.get_result(func_name, *args, **kwargs)
        return isinstance(bRes, bool) and bRes

    def print_result(self, result_object, ofile=sys.stdout):
        """
        Perform 'pretty' output of JSON data passed in result_object.
        """
        if result_object is None:
            ofile.write('<NO RESULT>\n')
        else:
            if isinstance(result_object, dict):
                ofile.write(json.dumps(result_object, ensure_ascii=False, \
                encoding=STR_ENCODING, indent=4, separators=(',', ': ')) + '\n')
            else:
                ofile.write(tostr(result_object) + '\n')

    #------------------ PRIVATE METHODS ----------------------#

    def __get_funcstring(self, func_name, quotemethod=True, *args):
        """
        Construct a partial REST method URL ('Funcname/arg1/arg2/...')
        from a function name (func_name) and arguments (args).
        """
        # surround function name by URI-coded quotation marks to prevent
        # DataSnap server from prefixing it with 'update'.
        # http://docwiki.embarcadero.com/RADStudio/XE5/en/DataSnap_REST_Messaging_Protocol
        sfuncstr = '%22' + func_name + '%22' if quotemethod else func_name
        sfuncstr += '/'
        # if there are arguments, separate them by '/' and append to URL
        if args:
            sargs = '/'.join(x if isinstance(x, basestring) else tostr(x) for x in args)
            sfuncstr += sargs
        return sfuncstr

    def __format_result_text(self, result_text):
        """
        Format result string as a JSON object (dictionary)
        (remove extra quotation marks and escape characters)
        """
        sRes = result_text.replace(r'["{', '[{').replace(r'}"]', '}]')
        sRes = sRes.replace(r'["[', '[[').replace(r']"]', ']]')
        sRes = sRes.replace(r'["\"', '["').replace(r'\""]', '"]')
        sRes = sRes.replace(r'\"', r'"')
        return tostr(sRes)

    def __format_result(self, result_object):
        """
        Format data returned by get_result:
            1) if result has the 'result' key,
                returns the first resulting object
            2) if result has the 'error' key,
                returns the error message
            3) otherwise, returns None
        """
        if isinstance(result_object, dict):
            if 'result' in result_object:
                return result_object['result'][0] \
                if len(result_object['result']) else None
            elif 'error' in result_object:
                return 'ERROR: ' + result_object['error']
            elif 'SessionExpired' in result_object:
                return 'ERROR: ' + result_object['SessionExpired']
            else:
                return result_object[len(result_object.keys())-1]
        return result_object or None

#-------------------------------------------------------------------------------