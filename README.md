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


