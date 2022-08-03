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

## Example Usage:
  ### Basic ArcGIS REST Feature Service Request:
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


  #### View the GRALE Request Log data:
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
          )...
        ])
