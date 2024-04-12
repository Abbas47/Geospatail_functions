#!/usr/bin/env python
# coding: utf-8

# In[1]:

import boto3
import os
import rasterio
import numpy as np
from rasterio.windows import Window


# In[2]:


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


# In[3]:


## User input
# input path for local
dataset_path = '/home/indian/Downloads/noise_data/water'
result_dir = 'output_water'
output_folder = os.path.join(dataset_path, result_dir)

path_exist(output_folder)

# input path s3
my_bucket = ''
bucket_prefix = ''
drive_path = ''

# for function
slice_height = 2196
slice_width = 2196
download = True # input, i.e., True or False. if download=True, the relevent data required for executing this script will be downloaded from s3 to local instance and if download=False, then the data will not be downloaded from s3. Deafult to False
upload = False # input, i.e., True or False. if upload=True, the data will be uploaded to s3 based on the path provided bu user and if upload=False, then the data will not be uploaded to s3. Deafult to False 

## Functions
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

# In[4]:
## Creating creating slicing
# download dataset from s3 to ec2
if download == True:
    dataset_path = s3_download(my_bucket, bucket_prefix)
else:
    dataset_path


for file in os.listdir(dataset_path):
    if file.endswith('.tif'):
        input_raster_path = os.path.join(dataset_path, file)
        input_raster = rasterio.open(input_raster_path)
        for y in range(0, input_raster.height, slice_height):
            for x in range(0, input_raster.width, slice_width):
                window = Window(x, y, min(slice_width, input_raster.width - x), min(slice_height, input_raster.height - y))
                slice_data = input_raster.read(window=window)
                slice_data = np.transpose(slice_data,(1,2,0))
                
                output_filename = file.replace('.tif', f'_{y}_{x}.tif')
                output_path = os.path.join(output_folder, output_filename)

                output_profile = input_raster.profile
                output_profile.update(width=window.width, height=window.height, transform=input_raster.window_transform(window))
                with rasterio.open(output_path, 'w', **output_profile) as dst:
                    for band_idx in range(slice_data.shape[-1]):
                        dst.write(slice_data[:, :, band_idx], band_idx + 1)

        input_raster.close()
        if upload == True:
            s3_upload(my_bucket, output_folder, drive_path)
        elif upload == False:
            pass
# In[ ]:




