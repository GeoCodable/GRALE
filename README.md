# GRALE - Geospatial Request And Log Extraction
## Main Sections:
  * [Description](#description)
  * [Quick Start](#quick-start)
  * [Logging and data lineage](#logging-and-data-lineage)
  * [Custom requests sessions](#custom-requests-sessions)
  * [Profiling ArcGIS REST API's](#profiling-arcgis-rest-apis)
  * [Other grale.esri methods](#other-graleesri-methods)


## Description:
  The GRALE module contains functions and classes to standardize requests sent to geospatial REST API's. Response data, metadata capture, and logging information are also standardized to create efficiencies as a preliminary step in ETL workflows that involve geospatial REST API's.  Advanced options are available to optimize speed and memory usage in the extraction phase of ETL workflows. Options include multi-threaded request/response cycles, 'low memory' options in an effort to reduce memory usage/errors and storage capacity required for outputs, in addition to .p12/PFX (pkcs12) support.  Output GeoJSON objects contain two additional keys named 'request_metadata' and 'request_logging'.  These additional keys extend the GeoJSON structure to provide logging information and metadata that can increase efficiencies when used as part of a larger extract, transform, and load (ETL) workflow.

  ***Note: Capabilities are limited to get requests on ArcGIS REST API feature and map services at this time.*** 

## Quick Start

### Import:
  
  ```python
    import grale
  ```
  
### Simple Feature Requests:
    
  #### Download GeoJSON files to a directory:
  
  _Perform a paginated, multi-threaded request for all features/records, return a list of output files_

  ```python
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    out_dir = r'D:\downloads'
    files = grale.esri.get_wfs_download(url=url, out_dir=out_dir)
  ```
  
  #### Get a list of GeoJSON objects:
  
  _Perform a paginated, multi-threaded request for all features/records, return a list of output GeoJSON objects_

  ```python
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    geojsons = grale.esri.get_wfs_geojsons(url=url)
  ```
  
  #### View request log data:
  
  ```python
    grale.GRALE_LOG.log
  ```
    
### Advanced Feature Requests:

  #### Download GeoJSON files to a directory:
  
   * Conserve memory and compress (gzip) results by using low_memory=True
   * Set the max records size to 500 for each request/output file
  
  ```python
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/2'
    headers = {
               'outSR':4326,           # set the output spatial reference to WGS-84
              }
    out_dir = r'D:\downloads'
    files = grale.esri.get_wfs_download( url=url,            # request url, required
                                         out_dir=out_dir,    # select an output directory, required   
                                         headers=headers,    # request query parameters, optional
                                         log=None,           # default to grale.GRALE_LOG.log, optional
                                         chunk_size=500,     # max of request 500 records or the API max request size, optional
                                         max_workers=None,   # default (Python 3.5+) # of processors on the machine X by 5, optional
                                         low_memory=False,   # True, output compressed GEOJSON files, optional
                                         cleanup=True)       # True, clean up low memory temp files 
    grale.GRALE_LOG.log   # view the request/result log
    gdf = grale.geojsons_to_df( files,                       # create a single geopandas dataframe from the list of GeoJSON files
                                df_type='GeoDataFrame') 
  ```
  
   #### Get a list of GeoJSON objects:
   
   * Set the max records size to 750 for each request/output file
   * Allow up to 4 threads.

  ```python
    log = grale.GraleReqestLog()  #initiate a new request log object (optional)
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    headers = {
               'outSR':4326,           # set the output spatial reference to WGS-84
               'resultOffset': 7000,   # skip over requesting the first 6999 records
                      }
    geojsons = grale.esri.get_wfs_geojsons( url=url,            # request url, required
                                            headers=headers,    # request query parameters, optional
                                            log=log,            # GraleReqestLog logging object, optional
                                            chunk_size=750,     # max chunk size/ record count per pull, optional
                                            max_workers=4,      # max number threads to run in parallel, optional
                                            low_memory=False)   # False, return a list of GeoJSON objects, optional
    df = grale.geojsons_to_df( geojsons,                        # create a single pandas dataframe from the list of GeoJSONs
                               df_type='DataFrame')     
  ```
    
## Logging and data lineage:
  The GRALE module uses a logging object to retain request-response cycle information for use in ETL processes.  The logging object retains request information     including parameters/headers, process ID's, and  UTC date-timestamps.  Response metrics include response status, size, and elapsed time. The process ID serves as the primary key in the logging object and is the unique key that identifies a specific request iteration attempt.  The "ppid" is a "parent process" unique identifier to which a sub-series of chunked request attempts belong to.  By default, output GeoJSON objects also contain an additional key named 'request_logging'.  This key retains the same logging data, but only for the specific request that returned the GeoJSON results.
  
  For examples, see:  [Log Structure](#log-structure) & [Viewing the GRALE request log](#viewing-the-grale-request-log)
  
### Log Structure:

  ```json
       {
        "processId": 
            {
            "grale_uuid":     "GRALE full ID, concatenation of the of ppid  & pid",
            "ppid":           "unique Parent Process ID for an iterated request(per data source)", 
            "pid":            "unique Process ID for the request iteration (per chunk)", 
            "utc_timestamp":  "UTC start timestamp of a request instance", 
            "parameters":     "parameters sent to a request instance",   
            "status":         "status category for a request instance",  
            "results":        ["list of detailed response messages/results"],
            "elapsed_time":   "elapsed time to complete the request cycle",
            "size":           "size of return object/data"
            }, 
        }
  ```
    
  
  #### Viewing the GRALE request log:
  
  ```python
      grale.GRALE_LOG.log
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
  ```
  
  ### GeoJSON Data lineage:
  GRALE functions which return data to memory or files, employ a modified (RFC 7946) GeoJSON structure consisting of two supplementary top level keys (**_'request_logging'_** & **_'request_metadata'_**).  These supplementary keys provide metadata relevant to geospatial ETL (extract, transform, and load) workflows.  It is important to note that these keys are in addition to the GeoJSON Specification (RFC 7946).  Likewise, two feature level keys are added to all output columns (**_"grale_utc"_** & **_"grale_uuid"_**) to retain the ability to track data lineage. 
    
  * Appended metadata and logging GeoJSON keys are:
     * **_'request_logging'_** which retains a list of logging data associated with the returned data from each request.
      * Can be **_joined_** to feature data records via the **_'grale_uuid'_**
     * **_'request_metadata'_** which contains a list of the full ESRI data source metadata.
      * Can be **_joined_** to feature data records and request_logging via the **_'ppid'_**
      * The ESRI REST Metadata includes, but is NOT limited to
        * columns names, aliases, and data types
        * allowed value known as domains
        * spatial reference information
        * Geometry types (point, line, polygon...)
        * Usage and copyright limits
          
  #### GeoJSON/JSON top level structure:
  
  ```json
    {
      "type": "FeatureCollection",
      "features": [],
      "request_logging": [],
      "request_metadata":[],
    }
  ```

## Custom requests sessions:
  * GRALE_SESSION:
    * The GRALE module offers the 'GRALE_SESSION' object as the default python requests session.   This default object is created at import as an instance of grale.sessionWrapper which serves as a object used to customize parameters of request sessions, retries, and requests_pkcs12. 
  * sessionWrapper:
    * Class constructor builds a wrapper around all standard request session, retry, and get parameters along with .p12/PFX support 
    (when credentials are supplied). All request session, retry, get, and requests_pkcs12 parameters can be set when initializing a sessionWrapper object or by redefining the properties. 
     * Use the python help() function for detailed documentation on all available properties.
       * Example:
         ```python
          help(grale.sessionWrapper)  
         ```

### Examples:
  
  Setting GRALE_SESSION properties using [DataBricks Secrets](https://docs.databricks.com/dev-tools/databricks-utils.html#dbutils-secrets):
  
  ```python
    grale.GRALE_SESSION.timeout = (5,30)
    grale.GRALE_SESSION.pkcs12_filename = dbutils.secrets.get(scope="secrets-scope", key="myCert") 
    grale.GRALE_SESSION.pkcs12_password = dbutils.secrets.get(scope="secrets-scope", key="myPswd") 
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    geojsons = grale.esri.get_wfs_geojsons(url=url)
  ```
  Creating a new custom session:
  
  ```python
    grale.GRALE_SESSION = grale.sessionWrapper(timeout = (120), max_retries=10)
    url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
    geojsons = grale.esri.get_wfs_geojsons(url=url)
  ```

## Profiling ArcGIS REST API's


## Other grale.esri methods:
  Use the python help() function for detailed documentation on each method. 
  
  * Example:
    ```python
    help(grale.merge_geojsons)  
    ```

  * **_merge_geojsons_**
    * merges a list of grale geojson objects into a single output geojson object including the [data lineage](#geojson-data-lineage) keys.   
  * **_read_geojson_**
    * Loads a GeoJSON object or given a file path, a gzip or GeoJSON and returns a python JSON object/dictionary
  * **_read_geojsons_**
    * Loads a list of GeoJSON objects, gzip files, or GeoJSON files and returns a list of python JSON objects/dictionaries
  * **_merge_geojsons_**
    * merges a list of grale geojson objects into a single output geojson object including the ['request_metadata' and 'request_logging'](#geojson-data-lineage) keys.
