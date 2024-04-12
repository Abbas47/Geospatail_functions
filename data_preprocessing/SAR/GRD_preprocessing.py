#!/usr/bin/env python
# coding: utf-8

# In[ ]:


### Import libraries
import sys
sys.path.append('/home/ubuntu/.snap/snap-python')
import time
start = time.time()
import os, gc
import boto3
import shutil
import pandas as pd
import rasterio as rio
from shapely.geometry import Polygon
from snappy import GPF, ProductIO, HashMap, jpy


# In[ ]:


def path_exist(path):
    '''
    Function for checking the exisiting path and if the path doesnt exist the give path will be created.
    Input parameters:
    1. path: file path
    '''
    # check whether the specified path exists or not
    isExist = os.path.exists(path)
    if not isExist:
        # create a new directory
        os. makedirs(path)


# In[ ]:


### User input
## input for path
# main-foldername/bucket-name
main_foldername = 'data'

# sub-main folders that comes under main folder 
submain_folder = 'SAR'

# folders that comes under weekly folder
raw_imagery = 'raw_img'
preprocessed_imagery = 'preproc_img'
band_folder_vh = 'VH'
band_folder_vv = 'VV'

## input for functions
proj = 'WGS84(DD)' # define projection
downsample = 0 # input 0 or 1 (1 -- need downsample to 40m and 0 -- no need to downsample)
subset = False # input, i.e., True or False. if download=True, the terrain corrected data will be cliped based on the polygon provided by user and if download=False, the terrain corrected data will not be cliped
poly_wkt = '' # define the polygon in wkt format for cliping the terrain corrected data
''' well-known-text (WKT) file for subsetting (can be obtained from SNAP by drawing a polygon)
    wkt = 'POLYGON ((-157.79579162597656 71.36872100830078, -155.4447021484375 71.36872100830078, \
    -155.4447021484375 70.60020446777344, -157.79579162597656 70.60020446777344, -157.79579162597656 71.36872100830078))' '''
download = False # input, i.e., True or False. if download=True, the relevent data required for executing this script will be downloaded from s3 to local instance and if download=False, then the data will not be downloaded from s3. Deafult to False
remove = False # input, i.e., True or False. if remove=True, the data used and generated from this script will be removed from local instance and if remove=False, then the data will not be removed from local instance. Deafult to False


### Define path
base_path = main_foldername
SAR_folder_path = os.path.join(base_path, submain_folder)
raw_imagery_path = os.path.join(SAR_folder_path, raw_imagery)
preprocessed_imagery_path = os.path.join(SAR_folder_path, preprocessed_imagery)
preprocessed_imagery_path_vh = os.path.join(preprocessed_imagery_path, band_folder_vh)
preprocessed_imagery_path_vv = os.path.join(preprocessed_imagery_path, band_folder_vv)

# path_exist(preprocessed_imagery_path)
path_exist(preprocessed_imagery_path_vh)
path_exist(preprocessed_imagery_path_vv)

# Declare bucket name, remote file, and destination for S3 and local
my_bucket = main_foldername
bucket_prefix = f'{submain_folder}/{raw_imagery}' # path of the directory where the raw imageries seats in the s3 bucket

# location for uploading the data from ec2 to s3
drive_path_vh = f'{submain_folder}/{preprocessed_imagery}/{band_folder_vh}'
drive_path_vv = f'{submain_folder}/{preprocessed_imagery}/{band_folder_vv}'
local_path = preprocessed_imagery_path


# In[ ]:


### Function
def do_apply_orbit_file(source):
    '''
    Function to do orbit correction
    Input parameters:
    1. source: Opened SAR imagery using snappy.ProductIO.readProduct(file_path)
    Output:
    Return orbit corrected data
    '''
    print('\tApply orbit file...')
    parameters = HashMap()
    parameters.put('orbitType', 'Sentinel Precise (Auto Download)')
    parameters.put('polyDegree', '3')
    # parameters.put('Apply-Orbit-File', True)
    output = GPF.createProduct('Apply-Orbit-File', parameters, source)
    return output

def do_thermal_noise_removal(source):
    '''
    Function to do thermal correction
    Input parameters:
    1. source: Orbit corrected data
    Output:
    Return thermal corrected data
    '''
    print('\tThermal noise removal...')
    parameters = HashMap()
    parameters.put('removeThermalNoise', True)
    output = GPF.createProduct('ThermalNoiseRemoval', parameters, source)
    return output

def do_calibration(source, polarization, band):
    '''
    Function to do radiometric calibration
    Input parameters:
    1. source: thermal corrected data
    2. polarization: name of intensity bands in the data
    3. band: 'VV' or 'VH'
    Output:
    Return radiometric corrected data
    '''
    print('\tCalibration...')
    parameters = HashMap()
    parameters.put('outputSigmaBand', True)
    try:
        parameters.put('sourceBands', polarization)
    except:
        print("different polarization!")
    parameters.put('selectedPolarisations', band)
    parameters.put('outputImageScaleInDb', False)
    output = GPF.createProduct("Calibration", parameters, source)
    return output

def do_speckle_filtering(source):
    '''
    Function to do speckel filtering
    Input parameters:
    1. source: radiometric corrected data
    Output:
    Return speckel filtered data
    '''
    print('\tSpeckle filtering...')
    parameters = HashMap()
    parameters.put('filter', 'Lee')
    parameters.put('numLooksStr', '1')
    parameters.put('filterSizeX', 5)
    parameters.put('filterSizeY', 5)
    # parameters.put('sigmaStr', '0.9')
    # parameters.put('targetWindowSizeStr', '3x3')
    # parameters.put('WindowSizeStr', '7x7')
    output = GPF.createProduct('Speckle-Filter', parameters, source)
    return output

def do_terrain_correction(source, proj, downsample):
    '''
    Function to do terrain correction
    Input parameters:
    1. source: speckel filtered data
    2. proj: projection for output data
    Output:
    Return terrain corrected data
    '''
    print('\tTerrain correction...')
    parameters = HashMap()
    parameters.put('demName', 'SRTM 3Sec')
    parameters.put('demResamplingMethod','BILINEAR_INTERPOLATION')
    parameters.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
    while downsample == 1:
        parameters.put('pixelSpacingInMeter', 40.0)
        break
    parameters.put('pixelSpacingInMeter', 10.0)
    parameters.put('mapProjection', proj)
    parameters.put('nodataValueAtSea', False)
    parameters.put('saveSelectedSourceBand', True)
#     parameters.put('saveProjectedLocalIncidenceAngle', True)
    output = GPF.createProduct('Terrain-Correction', parameters, source)
    return output

def do_subset(source, poly_wkt):
    '''
    Function to create the subset of processed imagery
    Input parameters:
    1. source: terrain corrected data
    2. wkt: polygon for creating subset
    Output:
    Return subset data
    '''
    print('\tSubsetting...')
    parameters = HashMap()
    parameters.put('geoRegion', poly_wkt)
    output = GPF.createProduct('Subset', parameters, source)
    return output

def covert_to_dB(source):
    '''
    Function to convert intensity value to db
    Input parameters:
    1. source: subset data/terrain corrected data
    Output:
    Return db converted data
    '''
    print('\tCoversion to dB...')
    parameters = HashMap()
    output = GPF.createProduct('LinearToFromdB', parameters, source)
    return output

def s3_download(bucket_name, bucket_prefix):
    '''
    Function is to download the directory from s3 to local
    Input parameters
    1. bucket_name: Define the name of the s3 bucket where data needs to be uploaded
    2. bucket_prefix: Define the directory path in the s3 bucket
    '''
    print(f'Data is downloading from s3 to local....')
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=bucket_prefix):
        if not obj.key[-1] == "/":
            sys_path = os.path.join(bucket_name, obj.key)
            if not os.path.exists(os.path.dirname(sys_path)):
                os.makedirs(os.path.dirname(sys_path))
            dir_path = os.path.dirname(sys_path)
            bucket.download_file(obj.key, sys_path) # save to same path
    return dir_path


# In[ ]:


## Preprocess data based on user input
# download raw imagery zip files from s3 to ec2 
if download == True:
    raw_imagery_path = s3_download(main_foldername, bucket_prefix)
elif download == False:
    raw_imagery_path


# In[ ]:


s3 = boto3.client('s3') # s3 client connection

dict_scene = {} # define an empty dictionary to save the extent of the scene imagery based on each scene

# looping through raw_imagery folder to do the preprocessing on each scene zipfile
for file in os.listdir(raw_imagery_path):
    if file.endswith('.zip'):
        filename = file.split('.')[0]
        file_path = os.path.join(raw_imagery_path, file)
        gc.enable() # enabling the memory management
        gc.collect() # clearing the memory for use
        S2CacheUtils = jpy.get_type('org.esa.s2tbx.dataio.cache.S2CacheUtils')
        sentinel_1 = ProductIO.readProduct(file_path)

        ## Extract polarizations
        band_list = list(sentinel_1.getBandNames())
        check_bands = ['Intensity_VH', 'Intensity_VV', 'Intensity_HH', 'Intensity_HV']
        polarization_list = []
        pols = []
        for check_band in check_bands:
            if check_band in band_list:
                pol = check_band.split('_')[1]
                polarization_list.append(check_band)
                pols.append(pol)
        polarization = ','.join(polarization_list) # converting list to string
        # Start preprocessing:
        # appling orbit correction on the sentinel-1 image
        applyorbit = do_apply_orbit_file(sentinel_1)
        thermalcorrection = do_thermal_noise_removal(applyorbit)
        scene_start = time.time()
        ## processing for single band
        for band in pols:
            # appling radiometric correction on the orbit corrected data
            calibrated = do_calibration(thermalcorrection, polarization, band)
            filtered = do_speckle_filtering(calibrated)
            del calibrated
            gc.collect()
            # appling terrain correction on the radiometric corrected data
            tercorrected = do_terrain_correction(filtered, proj, downsample)
            del filtered
            gc.collect()
            if subset == True:
                data = do_subset(tercorrected, poly_wkt)
            elif subset == False:
                data = tercorrected
            del tercorrected
            gc.collect()
            # converting intensity value to dB of terrain corrected data
            convert = covert_to_dB(data)
            del data
            gc.collect()
            raster_name = f'{filename}_{band}_Orb_Cal_Spk_TC_dB'
            # creating the saving path for local and s3 each band in the scene
            if band == 'VH':
                output_raster_path = os.path.join(preprocessed_imagery_path_vh, raster_name)
                drive_file_path = os.path.join(drive_path_vh, f'{raster_name}.tif')
            elif band == 'VV':
                output_raster_path = os.path.join(preprocessed_imagery_path_vv, raster_name)
                drive_file_path = os.path.join(drive_path_vv, f'{raster_name}.tif')

            # saving the preprocessed imagery in local instance
            ProductIO.writeProduct(convert, output_raster_path, 'GeoTIFF')
            del convert
            gc.collect()
        del applyorbit
        gc.collect()
        sentinel_1.dispose()
        sentinel_1.closeIO()
        S2CacheUtils.deleteCache()
        
        # reading the preprocessed imagery for getting the extent of the scene
        local_file_path = f'{output_raster_path}.tif'
        with rio.open(local_file_path) as src:
            tile_bounds = src.bounds
            polygon = Polygon([[tile_bounds.left, tile_bounds.top], [tile_bounds.left, tile_bounds.bottom], [tile_bounds.right, tile_bounds.bottom], [tile_bounds.right, tile_bounds.top]])
            dict_scene[filename] = polygon.wkt
        # removing the unzip folder of the scene
        # shutil.rmtree(folder_path)
        local_file_path = f'{output_raster_path}.tif'
        # os.remove(local_file_path)
        scene_end = time.time()
        print("The time of execution for one scene (VH and VV) :",(scene_end-scene_start))

