#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 09:18:07 2020

class to convert ERA5 data to DARDAR grid


@author: inderpreet

"""

import numpy as np
from era2dardar.ERA5 import ERA5p, ERA5s
from era2dardar.utils.alt2pressure import alt2pres
import typhon.physics.thermodynamics as thermodynamics 
from typhon.topography import SRTM30
from typhon import constants
from era2dardar.utils.scale_vmr import scale_vmr
from scipy import interpolate
from era2dardar.utils.convert_lon import shift_lon


class atmdata():
    """
    Class atmdata  which interpolates ERA5 data to DARDAR/Cloudsat grids;
    inputs are dardar/cloudsat class object and the pressure grid over 
    which values are to be interpolated
    The returned outputs for each are in ARTS grid format and 
    can be saved to xml using typhon xml functions
    """
    

    def __init__(self, dardar, p_grid = None):
        """
        
        Parameters
        ----------
        dardar : a DARDAR class instance
        p_grid : np.array, the pressure grid over which ERA5 
        is to be interpolated. Units are in [Pa]
        If None, then the ERA5 grid is used [hard coded right now]       

        Returns
        -------
        None.

        """        

        self.dardar  = dardar
        self.p_grid  = p_grid
 
       
        if p_grid is None:
            
            # use ERA5 pressure grid
            self.p_grid = np.array([   1,    2,    3,    5,    7,   10,   20,   30,   50,   70,  100,
        125,  150,  175,  200,  225,  250,  300,  350,  400,  450,  500,
        550,  600,  650,  700,  750,  775,  800,  825,  850,  875,  900,
        925,  950,  975, 1000, 1150]) * 100 # [Pa]
            


    @property    
    def t_0(self):
        """
        the start time of DARDAR pass

        Returns
        -------
        a datetime object containing the time of DARDAR pass
        """
        return self.dardar.t_0
    
    @property
    def t_1(self):
        """
        the end time of DARDAR pass

        Returns
        -------
        a datetime object containing the end time of DARDAR pass
        """
        return self.dardar.t_1
    
    @property
    def lon(self):
        """
        longitudes

        Returns
        -------
        np.array containing the longitudes defining the DARDAR scene
        the longitudes are shifted to range [-180, 180] or [0, 360]
        depending on the range which avoids the discontinuity
        """
        longitude = self.dardar.longitude
        longitude = shift_lon(longitude)
        
        return longitude
    
    @property
    def lat(self):
        """
        latitudes

        Returns
        -------
        np.array containing the latitudes defining the DARDAR scene
        """
        return self.dardar.latitude  
        
    @property    
    def temperature(self):
        """
        interpolated ERA5 temperature fields to DARDAR grid and pressure grid
        defined in self.p_grid

        Returns
        -------
        grid_t : np.array containing the interpolated values
        dimensions [p, lat, lon]

        """

        p           = self.p_grid        
        var         = "temperature"
        ERA_t       = ERA5p(self.t_0, self.t_1, var)
        grid_t      = ERA_t.interpolate(self.dardar, p* 0.01)
        grid_t      = np.expand_dims(grid_t, 2)
        
        return grid_t
    
    @property    
    def clwc(self):
        """
        interpolated ERA5 CLWC fields to DARDAR grid and pressure grid
        defined in self.p_grid

        Returns
        -------
        grid_lwc : np.array containing the interpolated values
        dimensions [1, p, lat, lon]

        """
        
        p           = self.p_grid   
            
        var         = "specific_cloud_liquid_water_content"
        ERA_lwc     = ERA5p(self.t_0, self.t_1, var)
        grid_lwc    = ERA_lwc.interpolate(self.dardar, p * 0.01)
        
        grid_p      = np.tile(p, (grid_lwc.shape[1], 1))
        grid_p      = grid_p.T 
        A           = np.squeeze(self.temperature)
        rho         = thermodynamics.density(grid_p, A) #air density
        grid_lwc    = grid_lwc * rho  #convert lwc units to mass concentration
        
        grid_lwc    = np.expand_dims(grid_lwc, axis = (0, 3))
        
        return grid_lwc
    
    @property
    def abs_species(self):  
        """        
        The absorption species are simply stored as a list of strings

        Returns
        -------
        String containing the names of absorption species

        """        

        abs_species   = ["N2","O2","H2O","LWC"]
        
        return abs_species

    @property
    def z_surface(self):
        """
        z_surface fields interpolated to DARDAR grid.
        The values are interpolated using topography module in typhon
        uses SRTM30 near-global digital elevation model (DEM) 

        Returns
        -------
        z_surface : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        
        #  z-surface, from typhon.topography
        lat_d         = self.dardar.get_data("latitude")
        lon_d         = self.dardar.get_data("longitude")
        z_surface     = SRTM30.interpolate(lat_d, lon_d)
        
        z_surface     = np.expand_dims(z_surface, axis = 1)
        
        return z_surface

    @property    
    def z_field(self):
        """
        interpolated ERA5 geopotential heights fields to DARDAR grid
        and pressure grid defined in self.p_grid

        Returns
        -------
        grid_z : np.array containing the interpolated values
        dimensions [p, lat, lon]

        """
        g           = constants.g
        p           = self.p_grid        
        var         = "geopotential"
        ERA_t       = ERA5p(self.t_0, self.t_1, var)
        grid_t      = ERA_t.interpolate(self.dardar, p* 0.01)
        grid_t      = np.expand_dims(grid_t, 2) / g #[convert geopot. to alt]
        
        return grid_t
    
    @property
    def skin_temperature(self):
        """
        ERA5 skin temperature fields interpolated to DARDAR grid.
       
        Returns
        -------
        grid_skt : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        var           = "skin_temperature"
        ERA_skt       = ERA5s(self.t_0, self.t_1, var)
        grid_skt      = ERA_skt.interpolate(self.dardar)
        grid_skt      = np.expand_dims(grid_skt, axis = 1)
        
        return grid_skt

    @property
    def t2m(self):
        """
        ERA5 2m temperature fields interpolated to DARDAR grid.
       
        Returns
        -------
        grid_t2m : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        var           = "2m_temperature"
        ERA_t2        = ERA5s(self.t_0, self.t_1, var)
        grid_t2m       = ERA_t2.interpolate(self.dardar)
        grid_t2m      = np.expand_dims(grid_t2m, axis = 1)
        
        return grid_t2m

    @property
    def wind_speed(self):
        """
        ERA5 10m u and v fields interpolated to DARDAR grid.
        The wind speed is calculated from u and v vectors
       
        Returns
        -------
        wind_speed : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        # u 10m 
        var           = "10m_u_component_of_wind"
        ERA_u         = ERA5s(self.t_0, self.t_1, var)
        grid_u        = ERA_u.interpolate(self.dardar)
        
        # v 10 m 
        var           = "10m_v_component_of_wind"
        ERA_v         = ERA5s(self.t_0, self.t_1, var)
        grid_v        = ERA_v.interpolate(self.dardar)
        
        # convert to wind speed
        wind_speed    = np.sqrt(grid_u**2 + grid_v**2)
        wind_speed    = np.expand_dims(wind_speed, axis = 1)
        
        return wind_speed
    
    @property    
    def wind_direction(self):
        """
        ERA5 10m u and v fields interpolated to DARDAR grid.
        The wind speed is calculated from u and v vectors
       
        Returns
        -------
        wind_direction : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        
        # u 10m 
        var           = "10m_u_component_of_wind"
        ERA_u         = ERA5s(self.t_0, self.t_1, var)
        grid_u        = ERA_u.interpolate(self.dardar)
        
        # v 10 m 
        var           = "10m_v_component_of_wind"
        ERA_v         = ERA5s(self.t_0, self.t_1, var)
        grid_v        = ERA_v.interpolate(self.dardar)
        
        # convert to wind direction
        wind_dir      = np.arctan2(grid_u, grid_v) * 180 / np.pi  # degree
        
        wind_dir    = np.expand_dims(wind_dir, axis = 1)
        
        return wind_dir
    
    @property
    def vmr_h2o(self):   
        """
        interpolated ERA5 VMR fields to DARDAR grid and pressure grid
        defined in self.p_grid
        
        VMR is calculated using specific humidity. The conversion is simply
        
        vmr = Q/1-Q
        
        The VMR is firstly calculated on ERA5 pressure grid and later 
        interpolated to desired log(p_grid) as log(vmr)
        
        The code for conversion of relative humidity is commented. 
        The RH2VMR conversion assumes the defintions of hydrostatic
        equilibrium from IFS

        Returns
        -------
        grid_q2vmr : np.array containing the interpolated values
        dimensions [1, p, lat, lon]

        """
        
        p                 = self.p_grid   
        
        # var             = "relative_humidity"
        # ERA_r           = ERA5p(t_0, t_1, var)  # loads ERA5 data as xarray 
        # grid_r          = ERA_r.interpolate(dardar, p_grid = None) 
        
        # if np.any(grid_r < 0):
        #     print ("encountered negative values")
         
        # temperature
            
        # p_grid          = ERA_q.era["level"].data * 100 # Pa
        # grid_p          = np.tile(p_grid, (grid_t.shape[1], 1))
        # grid_p          = grid_p.T 
        # r2vmr           = rh2vmr(grid_p , grid_t, grid_r)
        
        
#        grid_t          = self.temperature(p_grid = None)
            
#       interpolate log(vmr) as a function of log(p)
        
        # f_r             =  interpolate.interp1d(np.log(p_grid), np.log(r2vmr), axis = 0 )
        # grid_r2vmr      =  np.exp(f_r(np.log(p)))
        
        var             = "specific_humidity"
        ERA_q           = ERA5p(self.t_0, self.t_1, var)
        grid_q          = ERA_q.interpolate(self.dardar, p_grid = None)
        q2vmr           = thermodynamics.specific_humidity2vmr(grid_q)    
        p_era           = ERA_q.era["level"].data * 100 # Pa

#       interpolate log(vmr) as a function of log(p)     
            
        f_q             =  interpolate.interp1d(np.log(p_era), np.log(q2vmr), axis = 0 )
        grid_q2vmr      =  np.exp(f_q(np.log(p)))
        
        grid_q2vmr      = np.expand_dims(grid_q2vmr, axis = (0, 3))
        
        return grid_q2vmr
    
    @property
    def vmr_N2(self):
        """
        VMR values for N2.
        The standard value for N2 is scaled by VMR of h2o
        Returns
        -------
        grid_N2 : np.array containing the interpolated values in
        dimensions [1, p, lat, lon]
        """        
        grid_q2vmr       = self.vmr_h2o
        
        grid_N2          = np.ones(grid_q2vmr.shape) * 0.781 # vmr N2
        
        grid_N2          = scale_vmr(grid_N2, grid_q2vmr)
        
        return grid_N2

        
    @property    
    def vmr_O2(self): 
        """
        VMR values for O2.
        The standard value for O2 is scaled by VMR of h2o
        Returns
        -------
        grid_N2 : np.array containing the interpolated values in
        dimensions [1, p, lat, lon]
        """ 
        
        grid_q2vmr       = self.vmr_h2o
        
        
        grid_O2         = np.ones(grid_q2vmr.shape) * 0.209 # vmr O2

        grid_O2         = scale_vmr(grid_O2, grid_q2vmr)
        
        return grid_O2
        
    @property
    def iwc(self):
        """
        The IWC data from DARDAR interpolated to pressure grid defined in
        p_grid
        -------
        grid_N2 : np.array containing the interpolated values in
        dimensions [1, p, lat, lon]
        """ 
        
        p               = self.p_grid   
        
        iwc             = self.dardar.iwc
        height_d        = self.dardar.height
        p_grid_d        = alt2pres(height_d)
        f               = interpolate.interp1d(p_grid_d, iwc)
        grid_iwc        = f(p)
        grid_iwc        = grid_iwc.T
        grid_iwc        = np.expand_dims(grid_iwc, axis = (0, 3))
       
        return grid_iwc                    
        
    @property
    def Z(self):
        """
        The reflectivity data from DARDAR interpolated to pressure grid defined in
        p_grid
        -------
        grid_N2 : np.array containing the interpolated values in
        dimensions [1, p, lat, lon]
        """ 
        
        p               = self.p_grid   
        
        Z               = self.dardar.z
        height_d        = self.dardar.height
        p_grid_d        = alt2pres(height_d)
        f               = interpolate.interp1d(p_grid_d, Z)
        grid_z        = f(p)
        grid_z        = grid_z.T
        grid_z        = np.expand_dims(grid_z, axis = (0, 3))
       
        return grid_z      
    
    def variable_plevel(self, variable):
        """
        interpolated ERA5 pressure variable to DARDAR grid
        and pressure grid defined in self.p_grid
        
        Parameters
        -----------
        variable : string, name of variable

        Returns
        -------
        grid_z : np.array containing the interpolated values
        dimensions [p, lat, lon]

        """
        p           = self.p_grid        
        var         = variable
        ERA_t       = ERA5p(self.t_0, self.t_1, var)
        grid_t      = ERA_t.interpolate(self.dardar, p* 0.01)
        grid_t      = np.expand_dims(grid_t, 2)         
        return grid_t
    
    def variable_surface(self, variable):
        """
        interpolated ERA5 pressure variable to DARDAR grid
        
        Parameters
        -----------
        variable : string, name of variable

        Returns
        -------
        grid_z : np.array containing the interpolated values
        dimensions [lat, lon]

        """
        var           = variable
        ERA_t         = ERA5s(self.t_0, self.t_1, var)
        grid_t        = ERA_t.interpolate(self.dardar)
        grid_t        = np.expand_dims(grid_t, axis = 1)
        
        return grid_t

            

        
        
        