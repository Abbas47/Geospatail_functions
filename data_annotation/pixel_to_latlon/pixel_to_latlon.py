'''
To run this script user needs to make changes under "## User input" block only (line 16-21).
1. "# input for path"
    a. "path_json": define the JSON path which have the annotation
    b. "inputPath_img": define the tiff path for which the annotation has been done
    c. "dstPath_img": define the img path where the convereted image will be stored
'''

## Import libraries
import json
import rasterio
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

## User input
# for path
path_json ='/home/ab/annotation/new_bbox/49df97e7-b813-4423-a854-7377f6d364cf.json'
inputPath_img = '/home/ab/annotation/new_bbox/S1A_IW_GRDH_1SDV_20221221T230251_20221221T230316_046436_05902D_3789_VV__1024_12800.tif'
dstPath_shp = '/home/ab/annotation/new_bbox/bbox.shp'

## Function
def convertPixelLongLat(pixel_rows, pixel_cols, tif_transform, top_left_pixel_coordinates = None):
    '''
    Converting pixel coordinates to real world longitude and latitude coordinates. It works on lists of pixel coordinates, and point pixel coordinates
    Input parameters:
    1. pixel_rows: List of the pixel rows, the Y-coordinates, single integers can also be specified
    2. pixel_cols: List of the pixel cols, the X-coordinates, single integers can also be specified
    3. tif_transform: Transfrom of the tif file obtained from the meta
    4. top_left_pixel_coordinates: Top left pixel coordinates of the patch, add these values to the pixel_rows and pixel_cols. Format is [row, col]

    Output
    Returns the longitudes and latitudes of the pixel coordinates. Longitudes link with X-coordinates and latitudes link with the Y-coordinates
    '''

    if type(pixel_rows) == int and type(pixel_cols) == int:
        pixel_rows = [pixel_rows]
        pixel_cols = [pixel_cols]
        pass

    if top_left_pixel_coordinates:
        pixel_rows = [i + top_left_pixel_coordinates[0] for i in pixel_rows]
        pixel_cols = [i + top_left_pixel_coordinates[1] for i in pixel_cols]
        pass

    longs, lats = rasterio.transform.xy(tif_transform, pixel_rows, pixel_cols)
    return longs, lats
    pass

def create_shp(xmin, ymin, xmax, ymax, dst_crs):
    '''
    Function to create the shapefile using the xmin, ymin,ymax, ymax
    Input parameters:
    xmin, ymin, xmax, ymax
    
    Output
    Return geodataframe
    '''
    geometry = [box(xmin, ymin, xmax, ymax)]
    geodf = gpd.GeoDataFrame(crs=dst_crs, geometry=geometry)
    return geodf

## Execute
tile_src = rasterio.open(inputPath_img) # read tiff
tile_transform = tile_src.transform # get the tiff transformation 
del tile_src

count = 0
with open(path_json) as f: # read json
    data = json.load(f)
    for key, value in data.items():
        if key == 'objects':
            for item in value:
                for subkey, subvalue in item.items():
                    if subkey == 'annotation':
                        x, y, w, h = subvalue['coord'].values()
                        
                        # coords cannot be float
                        x_min = int(x)
                        y_min = int(y)
                        x_max = int(x+w)
                        y_max = int(y+h)
                        
                        lst_row = [y_min, y_max]
                        lst_col = [x_min, x_max]
                        pixel_rows  = list(map(float, lst_row))
                        pixel_cols  = list(map(float, lst_col))
                        longs, lats = convertPixelLongLat(pixel_rows, pixel_cols, tile_transform, top_left_pixel_coordinates = None)
                        gdf = create_shp(longs[0], lats[0], longs[1], lats[1], "EPSG:4326")
                        if count == 0:
                            merge_gdf = gdf
                            count += 1
                            break
                        else:
                            merge_gdf = merge_gdf.append(gdf, ignore_index=True)
                        
                        # save annotation shapefile
                        merge_gdf.to_file(dstPath_shp)
