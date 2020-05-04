
'''
DESCRIPTION
  Objective: Funcoes para Recortar um tif, Normalizar, Padronizar e Transformar um Raster pra um tif de pontos. 
  Requisites: Diretorio com rasters e 1 shapefile (para recorte)
  
  Developer: Laiza Cavalcante de Albuquerque Silva
  Period: Msc. Engineering Agriculture (2018-2020)
            (Geoprocessing + Remote Sensing + Agriculture)

'''

###############################################
# Importing packages
###############################################

import os
import fiona
import rasterio
import numpy as np
import pandas as pd
import geopandas as gp
import rasterio.mask
from matplotlib import pyplot as plt
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.geometry import MultiPolygon, Point
import shapely as sly
from tqdm import tqdm

#incluir a funcao raster to shp (sem ser por pontos)

class Raster_operations():
    def __init__(self, img_directory, shp_directory_crop):
        self.__imgdir = img_directory
        self.__shpdir = shp_directory_crop

    def clip_raster_by_shp(self):
        '''
        ### Clip a raster
            Inform raster path and shapefile path
            It will clip the raster using shp bondaries.
            Please, check if all of them has the same extent
        '''
        # Loading the shapefile
        with fiona.open(self.__shpdir, 'r') as shp:
            print('Shape info \n', shp.schema)
            features = [feature['geometry'] for feature in shp]
 
        # Loading raster
        with rasterio.open(self.__imgdirdir, 'r+') as tif:
            tif.nodata = np.nan
            #  Cropping it using a rasterio mask
            out_image, out_transform = rasterio.mask.mask(tif, features, crop=True, nodata=np.nan)
            
            # Updating profile information
            out_meta = tif.meta.copy()
            print(out_meta)
            # print('Before changes \n', out_meta)
            out_meta.update({'driver': 'GTiff',
                            'height': out_image.shape[1],
                            'width': out_image.shape[2],
                            'transform': out_transform,
                            'compress': 'lzw'
                            })   

            # Creating a new name for raster
            output = self.__imgdirdir[:-4] + '_C.tif'

            # Creating new file to save clipped tif
            with rasterio.open(output, 'w', **out_meta) as dest:
                dest.write(out_image) 
        
        return out_image

    def raster_nan_corret(self):
        '''
        ### Nodata handling
            Correcting abscence of nodata in raster
            Inform a raster 
            Ex: If nodata is -3.999e-10 will be replaced by np.nan
        '''
        with rasterio.open(self.__imgdirdir) as tif:
            image = tif.read(1) 
            profile = tif.meta.copy()
            profile.update({'nodata': np.nan})

            # Check if exist nodata
            if np.isnan(np.sum(image)) == True:
                pass
            else:
                # Using 1st value as nodata value
                wrong_nodata = image[0][0]
                # Replacing it by np.nan
                image[np.where( image==wrong_nodata)] = np.nan
            
        # Saving
        output = self.__imgdirdir[:-4] + '_Cor.tif'
        with rasterio.open(output, 'w', **profile) as tif2:
            tif2.write(image, 1 )

        return image

    def raster_normalize(self):
        '''
        ### Raster Normalization by mean and std
            Inform a raster to apply normalization
        '''
        with rasterio.open(self.__imgdirdir, 'r+') as tif:
            image = tif.read(1) 
            profile = tif.meta.copy()
            profile.update({'nodata': np.nan})

            # Check if exist nodata
            if np.isnan(np.sum(image)) != True:
                # Using 1st value as nodata value and replacing by np.nan
                wrong_nodata = image[0][0]
                image[np.where(image == wrong_nodata)] = np.nan

            # Getting info to compute Normalization
            mean_ = np.nanmean(image)
            std_ = np.nanstd(image)
            normalized = (image-mean_)/std_

        # Saving
        output = self.__imgdirdir[:-4] + '_Normalized.tif'
        with rasterio.open(output, 'w', **profile) as tif2:
            tif2.write(normalized, 1 )
        
        return normalized

    def raster_standartize (self):
        '''
        ### Raster Standartize by min and max
            Inform a raster to statndartize
        '''
        with rasterio.open(self.__imgdirdir) as tif:
            new_tif = tif.read(1) 
            profile = tif.profile.copy()
            profile.update({'nodata': np.nan})

            # Check if exist nodata
            if np.isnan(np.sum(new_tif)) != True:
                # Using 1st value as nodata value and replacing by np.nan
                wrong_nodata = new_tif[0][0]
                new_tif[np.where( new_tif==wrong_nodata)] = np.nan

            # Getting info to compute  Standartize
            max_ = np.nanmax(new_tif)
            min_ = np.nanmin(new_tif)

            pradonizado = (new_tif-min_)/(max_ - min_)

        # Saving
        output = self.__imgdirdir[:-4] + '_Stand.tif'
        with rasterio.open(output, 'w', **profile) as tif2:
            tif2.write(pradonizado, 1 )

        return pradonizado

    def raster_to_shp_points(self):
        '''
        ### Transform a raster to shapefile points
            Inform a raster path to write a new shapefile
            by the pixel centroid
        '''
        # Loading raster
        with rasterio.open(self.__imgdirdir) as tif:
            image = tif.read(1)  
            transform = tif.transform
            epsg = tif.profile['crs']

            # Check if exist nodata
            if np.isnan(np.sum(image)) != True:
            # Using 1st value as nodata value
                wrong_nodata = image[0][0]
                # Replacing it by np.nan
                image[np.where( image==wrong_nodata)] = np.nan
       
        # Getting XY position and values from raster
        points = []
        for (i, j), value in np.ndenumerate(image):           
            # Skip nan values to only compute the study area
            if np.isnan(value) != True:

                # Getting pixel centroid
                x, y = transform * (j + 0.5, i + 0.5)
                
                # Saving into a tuple (why not a dictionary?)
                point = (x, y, value)
                points.append(point)

        # Reading tuple as a pandas DataFrame
        df = pd.DataFrame(points, columns=['X', 'Y', 'value'])
        
        # Creating a Geometry and dropping X, Y columns
        geometry = [Point(xy) for xy in zip(df.X, df.Y,)]
        df = df.drop(['X', 'Y'], axis=1)

        # Creating a geodataframe and saving it
        gdf_ = gp.GeoDataFrame(df, crs={'init' : str(epsg)}, geometry=geometry)

        # Exporting shapefile
        out_shp = self.__imgdirdir[:-4] + '.shp'
        gdf_.to_file(out_shp )

        return gdf_

    # if __name__ == "__main__":
    #     main()


class Shape_operations():

    def __init__(self, pathshp1, pathshp2):
        self.__path_shp1 = pathshp1
        self.__path_shp2 = pathshp2

    def clip_shapes(self):
        '''
        ### Compute intersection operation (as in GeoPandas/QGIS)
            Return a new shapefile from common areas in two shapes
            Require two shapefiles
        '''
        # Reading shapefiles
        shp1 = gp.read_file(self.__path_shp1 )
        shp2 = gp.read_file(self.__path_shp2)

        # Check crs
        crs1, crs2 = shp1.crs, shp2.crs
        if crs1 == crs2:
            # Clipping shapefiles
            result = gp.overlay(shp1, shp2, how='intersection')
            result = result.drop('DN', axis=1)

            # Saving shapefile
            output_name = self.__path_shp1 [:-4] + '_rec10m.shp'
            result.to_file(self.__path_shp1 + output_name)

            info_newshp = dict( {'columns names': result.columns,
                                'shp1 extent': shp1.total_bounds,
                                'shp2 extent': shp2.total_bounds,
                                'final extent': result.total_bounds} )
        
        else:
            print('Shapefiles with different EPSG')

        return info_newshp

    def crs_change(self, epsg):
        '''
        ### Change shapefile EPSG
            Require one shapefile path and the desired EPSG
        '''
        # Reading shapefile
        shp1 = gp.read_file(self.__path_shp1 )
        
        # Changing EPSG
        shp1.crs = {'init': str(epsg)}

        # Saving
        output_name = self.__path_shp1 [:-4] +  str(epsg) + '.shp'
        shp1.to_file(output_name)

    # if __name__ == "__main__":
    #     main()
  

class UAV_funcs():

    def __init__(self, img_directory):
        self.__imgdir = img_directory
        # self.__shpdir = shp_directory

    def band_normalized_t1(self):
        '''
        ### Execute band normalization
            Require a raster with 3 bands (R,G,B) 
            The outpu will be a raster per band divided by sum of them
        '''
        with rasterio.open(self.__imgdir, 'r+') as tif:

            # Reading profile and Setting nan values
            tif.nodata = np.nan
            profile = tif.meta.copy() 
            profile.update({'count': 1, 'compress': 'lzw', 'dtype': 'float32', 'Nodata': np.nan})

            # Checking bands:
            band_info = tif.indexes

            # Creating names for output
            outputR = self.__imgdir[:-4] +  '_R_N.tif'
            outputG = self.__imgdir[:-4] +  '_G_N.tif'
            outputB = self.__imgdir[:-4] +  '_B_N.tif'

            # Reading raster by tiles (raster windows)
            # tiles = tif.block_windows(1)
            for band in band_info:
                if band == 1:
                    with rasterio.open(outputR, 'w', **profile) as dst:
                        tiles = tif.block_windows(1)

                        for idx, window in tqdm(tiles):   
                            band_R = tif.read(1, window=window, masked=True).astype('float32')             
                            band_G = tif.read(2, window=window, masked=True).astype('float32')
                            band_B = tif.read(3, window=window, masked=True).astype('float32')
                
                            # Como resolver o problema do 0?
                            imgR = band_R / (band_R + band_G + band_B)
                            dst.write_band(1, imgR, window=window)

                elif band == 2:
                    tiles = tif.block_windows(1)
                    
                    with rasterio.open(outputG, 'w', **profile) as dst:
                        for idx, window in tqdm(tiles):
                            band_R = tif.read(1, window=window, masked=True).astype('float32')             
                            band_G = tif.read(2, window=window, masked=True).astype('float32')
                            band_B = tif.read(3, window=window, masked=True).astype('float32')
                            imgG = band_G / (band_R + band_G + band_B) 
                            dst.write_band(1, imgG, window=window)

                if band == 3:
                    tiles = tif.block_windows(1)

                    with rasterio.open(outputB, 'w', **profile) as dst:
                        for idx, window in tqdm(tiles):   
                            band_R = tif.read(1, window=window, masked=True).astype('float32')             
                            band_G = tif.read(2, window=window, masked=True).astype('float32')
                            band_B = tif.read(3, window=window, masked=True).astype('float32')
                            imgB = band_B / (band_R + band_G + band_B) 
                            dst.write_band(1, imgB, window=window)

        return imgR, imgG, imgB           

    def band_normalized_t2(self):
        '''
        ### Execute band normalization
            Require a raster with 3 bands (R,G,B) 
            The output will be ONE RASTER with each band divided by sum of them
        '''

        with rasterio.open(self.__imgdir, 'r+') as tif:

            # Reading profile and Setting nan values
            tif.nodata = np.nan
            profile = tif.meta.copy() 
            profile.update({'compress': 'lzw', 'dtype': 'float32', 'Nodata': np.nan})

            # Checking bands:
            band_info = tif.indexes

            # Creating names for output
            output = self.__imgdir[:-4] +  '_N_.tif'

            # Reading raster by tiles (raster windows)
            tiles = tif.block_windows(1)

            with rasterio.open(output, 'w', **profile) as dst:

                for idx, window in tqdm(tiles):   
                    band_R = tif.read(1, window=window, masked=True).astype('float32')             
                    band_G = tif.read(2, window=window, masked=True).astype('float32')
                    band_B = tif.read(3, window=window, masked=True).astype('float32')
        
                    imgR = band_R / (band_R + band_G + band_B)
                    imgG = band_G / (band_R + band_G + band_B)
                    imgB = band_B / (band_R + band_G + band_B)
                    result = np.array([imgR, imgG, imgB])

                    dst.write(result, window=window)


# #%%
# rast_dir = r'D:\liz_tifs\rgb.tif'
# shp_dir = 'C:/Users/liz/Pictures/Saved Pictures/Cultivar_BRS1003IPRO_31982_rec10.shp'
# rast_class = UAV_funcs(rast_dir)
# rast_class.band_normalized_t2()


