'''
To run this script user needs to make changes under "## User input" block only (line 17-27).
1. "# input for path"
    a. "inputPath_img": define the tiff path which needs to be converted into img
    b. "dstPath_img": define the img path where the convereted image will be stored
2. "# input for function"
    a. "outputFormat": define the final output image format.i.e., png or jpeg
    b. "select_band_from_raster": input, i.e., True or False. if select_band_from_raster=True, new raster will be created using the selected band defined by user and if select_band_from_raster=False, band selection wont be executed for the defined raster
    c. "band_list": specify the band list to create raster
'''
## Import libraries
from osgeo import gdal
import rasterio as rio
import numpy as np
import subprocess

## User input
# input for path
inputPath_img = '/home/indian/Downloads/20180818T112111_20180818T112627_T29SNB.tif'
outputPath_img = '/home/indian/Downloads/20180818T112111_20180818T112627_T29SNB_selected.tif'
dstPath_img = '/home/indian/Downloads/20180818T112111_20180818T112627_T29SNB_converted.jpg'

# input for function
select_band_from_raster = True # # input, i.e., True or False. if select_band_from_raster=True, new raster will be created using the selected band defined by user and if select_band_from_raster=False, band selection wont be executed for the defined raster
band_list = [4,3,2] # specify the band list to create raster
outputPixType = 'Byte'
outputFormat = 'png'

## Function
def select_band(inputRasterPath, outputRasterPath, bandList):
    '''
    Function to create a raster with the select bands 
    Input parameters:
    1. inputRasterPath: Define the path for raster
    2. outputRasterPath: Define the path for raster with selected bands
    3. bandList: Define list with the band no to create a raster
    '''
    with rio.open(inputRasterPath) as src:
        profile = src.meta
        array = src.read(bandList)

    # update profile
    profile.update(
        count = 3
    )

    transposed_array = np.transpose(array)

    # Save the merged data as a TIFF
    with rio.open(outputRasterPath, "w", **profile) as dst:
        for band_idx in range(transposed_array.shape[-1]):
            dst.write(transposed_array[:, :, band_idx], band_idx + 1)

def _16bit_to_8Bit(inputRaster, outputRaster, PixType, Format, percentiles=[2, 98]):
    '''
    Function for converting tiff to img
    Input parameters:
    1. inputRaster: Define the path for tiff
    2. outputRaster: Define the path for output png/jpeg
    3. PixType: Define output pixel type
    4. Format: Define output file format
    '''

    srcRaster = gdal.Open(inputRaster)
    cmd = ['gdal_translate', '-ot', PixType, '-of', 
            Format]

    for bandId in range(srcRaster.RasterCount):
        bandId = bandId+1
        band = srcRaster.GetRasterBand(bandId)

        bmin = band.GetMinimum()        
        bmax = band.GetMaximum()
        # if not exist minimum and maximum values
        if bmin is None or bmax is None:
            (bmin, bmax) = band.ComputeRasterMinMax(1)
        # else, rescale
        band_arr_tmp = band.ReadAsArray()
        bmin = np.percentile(band_arr_tmp.flatten(), 
                            percentiles[0])
        bmax= np.percentile(band_arr_tmp.flatten(), 
                            percentiles[1])

        cmd.append('-scale_{}'.format(bandId))
        cmd.append('{}'.format(bmin))
        cmd.append('{}'.format(bmax))
        cmd.append('{}'.format(0))
        cmd.append('{}'.format(255))

    cmd.append(inputRaster)
    cmd.append(outputRaster)
    print("Conversin command:", cmd)
    subprocess.call(cmd)
## Execution
# creating raster with selected bands
if select_band_from_raster == True:
    select_band(inputPath_img, outputPath_img, band_list)
else:
    outputPath_img = inputPath_img

# Coverting tiff to img
_16bit_to_8Bit(outputPath_img, dstPath_img, PixType=outputPixType, Format=outputFormat)

