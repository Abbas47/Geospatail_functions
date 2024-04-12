## Import libraries
import  numpy as np
import pathlib
from math import floor 
from PIL import Image
from osgeo import gdal
from numpy import asarray
from matplotlib import pyplot as plt

## User input
# for path
img_path = ''

# for function
tile_size = (125, 125) 
step_size = (125, 125)

## Function
def gtiff_to_array(file_path):
    """Takes a file path and returns a tif file as a 3-dimensional numpy array, width x height x bands."""
    data = gdal.Open(file_path)
    bands = [data.GetRasterBand(i+1).ReadAsArray() for i in range(data.RasterCount)]
    return np.stack(bands, axis=2)

def read_img(img_path):
    '''
    Function to read image in png/jpeg format
    Input parameters:
    1. img_path: Define image path

    Output
    Return image as array
    '''
    image = Image.open(img_path)
    data = asarray(image) # convert image to numpy array

    print(type(data))

    # summarize shape
    print(data.shape)
    return data

def slice_scene(scene, tile_size, step_size):
    '''
    Function to slice the image provided in nupy array based on used requirements
    1. scene: Provide image in numpy array format
    2. tile_size: Define tuple with x, y direction size in which image needs to be sliced
    3. atep_size: Define tuple with x,y direction between the starting point of two consecutive tiles

    Output
    Return sliced tiles array in a list
    '''
    slices = []
    tile_height, tile_width = tile_size
    step_height, step_width = step_size

    # for scene in scene:
    height, width = scene.shape[:2]
    
    if len(scene.shape) == 3:
        channels = scene.shape[2]
    else:
        channels = 1
    # height, width, channels = scene.shape
    for y in range(0, height, step_height):
        for x in range(0, width, step_width):
            if y + tile_height > height or x + tile_width > width:
                # Calculate the required padding
                pad_height = max(0, y + tile_height - height)
                pad_width = max(0, x + tile_width - width)
                
                # Pad the slice with zeros
                if channels == 1:
                    slice = np.pad(scene[y:, x:], ((0, pad_height), (0, pad_width)), mode='constant')
                else:
                    slice = np.pad(scene[y:, x:, :], ((0, pad_height), (0, pad_width), (0, 0)), mode='constant')
                # Crop the slice to the specified tile size
                slice = slice[:tile_height, :tile_width]
            else:
                if channels == 1:
                    slice = scene[y:y+tile_height, x:x+tile_width]
                else:
                    slice = scene[y:y+tile_height, x:x+tile_width, :]
            slices.append(slice)

    return slices

## Execution
file_extension = pathlib.Path(img_path).suffix
if file_extension == '.tif' or file_extension == '.tiff':
    array = gtiff_to_array(img_path) # to read tiff
else:
    array = read_img(img_path) # to read jpeg/png
tiles = slice_scene(array, tile_size, step_size)