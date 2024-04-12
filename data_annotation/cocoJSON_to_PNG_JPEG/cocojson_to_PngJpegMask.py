'''
To run this script user needs to make changes under "## User input" block only (block 3).
1. "# input for path"
    a. "annFile": define the cocoJSON annotation file path
    
Note: the final jpeg mask will be create in the same directory where the cocoJSON is saved.
'''

## Import libraries
from pycocotools.coco import COCO
import numpy as np
import cv2

### For visualizing the outputs ###
import matplotlib.pyplot as plt
from matplotlib import image
get_ipython().run_line_magic('matplotlib', 'inline')

## User input
# input for path
annFile='/home/indian/annotation/27-june-20230627T142741Z-001/27-june/train/annotations.json'

## Function
def getClassName(classID, cats):
    '''
    Function to get the class name using classID
    Input parameteres:
    1. classID: Define the classID to get the name of the class
    2. cats: provide the dictionary with classID as key and class name as value
    '''
    for i in range(len(cats)):
        if cats[i]['id']==classID:
            return cats[i]['name']
    return "None"

# Initialize the COCO api for instance annotations
coco=COCO(annFile)

# Load the categories in a variable
catIDs = coco.getCatIds()
cats = coco.loadCats(catIDs)

print(cats)
print('The class name is', getClassName(77, cats))

## GENERATE A SEGMENTATION MASK

# Define the classes out of annoated classes which you want to use to create a mask.
filterClasses = ['building', 'car', 'lawn', 'monument', 'open-ground', 'pound', 'road', 'ship', 'tree', 'water']

imgIds = coco.getImgIds()
# Fetch class IDs only corresponding to the filterClasses
catIds = coco.getCatIds(catNms=filterClasses)
# Define the image index from the imgIds list
img = coco.loadImgs(imgIds[0])[0]
annIds = coco.getAnnIds(imgIds=img['id'], catIds=catIds, iscrowd=None)
anns = coco.loadAnns(annIds)
# Define np zero array using heigth and width of the image
mask = np.zeros((img['height'],img['width']))

# Plot the mask with define classes
for i in range(len(anns)):
    className = getClassName(anns[i]['category_id'], cats)
    pixel_value = filterClasses.index(className)+1
    mask_segmentation = np.maximum(coco.annToMask(anns[i])*pixel_value, mask)
plt.imshow(mask)

# save mask
cv2.imwrite(img['file_name'].replace('.jpg', '_mask.png'), mask_segmentation)
# image.imsave(img['file_name'].replace('.jpg', '_mask.jpg'), mask_segmentation)

## GENERATE A BINARY MASK

# Plot the mask with binary classes
for i in range(len(anns)):
    mask_binary = np.maximum(coco.annToMask(anns[i]), mask)
plt.imshow(mask)

# save mask
image.imsave(img['file_name'].replace('.jpg', '_binarymask.jpg'), mask_binary)
# image.imsave(img['file_name'].replace('.jpg', '_mask.jpg'), mask_binary)

