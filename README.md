# GRALE - Geospatial Request And Log Extraction
## Description:
  The GRALE module contains functions and classes to standardize requests
  sent to geospatial REST API's. Response data, metadata capture, and 
  logging information are also standardized to create efficiencies as a 
  preliminary step in ETL workflows that involve geospatial REST API's.  
  Advanced options are available to optimize speed and memory 
  usage in the extraction phase of ETL workflows. Options include
  multi-threaded request/response cycles, 'low memory' options in 
  an effort to reduce memory usage/errors and storage capacity required 
  for outputs, in addition to .p12/PFX (pkcs12) support.  

  **Note: Capabilities are limited to get requests on ArcGIS REST API feature and map services at this time.**  

## Logging:
  The GRALE module uses a logging object to retain request-response cycle information for use in ETL processes.  The logging object retains request information     including parameters/headers, process ID's, and  UTC date-timestamps.  Response metrics include response status, size, and elapsed time. The proces ID serves as the primary key in the logging object and is the unique key that identifies a specific request iteration attempt.  The "ppid" is a "parent process" unique identifier  to which a sub-series of chunked request attempts belong to.
  
  For examples, see:  [Log Structure](#log-structure) & [Viewing the GRALE request log](#viewing-the-grale-request-log)
### Log Structure:  
            {
            'processId':
                {
                'ppid':           'parent process UUID for the process', 
                'utc_timestamp':  'UTC start timestamp of a request instance', 
                'parameters':     'parameters sent to a request instance',   
                'status':         'status category for a request instance','  
                'results':        'detailed messages for a request instance',
                'elapsed_time':   'elapsed time to complete the request instance',
                'size':           'size of return object/data'
                }
            }
## Example Usage:
  ### Basic ArcGIS REST feature service request:
  #### Perform a basic multi-threaded get request for all features/records in a service and return a list of GeoJSON objects.
      In [1]: import grale
      In [2]: url = r'https://someServer/arcgis/rest/services/transportation/MapServer/1'
      In [3]: geojsons = grale.esri_wfs_geojsons(url)
      >>> Pull will require 4 request(s)
      >>> Requesting: 3050 total features
      >>> Chunk size set at: 1000 features
      >>>	-Success |:| ['Size: 530301(B), Time :0.940629(s)']
      >>>	-Success |:| ['Size: 530628(B), Time :2.712735(s)']
      >>>	-Success |:| ['Size: 531134(B), Time :1.368457(s)']
      >>>	-Success |:| ['Size: 9753(B), Time :0.93853(s)']
      >>> Returned: 3050 out of 3050 features


  #### Viewing the GRALE request log:
      In [4]: grale.GRALE_LOG.log
      >>> OrderedDict([
          ('03db2910-8f19-46a9-8bcc-483968b2d6f1',
            {	
              'elapsed_time': '1061.342(ms)',
              'parameters': {'base_url': ['https://someServer/arcgis/rest/services/transportation/MapServer/1/query'],
                      'f': ['JSON'],
                      'outFields': ['*'],
                      'outSR': ['4326'],
                      'resultOffset': ['17000'],
                      'where': ['1=1']},
              'process_id': '690594ca-d724-409e-a4e9-10ddd450b5a2',
              'request': 'https://someServer/arcgis/rest/services/transportation/MapServer/1/query?where=...',
              'results': ['Size: 533583(B),Time :1.061342(s)'],
              'size': '533583(B)',
              'status': 'Success',
              'utc_timestamp': '2022-08-03T18:51:22.408314'
            }
          ),
          ('6fa266fa-2f95-40f4-adac-b0a9798a6af0',
            {
              'elapsed_time': '998.368(ms)',
              'parameters': {'base_url': ['https://someServer/arcgis/rest/services/transportation/MapServer/1/query'],
                      'f': ['JSON'],
                      'outFields': ['*'],
                      'outSR': ['4326'],
                      'resultOffset': ['18000'],
                      'resultRecordCount': ['750'],
                      'where': ['1=1']},
              'process_id': '690594ca-d724-409e-a4e9-10ddd450b5a2',
              'request': 'https://someServer/arcgis/rest/services/transportation/MapServer/1/query?where=...',
              'results': ['Size: 400397(B),Time :0.998368(s)'],
              'size': '400397(B)',
              'status': 'Success',
              'utc_timestamp': '2022-08-03T18:51:22.942478'
            }
          ),
          ('f5f5ef82-03e6-4c68-bf78-9e99a4196145',
            {
              'elapsed_time': '50.531(ms)',
              'parameters': {'base_url': ['https://someServer/arcgis/rest/services/transportation/MapServer/1456/query'],
                      'f': ['JSON'],
                      'outFields': ['*'],
                      'outSR': ['4326'],
                      'resultOffset': ['0'],
                      'where': ['1=1']},
              'ppid': '818aeb1e-4910-4c9a-bf8a-68da43061aac',
              'request': 'https://someServer/arcgis/rest/services/transportation/MapServer/1456/query?where=...',
              'size': '52(B)',
              'status': 'Error: (Unidentified)',
              'results': 'ResponseText:{"error":{"code":500,"message":"json","details":[]}}',
              'utc_timestamp': '2022-08-03T18:51:23.568821'
            }
          )...          
        ])
