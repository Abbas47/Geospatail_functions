## Import libraries
import  numpy as np
from math import floor 
from PIL import Image
from numpy import asarray

# Function
def stitch_tiles(tiles, scene_size, tile_size, step_size, dtype, data_type=None):
    '''
    This function blends the small tiles back into one big image.

    Arguments:
    1. tiles: List of small tiles.
    2. scene_size: Size of the original scene.
    3. tile_size: Size of each tile.
    4. step_size: Step size used for tiling.
    5. dtype: Define the dtype of the numpy array/original tiff
    6. data_type: Define mask as a string element if the image mask needs to be stitched back. For example: data_type = 'mask'

    Returns:
    1. The blended image.
    '''
    
    tiles = np.asarray(np.round(tiles), dtype=np.uint8)
    if data_type == 'mask':
        height, width = scene_size
    else:
        height, width, band = scene_size
    
    tile_height, tile_width = tile_size
    step_height, step_width = step_size

    num_rows = height/tile_height
    num_cols = width/tile_width
    flag_row = isinstance(num_rows, float)
    flag_col = isinstance(num_cols, float)
    if flag_row:
        int_row = floor(num_rows)
        num_rows = round(int_row + 1)
    if flag_col:
        int_col = floor(num_cols)
        num_cols = round(int_col + 1)
    
    if data_type == 'mask':
        blended_image = np.zeros((num_rows*tile_height, num_cols*tile_width), dtype)
    else:
        blended_image = np.zeros((num_rows*tile_height, num_cols*tile_width, band), dtype)

    index = 0
    for row in range(num_rows):
        for col in range(num_cols):
            y = row * step_height
            x = col * step_width
            slice_image = tiles[index]
            if data_type == 'mask':
                blended_image[y:y+tile_height, x:x+tile_width] = slice_image
            else:
                blended_image[y:y+tile_height, x:x+tile_width, :] = slice_image
            index += 1

    return blended_image