#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Thu Nov 26 12:33:27 2020

@author: inderpreet
"""

from pyhdf.SD import SD, SDC
import os
from datetime import datetime, timedelta
import numpy as np
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

class DARDARProduct():
    """
    The DARDARProduct class defines an interface to read DARDAR profiles
    
    """    
    
    def __init__(self, filename, latlims = None):
        """
        Opens the dardar hdf4 dataset

        Parameters
        ----------
        filename  (str): input DARDAR file
        latlims (None, list)= None, global data is returned; 
                [lat1, lat2], list containing lower and upper limits of
        latitude values used to subset DARDAR pass


        """
        self.filename = filename
#        file_name = 'MYD06_L2.A2007219.2010.006.2014053202546.hdf'
        self.file = SD(self.filename, SDC.READ)
        
        datasets_dic = self.file.datasets()

# list of SDS variables
        self.SDS = datasets_dic.keys()
        
        if latlims is not None:                
            self.latlims = latlims
      
    def get_data(self, variable):
        """
        get the data for the selected variable
        complete list of SDS variables is also contained in self.SDS

        Parameters
        ----------
        variable : Input SDS variable,

        Returns
        -------
        ndarray containing the input SDS variable

        """
        if variable not in self.SDS:
            raise Exception("'Valid SDS should be one of ", self.SDS) 
            
        sds_obj = self.file.select(variable) # select sds

        data = sds_obj.get() # get sds data    
            
        if self.latlims is not None:
            # subsetting  data   
            if variable != "height":
                lat1, lat2 = self.latlims
                lat  = self.file.select('latitude').get()
                
                inds = np.where((lat >= lat1) & (lat <= lat2))
                
                data = data[inds]   
                
        return data
    
   
    def filename2date(self):
        """
        extracts time stamp from dardar filename

        Returns
        -------
        datetime object with the time stamp of DARDAR data
        """
        
        filename = os.path.basename(self.filename)
        filename = filename.split("_")[2]
        pattern = "%Y%j%H%M%S"
        return datetime.strptime(filename, pattern)
        
    
    def match_era5(self, variable):
        """
        gives the nearest temporal neighbour of DARDAR data

        Parameters
        ----------
        variable : the geophysical parameter to be downloaded
        for example, temperature, 
        Returns
        -------
        era5_filename : string of nearest collocated ERA5 filename
        """

        
        t_dardar = self.filename_to_date()
        
        if t_dardar.minute > 30:
            t_dardar += timedelta(hours = 1)
        
        year  = t_dardar.year
        month = f"{t_dardar.month:02d}"
        day   = f"{t_dardar.day:02d}"
        hour  = f"{t_dardar.hour:02d}"      

            
        era5_filename = (
            "reanalysis-era5-pressure-levels_" + str(year) + str(month) 
            + str(day) + str(hour) + "_"  + variable + '.nc')
            
        return era5_filename    
    
    
    def plot_overpass(self):
        """
        plots the overpass of DARDAR

        Returns
        -------
        None.

        """
        plt.figure(figsize=(12, 6))
        m = Basemap(llcrnrlon=0.,llcrnrlat=-85.,urcrnrlon=360.,urcrnrlat=85.,\
                      rsphere=(6378137.00,6356752.3142),\
                      resolution='c',projection='cyl')
        m.shadedrelief(scale = 0.1)
        
        lon_d = self.get_data("longitude")
        lat_d = self.get_data("latitude")
        lon_d = lon_d % 360
        m.scatter(lon_d[:],lat_d[:], latlon = True)
        plt.savefig('dardar_pass.png', bbox_inches = 'tight')
        plt.show()
        