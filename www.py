### Copyright 2014-2015 Gaia Clary
###
### This file is part of Sparkles.
### 

### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, addon_utils
import urllib.request, mimetypes, http, xml, os, sys, re, tempfile
import logging
from urllib.error import URLError, HTTPError
from os import path
from bpy.props import *

registerlog = logging.getLogger("avastar.register")

def extract_host_from(url):
    if url.find("://") == -1 :
        host = ""
    else:
        split = url.split("://", 1)
        if len(split) == 2:
            split = split[1].split("/", 1)
        host = split[0]
    return host







def call_url(self, url, supported_extensions=None):
    response = None
    code = 200
    if url.startswith("blender://"):
        print("URL is a blender data source")

        ds = url[10:].split("/")
        mod  = sys.modules[ds[0]]
        func = ds[1]
        print("Call %s.%s" % (mod,func)) 
        data_source = getattr(mod,func)
        data = data_source()
        extension = None
        filename = None
    else:
        ssl_context = install_certificates()
        try:

            https_handler = urllib.request.HTTPSHandler(context=ssl_context)
            opener = urllib.request.build_opener(https_handler)
            print("Calling:[%s]" % url)
            response = opener.open(url)
        except HTTPError as e:
            code = e.code
            msg = 'URL Reader: The server rejected to process the request.'
            print(msg)
            print('Error code: ', code)
            self.report({'ERROR'},(avastar_www_error_popup_text %(msg, code, http.client.responses[e.code])))
            return None, None, None, code
        except URLError as e:
            code = 500
            msg = 'URL  Reader: The server did not respond.'
            print(msg)
            print('Reason: ', e.reason)
            self.report({'ERROR'},("%s.\n Reason:%s\nDownload aborted." %(msg, e.reason)))
            return None, None, None, code
        except:
            code = 500
            msg = "URL Reader: Could not get data from server HTTP for unknown reason."
            print("system info:", sys.exc_info())
            print(msg)
            self.report({'ERROR'},("%s.\nDownload aborted." %(msg)))
            return None, None, None, code

        data = None

        if response is None:

            filename  = os.path.basename(url)
            extension = os.path.splitext(filename)[1]
        else:

            extension, filename = get_extension_and_name(self, response, supported_extensions)

    return response, extension, filename, code

def update_url(self, url, supported_extensions=None):
    data, ext, fname, code = call_url(self, url, supported_extensions)
    return data

def create_feed_url(link, userid="", password=""):
    url = link.replace("$userid",userid.replace(" ","+"))
    url = url.replace("$password",password.replace(" ","+"))

    url = prepare_url(url)
    return url
    






def prepare_url(href, query=None):
    url = ""
    




    if sys.platform.lower().startswith("win"):
        if href[1] == ":": # is a windows file
            url = "file:///"
    else:
        if href.startswith("/"): # is a unix file
            url = "file://"
    url += href
    

    if not query is None and href.startswith("http"):
        hasQuery = (url.find("?") != -1)
        if not hasQuery:
            url += "?"
        else:
            if not url.endswith(("?", "&")):
                url +="&"
        url += query

    return url

    







def get_extension_and_name(self, response, supported_extensions=None):

    filename = None
    extension = None
    

    content_disposition = response.getheader('content-disposition')
    if not content_disposition is None:
        namep_match = self.filename_pattern.match(content_disposition)
        if not namep_match is None:
            filename = namep_match.group(1)
            extp_match = self.extension_pattern.match(filename)
            if not extp_match is None:
                extension = "." + extp_match.group(1)
        return extension, filename
    

    content_type = response.getheader('content-type')
    if not content_type is None:

        extension = mimetypes.guess_extension(content_type.lower())
          

        if supported_extensions == None or extension in supported_extensions:
            path = urllib.parse.urlparse(response.geturl()).path
            fn   = path.rpartition('/')[2]
            ext  = '.' + fn.rpartition('.')[2]
            if supported_extensions == None or ext in supported_extensions:
                filename = fn
            return extension, filename;

    return None, None


def install_certificates():




    import ssl
    import platform
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.check_hostname = True
    ssl_context.load_default_certs()

    if platform.system().lower() == 'darwin':
        import certifi
        ssl_context.load_verify_locations(
            cafile=os.path.relpath(certifi.where()),
            capath=None,
            cadata=None)
    return ssl_context


classes = (

)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)
        registerlog.info("Registered www:%s" % cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
        registerlog.info("Unregistered www:%s" % cls)
