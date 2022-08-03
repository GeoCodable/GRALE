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

## General Requests:
  ### ArcGIS REST Feature Service:
  #### Perform a basic multi-threaded get request for all features ina service
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

  
