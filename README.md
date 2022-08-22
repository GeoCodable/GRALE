# GRALE - Geospatial Request And Log Extraction
## Description:
  The GRALE module contains functions and classes to standardize requests sent to geospatial REST API's. Response data, metadata capture, and logging information are also standardized to create efficiencies as a preliminary step in ETL workflows that involve geospatial REST API's.  Advanced options are available to optimize speed and memory usage in the extraction phase of ETL workflows. Options include multi-threaded request/response cycles, 'low memory' options in an effort to reduce memory usage/errors and storage capacity required for outputs, in addition to .p12/PFX (pkcs12) support.  Output GeoJSON objects contain two additional keys named 'request_metadata' and 'request_logging'.  These additional keys extend the GeoJSON structure to provide logging information and metadata that can increase efficiencies when used as part of a larger extract, transform, and load (ETL) workflow.

  ***Note: Capabilities are limited to get requests on ArcGIS REST API feature and map services at this time.*** 
  
## Quick Start Examples:

  ### Import:  
    In [1]:import grale
  ### Basic Data Requests:  
    
  ### Download GeoJson files to a directory:
  ***Perform a paginated, multi-threaded request for all features/records, return a list of output files***
  
    In [2]:url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    In [3]:out_dir = r'D:\downloads'
    In [4]:files = grale.esri.get_wfs_download(url=url, out_dir=out_dir)
    
  ### Get a list of GeoJSON objects:
  ***Perform a paginated, multi-threaded request for all features/records, return a list of output GeoJSON objects***
  
    In [5]:url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    In [6]:geojsons = grale.esri.get_wfs_geojsons(url=url)
    
  ### View request log data:
    In [7]:grale.GRALE_LOG.log
    
## Advanced Usage:

### Feature Data Requests:
  #### Return a list of json objects or when low_memory=True, compressed (gzip) temp file paths.

    In [1]: log = grale.GraleReqestLog()  #initiate a new request log object (optional)
    In [2]: url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    In [3]: headers = {
                      'outSR':4326,           # set the ouptut spatial reference to WGS-84
                      'resultOffset': 7000,   # skip over requesting the first 6999 records
                      }
    In [4]: geojsons = grale.esri.get_wfs_geojsons( url=url,            # request url, required
                                                    headers=headers,    # request query parameters, optional
                                                    log=log,            # GraleReqestLog logging object, optional
                                                    chunk_size=750,     # max chunk size/ record count per pull, optional
                                                    max_workers=4,      # max number threads to run in parallel, optional
                                                    low_memory=False)   # False, return a list of GeoJSON objects, optional
                                                
  #### Download the GeoJSON to geojson files or when low_memory=True, compressed (gzip) files returning a list of file paths.
    In [1]: url = r'https://someServer/arcgis/rest/services/transportation/MapServer/2'
    In [2]: headers = {
                        'outSR':4326,           # set the ouptut spatial reference to WGS-84
                       }
    In [3]: out_dir = r'D:\downloads'
    In [4]: files = grale.esri.get_wfs_download(  url=url,            # request url, required
                                                  out_dir=out_dir,    # select an ouptput directory, required   
                                                  headers=headers,    # request query parameters, optional
                                                  log=None,           # default to grale.GRALE_LOG.log, optional
                                                  chunk_size=None,    # default to service max allowed request size, optional
                                                  max_workers=None,   # default (Python 3.5+) # of processors on the machine X by 5, optional
                                                  low_memory=False,   # True, output compressed GEOJSON files, optional
                                                  cleanup=True)       # True, clean up low memory temp files 
    In [5]: grale.GRALE_LOG.log   # view the request/result log
    
### Logging:
  The GRALE module uses a logging object to retain request-response cycle information for use in ETL processes.  The logging object retains request information     including parameters/headers, process ID's, and  UTC date-timestamps.  Response metrics include response status, size, and elapsed time. The proces ID serves as the primary key in the logging object and is the unique key that identifies a specific request iteration attempt.  The "ppid" is a "parent process" unique identifier  to which a sub-series of chunked request attempts belong to.  By default, output GeoJSON objects also contain an additional key named 'request_logging'.  This key stores the same logging data, but only for the specific request that returned the GeoJSON results.
  
  For examples, see :  [Log Structure](#log-structure) & [Viewing the GRALE request log](#viewing-the-grale-request-log)
#### Log Structure:
                 {
                  'processId': 'unique process ID for the request iteration (per chunk)',
                      {
                      'grale_uuid':     'GRALE full ID, concat of the of the ppid  & pid'
                      'ppid':           'unique parent process ID for an iterated request(per data source)', 
                      'pid':            'unique process ID for the request iteration (per chunk)', 
                      'utc_timestamp':  'UTC start timestamp of a request instance', 
                      'parameters':     'parameters sent to a request instance',   
                      'status':         'status category for a request instance','  
                      'results':        ['list of detailed response messages/results'],
                      'elapsed_time':   'elapsed time to complete the request instance',
                      'size':           'size of return object/data'
                      }
                  }
                
  #### Viewing the GRALE request log:
      In [4]: grale.GRALE_LOG.log
      >>> {
          '03db2910-8f19-46a9-8bcc-483968b2d6f1',
            {	
              'grale_uuid': '690594ca-d724-409e-a4e9-10ddd450b5a2_03db2910-8f19-46a9-8bcc-483968b2d6f1',
              'ppid': '690594ca-d724-409e-a4e9-10ddd450b5a2',
              'pid' : '03db2910-8f19-46a9-8bcc-483968b2d6f1',
              'utc_timestamp': '2022-08-03T18:51:22.408314',
              'request': 'https://someServer/arcgis/rest/services/transportation/MapServer/1/query?where=...',
              'parameters': {'base_url': ['https://someServer/arcgis/rest/services/transportation/MapServer/1/query'],
                      'f': ['JSON'],
                      'outFields': ['*'],
                      'outSR': ['4326'],
                      'resultOffset': ['17000'],
                      'resultRecordCount': ['1000'],
                      'where': ['1=1']},
              'status': 'Success',
              'results': ['Size: 533583(B),Time :1.061342(s)'],
              'elapsed_time': '1061.342(ms)',
              'size': '533583(B)',
            },
          '6fa266fa-2f95-40f4-adac-b0a9798a6af0',
            {	          
              'grale_uuid': '690594ca-d724-409e-a4e9-10ddd450b5a2_6fa266fa-2f95-40f4-adac-b0a9798a6af0',
              'ppid': '690594ca-d724-409e-a4e9-10ddd450b5a2',
              'pid' : '6fa266fa-2f95-40f4-adac-b0a9798a6af0',
              'utc_timestamp': '2022-08-03T18:51:22.408314',
              'request': 'https://someServer/arcgis/rest/services/transportation/MapServer/1/query?where=...',
              'parameters': {'base_url': ['https://someServer/arcgis/rest/services/transportation/MapServer/1/query'],
                      'f': ['JSON'],
                      'outFields': ['*'],
                      'outSR': ['4326'],
                      'resultOffset': ['18000'],
                      'resultRecordCount': ['1000'],
                      'where': ['1=1']},
              'status': 'Error: (Unidentified)',
              'results': 'ResponseText:{"error":{"code":500,"message":"json","details":[]}}',
              'elapsed_time': '1061.342(ms)',
              'size': '52(B)',
            }, ...
          }
