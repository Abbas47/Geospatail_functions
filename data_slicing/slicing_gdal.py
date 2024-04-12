# Import libraries
import os
import boto3
import shutil
import numpy as np
import pandas as pd
from osgeo import gdal
from time import time
start = time()

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

        
# input path
## for data download and upload from s3
my_bucket = ''
bucket_prefix = ''
drive_path = ''

## for script
base_path = ''
output_path = os.path.join(base_path, 'dump')
final_output = os.path.join(base_path, 'Sliced')
dataset_path = ''

path_exist(output_path)

# input for script
tile_size_x = 256 # define x patch size for slice
tile_size_y = 256 # define y path size for slice
download = True # input, i.e., True or False. if download=True, the relevent data required for executing this script will be downloaded from s3 to local instance and if download=False, then the data will not be downloaded from s3. Deafult to False
check = False # input, i.e., True or False. if the patches with nodata value need to be discarded then input will be True else it will be False
upload = False # input, i.e., True or False. if upload=True, the data will be uploaded to s3 based on the path provided bu user and if upload=False, then the data will not be uploaded to s3. Deafult to False 

# functions
def slicing_raster (input_raster_path, output_raster_path, x_patch, y_patch):
    '''
    fuction for slicing raster into small patches based on patch size defined by user and return nodata value of raster
    Input parameteres:
    1. input_raster_path: Define input raster path
    2. output_raster_path: Define output raster path
    3. x_patch: Define patch size in x direction
    4. y_patch: Define patch size in y direction
    
    Return:
    Nodata value of the raster
    
    Note: output_raster_path = /home/ab/Little_place_labs/office/test_data/final_test/VV_dB_
    '''
    print('slicing initiated')
    print(input_raster_path)
    ds = gdal.Open(input_raster_path)
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    if nodata == None:
        nodata = np.nan
    xsize = band.XSize
    ysize = band.YSize
    for i in range(0, xsize, x_patch):
        for j in range(0, ysize, y_patch):
            com_string = f"gdal_translate -of GTIFF -srcwin {i}, {j}, {x_patch}, {y_patch} {input_raster_path} {output_raster_path}_{i}_{j}.tif"
            os.system(com_string)
    ds = None
    return nodata

def slice_check(imagery_path, nodata, dst_path, x_patch, y_patch, tick):
    '''
    function to check whether the sliced raster is consists of nodata value
    Input parameteres:
    1. imagery_path: Define input sliced raster path
    2. nodata: Define Nodata value of raster
    3. x_patch: Define patch size in x direction
    4. y_patch: Define patch size in y direction
    5. tick:
    
    Return:
    tick
    '''
    print('slice check initiated')
    ds = gdal.Open(imagery_path)
    band = ds.GetRasterBand(1)
    rasterArray = band.ReadAsArray()
    
    # for nodata check
    flag = nodata in rasterArray
    xsize = band.XSize
    ysize = band.YSize
    
    # patch size check
    if xsize != x_patch or ysize != y_patch:
        print(f'Issue with the patch size {xsize}, {ysize}')
        size_flag = True
    else:
        size_flag = False
    
    # nan check
    dim = rasterArray.shape[0] * rasterArray.shape[1]
    array = rasterArray[~np.isnan(rasterArray)]
    if dim != array.shape[0]:
        nan_flag = True
    else:
        nan_flag = False
        
    # zero patch check
    non_zero = np.count_nonzero(rasterArray)
    if non_zero == 0:
        zero_flag = True
    else:
        zero_flag = False

    if flag == True or size_flag == True or nan_flag == True or zero_flag == True:
        os.remove(imagery_path)
    else:
        shutil.copy2(imagery_path, dst_path)
        os.remove(imagery_path)
        tick += 1
    ds = None
    return tick

def s3_download(bucket_name, bucket_prefix):
    '''
    Function is to download the directory from s3 to local
    Input parameters
    1. bucket_name: Define the name of the s3 bucket where data needs to be uploaded
    2. bucket_prefix: Define the directory path in the s3 bucket
    Output
    Return local directory path
    '''
    print('downloading data from s3')
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=bucket_prefix):
        if not obj.key[-1] == "/":
            sys_path = os.path.join(f'/home/ubuntu/orbitalAI/phisat-2/data/{bucket_name}', obj.key)
            if not os.path.exists(os.path.dirname(sys_path)):
                os.makedirs(os.path.dirname(sys_path))
            dir_path = os.path.dirname(sys_path)
            bucket.download_file(obj.key, sys_path) # save to same path
    return dir_path

def s3_upload(bucket_name, local_path, drive_path):
    '''
    Function is to upload the whole directory data to the desired location on s3
    Input parameters
    1. bucket_name: Define the name of the s3 bucket where data needs to be uploaded
    2. local_path: Location of the directory in the local instance
    3. drive_path: Location of the directory in the s3 bucket
    '''
    print('uploading data to s3')
    s3 = boto3.client('s3')
    for file in os.listdir(local_path):
        if not file.startswith('.') or file.endswith('.xml'):
            local_file_path = os.path.join(local_path, file)
            drive_file_path = os.path.join(drive_path, file)
            s3.upload_file(Filename=local_file_path, Bucket=bucket_name, Key=drive_file_path)
            print(f'{file} uploaded to s3')
            

## Creating creating slicing
# download dataset from s3 to ec2
if download == True:
    dataset_path = s3_download(my_bucket, bucket_prefix)
else:
    dataset_path

# creat an empy list to add value to dataframe
name = []
nodata = []
total_file_count = []
final_file_count = []

# folder_list = ['Upsampled_images', 'Upsampled_masks']
folder_list = ['Upsampled_images']
for folder in os.listdir(base_path):
    if folder in folder_list:
        final_output_path = f'{final_output}/{folder}'
        path_exist(final_output_path)
        folder_path = os.path.join(base_path, folder)
        for file in os.listdir(folder_path):
            if file.endswith('.tif'):
                name.append(f'{file}')
                filename = file.split('.')[0]
                input_raster_path = os.path.join(folder_path, file)
                
                if check == True:
                    output_raster_path = os.path.join(output_path, filename)
                elif check == False:
                    output_raster_path = os.path.join(final_output_path, filename)

                # slicing down the raster based on defined patch size and retrun nodata value of raster
                nodata_value = slicing_raster (input_raster_path, output_raster_path, tile_size_x, tile_size_y)
                nodata.append(nodata_value)
                
                if check == True:
                    # checking whether the sliced patches is consist of nodata value, if yes then it will be removed
                    count = 0
                    tick = 0
                    for filename in os.listdir(output_path):
                        if filename.endswith('.tif'):
                            count += 1
                            imagery_path = os.path.join(output_path, filename)
                            tick = slice_check(imagery_path, nodata_value, final_output_path, tile_size_x, tile_size_y, tick)
                
                    total_file_count.append(count)
                    final_file_count.append(tick)
                elif check == False:
                    pass
        print(final_output_path)
        print(drive_path)
        if upload == True:
            s3_upload(my_bucket, final_output_path, f'{drive_path}/{folder}_final')
        elif upload == False:
            pass

if check == True:
    # create a data frame for a broaded overviw of the data, i.e., total number of slicied imagery and how many where selected out of it
    df = pd.DataFrame(columns = ['name', 'nodata', 'total_files', 'final_files'])
    df['name'] = name
    df['nodata'] = nodata
    df['total_files'] = total_file_count
    df['final_files'] = final_file_count
    df.to_csv(f'{dataset_path}/slice_data_report.csv')
elif check == False:
    pass

end = time()
print("The time of execution for slicing script:",(end-start))