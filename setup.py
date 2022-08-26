import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='grale',                           # name of the package
    version='0.0.1',                        # release version
    author='GeoCodable',                    # org/author
    description=\
        '''
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

        *Note: 0.0.1 Capabilities are limited to get requests on ArcGIS REST API's 
            feature and map services at this time.  
         
        ''',
    long_description=long_description,      # long description read from the the readme file
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),    # list of all python modules to be installed
    classifiers=[                           # information to filter the project on PyPi website
                        'Programming Language :: Python :: 3',
                        'License :: OSI Approved :: MIT License',
                        'Operating System :: OS Independent',
                        'Natural Language :: English',
                        'Programming Language :: Python :: 3.7',
                        ],                                      
    python_requires='>=3.7',                # minimum version requirement of the package
    py_modules=['grale'],                   # name of the python package
    package_dir={'':'src'},                 # directory of the source code of the package
    install_requires=[                      # package dependencies

                    ## Python 3 Standard Library Members 
                    ##-----------------------------------------                        
                    'sys', 
                    'os', 
                    'datetime', 
                    're', 
                    'shutil', 
                    'requests',  
                    'urllib', 
                    'urllib3',
                    'uuid', 
                    'json', 
                    'gzip',  
                    'threading', 
                    'concurrent',
                    'requests_pkcs12', 
                    'arcgis2geojson', 
                    'pandas', 
                    'geopandas', 
                    'shapely'
                    ##-----------------------------------------
                ]
    )
