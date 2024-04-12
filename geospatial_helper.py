# import libraries
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
try:
    from osgeo import gdal
except:
    import gdal
import rasterio.warp
from rasterio.crs import CRS
from shapely.geometry import box
from rasterio.warp import calculate_default_transform, reproject, Resampling


# function to convert coordinate from degree minute second to decimal degree
def dms_to_dd(d, m, s):
    dd = d + float(m)/60 + float(s)/3600
    return dd


# function to create csv to shp
# input csv path, output path, cooordinate system in epsg, and column name of longitude(x) & latitude(y) in csv file.
def create_shp(csv_path, output_path, dst_crs, longitude, latitude):
    read_csv = pd.read_csv(csv_path)
    shp = gpd.GeoDataFrame(read_csv, geometry=gpd.points_from_xy(read_csv[longitude], read_csv[latitude]), crs=dst_crs)
    shp.to_file(output_path)


# function to create buffer around the points
# input shapefile path, buffer shape in int, output path, and buffer radius in meters
# buffer shape: round = 1, flat = 2, square = 3
def buffer(shp_path, buffer_shp, output_path, buffer_radius, dst_crs):
    shp = gpd.read_file(shp_path)
    if shp.crs != 32640:
        shp = shp.to_crs(epsg=32640)
    else:
        pass
    shp['geometry'] = shp.buffer(buffer_radius, cap_style=buffer_shp)
    shp = shp.to_crs(epsg=dst_crs)
    print(shp.crs)
    shp.to_file(output_path)


def scale_image(raster, filename, base_path, file_path):
    #translate to 8 bit

    # reading every band as array and sorting the vaue at 2nd and 98th percentile
    no_bands =[count+1 for count in range(raster.RasterCount)]

    p2_dict = {}
    p98_dict = {}

    for i in no_bands: 
        band = raster.GetRasterBand(i)
        rasterArray = band.ReadAsArray()
        nodata = band.GetNoDataValue()
        array = np.ma.masked_equal(rasterArray, nodata)
        narray = rasterArray[rasterArray != nodata]  # remove nodata value from array
        p2 = np.percentile(narray, 2)
        p98 = np.percentile(narray, 98)
        p2_dict[i] = round(p2)
        p98_dict[i] = round(p98)

    # creating command line for gdal translate option
    string_ = ""
    for i in no_bands:
        test =  f"-b {i} -scale_{i} {p2_dict[i]} {p98_dict[i]} 0 255"
        string_ = string_ +" "+ test
    command_line = "-of GTiff"+string_+" -a_nodata none -ot Byte"

    file_id = filename.replace(".tif","")
    temp_file_id = file_id+"_scaled.tif"
    converted_imagery_path = base_path+"/"+temp_file_id
    # translate image into 8 bit
    translateoptions = gdal.TranslateOptions(gdal.ParseCommandLine(command_line))
    ds  = gdal.Translate(converted_imagery_path, file_path, options=translateoptions)
    ds = None
    return converted_imagery_path


def GetExtent(ds, src_crs, dst_crs):
    """ Return list of corner coordinates to desired CRS """
    feature_proj = rasterio.warp.transform_geom(
        src_crs,
        dst_crs,
        box(*ds.bounds))
    
    ymax, xmax = feature_proj['coordinates'][0][1]
    ymin, xmin = feature_proj['coordinates'][0][3]
    return xmin, ymin, xmax, ymax


#function to reproject the raster into desired coordinate system using nearest neighbour resampling method
# input raster path, output raster path, and coordinate system in which the raster needs to be reprojected in EPSG
def reproject_raster(dst_crs, raster_path, output_path):
    with rasterio.open(raster_path) as src:
        transform, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        
        with rasterio.open(output_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)


def validate_image(filename):
    """
    Takes the filename of the uploaded image and checks 
    for file format, spatial reference and number of bands. 
    If all the checks are passed, returns 0 with other params.
    Otherwise returns a differet code for different errors. """
    band_list = {}
    band_list["bands"]=[]

    base_path = os.path.join(os.getcwd(),'media')
    file_path = base_path+"/"+filename   

    if filename.lower().endswith('tif'):
        srcRst = rio.open(file_path)
        epsg_flag = False
        bands_flag = False
        temp_flag = False
        srcCrs = srcRst.crs
        geotransform = srcRst.transform

        if srcCrs != None:
            epsg_flag = True

            array = srcRst.read()
            if array.dtype != 'uint8':
                return (filename, 3, band_list) # band_list will be empty
            
            resolution = geotransform[0]

            pixel_area = resolution**2
            pixels_x = srcRst.width
            pixels_y = srcRst.height

            #pixel area times number of pixels
            area = (pixel_area * pixels_x * pixels_y * 1e-6)

            if srcCrs != 4326:
                temp_flag = True
                temp_file_name = filename.split('.')[0]+'_wgs.tif'
                dst_file_path = base_path+'/'+temp_file_name
                dstCrs = 'EPSG:4326'
                
                x = reprojectRaster(srcRst, dstCrs, dst_file_path)
                
            
            band_count = srcRst.count
            
            if band_count >= 3:
                for i in range(band_count):
                    band_list["bands"].append("b"+str(i+1))
                    
                transformed_extent = GetExtent(srcRst, srcCrs, x)
                img_extent = {'x_min':transformed_extent[0],'y_min':transformed_extent[1],'x_max':transformed_extent[2],'y_max':transformed_extent[3]}
                srcRaster = None
                
                if temp_flag:
                    # return (temp_file_name, 0)
                    return (temp_file_name, 0, band_list,img_extent,resolution, area, band_count)
                else:
                    return (filename, 0, band_list,img_extent,resolution, area, band_count)
            else:            
                return (filename, 1, band_list)
        else:
            return (filename, 2, band_list)
    else:
        return (filename, -1, band_list)


# function to extract the raster value using polygon
# input shapefile path, raster path, output shapefile path, and band number from whihc the value have to be extracted
def extract_polygonvalue(raster_path, shp_path, output_shp, band):
    polyData = gpd.read_file(shp_path)
    src = rasterio.open(raster_path)
    if polyData.crs != src.crs:
        print('Raster and shapefile are not in the same projection coordinate')
    else: 
        affine = src.transform
        array = src.read(band)
        df_zonal_stats = pd.DataFrame(zonal_stats(polyData, array, affine=affine, stats=['min', 'max', 'mean', 'median', 'std', 'majority']))
        
        # adding statistics back to original GeoDataFrame
        polyData = pd.concat([polyData, df_zonal_stats], axis=1)
        polyData.dropna(subset=['min'])
        polyData.to_file(output_shp)
        pointData.drop([index], axis=0, inplace=True)


# function is to normalize the value of raster
# input raster ptah, and output path
def normalize_band(raster_path, output_path):
    src = rasterio.open(raster_path)
    raster = src.read(1)
    
    #### check null value in raster!!!!!!!!!!!
    
    # normalize raster
    normalize = (raster - raster.min()) / (raster.max() - raster.min())
    kwargs = src.meta.copy()
    kwargs.update(
        dtype=rasterio.float32)
    with rasterio.open(output_path, 'w', **kwargs) as dst:
        dst.write_band(1, normalize)
    src = None
    

# function to extract single band from multispectral band imagery
# input raster path, output raster path, cooordinate sysytem of raster, and band number which needs to be extracted 
def extract_band(raster_path, output_path, band, src_crs):
    command_line = f'-a_srs {src_crs} -of GTiff -b {band}'
    translateoptions = gdal.TranslateOptions(gdal.ParseCommandLine(command_line))
    ds  = gdal.Translate(output_path, raster_path, options=translateoptions)
    ds = None


# function to read the raster and return one band array and metadata
# input raster path and the band which need to be read
def raster(path, band):
    src = rasterio.open(path)
    array = src.read(band)
    meta_data = src.meta
    return array, meta_data


# function convert image into pandas dataframe
def image_to_pandas(image):
    df = pd.DataFrame([image[:,:,0].flatten(),
                       image[:,:,1].flatten(),
                       image[:,:,2].flatten()]).T
    df.columns = ['Red_Channel','Green_Channel','Blue_Channel']
    return df

