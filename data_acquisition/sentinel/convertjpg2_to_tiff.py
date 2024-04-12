### Import Libraries
import time
start_conversion = time.time()
import boto3
import os, gc
import numpy as np
import rasterio
from rasterio.enums import Resampling


### input for path
# local path
basePath = ''
folderName = 'S2A_MSIL1C_20230603T112121_N0509_R037_T29SPC_20230603T150055.SAFE'
folderPath = os.path.join(basePath,folderName)
directoryPath = os.path.join(folderPath, "GRANULE", os.listdir(os.path.join(folderPath, "GRANULE"))[0],  "IMG_DATA")

# s3 path
bucket_name = ''
drive_path = ''

### input for function
band_list = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B10', 'B11', 'B12'] # Identify bands (modify this based on your requirements)
common_resolution = 10  # in meters
file_format = '.jp2'
max_depth = 2  # desired depth to check the file format
remove = False # input, i.e., True or False. if remove=True, the data used and generated from this script will be removed from local instance and if remove=False, then the data will not be removed from local instance. Deafult to False
upload = False # input, i.e., True or False. if upload=True, the data will be uploaded to s3 based on the path provided bu user and if upload=False, then the data will not be uploaded to s3. Deafult to False 

### Functions
def get_files_with_format(root_directory, file_format, max_depth):
    matched_files = []
    for root, dirs, files in os.walk(root_directory):
        # Calculate the current depth level
        current_depth = root.count(os.sep) - root_directory.count(os.sep)
        if current_depth > max_depth:
            # If the current depth exceeds the specified max_depth, stop traversing
            break
        
        for file in files:
            if file.endswith(file_format):
                matched_files.append(os.path.join(root, file))
    return matched_files, current_depth

def s3_upload(bucket_name, local_file_path, drive_path):
    '''
    Function is to upload the whole directory data to the desired location on s3
    Input parameters
    1. bucket_name: Define the name of the s3 bucket where data needs to be uploaded
    2. local_path: Location of the directory in the local instance
    3. drive_path: Location of the directory in the s3 bucket
    '''
    print(f'Data is uploading from local to s3....')
    s3 = boto3.client('s3')
    file = os.path.basename(local_file_path)
    drive_file_path = os.path.join(drive_path, file)
    s3.upload_file(Filename=local_file_path, Bucket=bucket_name, Key=drive_file_path)


matching_files, current_depth = get_files_with_format(directoryPath , file_format, max_depth)
output_tiff = os.path.join(basePath, folderName.replace('.SAFE', '.tif')) 


final_bandPaths = []

if current_depth == 0:
    for bandPath_string in matching_files:
        band_element = bandPath_string.split('_')[-1].split('.')[0]
        if  band_element in band_list:
            final_bandPaths.append(bandPath_string)
            band_list.remove(band_element)
    # Sorting list
    final_bandPaths.sort(key=lambda x: x.split('_')[-1].split('.')[0])
else:
    for bandPath_string in matching_files:
        band_element = bandPath_string.split('_')[-2]
        if  band_element in band_list:
            final_bandPaths.append(bandPath_string)
            band_list.remove(band_element)
    # Sorting list
    final_bandPaths.sort(key=lambda x: x.split('_')[-2])

print(band_list)
print(final_bandPaths)

# inser 8A band from last to 9th place in the list
last_element = final_bandPaths.pop()  # Remove and get the last element
final_bandPaths.insert(8, last_element)  # Insert the last element at index 2
print(final_bandPaths)

print('part1')
gc.enable() # enabling the memory management
gc.collect() # clearing the memory for use
resampled_bands = []
for band_path in final_bandPaths:
    with rasterio.open(band_path) as src:
        resampled_band = src.read(
            out_shape=(
                src.count,
                int(src.height * (src.res[0] / common_resolution)),
                int(src.width * (src.res[1] / common_resolution))
            ),
            resampling=Resampling.bilinear
        )
        resampled_bands.append(resampled_band)
        gc.collect() # clearing the memory for use

print('part2')
# Stack the resampled bands along a new dimension
merged_data = np.stack(resampled_bands, axis=1)
merged_data = merged_data[0]
transposed_array = np.transpose(merged_data, (1, 2, 0))
gc.collect() # clearing the memory for use

print('part3')
# Get spatial information from one of the resampled bands
with rasterio.open(final_bandPaths[0]) as src:
    profile = src.profile
gc.collect() # clearing the memory for use

print('part4')
# Update the profile for the merged TIFF
profile.update(
    driver='GTiff',
    dtype=rasterio.uint16,  # Change the dtype as needed
    width=merged_data.shape[2],
    height=merged_data.shape[1],
    transform=src.transform * src.transform.scale(
        (src.width / merged_data.shape[2]),
        (src.height / merged_data.shape[1])
    ),
    count=transposed_array.shape[-1]
    # compress="lzw",  # compression method
    # predictor=2  # For LZW compression, you can use predictor value 2
)
gc.collect() # clearing the memory for use
print(profile)

print('part5')
# Save the merged data as a TIFF
with rasterio.open(output_tiff, "w", **profile) as dst:
    for band_idx in range(transposed_array.shape[-1]):
        dst.write(transposed_array[:, :, band_idx], band_idx + 1)
gc.collect() # clearing the memory for use

### Export to s3
if upload == True:
    # Connect to S3 bucket and download file 
    s3_upload(bucket_name, output_tiff, drive_path)
elif upload == False:
    pass

# remove the data from the local
if remove == True:
    os.remove(output_tiff)  # remove raw imagery folder
elif remove == False:
    pass

end = time.time()
end_conversion = time.time()
print("The time of execution of data acquistion script:",(end_conversion - start_conversion))