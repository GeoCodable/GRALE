# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# metadata
__name__            = 'grale'
__alias__           = 'grale'
__author__          = 'GeoCodable'
__credits__         = ['GeoCodable']
__version__         = '0.0.4'
__maintainer__      = 'GeoCodable'
__email__           = 'https://github.com/GeoCodable'
__status__          = 'Alpha'
__create_date__     = '20220118'  
__version_date__    = '20220123'
__info__ = \
    '''
    Description:
    
    GRALE - Geospatial Request and Log Extraction

    The GRALE module contains functions and classes to standardize requests
    sent to geospatial REST API's. Response data, metadata capture, and 
    logging information are also standardized to create efficiencies as a 
    preliminary step in ETL workflows that involve geospatial REST API's.  
    Advanced options are available to optimize speed and memory 
    usage in the extraction phase of ETL workflows. Options include
    multi-threaded request/response cycles, 'low memory' options in 
    an effort to reduce memory usage/errors and storage capacity required 
    for outputs, and .p12/PFX credentialing support.  

    *Note: 0.0.1 Capabilities are limited to GET requests on ArcGIS REST API's 
        feature and map services at this time.  
 
    '''
__all__         = [ 'THREAD_LOCAL', 'MESSAGE_LOCK', 
                    'GRALE_SESSION', 'GRALE_LOG',
                    'geojsons_to_df', 'merge_geojsons', 
                    'parse_qs', 'read_geojson', 
                    'read_geojsons', 'graleReqestLog',
                    'sessionWrapper', 'esri'
                   ]
#------------------------------------------------------------------------------ 
import sys, os, re, uuid, json, gzip, requests, requests_pkcs12, urllib3
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from arcgis2geojson import arcgis2geojson
from datetime import datetime as dt
from shutil import rmtree
import threading

import pandas as pd
from shapely.geometry import shape 
#------------------------------------------------------------------------------                    
#------------------------------------------------------------------------------ 
# functions
#------------------------------------------------------------------------------ 
def _bytes_unit_conversion(size_bytes):
    """Function converts bytes into the largest (divisible by 1024)
    unit of measure, retuning a dictionary with the value and best 
    unit of measure Ex. 1000000 = '976.56(KB)'
    
    Parameters
    ----------
    size_bytes : int, required
        integer representing size in bytes
        
    Returns
    -------
    dictionary : 
        A string representing the value with the largest 
        unit of measure for the given byte value

    Examples
    -------
    >>> _bytes_unit_conversion(1000000)
    >>> '976.56(KB)'
    """
 
    kibi  = 1024
    n = 0
    rtnUnits = {0 : 'B' , 1: 'KB', 2: 'MB',
                3 : 'GB', 4: 'TB', 5: 'PB',
                6 : 'EB', 7: 'ZB', 8: 'YB'}    
    rtnSize = size_bytes
    while rtnSize >= kibi and n < 9:
        rtnSize /= kibi 
        n += 1
    return f'{round(rtnSize,2)}({rtnUnits[n]})'
#------------------------------------------------------------------------------            
def _parse_url_query(url):
    """
    This function takes a url string with request query/parameters 
    and returns a dictionary of of parameter values and the base 
    URL/API resource path as a string.
    
    Parameters
    ----------
    url : str, required
        String API URL with query parameters.
        Ex. r'https://someResource/query?outSR=4326&f=JSON'
    Returns
    -------
    p_params : dictionary
        Each key in the dictionary represents a parsed parameter
        within an API query (str). values are returned as lists
        to account for in the event that a parameter is used 
        multiple times. Along with the parameters is 
        the base_url which is the resource/API locator. 

    """   
    pUrl = urlparse(url)
    p_params = parse_qs(pUrl.query)
    p_params['base_url'] = [pUrl._replace(query=None).geturl()]
    
    return p_params
#------------------------------------------------------------------------------
def _validate_file_name(file_name, ext=None):

    """
    Function returns a validated file name by removing any characters 
    which are not allowed in file names.  The function also accounts
    for max allowed file name length (255). When an extension type is
    supplied, the file name length is adjusted based on the max length(255) 
    minus the length of the extension type. 

    Parameters
    ----------
    file_name : str, required
        file name string to be applied
    ext : str, optional
        file extension type without the leading decimal/period

    Returns
    -------
    file_name : str
        A validated and/or re-formatted file name including extension 
        when supplied supplied. 

    """    
    
    file_name = str(file_name)
    file_name = re.sub(r'[^\.\w\s-]', '', file_name.lower())
    file_name = re.sub(r'[-\s]+', '-', file_name).strip('-_')

    if not bool(file_name):
        file_name = str(uuid.uuid4())
    if bool(ext):
        prefix_len = 255 - (len(ext) + 1)
        file_name = f'{file_name[0:prefix_len]}.{ext}' 
    else:
        file_name = file_name[0:255] 
    return file_name
#------------------------------------------------------------------------------
def _get_file_name_seq_path(f_path):

    """
    Function returns a validated file path that prevents overwriting existing 
    files. If the input file path already exists, the function will iterate 
    until it finds a file path that does not exist yet. The return file path 
    will be named via a sequence number preceding the file name.
        i.e.  "input_file.csv" returns "1_input_file.csv" when input_file.csv 
        already exists

    Parameters
    ----------
    f_path : str, required
        file path string to be applied

    Returns
    -------
    out_path : str
        A validated and/or re-formatted file path which does not previously 
        exist in a given directory. 

    """       
    
    file_name, file_ext = os.path.splitext(os.path.basename(f_path))
    p_dir = os.path.abspath(os.path.join(f_path, os.pardir))
    valid_name = _validate_file_name(file_name, ext=file_ext[1:])  
    out_path = os.path.join(p_dir, valid_name)

    if not os.path.isfile(out_path):
        return out_path
    else:
        i = 0
        while os.path.isfile(out_path):
            i += 1
            new_file_name = f'{i}_{valid_name}'
            out_path = os.path.join(p_dir, new_file_name)
    return (out_path)
#------------------------------------------------------------------------------
def _get_nested_key_value(dict_obj, key):
    """Recursive value lookup for given and key 
    in a nested dictionary.

    This function recursively searches a nested 
    dictionary structure like JSON for the first 
    occurrence of a key. Once the key is found, 
    it's associated value is returned. If the key 
    is not found, None is returned.
    
    Parameters
    ----------
    dict_obj : dict, required
        Dictionary object to be recursively searched

    key : any immutable type(string,number,tuple,...), required 
        Value representing a nested or un-nested
        dictionary key
        
    Returns
    -------
    n_val : any immutable type, (ex. strings,numbers,tuples)
        If the key exists in the dictionary at any level 
        of nesting, the value will be returned, else None 
        is returned.

    Examples
    -------
    >>> d = {'data': {'apple': 'red', 'banana': 'yellow'}}
    >>> _get_nested_key_value(d, 'banana')
    >>> 'yellow'
    """   
    n_val = None
    if key in dict_obj: 
        return dict_obj[key]
    for k, v in dict_obj.items():
        if isinstance(v,dict):
            n_val = _get_nested_key_value(v, key)
            if n_val is not None:
                return n_val
    if n_val is None:
        return n_val
#------------------------------------------------------------------------------            
def _extract_nested_key_values(dict_obj, keys=None):
    """
    Lookup and return dictionary values/properties 
    against a list of keys. 

    This function takes in a list of keys to lookup 
    within a nested dictionary. If the key is not found, 
    the value of the first occurrence is returned. 
    Otherwise, None is returned.
    
    Parameters
    ----------
    dict_obj : dict, required
        Dictionary object to be recursively searched

    keys : list, optional
        List of keys to search/lookup with in a dictionary. 
        
    Returns
    -------
    out_meta : dictionary
        For each key in keys, if the key is in 
        the dict_obj object, the corresponding value
        is returned in a dictionary.  Otherwise the 
        value for the key in the return is None. 

    """   

    out_meta = {}
    if keys: 
        out_meta = {p: _get_nested_key_value(dict_obj, p) 
                    for p in keys}
    else:
        out_meta = dict_obj
    return out_meta
#------------------------------------------------------------------------------ 
def _print(message):
    '''
    Function calls a thread-safe print() via threading.Lock
    to avoid issues with multiple threads printing at the same 
    time on the same line.
    
    Parameters
    --------------------- 
    message : str, required
        Message string to be printed      
    '''
    with MESSAGE_LOCK:
        print(message)    
#------------------------------------------------------------------------------    
def _prep_url(url, headers={}, req_type='GET'):
    """
    Return a prepared/formatted url string given a URL and 
    dictionary of request headers/parameters.  

    Parameters
    ----------
    url : str, required
        Uniform Resource Locator (URL) string of characters which identifies
        a name or a resource on the internet
    headers: dictionary, optional
        Dictionary of request headers;
        See API/REST documentation for all request options;
        Default behavior sends requests without parameters/headers
    req_type : str, optional
        Specifies the request type;
        Valid values include: 'GET', 'POST', 'PUT', 'PATCH' and 'HEAD'
        Default behavior will default to a 'GET' request.

    Returns
    -------
    preped_url : str
        A prepared/formatted request url that includes all header info.

    """        
    preped_url = requests.Request(  req_type,
                                    url, 
                                    params=headers
                                  ).prepare().url
    return preped_url
#------------------------------------------------------------------------------    
def _request_handler(url, showMessages=False, log=None, pid=None):
    """
    Function acts as a request handler for to logging and/or 
    print response status and error messages. Errors will return 
    information to a log object and or print the error rather than
    stopping the program.
    *See the requests python docs for more keyword argument options.
    
    Parameters
    ----------
    url : str, required
        REST API url for the ESRI Feature Service
    showMessages: Boolean, optional
        Boolean option to print messages;
        Default, no messages will be printed to the console
    log : object, optional
        grale request logging object (processLog class).
        If unspecified logging results will persist in grale.GRALE_LOG.log;       
    pid : str, optional
        Unique process.request id for logging
        Default, str(uuid.uuid4())
    Returns
    -------
    rtn_tuple : tuple 
        rtn_tuple:  tuple containing the response object (resp), 
                    the status category (status), and a more detailed 
                    message to convey response results (message)    
    Example
    -------
    >>> url = "https://website.com/.../ArcGIS/rest/services/Parks/FeatureServer/0/query?where1=1"
    >>> response, status, message = _request_handler(
                                                    url=url, 
                                                    log=log, 
                                                    showMessages=True,
                                                    )   
    >>> print(status)
    >>> 'Success' 
    >>> print(message)
    >>> 'Size: 529744(B),Time :1.140771(s)'                                     
    """
       
    resp    = None
    status  = ''
    message = ''
    elapsed_time = '0 (ms)'
    size_bytes = 0
    
    if not log:
        log=GRALE_LOG
        
    try:   
        resp = GRALE_SESSION.get(url)
        resp.raise_for_status()
        
    except requests.exceptions.HTTPError as err:
        status  = 'Error: (HTTPError)'
        message = err
    except requests.exceptions.ConnectionError as err:
        status  = 'Error: (ConnectionError)'
        message = err
    except requests.exceptions.Timeout as err:
        status  = 'Error: (Timeout)'
        message = err
    except requests.exceptions.RequestException as err:
        status  = 'Error: (Unidentified)'
        message = err
    finally:
        if bool(resp):
            if resp.status_code != 200 or 'error' in (resp.text).lower():
                status   = 'Error: (Unidentified)'
                message  = f'ResponseText:{resp.text}'
            else:    
                status   = 'Success'
                message  = [f'Size: {len(resp.content)}(B),' 
                           f'Time :{resp.elapsed.total_seconds()}(s)']
                
            elapsed_time = f'{resp.elapsed.total_seconds()*1000}(ms)'
            size_bytes = f'{len(resp.content)}(B)'
    if showMessages:
        _print(f'\t-{status} |:| {message}')
    log.log_message(url, status, message, elapsed_time, size_bytes, pid)
    rtn_tuple = (resp, status, message)
    return rtn_tuple    
#------------------------------------------------------------------------------  
def _write_geojson_files(geojsons, out_dir, delim = '_._', 
                      ext='geojson', prefix=None, suffix=None,
                      low_memory=None):
    """
    Function takes in a list of geojson/json strings or file paths
    to write results to an output directory/file.  
    
    Parameters
    ----------
    geojsons : list, required
        List of geojson or json string values or files
    out_dir : str, required
        Output location/directory for files to be written         
    delim: str, optional
        Optional file name delimitator
        Default behavior applies '_._' between prefix and suffix values
    ext: str, optional
        Output file extension type, json, geojson, or gz
        Default behavior applies the extension type as geojson
    prefix : str, optional
        file name prefix;
        Default behavior applies the a pattern of data from the request metadata
            Pattern: 'serviceName_._serviceId_._' 
                Ex. 'airport-runway_._2'
    suffix : str, optional
        file name suffix;
        Default behavior applies the a pattern of data from the request metadata
            Pattern: 'timeStamp_._resultOffset_._ParentProcessId_requestUUID
                ' Ex. '2022-07-11t174028.533437_._500_._1b0510b3-543d-4bc4-95fe-ddc10b442ce3_._f6e8e317-a91d-4b72-b3cd-5cfc9c02e3d'
    low_memory : bool, optional
        If true, results are compressed using gzip format;
        Default None or False              
    Returns
    -------
    file_paths : list 
        file_paths:  list of output file paths.    
    """
    
    file_paths = []
    for i in geojsons: 
        data = read_geojson(i)
        if not bool(data):
            continue
        f_name = 'temp'
        if not prefix:
            if 'request_metadata' in data: 
                md = data['request_metadata'][0]
                if 'name' in md:
                    f_name = f"{md['name']}"
                if 'id' in md:
                    f_name += f"{delim}{md['id']}" 
        else:
            f_name = prefix
            
        if not suffix:
            sd = []
            if 'request_logging' in data:
                rl = data['request_logging'][0]
                if 'utc_timestamp' in rl:
                    sd.append(rl['utc_timestamp'])
                else:
                    sd.append(dt.utcnow().isoformat(timespec='seconds', sep='T'))
                if 'parameters' in rl:
                    if 'resultOffset' in rl['parameters']:
                        sd.append(rl['parameters']['resultOffset'][0])
                if 'grale_uuid' in rl: 
                    sd.append((rl['grale_uuid']).replace('_',delim))
            elif bool(f_name):
                sd.append(dt.utcnow().isoformat(timespec='seconds', sep='T'))    
            else:
                sd.append(dt.utcnow().isoformat(timespec='seconds', sep='T'))
            f_name += delim.join(sd)
        else:
            f_name += f"{delim}{suffix}"
                
        if not low_memory and ext != '.gz': 
            f_path = _get_file_name_seq_path(
                                 os.path.join(
                                              out_dir, 
                                              f'{f_name}.{ext}'
                                              )
                                            ) 
            with open(f_path, 'w') as gjf:
                gjf.write(json.dumps(data, indent=4))
        else:
            f_path = _get_file_name_seq_path(
                                 os.path.join(
                                              out_dir, 
                                              f'{f_name}.{"gz"}'
                                              )
                                            )                   
            with gzip.open(f_path, 'wb') as f:
                f.write(json.dumps(data, indent=4).encode()) 
        file_paths.append(f_path)
    return(file_paths)    
#------------------------------------------------------------------------------ 
def read_geojson(in_geojson):
    """
    Function reads/loads a geojson object, gzip 
    file or GeoJSON file to return a python json
    object/dictionary.
    
    Attributes/Parameters
    --------------------- 
    in_geojson : str, Required
        String geojson object or a file path pointing
        to a gzip or geojson file. 
    """
    if not bool(in_geojson):
        _print('Warning: No data to process')
        return {}
    elif isinstance(in_geojson, str):
        if not os.path.isfile(in_geojson):
            return json.loads(in_geojson)
        else:
            try:
                in_ext = os.path.splitext(in_geojson)[1]
                if in_ext == '.gz' or in_ext == '.gzip':
                    with gzip.open(in_geojson,'rb') as f:
                        json_obj = json.loads(f.read().decode())
                elif in_ext == '.geojson' or in_ext == '.json':
                    with open(in_geojson) as f:
                        json_obj = json.loads(f.read())            
                else:
                    _print(f'Unsupported file: {in_geojson}')
                return json_obj
            except IOError as e:
                _print(f'I/O error({e.errno}): {e.strerror}')
            except: #handle other exceptions such as attribute errors
                _print (f'Unexpected error:, {sys.exc_info()[0]}')
    elif isinstance(in_geojson, dict):
        return in_geojson
    else:
        _print(f'Unsupported data type: {type(in_geojson)}')
        return {}
#------------------------------------------------------------------------------ 
def read_geojsons(in_geojsons):
    """
    Function calls the read_geojson function to 
    read/loads a list of geojson objects, gzip 
    file or geojosn file to return a list of python 
    json objects/dictionaries.
    
    Parameters
    ----------
    in_geojson : str or list, Required
        list of strings or a single string geojson 
        object or a file path pointing to a gzip or
        geojson file. 
    """
    results = []
    if not bool(in_geojsons):
        _print('Warning: No data to process')
        return results
    elif not isinstance(in_geojsons,list):
        geojsons = [in_geojsons]
    else:
        geojsons = in_geojsons
        
    for gj in geojsons:
        data = read_geojson(gj)
        results.append(data)
    return results
#------------------------------------------------------------------------------ 
def merge_geojsons(in_geojsons, out_path=None): 
    """
    Function merges a list of grale geojson objects
    into a single output geojson object including the
    'request_metadata' and 'request_logging' keys. 
    
    Parameters
    ----------
    in_geojson : str or list, Required
        list of strings or a single string geojson 
        object or a file path pointing to a gzip or
        geojson file. 
    out_path : str, required
        Optional file path to output merged geojson 
        data to a file. 
        default, None 
    """

    out_gj = {'type' : [], 
              'features' : [],  
              'request_metadata' : [],
              'request_logging' : []
              }
    results = []
    
    if not bool(in_geojsons):
        _print('Warning: No data to process')
        return out_gj   
    elif isinstance(in_geojsons,list):
        geojsons = in_geojsons
    elif isinstance(in_geojsons,str):    
        return json.dumps(read_geojson(in_geojsons), indent=4)
    else:
        geojsons = in_geojsons
    read_gj = read_geojsons(geojsons)
            
    for gj in read_gj:
        for k,v in out_gj.items():
            if k in gj:
                i_val = gj[k]
                if isinstance(i_val,list):
                    out_gj[k].extend(i_val)
                else:
                    out_gj[k].append(i_val)
    
    # only store unique metadata objects once joinable on the ppid
    rm_set = set([json.dumps(i) for i in out_gj['request_metadata']])
    out_gj['request_metadata'] =  [json.loads(m) for m in rm_set]
    
    feat_types = set(out_gj['type'])
    if len(feat_types) == 1:
        out_gj['type'] = out_gj['type'][0]
    else:
        _print('Warning: inputs are of mixed GeoJSON text sequences!')
    _print(f'\t-Merged {len(out_gj["features"])} features')
    
    if out_path:
        f_path = _get_file_name_seq_path(out_path) 
        with open(f_path, 'w') as gjf:
            gjf.write(json.dumps(out_gj, indent=4))
        _print(f'\t-Output merged results to:  {f_path}')
    return json.dumps(out_gj, indent=4)
#------------------------------------------------------------------------------ 
def geojsons_to_df(in_geojsons, df_type='DataFrame'):
    """
    Function converts a geojson or a list of geojson
    objects into a dataframe of either the pandas
    or geopandas type. The pandas dataframe type will
    retain the geometry/spatial info as a string while
    the geopandas dataframe is a fully spatially enabled 
    data type with available spatial properties/functions. 
    
    Parameters
    ----------
    in_geojson : str or list, Required
        list of strings or a single string geojson 
        object or a file path pointing to a gzip or
        geojson file. 
    df_type : str, Optional
        Option to return a pandas 'DataFrame' type or
        a geopandas 'GeoDataFrame' type.  Allowed 
        values include 'DataFrame' and 'GeoDataFrame'
        Default, 'DataFrame'
        
    """
    merged = merge_geojsons(in_geojsons)
    gj = json.loads(merged)

    if df_type =='GeoDataFrame':
        try: 
            if 'geopandas' not in sys.modules:
                import geopandas
            return geopandas.GeoDataFrame.from_features(gj["features"])  
        except:
            _print('''Warning: GeoPandas install is not available!
                      Please ensure GeoPandas is installed then try to 
                      import the package directly. If errors persist,
                      attempt to reinstall GeoPandas. 
                      Defaulting data to pandas.dataframe''')
                      df_type ='DataFrame'
            
    if df_type =='DataFrame':
        df_rows = [ {**gj['features'][i]['properties'], 
                     **{'geometry':shape(gj['features'][i]['geometry']).wkt}
                    } 
                    for i in range(len(gj['features']))
                   ]
        return pd.DataFrame(df_rows)
#------------------------------------------------------------------------------
# module classes
#------------------------------------------------------------------------------   
class graleReqestLog:
    """
    Class object to store/log request parameters and result metadata.
    ...

    Attributes
    ----------
    log : ordered dictionary
        dictionary to store information about a given iteration of a 
        larger process.  all dictionary values are string objects.
        log attribute data structure:
            {
            'process UUID':
                {
                'ppid': 'parent process UUID for the iteration/process', 
                'utc_timestamp': 'UTC start timestamp of the iteration/process', 
                'parameters': 'parameters sent to an iteration/process',   
                'status' : 'status category of an iteration/process','  
                'results': 'detailed messages of an iteration/process',
                'elapsed_time': 'total time to run an iteration/process',
                'size': 'size of iteration/process return object'
                }
            }

    ppid : str
        String representing a UUID for a given process.  The ppid 
        value is shared between iterations of a parent process
        
    Methods
    -------
    log_message(self, parameters, status, message, elapsed_time, size_bytes)
        Method for updating the log attribute/dictionary with values from 
        a given process/iteration.   

        Parameters
        ----------
        parameters : str, required
            general parameters of interest sent to the process
        status : str, required
            the return status category EX. 'Success' or 'Error'
        message : str, required
            Detailed process message(s) for debugging and metrics
        elapsed_time : str, required
            total time for the process iteration
        size_bytes : str, required
            return size in bytes for the process iteration

        Returns
        -------
        None : None
            Updates the graleReqestLog.log attribute with a new dictionary item
            to log a process/iteration result.  See dictionary key 
            definitions in the log attribute documentation:

    Example
    -------
    >>> REQUEST_LOG = graleReqestLog()
    >>> REQUEST_LOG.log_message('a=2', 'Error', 'Some Error Message', 
                                '5618.493(ms)', '8807(B)')
    >>> pid     = str(uuid.uuid4())
    >>> response, status, message = _request_handler(
                                                    url=url, 
                                                    log=log, 
                                                    showMessages=True,
                                                    pid=pid
                                                    )   
    >>> REQUEST_LOG.log
    """
    
    def __init__(self):
            
        # dictionary to store the request logging
        self.log = {}
        
        # generate a unique run id
        self.ppid = str(uuid.uuid4())

    def log_message(self, req_url, status, message, 
                            elapsed_time, size_bytes,
                            pid=None):
        if not pid:
            pid = str(uuid.uuid4())
        ts = dt.utcnow().isoformat(timespec='seconds', sep='T')
        
        params = _parse_url_query(req_url)
        grale_uuid = f'{self.ppid}_{pid}'
        self.log[pid] = {
                        'grale_uuid' : grale_uuid,
                        'ppid': self.ppid,
                        'pid' : pid,
                        'utc_timestamp': ts,
                        'request' : req_url,
                        'parameters': params,  
                        'status' : status,   
                        'results': message,
                        'elapsed_time': elapsed_time,
                        'size': size_bytes
                        }
                                
#------------------------------------------------------------------------------   
class sessionWrapper(object):
    """ 
    Class constructor builds a wrapper around all standard request 
    session, retry, and get parameters along with .p12/PFX support 
    (when credentials are supplied). All request session, retry, get, 
    and requests_pkcs12 parameters can be set when initializing 
    a sessionWrapper object or by redefining the properties.  
        
    Parameters
    -----------------------------------------
    max_retries : int, optional, *See urllib3.Retry
        Total number of retries to allow. Takes precedence over other counts.
        Default, 5 retries allowed
    connect : int, optional, *See urllib3.Retry
        How many connection-related errors to retry on.
        Default, None
    read : int, optional, *See urllib3.Retry
        How many times to retry on read errors.
        Default, None
    max_redirects : int, optional, *See urllib3.Retry
        How many redirects to perform. Limit this to avoid infinite redirect
        loops.
        Default, set to allow 10 redirects as is standard in web browsers
    status : int, optional, *See urllib3.Retry
        How many times to retry on bad status codes.
        Default, None
    other : int, optional, *See urllib3.Retry
        How many times to retry on other errors. Other errors are errors 
        that are not connect, read, redirect or status errors.
        Default, None
    allowed_methods : iterable , optional, *See urllib3.Retry
        Set of uppercased HTTP method verbs that we should retry on.
        By default, we only retry on methods which are considered to be
        idempotent (multiple requests with the same parameters end with the
        same state). See :attr:'Retry.DEFAULT_ALLOWED_METHODS'.
        Default, urllib3.util.retry._Default     
    status_forcelist : iterable , optional, *See urllib3.Retry
        A set of integer HTTP status codes that we should force a retry on.
        A retry is initiated if the request method is in ''allowed_methods''
        and the response status code is in ''status_forcelist''.
        Default, list of all status codes of 408 and above    
    backoff_factor : float, optional, *See urllib3.Retry
        A backoff factor (delay) to apply between attempts after the second try
        (most errors are resolved immediately by a second try without a
        delay). ex. urllib3 will sleep for:
            {backoff factor} * (2 ** ({number of total retries} - 1)) seconds.
            If the backoff_factor is 0.1, then :func:'.sleep' will sleep
            for [0.0s, 0.2s, 0.4s, ...] between retries. 
        Default, 0 or disabled
    raise_on_redirect : bool, optional, *See urllib3.Retry
        Whether, if the number of redirects is
        exhausted, to raise a MaxRetryError, or to return a response with a
        response code in the 3xx range.
        Default, True
    raise_on_status : bool, optional, *See urllib3.Retry
        Similar meaning to ''raise_on_redirect'':
            whether to should raise an exception, or return a response,
            if status falls in ''status_forcelist'' range and retries have
            been exhausted.
        Default, True
    history : tuple, optional, *See urllib3.Retry
        The history of the request encountered during each call to :
        meth:'~Retry.increment'. The list is in the order the requests 
        occurred. Each list item is of class :class:'RequestHistory'.
        Default, None
    respect_retry_after_header : bool, optional, *See urllib3.Retry
        Whether to respect Retry-After header on status codes defined 
        as: attr:'Retry.RETRY_AFTER_STATUS_CODES' or not.
        Default, True
    remove_headers_on_redirect : iterable , optional, *See urllib3.Retry
        Sequence of headers to remove from the request when a response
        indicating a redirect is returned before firing off the redirected
        request.
        Default, Default, frozenset(["Authorization"]) 
    _Retry : urllib3.Retry, optional, *requests.adapters.HTTPAdapter
        urllib3.Retry derived from sessionWrapper object attributes
        for granular control over the conditions under which a request is
        retried.  The retry object sets the maximum number of retries each 
        connection should attempt. Note, this applies only to failed DNS 
        lookups, socket connections and connection timeouts, never to 
        requests where data has made it to the server. The Retry
        object also handles redirect parameters for a session. 
        Default, 5 retries(self.max_retries), 10 redirects (self.max_redirects)    
    pool_connections : int, optional, *requests.adapters.HTTPAdapter
        The number of urllib3 connection pools to cache.
        Default, 10 set by requests.adapters.DEFAULT_POOLSIZE
    pool_maxsize : int, optional, *requests.adapters.HTTPAdapter
        The maximum number of connections to save in the pool.
        Default, 10 set by requests.adapters.DEFAULT_POOLSIZE 
    pool_block : bool, optional, *requests.adapters.HTTPAdapter
        Whether the connection pool should block for connections.
        Default, False set by requests.adapters.DEFAULT_POOLBLOCK        
    pkcs12_filename : str , optional, *See requests_pkcs12.Pkcs12Adapter
        Path to a file containing a byte string or unicode string that
        contains the file name of the encrypted PKCS#12 certificate. 
        Either this argument or pkcs12_data must be provided.
        Default, None
    pkcs12_data : str , optional, *See requests_pkcs12.Pkcs12Adapter
        A byte string that contains the encrypted PKCS#12 certificate 
        data. Either this argument or pkcs12_filename must be provided.
        Default, None
    pkcs12_password : str , optional, *See requests_pkcs12.Pkcs12Adapter
        A byte string or unicode string that contains
        the password. This argument must be provided whenever pkcs12_filename 
        or pkcs12_data is provided.
        Default, None
    ssl_protocol : _SSLMethod , optional, *See requests_pkcs12.Pkcs12Adapter
        A protocol version from the ssl library.
        Default, requests_pkcs12.default_ssl_protocol       
    headers : dict, optional, *requests.Session
        Dictionary of HTTP Headers to send with a request.
        Default, requests.utils.default_headers()
    cookies : RequestsCookieJar, optional, *requests.Session
        Dictionary or CookieJar object to send with a request.
        Default, requests.cookies.cookiejar_from_dict({})
    auth: tuple, optional, *requests.Session
        Auth tuple or callable to enable Basic/Digest/Custom 
        HTTP Auth.
        Default, None
    proxies : dict, optional,  *requests.Session
        Dictionary mapping protocol or protocol and hostname 
        to the URL of the proxy.
        Default, {}
    hooks : dict, optional,  *requests.Session
        Dictionary of hooks can be used to alter the request 
        process and/or call custom event handling
        Default, requests.hooks.default_hooks()
    params : dict, optional,  *requests.Session
        Dictionary or bytes to be sent in the query string for
        a request.
        Default, requests.hooks.default_hooks()
    verify : bool, optional,  *requests.Session
        Either a Boolean, in which case it controls whether to 
        verify the server's TLS certificate, or a string, in 
        which case it must be a path to a CA bundle to use. 
        Defaults to 'True'. When set to 'False', requests will 
        accept any TLS certificate presented by the server, and 
        will ignore hostname mismatches and/or expired certificates,
        which will make your application vulnerable to 
        man-in-the-middle (MitM) attacks. Setting verify to 'False' 
        may be useful during local development or testing.
        Default, True
    cert :  str or tuple, optional, *requests.Session
        Either a string path to ssl client cert file (.pem) or
        a tuple of('cert', 'key') pair.
        Default, None
    stream : bool, optional, *requests.Session
        Option to immediately download the response content.
        Default, False   
    timeout : int or tuple, optional, *requests.get
        Details how long (sec) to wait for a client connection 
        and how long (sec) to wait for a read response.
        Default, (30,180)
    verify : bool or str, optional,  *requests.get
        Either a Boolean, in which case it controls whether to 
        verify the server's TLS certificate, or a string, in 
        which case it must be a path to a CA bundle to use. 
        Defaults to 'True'. When set to 'False', requests will 
        accept any TLS certificate presented by the server, and 
        will ignore hostname mismatches and/or expired certificates,
        which will make your application vulnerable to 
        man-in-the-middle (MitM) attacks. Setting verify to 'False' 
        may be useful during local development or testing.
        Default, True) 
    """

    def __init__(self, **kwargs):
        #----------------------------------------------------------------------       
        # Set default attributes
        #---------------------------------------------------------------------- 
        
        # default requests.adapters.Retry params
        self.max_retries = 5  
        self.connect = None
        self.read = None
        self.max_redirects = 10 # None is default, 10 is standard in web browsers
        self.status = None
        self.other = None
        self.allowed_methods = urllib3.util.retry._Default
        self.status_forcelist = [sc for sc in requests.status_codes._codes
                                 if sc >= 408] # default is None
        self.backoff_factor = 0
        self.raise_on_redirect = True
        self.raise_on_status = True
        self.history = None
        self.respect_retry_after_header = True
        self.remove_headers_on_redirect = frozenset(["Authorization"])
        #self.method_whitelist = urllib3.util.retry._Default
        
        # default requests.adapters.HTTPAdapter params
        self.pool_connections = requests.adapters.DEFAULT_POOLSIZE 
        self.pool_maxsize = requests.adapters.DEFAULT_POOLSIZE
        self.pool_block = requests.adapters.DEFAULT_POOLBLOCK
        
        # default requests_pkcs12.Pkcs12Adapter params
        self.pkcs12_data = None
        self.pkcs12_filename = None
        self.pkcs12_password = None
        self.ssl_protocol = requests_pkcs12.default_ssl_protocol
        
        # default requests.Session params
        self.headers = requests.utils.default_headers()
        self.cookies =  requests.cookies.cookiejar_from_dict({})
        self.auth =  None
        self.proxies =  {}
        self.hooks =  requests.hooks.default_hooks()
        self.params =  {}
        self.verify =  True
        self.cert =  None
        self.stream =  False
        self.trust_env =  True
        
        # default requests.get params
        self.timeout = (30, 180)  # 30 sec connect and 180 sec read
        
        # default urllib3.Retry object
        self._Retry = None        
        # default requests HTTP adapter
        self._HTTPAdapter = None
        # default requests_pkcs12 adapter
        self._Pkcs12Adapter = None
        # default requests session 
        self._Session = None

        # allow the object to be initialized with kwargs
        self.__dict__.update(kwargs)
    #--------------------------------------------------------------------------
    # methods 
    #--------------------------------------------------------------------------
    def _get_base_url(self, url):
        """
        Method returns a base url without query parameters. 

        Parameters
        --------------------- 
        url : str, required
            Uniform Resource Locator (URL) string of characters which 
            identifies a name or a resource on the internet
        """    
        # parse the base url from the url
        pUrl = urlparse(url)
        return pUrl._replace(query=None).geturl()        
    
    def _set_retry(self):
        """
        *See urllib3.Retry source for source documentation

        Creates a default urllib3.Retry object that allows automatic retries
        of the exact requests parameters that returned in failure. The Retry
        object also handles redirect parameters for a session. 

        Parameters
        ----------
        self.max_retries : int, optional, *See urllib3.Retry
            Total number of retries to allow. Takes precedence over other counts.
            Default, 5 retries allowed
        self.connect : int, optional, *See urllib3.Retry
            How many connection-related errors to retry on.
            Default, None
        self.read : int, optional, *See urllib3.Retry
            How many times to retry on read errors.
            Default, None
        self.max_redirects : int, optional, *See urllib3.Retry
            How many redirects to perform. Limit this to avoid infinite redirect
            loops.
            Default, set to allow 10 redirects as is standard 
        self.status : int, optional, *See urllib3.Retry
            How many times to retry on bad status codes.
            Default, None
        self.other : int, optional, *See urllib3.Retry
            How many times to retry on other errors. Other errors are errors 
            that are not connect, read, redirect or status errors.
            Default, None
           
        self.allowed_methods : iterable , optional, *See urllib3.Retry
            Set of uppercased HTTP method verbs that we should retry on.
            By default, we only retry on methods which are considered to be
            idempotent (multiple requests with the same parameters end with the
            same state). See :attr:'Retry.DEFAULT_ALLOWED_METHODS'.
            Default, urllib3.util.retry._Default    
           
        self.status_forcelist : iterable , optional, *See urllib3.Retry
            A set of integer HTTP status codes that we should force a retry on.
            A retry is initiated if the request method is in ''allowed_methods''
            and the response status code is in ''status_forcelist''.
            Default, list of all status codes of 408 and above    
           
        self.backoff_factor : float, optional, *See urllib3.Retry
            A backoff factor (delay) to apply between attempts after the second try
            (most errors are resolved immediately by a second try without a
            delay). ex. urllib3 will sleep for:
                {backoff factor} * (2 ** ({number of total retries} - 1)) seconds.
                If the backoff_factor is 0.1, then :func:'.sleep' will sleep
                for [0.0s, 0.2s, 0.4s, ...] between retries. 
            Default, 0 or disabled
        self.raise_on_redirect : bool, optional, *See urllib3.Retry
            Whether, if the number of redirects is
            exhausted, to raise a MaxRetryError, or to return a response with a
            response code in the 3xx range.
            Default, True
        self.raise_on_status : bool, optional, *See urllib3.Retry
            Similar meaning to ''raise_on_redirect'':
                whether to should raise an exception, or return a response,
                if status falls in ''status_forcelist'' range and retries have
                been exhausted.
            Default, True
        self.history : tuple, optional, *See urllib3.Retry
            The history of the request encountered during each call to :
            meth:'~Retry.increment'. The list is in the order the requests 
            occurred. Each list item is of class :class:'RequestHistory'.
            Default, None
            
        self.respect_retry_after_header : bool, optional, *See urllib3.Retry
            Whether to respect Retry-After header on status codes defined 
            as: attr:'Retry.RETRY_AFTER_STATUS_CODES' or not.
            Default, True
        self.remove_headers_on_redirect : iterable , optional, *See urllib3.Retry
            Sequence of headers to remove from the request when a response
            indicating a redirect is returned before firing off the redirected
            request.
            Default, frozenset(["Authorization"])
        """
        self._Retry = requests.adapters.Retry(
                                        total = self.max_retries,
                                        connect = self.connect,
                                        read =  self.read,
                                        redirect = self.max_redirects,
                                        status = self.status,
                                        other = self.other,
                                        allowed_methods = self.allowed_methods,
                                        status_forcelist = self.status_forcelist,
                                        backoff_factor = self.backoff_factor,
                                        raise_on_redirect = self.raise_on_redirect,
                                        raise_on_status = self.raise_on_status,
                                        history = self.history,
                                        respect_retry_after_header = \
                                            self.respect_retry_after_header,
                                        remove_headers_on_redirect = \
                                            self.remove_headers_on_redirect,
                                        #method_whitelist = self.method_whitelist
                                        )
    #--------------------------------------------------------------------------                                        
    def _set_http_adapter(self):
        '''
        Method creates a default HTTP adapter to mount on a request session
        using custom properties from the defined sessionWrapper object 
        attributes. Creating the adapter allows full control of the session 
        HTTP properties.          
        
        *See requests.adapters.HTTPAdapter source for source documentation
        
        The HTTPAdapter provides a general-case interface for requests 
        sessions to contact HTTP and HTTPS urls by implementing the 
        Transport Adapter interface. This class will usually be created 
        by the :class:'Session <Session>' class under the
        covers. 
        
        Attributes/Parameters
        ----------    
        self._Retry : urllib3.Retry, optional, *requests.adapters.HTTPAdapter
            urllib3.Retry derived from sessionWrapper object attributes
            for granular control over the conditions under which a request is
            retried.  The retry object sets the maximum number of retries each 
            connection should attempt. Note, this applies only to failed DNS 
            lookups, socket connections and connection timeouts, never to 
            requests where data has made it to the server. The Retry
            object also handles redirect parameters for a session. 
            Default, 5 retries(self.max_retries), 10 redirects (self.max_redirects)      
        self.pool_connections : int, optional, *requests.adapters.HTTPAdapter
            The number of urllib3 connection pools to cache.
            Default, 10 set by requests.adapters.DEFAULT_POOLSIZE
        self.pool_maxsize : int, optional, *requests.adapters.HTTPAdapter
            The maximum number of connections to save in the pool.
            Default, 10 set by requests.adapters.DEFAULT_POOLSIZE 
        self.pool_block : bool, optional, *requests.adapters.HTTPAdapter
            Whether the connection pool should block for connections.
            Default, False set by requests.adapters.DEFAULT_POOLBLOCK
        '''     
        self._set_retry()
        
        self._HTTPAdapter = requests.adapters.HTTPAdapter(
                                        max_retries = self._Retry,
                                        pool_connections = self.pool_connections,
                                        pool_maxsize = self.pool_maxsize,
                                        pool_block = self.pool_block
                                                          )
    #--------------------------------------------------------------------------        
    def _set_pkcs12_adapter(self):
        '''
        
        Method creates a Pkcs12 adapter to mount on a request session
        using custom properties from the defined sessionWrapper object 
        attributes. Creating the adapter allows full control of the session 
        Pkcs12Adapter properties.  
        
        *See requests_pkcs12.Pkcs12Adapter for complete documentation
        
        PKCS#12 adapters add support to the Python requests library
        without monkey patching or temporary files. Instead, it is 
        integrated into requests as recommended by its authors to 
        create a custom TransportAdapter, which provides a custom 
        SSLContext.

        Attributes/Parameters
        ----------        
        self.pkcs12_filename : str , *required, *See requests_pkcs12.Pkcs12Adapter
            Path to a file containing a byte string or unicode string that
            contains the file name of the encrypted PKCS#12 certificate. 
            Either this argument or pkcs12_data must be provided.
            Default, None
        self.pkcs12_data : str , *required, *See requests_pkcs12.Pkcs12Adapter
            A byte string that contains the encrypted PKCS#12 certificate 
            data. Either this argument or pkcs12_filename must be provided.
            Default, None
        self.pkcs12_password : str , *required, *See requests_pkcs12.Pkcs12Adapter
            A byte string or unicode string that contains
            the password. This argument must be provided whenever pkcs12_filename 
            or pkcs12_data is provided.
            Default, None
        self.ssl_protocol : _SSLMethod , optional, *See requests_pkcs12.Pkcs12Adapter
            A protocol version from the ssl library.
            Default, requests_pkcs12.default_ssl_protocol   
        '''     
        self._Pkcs12Adapter = requests_pkcs12.Pkcs12Adapter(
                                        pkcs12_data = self.pkcs12_data,
                                        pkcs12_filename = self.pkcs12_filename,
                                        pkcs12_password = self.pkcs12_password,
                                        ssl_protocol = self.ssl_protocol
                                                            )
    #--------------------------------------------------------------------------
    def _set_session(self, url=None):
        '''
        Method updates the default requests session 
        (self.default_session) using http and/or pkcs12 
        adapters using custom properties defined in the 
        sessionWrapper object attributes.
        
        *See requests.Session for complete documentation
        
        requests.Session objects persist cookies, connection-pooling, 
        request configurations and other parameters across requests 
        using connection pooling. A a primary benefit, when 
        multiple requests are made to the same API, the connection 
        can be reused for more performant request response cycles.  

        Attributes/Parameters
        --------------------- 
        url : str, optional
            Uniform Resource Locator (URL) string of characters which 
            identifies a name or a resource on the internet
        ---------------------    
        self.headers : dict, optional, *requests.Session
            Dictionary of HTTP Headers to send with a request.
            Default, requests.utils.default_headers()
        self.cookies : RequestsCookieJar, optional, *requests.Session
            Dictionary or CookieJar object to send with a request.
            Default, requests.cookies.cookiejar_from_dict({})
        self.auth: tuple, optional, *requests.Session
            Auth tuple or callable to enable Basic/Digest/Custom 
            HTTP Auth.
            Default, None
        self.proxies : dict, optional,  *requests.Session
            Dictionary mapping protocol or protocol and hostname 
            to the URL of the proxy.
            Default, {}
        self.hooks : dict, optional,  *requests.Session
            Dictionary of hooks can be used to alter the request 
            process and/or call custom event handling
            Default, requests.hooks.default_hooks()
        self.params : dict, optional,  *requests.Session
            Dictionary or bytes to be sent in the query string for
            a request.
            Default, requests.hooks.default_hooks()
        self.verify : bool, optional,  *requests.Session
            Either a Boolean, in which case it controls whether to 
            verify the server's TLS certificate, or a string, in 
            which case it must be a path to a CA bundle to use. 
            Defaults to 'True'. When set to 'False', requests will 
            accept any TLS certificate presented by the server, and 
            will ignore hostname mismatches and/or expired certificates,
            which will make your application vulnerable to 
            man-in-the-middle (MitM) attacks. Setting verify to 'False' 
            may be useful during local development or testing.
            Default, True
        self.cert :  str or tuple, optional, *requests.Session
            Either a string path to ssl client cert file (.pem) or
            a tuple of('cert', 'key') pair.
            Default, None
        self.stream : bool, optional, *requests.Session
            Option to immediately download the response content.
            Default, False
        self.max_redirects : int, optional, *See urllib3.Retry
            How many redirects to perform. Limit this to avoid infinite 
            redirect loops.
            Default, set to self.max_redirects default of 10      
        '''        
        # parse the base url from the url
        if url:
            url_base = self._get_base_url(url)
        
        # create a general request session
        self._Session = requests.Session()
        
        # set the session attributes based on the class attributes
        self._Session.headers = self.headers
        self._Session.cookies = self.cookies
        self._Session.auth = self.auth
        self._Session.proxies = self.proxies
        self._Session.hooks = self.hooks
        self._Session.params = self.params
        self._Session.verify = self.verify
        self._Session.cert = self.cert
        self._Session.stream = self.stream
        self._Session.trust_env = self.trust_env
        self._Session.max_redirects = self.max_redirects        
        
        # set/update the _HTTPAdapter
        self._set_http_adapter()
        
        if url: 
            self._Session.mount(url_base, self._HTTPAdapter)       
        
        # if p12/PFX data is supplied, create a pkcs12 adapter        
        if (self.pkcs12_data or self.pkcs12_filename) and self.pkcs12_password:
            self._Pkcs12Adapter = self._set_pkcs12_adapter()
            # mount the pkcs12 adapter
            self._Session.mount(url_base, self._Pkcs12Adapter)
    #--------------------------------------------------------------------------
    def _thread_safe_session(self):
        """
        Method returns a thread safe request session. 
        Ambiguity exists around request sessions being 
        thread safe. The returned session/data should 
        be thread specific.
        
        Attributes/Parameters
        --------------------- 
        self._Session : request.Session, Required
            An initialized request session object
        """
        if not hasattr(THREAD_LOCAL,'session'):
            THREAD_LOCAL.session = self._Session
        return THREAD_LOCAL.session
    #--------------------------------------------------------------------------
    def get(self, url, timeout=None, verify=None, reset_session=False):
        '''
        Method preforms a get request using a thread safe 
        request wrapper session. The request wrapper session 
        object wraps standard request session, retry, and 
        get parameters with .p12/PFX support when credentials 
        are supplied. 
        
        Parameters
        --------------------- 
        url : str, required
            Uniform Resource Locator (URL) string of characters which 
            identifies a name or a resource on the internet  
        timeout : int or tuple, optional, *requests.get
            Details how long (sec) to wait for a client connection 
            and how long (sec) to wait for a read response.
            Default, , self.timeout=(30,180)
        verify : bool or str, optional,  *requests.get
            Either a Boolean, in which case it controls whether to 
            verify the server's TLS certificate, or a string, in 
            which case it must be a path to a CA bundle to use. 
            Defaults to 'True'. When set to 'False', requests will 
            accept any TLS certificate presented by the server, and 
            will ignore hostname mismatches and/or expired certificates,
            which will make your application vulnerable to 
            man-in-the-middle (MitM) attacks. Setting verify to 'False' 
            may be useful during local development or testing.
            Default, self.verify=True)
        reset_session : bool, optional, 
            Option to reset/re-create a the request.session object
            Default, False
        '''            
        
        # if no timeout set, use default (30sec connect and 180sec read)
        if timeout is None:
            timeout = self.timeout
        
        # if no verify set, use default (True)        
        if verify is None:
            verify = self.verify
        # disable insecure request warnings when verify = false
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 
        
        if not isinstance(self._Session, requests.Session) or reset_session:
            # initialize a session if none or reset the session
            self._set_session(url)
            
        elif not self._get_base_url(url) in \
            list(self._Session.__dict__['adapters'].keys()):
            # mount the new url to the session
            self._Session.mount(self._get_base_url(url), self._HTTPAdapter)
        
        # get a thread safe session object
        s = self._thread_safe_session()
        # get the response object        
        resp = s.get(
                     url,
                     timeout=timeout,
                     verify=verify
                     )           
        return resp         
#------------------------------------------------------------------------------  
# ESRI REST class with specific methods
#------------------------------------------------------------------------------ 
class esriRestApi(object):
    """
    Return ESRI Service metadata. 

    This function performs a request against an ESRI
    REST API to return feature specific metadata 
    pertaining to the service endpoint. If meta_props 
    is not specified, all metadata will be returned 
    in its original form.
    """
    def __init__(self, **kwargs):
        #----------------------------------------------------------------------       
        # Set default attributes
        #----------------------------------------------------------------------

        #----------------------------------------------------------------------
        # allow the object to be initialized with kwargs
        self.__dict__.update(kwargs)    
    #-------------------------------------------------------------------------- 
    def get_service_metadata(self, url, meta_props=None, showMessages=False, log=None):
        """
        Return ESRI Service metadata. 

        This function performs a request against an ESRI
        REST API to return feature specific metadata 
        pertaining to the service endpoint. If meta_props 
        is not specified, all metadata will be returned 
        in its original form.
        
        Parameters
        ----------
        url : str, required
            REST API url for the ESRI feature service or table
        meta_props : list, optional
            List of metadata properties to return. 
            Default behavior of None will return all metadata in its original form
        showMessages: Boolean, optional
            Boolean option to print messages;
            Default, no messages will be printed to the console
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log;        
        Returns
        -------
        metadata : dictionary
            A dictionary of key metadata is returned.
            If meta_props is not specified, all 
            metadata will be returned in its original 
            form.

        >>> 
        """
        if not log:
            log=GRALE_LOG
        
        pid     = str(uuid.uuid4())    
        prepedUrl = _prep_url(url, headers={'f': 'JSON'})
        response, status, message = _request_handler(
                                                     prepedUrl, 
                                                     log=log,
                                                     pid=pid
                                                     )
                
        if not status.startswith('Error:'):
            json_resp = response.json()
        else:
            json_resp = {'Error': {'status':status, 'message':message}}
            return json_resp
        metadata = _extract_nested_key_values(
                   json_resp
                   ,meta_props)
        del response
        return metadata
    #--------------------------------------------------------------------------    
    def get_wfs_record_count(self, url, where=None, showMessages=False, log=None):
        """
        Return the total count from an ESRI REST API query . 

        This function returns a total record count returned 
        from a query against an ESRI REST feature service.
        
        Parameters
        ----------
        url : str, required
            REST API query (/query) url for the ESRI Feature Service
        where : str, optional
            String specifying the selection clause to query a subset of data;
            Default behavior ('None') selects all data
        showMessages: Boolean, optional
            Boolean option to print messages;
            Default, no messages will be printed to the console
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log;             
        Returns
        -------
        int : 
            A total record count for a given query against and
            ESRI REST feature service.

        """
        if not log:
            log=GRALE_LOG
            
        headers = {'where': where, 'returnCountOnly': 'true', 'f': 'json'}
        prepedUrl = _prep_url(url, headers=headers)
        pid     = str(uuid.uuid4())
        response, status, message = _request_handler(
                                                     prepedUrl, 
                                                     log=log,
                                                     pid=pid
                                                     )      
        if not status.startswith('Error:'):
            json_resp = response.json()
        else:
            json_resp = {}

        if 'count' in json_resp:
            rec_cnt = json_resp['count']
        else:
            rec_cnt = 0
        return rec_cnt
    #--------------------------------------------------------------------------
    def get_rest_services(self, url, service_types=[], 
                               dirs=[],showMessages=False, log=None):
        """
        Function returns a dictionary of service definitions found on
        a given ESRI REST endpoint.  The function searches for services 
        at the top level directory (services) and also within sub-directories
        (folders). Once located, a dictionary item is created using the 
        service URL as the key and the service definition as the value.  
        
        Parameters
        ----------
        url : str, required
            Top level REST API url for the ESRI REST endpoint;
            Ex. https://some_url.../arcgis/rest
        service_types: list, optional
            List of service types to return;
            Valid list values include: 'MapServer', 'FeatureServer', 'ImageServer', 
                                   'GeocodeServer', 'GPServer', 'GlobeServer', 
                                   'NAServer', 'GeometryServer', 'GeoDataServer', 
                                   'MobileServer';
            ESRI ESRI SDK documentation for updated server types;
            Default behavior of an empty list returns all service types
        dirs: list, optional
            List of directories (folders) to search for services within.  
            Ex. ['services', 'airports'] were 'services' is the top level 
            directory and 'airports' is a sub-folder. 
            Default behavior of an empty list returns all services
        showMessages: Boolean, optional
            Boolean option to print messages;
            Default, no messages will be printed to the console
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log;        
                 
        Returns
        -------
        svc_defs : dictionary 
            Dictionary where the key is the service URL and the service 
            definition is the value
        Example
        -------
        >>> url = r'https://some_url/arcgis/rest'
        >>> service_types = ['MapServer','FeatureServer']
        >>> dirs = ['services', 'airports']

        >>> # get service URL's and service definitions
        >>> sd = grale.esri.get_rest_services(
                                              url=url, 
                                              service_types=service_types, 
                                              log=REQUEST_LOG,
                                              showMessages=False, 
                                              dirs=dirs
                                              )           
        >>> print(sd)                        
        """    
        #--------------------------------------------------------------------------
        if not log:
            log=GRALE_LOG
        pid     = str(uuid.uuid4())    
        svc_defs = {}
        prepedUrl = _prep_url(f"{url}/services", headers={'f':'json'})

        response, status, message = _request_handler(prepedUrl, 
                                                     log=log, 
                                                     showMessages=showMessages,
                                                     pid=pid)
        svcs_root = response.json()
        #--------------------------------------------------------------------------
        # list out all of the paths/dirs containing services
        root_dirs =[]
        if (bool(dirs) and 'services' in dirs) or not bool(dirs): 
            if 'services' in svcs_root.keys():
                if len(svcs_root['services']) > 0:
                    root_dirs.append('services')
        
        if 'folders' in svcs_root.keys():
            if bool(dirs):  
                root_dirs.extend([fldr for fldr in 
                                  svcs_root['folders'] 
                                  if fldr in dirs ])
            else:
                root_dirs.extend([fldr for fldr in svcs_root['folders']])
        #--------------------------------------------------------------------------
        # list out all of the services
        svcs = {}
        for rd in root_dirs:
            pid  = str(uuid.uuid4())
            if rd == 'services':
                prepedUrl = _prep_url(f"{url}/services", headers={'f':'json'})
                response, status, message  = _request_handler(prepedUrl, 
                                                              log=log, 
                                                              showMessages=showMessages,
                                                              pid=pid)            
            else:
                prepedUrl = _prep_url(f"{url}/services/{rd}", headers={'f':'json'})

                response, status, message  = _request_handler(prepedUrl, 
                                                              log=log, 
                                                              showMessages=showMessages,
                                                              pid=pid)              
               
            svcs[f'{rd}'] = response.json()['services']
        #--------------------------------------------------------------------------
        # build a dictionary to store the services by url with the service definitions
        for k,v in svcs.items():
            for s in v:
                if bool(service_types):
                    if s['type'] not in service_types: continue
                svc_url = (f"{url}/services/{s['name']}/{s['type']}")
                
                pid     = str(uuid.uuid4())
                prepedUrl = _prep_url(svc_url, headers={'f':'JSON'}) 
                response, status, message  = _request_handler(url=prepedUrl, 
                                                              log=log, 
                                                              showMessages=showMessages,
                                                              pid=pid) 
                svc_defs[svc_url] = response.json()       
        #--------------------------------------------------------------------------
        return svc_defs
    #--------------------------------------------------------------------------
    def get_rest_data_sources(self, service_defs):
        """
        Function returns a dictionary of data source definitions found 
        within an ESRI REST service.  The function extracts the individual 
        data sources (layers and tables) along with their basic properties/
        definitions. 
        
        Parameters
        ----------
        service_defs : dictionary, required
            Dictionary resulting from the "self.get_rest_services" function, 
            where the key is the service URL and the service definition is 
            the value.

        Returns
        -------
        svc_defs : dictionary 
            Dictionary of data source definitions found within an ESRI REST 
            service, where the keys are the data source URL's and the values 
            are dictionaries containing the basic data source properties.
            
        Example
        -------                  
        >>> # get data source URL's and basic definitions
        >>> ds = grale.esri.get_rest_data_sources(sd)
        >>> print(ds['https://some_url/arcgis/rest/services/airports/MapServer/1'])
        >>> {'id': 1,
             'name': 'Runways',
             'parentLayerId': 0,
             'defaultVisibility': True,
             'subLayerIds': None,
             'minScale': 300000,
             'maxScale': 0,
             'type': 'Feature Layer',
             'geometryType': 'esriGeometryPolygone'}
        """     
        data_sources = {}
        for url, svc_def in service_defs.items():
            if 'layers' in svc_def:
                for lyr in svc_def['layers']:
                    data_sources[f"{url}/{lyr['id']}"] = lyr 
            if 'tables' in svc_def:                
                for tbl in svc_def['tables']:
                    data_sources[f"{url}/{lyr['id']}"] = tbl
        return data_sources
    #--------------------------------------------------------------------------
    def get_rest_data_source_defs(self, data_sources, showMessages=False, log=None):
        """
        Function returns a dictionary of data sources with the full data 
        source definition including metadata and data structures. The input 
        "data_sources" dictionary is a result of the "self.get_rest_data_sources"
        function, where the keys are the data source URL's and the values are the 
        basic properties of the data source.  The output returned is a deep copy of
        the "data_sources" dictionary with an additional nested key/property 
        "source_definition" containing a dictionary containing the full metadata 
        and data structure for the given data source. 
        
        Parameters
        ----------
        data_sources : dictionary, required
            Dictionary resulting from the "self.get_rest_data_sources" function, 
            where the key is the data source URL's and the values are the basic
            properties of the data source.
        showMessages: Boolean, optional
            Boolean option to print messages;
            Default, no messages will be printed to the console
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log;     
                 
        Returns
        -------
        data_src_defs : dictionary 
            Dictionary of data source definitions found within an ESRI ReST 
            service, where the keys are the data source URL's and the values 
            are dictionaries containing the basic data source properties
            with detailed metadata and data structures.
        Example
        -------

        >>> # get the full data source structure and metadata 
        >>> ds_defs = grale.esri.get_rest_data_source_defs(ds,
                                                      log=REQUEST_LOG,
                                                      showMessages=False,        
                                                      )     
        >>> print(ds_defs['https://someServer/rest/services/airports/MapServer/1'])
        >>> {'id': 1,
             'name': 'Runways',
             'parentLayerId': 0,
             'source_definition': 
                 {'currentVersion': 10.81,
                  'id': 9,
                  'name': 'Runways',
                  'type': 'Feature Layer',
                  'fields': [{'name': 'OBJECTID',
                    'type': 'esriFieldTypeOID',
                    'alias': 'OBJECTID',
                    'domain': None}...]
                  ...
                 }
            }             
        """        
        data_src_defs = {k: v for k, v in data_sources.items()}
        for url, ds_def in data_src_defs.items():
            prepedUrl = _prep_url(url, headers={'f':'json'})
            pid     = str(uuid.uuid4())
            response, status, message  = _request_handler(prepedUrl, 
                                                          log=log, 
                                                          showMessages=showMessages,
                                                          pid=pid)
            d = {k: v for k, v in ds_def.items()}
            d['source_definition'] = response.json()                                              
            data_src_defs[url] = d
         
        return data_src_defs
    #--------------------------------------------------------------------------  
    def get_wfs_geojsons(self, url, headers={}, chunk_size=None, log=None, 
                           low_memory=False, max_workers=None):
        """
        Function performs a paginated request to an ESRI REST WFS service 
        and returns the results as a list of geoJSON files or compressed
        geoJson files along with full feature service metadata nested under 
        the 'service_metadata' key.  Function determines the total number
        of records available given the header criteria.  The function then 
        paginates the results based on the lesser of the chnk_size and the 
        service maxRecord limit and appends the results to a list of outputs.  
        When the log parameter is specified, data will also be returned 
        nested under the 'request_logging' key. The geojson format is often 
        not enabled, available, or operational on each ESRI feature service 
        to include those that have M-values. As a result, the function defaults 
        to requesting a standard ESRI JSON format that is post processed into 
        geoJSON via the arcgis2geojson package. To provide the time of request 
        for each process/subprocess, the UTC timestamp for each request will be 
        nested under the 'request_metadata' key as the 'grale_utc'.  
        
        Parameters
        ----------
        url : str, required
            REST API url for the ESRI Feature Service
        headers: dictionary, optional
            Dictionary of request headers;
            See ESRI REST documentation on WFS API requests for all options;
            Default behavior requests all records and fields without additional 
            headers beyond a default output spatial reference (outSR) WKID
            of '4326'/WGS-84.  See ESRI REST API documentation for a full list 
            of allowed request headers.
        chunk_size : int, optional
            Number of records to return per response;
            Default behavior follows the REST API "max record" value
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log; 
        low_memory : bool, optional
            Option to compress each return result with the gzip algorithm
            When set to True, the chunked results are written to gzip files over 
            retaining the data in memory/RAM. When set to False, the geojson data 
            is retained in memory/RAM for speed among smaller datasets;
            Default behavior of False returns a list of uncompressed geojson files        
        max_workers : int, optional
            Default python 3.5: 
                If max_workers is None or not given,
                it will default to the number of processors on the machine,
                multiplied by 5. 
                See https://docs.python.org/3/library/concurrent.futures.html
            Default python 3.8: 
                Default value of max_workers is changed to 
                min(32, os.cpu_count() + 4). This default value preserves at 
                least 5 workers for I/O bound tasks. It utilizes at most 32 CPU 
                cores for CPU bound tasks which release the GIL. And it avoids 
                using very large resources implicitly on many-core machines.
                See https://docs.python.org/3/library/concurrent.futures.html
                              
        Returns 
        -------
        out_geojsons : list 
            out_geojsons:  list of uncompressed or compressed string geojson 
                objects which result from a series of requests against an ESRI 
                REST feature service.     
        Example
        -------
        >>> url="https://website.com/.../ArcGIS/rest/services/Parks/FeatureServer/0"
        >>> results = grale.esri.get_wfs_download(
        >>>                         url, 
                                    headers={'fields' :['STATE', 'CITY'], 
                                             'where':'COUNTRY=US')
        """
        if not log:
            log=GRALE_LOG
            
        # if low memory, default to gzip outputs and set the temp directory
        temp_dir = None
        if low_memory:
            import tempfile
            temp_dir = os.path.join(tempfile.gettempdir(),
                                    _validate_file_name(str(uuid.uuid4()))
                                    )
            os.mkdir(temp_dir)
            
        # store the returned record count
        rtnRecordCnt = 0
        # store the output compression size
        uncompSize  = 0
        compSize    = 0
        #--------------------------------------------------------------------------
        def _wfs_request(queryURL, iheaders):
            """
            Internal function of get_wfs_geojsons performs a requests 
            to an ESRI REST WFS service and appends the resulting geojson 
            data to a list named 'out_geojsons'.  
            
            Parameters
            ----------
            queryURL : str, required
                REST API url for the ESRI Feature Service
            iheaders: dictionary, required
                Dictionary of request headers;
                See ESRI REST documentation on WFS API requests for all options;
                Default behavior requests all records without parameters
                     
            Returns
            -------
            iheaders : dictionary 
                iheaders:  Modified dictionary of request headers;    
            """        
            nonlocal rtnRecordCnt
            nonlocal uncompSize
            nonlocal compSize
            nonlocal out_geojsons
            
            
            remaining = total_records - iheaders["resultOffset"]
            if remaining < chunk_size:
                iheaders["resultRecordCount"] = remaining
            else:
                iheaders["resultRecordCount"] = chunk_size
            # get features/records 
            prepedUrl = _prep_url(queryURL, headers=iheaders)
            pid     = str(uuid.uuid4())
            response, status, message = _request_handler(
                                                         url=prepedUrl, 
                                                         log=log, 
                                                         showMessages=True,
                                                         pid=pid
                                                         )
            
            # check for errors and return empty json with errors
            if not status.startswith('Error:'):
                if iheaders['f']  == 'JSON':
                    # convert ESRI JSON records to a dictionary/sudo geojson 
                    geoJsonDict = arcgis2geojson(response.json())
                elif iheaders['f']  == 'geoJSON':
                    geoJsonDict = response.json()
            else:
                geoJsonDict = {'type':'FeatureCollection'}

            # tag the request_metadata with the grale_uuid
            ld = log.log[pid]
            metadata['ppid']= ld['ppid']

            # add the request logging to the geojson feature
            geoJsonDict['request_logging']  = [ld]
     
            # embed WFS metadata within the geojson object        
            geoJsonDict['request_metadata']  = [metadata] 


            # add a record level request timestamp attribute      
            if 'features' in geoJsonDict:
                for f in geoJsonDict['features']:
                    f['properties']['grale_utc'] = ld['utc_timestamp']
                    f['properties']['grale_uuid'] = ld['grale_uuid']
                    
            else:
                 geoJsonDict['features'] = []

            gj = json.dumps(geoJsonDict)
            
            # if low memory, write the files to temp files and return the paths
            if temp_dir:
                tf = _write_geojson_files(geojsons=[gj], 
                                          out_dir=temp_dir, 
                                          low_memory=True)[0]
                uncompSize += sys.getsizeof(gj)
                compSize += os.path.getsize(tf)
                out_geojsons.append(tf)
            else:
                # append the results to the output list
                out_geojsons.append(gj)
            
            # add the number of features to rtnRecordCnt
            rtnRecordCnt +=  len(geoJsonDict['features'])
            
            # clean up
            del(geoJsonDict, gj, response)
            
            # return the headers
            #return iheaders
        #--------------------------------------------------------------------------
        def _threaded_wfs_requests(gen_reqests, max_workers=None):

            """
            Internal function of get_wfs_geojsons that enables
            multi-threading of requests against an ESRI REST WFS service,
            using the internal '_wfs_request' function. 

            Parameters
            ----------
            max_workers : int, optional
                Default python 3.5: 
                    If max_workers is None or not given,
                    it will default to the number of processors on the machine,
                    multiplied by 5. 
                    See https://docs.python.org/3/library/concurrent.futures.html
                Default python 3.8: 
                    Default value of max_workers is changed to 
                    min(32, os.cpu_count() + 4). This default value preserves at 
                    least 5 workers for I/O bound tasks. It utilizes at most 32 CPU 
                    cores for CPU bound tasks which release the GIL. And it avoids 
                    using very large resources implicitly on many-core machines.
                    See https://docs.python.org/3/library/concurrent.futures.html
            Returns
            -------
            iheaders : dictionary 
                iheaders:  Modified dictionary of request headers;    
            """              
            
            threads= []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for r in gen_reqests:
                    threads.append(executor.submit(_wfs_request, r[0], r[1]))
                    
        #-------------------------------------------------------------------------- 
        _print('-'*79)       
        # default behavior matches all features
        if 'where' in headers.keys():
            if headers['where'] is None:
                headers['where'] = '1=1'
        else:
            headers['where'] = '1=1'
            
        if 'outFields' in headers.keys():
            if headers['outFields'] is None:
                headers['outFields'] = '*'
            else:
                headers['outFields'] = ', '.join(headers['outFields'])
        else:
            headers['outFields'] = '*'      

        # build base query URL
        queryURL = '{0}/query'.format(url)
        
        # gather the service metadata values into a dictionary
        metadata = self.get_service_metadata(url, log=log)               

        if 'Error' in metadata.keys():
            _print(f'Invalid URL: {url} See status in log for more info!')
            return []
            
        headers['f'] = 'JSON'
        # ensure the requested type is supported
        if headers['f'] not in [f.strip() for f in 
                   (metadata['supportedQueryFormats']).split(',')]:

            _print(f'{headers["f"]} is not supported on WFS service!')
            _print('Supported formats include: ' +\
                             f'\t-{metadata["supportedQueryFormats"]}' +\
                             f'\t-{headers["f"]} was requested')

        #get the total record count  
        total_records = self.get_wfs_record_count(
                                                url=queryURL, 
                                                where=headers['where'], 
                                                log=log)

        # Check the total record limit
        if 'limit' in headers:
            if headers['limit'] is not None:
                total_records = headers['limit']
            
        # params for record offset/starting point
        if 'resultOffset' in headers:
            if headers['resultOffset'] is None:        
                headers['resultOffset'] = 0
        else:
            headers['resultOffset'] = 0
        result_offset = headers['resultOffset']
        
        if 'Error' not in metadata:
            #set the max chunk size
            if not chunk_size:
                chunk_size = metadata["maxRecordCount"]
            else:
                chunk_size = min([chunk_size, metadata["maxRecordCount"]])    
        
            # params for feature/record request(s)
            if 'outSR' in headers:
                if headers['outSR'] is None:        
                    headers['outSR'] = metadata["wkid"]
            else:
                 headers['outSR'] = '4326'
        
        if total_records > 0: 
           
            if result_offset > total_records:
                _print(f'Warning: resultOffset({result_offset}) is ',
                    f'greater than available records({total_records})\n',
                    'Please see logging for more information')
                return [], metadata
            else:
                request_size = total_records - result_offset
                # determine the number of calls required
                n_calls = int((request_size) / chunk_size) + \
                             ((request_size) % chunk_size > 0)
                _print(f'Pull will require {n_calls} request(s)')
        else:
            _print('No records returned...See log for more information')
            return [], metadata
        
        out_geojsons = []
        _print('Requesting: {0} out of {1} total features'.format(
                                                                 request_size,
                                                                 total_records
                                                                 ))
        _print(f'Chunk size set at: {chunk_size} features:\n')
        
        gen_reqests = []
        
        while result_offset < total_records:
            iheaders = {k: v for k, v in headers.items()}
            iheaders['resultOffset'] = result_offset
            gen_reqests.append((queryURL, iheaders))
            
            # add the number of features to the result offset
            result_offset += chunk_size

        _threaded_wfs_requests(gen_reqests, max_workers=max_workers)
            
     
        _print(f'Returned: {rtnRecordCnt} of {request_size} requested features')
        if low_memory:
            _print('Compressed results using gzip from' + \
                  f'{_bytes_unit_conversion(uncompSize)} to ' + \
                  f'{_bytes_unit_conversion(compSize)}')
        _print('-'*79)    
        return out_geojsons
    #--------------------------------------------------------------------------
    def get_wfs_download(self, url, out_dir, headers={}, max_workers=None, 
                         chunk_size=None, log=None, low_memory=False, 
                         cleanup=True): 
        """
        Function executes the get_wfs_geojsons function to perform paginated 
        request against an ESRI REST WFS service returning the results as
        chunked geoJSON files or compressed geoJson files which include full 
        feature service metadata nested under the 'service_metadata' key.  
        Logging data will also be returned nested under the 'request_logging' key. 
        To provide the time of request for each process/subprocess, the UTC 
        timestamp for each request will be nested under the 'request_metadata' 
        key as the 'grale_utc'.  
        
        Parameters
        ----------
        url : str, required
            REST API url for the ESRI Feature Service
        out_dir : str, required
            Output location/directory for files to be written        
        headers: dictionary, optional
            Dictionary of request headers;
            See ESRI REST documentation on WFS API requests for all options;
            Default behavior requests all records and fields without additional 
            headers beyond a default output spatial reference (outSR) WKID
            of '4326'/WGS-84.  See ESRI REST API documentation for a full list 
            of allowed request headers.
        max_workers : int, optional
            Default python 3.5: 
                If max_workers is None or not given,
                it will default to the number of processors on the machine,
                multiplied by 5. 
                See https://docs.python.org/3/library/concurrent.futures.html
            Default python 3.8: 
                Default value of max_workers is changed to 
                min(32, os.cpu_count() + 4). This default value preserves at 
                least 5 workers for I/O bound tasks. It utilizes at most 32 CPU 
                cores for CPU bound tasks which release the GIL. And it avoids 
                using very large resources implicitly on many-core machines.
                See https://docs.python.org/3/library/concurrent.futures.html        
        chunk_size : int, optional
            Number of records to return per response;
            Default behavior follows the REST API "max record" value
        log : object, optional
            grale request logging object (processLog class).
            If unspecified logging results will persist in grale.GRALE_LOG.log;       
        low_memory : bool, optional
            Option to compress each return result with the gzip algorithm;
            Default behavior of False returns a list of uncompressed geojson files        
        cleanup : bool, optional
            Option to clean up temporary files used during compression/low 
            memory mode;
            Default behavior removes the temporary directory and files     

        Returns
        -------
        out_geojsons : list 
            out_geojsons:  list of uncompressed or compressed string objects 
                            representing geojson which result from a series of 
                            requests against an ESRI WFS REST feature service.     
        Example
        -------
        >>> url = "https://website.com/.../ArcGIS/rest/services/Parks/FeatureServer/0"
        >>> out_dir = 'C:\\Users\\userName\\Downloads\\airfield_data'
        >>> results = grale.esri.get_wfs_download(
        >>>                         url, 
                                    out_dir,
                                    headers={'fields' :['STATE', 'CITY'], 
                                             'where':'COUNTRY=US'},
                                    low_memory=True
                                    )
        """
        if not log:
            log=GRALE_LOG
            
        if not os.path.isdir(out_dir):
            _print('Error: Output directory does not exist')
            return {'Error: Output directory does not exist'}
            
        results = self.get_wfs_geojsons(url=url, 
                                    headers=headers, 
                                    log=log, max_workers=max_workers, 
                                    chunk_size=chunk_size,
                                    low_memory=low_memory)
                                    
        file_paths = _write_geojson_files(results, 
                                          out_dir, 
                                          low_memory=low_memory)
        
        # clean up temp file directory
        if len(results) > 2 and cleanup:
            p_dir = os.path.abspath(os.path.join(results[0], os.pardir))
            if os.path.isdir(p_dir):
                try:
                    rmtree(p_dir)
                except:
                    _print('Could not clean up temp file directory!')
        return file_paths
#------------------------------------------------------------------------------  
#------------------------------------------------------------------------------
# global vars
THREAD_LOCAL    = threading.local()
MESSAGE_LOCK    = threading.Lock()
GRALE_SESSION   = sessionWrapper()
GRALE_LOG       = graleReqestLog()
#------------------------------------------------------------------------------     
