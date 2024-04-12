'''
To run this script user needs to make changes under "## User input" block only (line 38-54).
1. "# input for path"
    a. "raster_name": define the raster name for which the annotation has been made
    b. "outputrastername": define the masked raster name for final output
    c. "shp_name": define the shapefile name for which holds the annotation in .shp format
    e. "base_path": define the base path
2. "# input for function"
    a. "pixel_size": define the pixe sixe for the output raster
'''

## Import libraries
import os, gc
import json
import shutil
import numpy as np
from osgeo import ogr
from osgeo import gdal
import rasterio as rio
import geopandas as gpd
# from rasterio import mask
from fiona.crs import from_epsg
from shapely.geometry import Polygon
from rasterio.windows import get_data_window, transform

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

## User Input
# for path
raster_name=''
outputrastername= ''
shp_name=''
base_path = ''
raster_path = os.path.join(base_path, raster_name)
shp_path = os.path.join(base_path, shp_name)
mask_path = os.path.join(base_path, outputrastername)
dump_folder_path = os.path.join(base_path, 'dump')

# check path exist or not
path_exist(dump_folder_path)

# input for function
pixel_size = 10 # Define the pixe sixe for the output raster

## Functions
def remove_nodata(input_raster, output_raster, nodata_value=None):
    '''
    Function to remove/mask the nodata value from raster
    input_raster: Define the input raster path
    output_raster: Define output raster path
    nodata_value: Define nodata value which need to be masked
    '''
    with rio.open(input_raster, 'r+') as src:  # open as append mode r+
        if nodata_value != None:
            src.nodata = nodata_value  # define empty areas value, so it can be set as NoData -- np.nan
        profile = src.profile.copy()
        data_window = get_data_window(src.read(masked=True))
        data_transform = transform(data_window, src.transform)
        profile.update(
            transform=data_transform,
            height=data_window.height,
            width=data_window.width)

        data = src.read(window=data_window)

        with rio.open(output_raster, 'w', **profile) as dst:
            data[np.isnan(data)] = src.nodata
            dst.write(data)

def exract_layer_extent(raster_path, out_shp_path):
    '''
    Function is to get the extent of the raster
    1. raster_path: Provide the raster path for which the extent has to be created
    2. out_shp_path: Provide the path to save the raster extent
    3. epsg: Define the projection of the shapefile

    Return
    projection system of the raster
    '''
    dataset = rio.open(raster_path)
    epsg = dataset.crs.to_epsg()
    xmin, ymin, xmax, ymax = dataset.bounds
    
    polygons = []
    polygons.append(Polygon([(xmin,ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]))
    grid = gpd.GeoDataFrame({'geometry':polygons})
    grid.crs = from_epsg(epsg) # Set the GeoDataFrame's coordinate system
    grid.to_file(out_shp_path)
    del dataset
    return epsg

def overlay(shp_path1, shp_path2, out_shp, dst_crs):
    '''
    Function to preform the vector clip
    1. shp1: Provide the shapefile path
    2. shp2: Provide the shapefile path
    3. out_shp: Provide the path to save final clipped shp result
    4. keep_geom: Define true or False to keep the geometry of the shapefile
    '''
    shp1 = gpd.read_file(shp_path1)
    shp2 = gpd.read_file(shp_path2)
    if shp1.crs != dst_crs:
        shp1 = shp1.to_crs({'init': f'epsg:{dst_crs}'})
    if shp2.crs != dst_crs:
        shp2 = shp2.to_crs({'init': f'epsg:{dst_crs}'})
    clip_shp = gpd.overlay(shp1, shp2, how='intersection', keep_geom_type=None, make_valid=True)
    clip_shp.to_file(out_shp, driver='ESRI Shapefile')
    del shp1, shp2

def rasterize(extent_shp_path, clip_shp_path, output_raster, pixel_size):
    '''
    Function to rasterize the vector
    1. extent_shp_path: Define extent shapefile path for output raster
    2. clip_shp_path: Define the shapefile path for rasterization
    3. output_raster: Define the output raster path
    4. pixel_size: Define the pixel size of the raster
    '''
    input_shp = ogr.Open(extent_shp_path)
    shp_layer = input_shp.GetLayer()
    
    xmin, xmax, ymin, ymax = shp_layer.GetExtent()

    ds = gdal.Rasterize(output_raster, clip_shp_path, xRes=pixel_size, yRes=pixel_size, 
                        burnValues=1, outputBounds=[xmin, ymin, xmax, ymax], 
                        outputType=gdal.GDT_Byte)
    ds = None

## Creating mask
error_dict = {}
try:
    # define outfiles path with names
    output_raster_nodata = os.path.join(base_path, f'{raster_name}_nodata.tif')
    extent_shp_path = os.path.join(dump_folder_path, f'{raster_name}_extent.shp')
    clip_shp_path = os.path.join(dump_folder_path, f'{raster_name}_clip.shp')
    output_raster = os.path.join(base_path, f'{raster_name}_mask.tif')
    remove_nodata(raster_path,output_raster_nodata, nodata_value=0.0)
    epsg = exract_layer_extent(output_raster_nodata, extent_shp_path)
    overlay(shp_path, extent_shp_path, clip_shp_path, epsg)
    rasterize(extent_shp_path, clip_shp_path, output_raster, pixel_size)
except Exception as e:
            print(f'Error:{e}')
            error_dict[shp_name] = e

# saving the error dict as json
with open(f'{base_path}error.json','w') as outfile:
    json.dump(error_dict, outfile)

# shutil.rmtree(dump_folder_path) # remove dump dir
