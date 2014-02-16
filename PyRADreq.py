# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        PyRADreq
# Purpose:
#
# Author:      ShafikovIS
#
# Created:     27.10.2013
# Copyright:   (c) ShafikovIS 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import sys, requests, json

#-------------------------------------------------------------------------------

class EGenericError(Exception):
    """
    Base exception type to use in this library.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

#-------------------------------------------------------------------------------

class Req:
    """
    Class for raw client-server communication.
    Exposes the 'get_result' method that returns the actual result of
    executing a server method.
    """
    def __init__(self, DSConfig=None):
        """
        <Constructor>
        Assign the DataSnap server URL (including hostname & port)
        and the client login/password either from the commandline parameters
        or optionally from a dictionary argument.
        """
        # if DSConfig is None, use commandline params
        if not DSConfig:
            # there must be exactly 6 params (argv[0] = script path)
            if len(sys.argv) != 6:
                raise EGenericError(u'There must be exactly 5 commandline parameters!')
            else:
                # construct Dserver URL (string) and Auth (tuple) from commandline params
                self.Dserver = u'http://{0}:{1}/{2}/'.format(*sys.argv[1:4])
                self.Auth = (sys.argv[4], sys.argv[5])
        # otherwise, use DSConfig
        else:
            # check DSConfig (must be a dictionary and contain these 5 keys)
            if isinstance(DSConfig, dict) and \
            ([u'Hostname', u'Login', u'Password', u'Port', u'URL'] <= sorted(DSConfig.keys())):
                # construct Dserver URL (string) and Auth (tuple) from DSConfig values
                self.Dserver = u'http://{Hostname}:{Port}/{URL}/'.format(**DSConfig)
                self.Auth = (DSConfig[u'Login'], DSConfig[u'Password'])
            else:
                raise EGenericError(u'Wrong parameter DSConfig passed to Req constructor!')
        # check connection, raise an error on failure
        if not self.check_connection():
            raise EGenericError(u'Failed to connect to the DataSnap server!')

    #------------------ PUBLIC METHODS ----------------------#

    def check_connection(self):
        """
        Execute the 'CheckConnection' method on the server that returns true.
        If this method raises no errors and returns true, it means that the
        client-server connection is established properly.
        """
        return self.get_result_bool(u'CheckConnection')

    def get_result(self, sFunc, *args):
        """
        Execute a server-side function with the name given by sFunc
        and the optional arguments passed as args.
        If no errors occur, returns a formatted result that may be of any
        type.
        """
        try:
            # make REST url from hostname, port, server url, the function name and arguments
            surl = self.Dserver + self.__get_funcstring(sFunc, *args)
            # post request and authorization data
            req = requests.post(url=surl, auth=self.Auth)
        except requests.exceptions.RequestException as err:
            # internation Requests exception
            raise EGenericError(err)
        except:
            # some other exception
            raise EGenericError(u'Unexpected error in get_result!')
        else:
            # if no exceptions are raised,
            # format result string as a JSON object (dictionary)
            # (remove extra quotation marks and escape characters)
            sRes = req.text.replace(r'["{', '[{').replace(r'}"]', '}]')
            sRes = sRes.replace(r'["[', '[[').replace(r']"]', ']]')
            sRes = sRes.replace(r'["\"', '["').replace(r'\""]', '"]')
            sRes = sRes.replace(r'\"', r'"').encode('utf-8')
            try:
                # parse result into a dictionary and return formatted data
                return self.__format_result(json.loads(sRes))
            except:
                # we get here if json.loads has raised an exception
                raise EGenericError(u'Error calling in json.loads(%s)!' % sRes)

    def get_result_bool(self, sFunc, *args):
        """
        Wrapper method for Boolean results.
        Perform an additional type check (result must be Boolean).
        """
        bRes = self.get_result(sFunc, *args)
        return isinstance(bRes, bool) and bRes

    def print_result(self, Res, ofile=sys.stdout):
        """
        Perform 'pretty' output of JSON data passed in Res.
        """
        if Res is None:
            ofile.write(u'<NO RESULT>')
        else:
            if isinstance(Res, dict):
                ofile.write(json.dumps(Res, ensure_ascii=False, indent=4, separators=(',', ': ')))
            else:
                ofile.write(unicode(Res))

    #------------------ PRIVATE METHODS ----------------------#

    def __get_funcstring(self, sfunc, *args):
        """
        Construct a partial REST method URL ('Funcname/arg1/arg2/...')
        from a function name (sfunc) and arguments (args).
        """
        # surround function name by URI-coded quotation marks to prevent
        # DataSnap server from prefixing it with 'update'.
        # http://docwiki.embarcadero.com/RADStudio/XE5/en/DataSnap_REST_Messaging_Protocol
        sfuncstr = u'%22' + sfunc + u'%22/'
        # if there are arguments, separate them by '/' and append to URL
        if args:
            sargs = u'/'.join([x if isinstance(x, basestring) \
                                 else unicode(x) for x in args])
            sfuncstr += sargs
        return sfuncstr

    def __format_result(self, dRes):
        """
        Format data returned by get_result:
            1) if result has the 'result' key,
                returns the first resulting object
            2) if result has the 'error' key,
                returns the error message
            3) otherwise, returns None
        """
        if u'result' in dRes:
            return dRes[u'result'][0] if len(dRes[u'result']) else None
        elif u'error' in dRes:
            return u'ERROR: ' + dRes[u'error']
        return None