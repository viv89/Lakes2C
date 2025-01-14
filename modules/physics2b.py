# -*- coding: utf-8 -*-
"""
Created on Tue May 10 11:56:22 2022

@author: vija
"""

import numpy as np
import pandas as pd

# disable warnings "A value is trying to be set on a copy of a slice from a DataFrame"
pd.options.mode.chained_assignment = None  # default='warn'

class obj(object):
    '''
        A small class which can have attributes set
    '''
    pass

# Lake module
    
class lake:
    
    def __init__(self, lake_data, params, properties):
        
        
        # initialize objects
        self.data    = obj()    
        self.params  = obj()
        self.props   = obj()
        self.vars    = obj()
        self.vardata = obj()
        self.hist    = obj()
        
        # read data and parameters
        self.data.V         = lake_data['volume']
        self.data.L         = lake_data['length']
        self.data.W         = lake_data['width']
        self.data.A_surf    = lake_data['surf_area']
        # self.data.h         = lake_data['depth']  
        self.data.ext_coeff = lake_data['extinction_coeff']
        self.data.Tw_init   = lake_data['wtemp_init']
        self.data.latitude  = lake_data['latitude']
        
        self.params.n_years = params['n_years']
        self.params.nt     = params['nt']
        self.params.dt     = params['dt']
        
        self.props.rho_0 = properties['rho_0']
        self.props.g     = properties['g']
        self.props.cp    = properties['cp']
        # self.props.eps_w = properties['eps_w']
        self.props.alpha = properties['alpha']
        
       
        # Lake geometry assumption (cone)
        self.data.avg_depth = self.data.V/self.data.A_surf
        self.data.z_therm = self.thermocline_depth(self.data.L,self.data.W) # thermocline depth 
        self.data.V_epi   = self.data.A_surf*self.data.z_therm
        self.data.V_hypo  = self.data.V - self.data.V_epi
        self.data.thickness_trans  = min(2*self.data.z_therm, self.data.avg_depth/3)
        if self.data.z_therm > 0.667*self.data.avg_depth:
            self.data.lake_type = 'shallow'
            print('Lake classified as shallow lake. One-capacitance model will be applied.')
        else:
            self.data.lake_type = 'deep'
            print('Lake classified as deep lake. Two-capacitance model will be applied.')
        # Lake geometry assumption (changed)
        # self.data.z_therm = self.thermocline_depth(self.data.L,self.data.W) # thermocline depth  
        # self.data.V_epi   = self.data.A_surf*self.data.z_therm 
        # self.data.V_trans = self.data.A_surf*self.data.thickness_trans
        # self.data.V_hypo  = self.data.V - self.data.V_epi - self.data.V_tran
        # self.data.delta_z = 3*self.data.V_hypo/(2*self.data.A_surf)
        # self.data.z_b1    = self.data.z_therm
        # self.data.z_b2    = self.data.z_b1 + self.data.thickness_trans
        # self.data.h       = self.data.z_b2 + self.data.delta_z
        # self.data.thickness_trans  = min(5*self.data.z_therm, self.data.h/3)
        
        # self.data.A_b1    = self.data.A_surf
        # self.data.z_b2    = self.data.z_b1 + self.data.thickness_trans
        
        # self.data.h_cal   = self.data.h-self.data.z_b2
        # self.data.V_hypo  = np.pi*self.data.h_cal**2*()
        
        # light transmission through water column
        self.data.light_fraction = self.light_extinction(self.data.ext_coeff, self.data.z_therm) #0.15 #
        
        # initialize model variables
        self.vars.Tw  = self.data.Tw_init*np.ones(2)
        self.vars.rho = np.zeros(2)
        self.vars.kz  = np.zeros(1) 
        
        self.hist = pd.DataFrame(columns=['Te','RHe','v_wind','ghi',
                                          'Tw_e','Tw_h','Psat','rho_e','rho_h','kz',
                                          'Q_ev','Q_conv','Q_lw','Q_sw','Q_sw_tr','Q_diff','Tsky',
                                          'heating_demand','cooling_demand','Q_load'])
        self.hist.Tw_e  = np.zeros(self.params.nt)
        self.hist.Tw_h  = np.zeros(self.params.nt)
        self.hist.rho_e = np.zeros(self.params.nt)
        self.hist.rho_h = np.zeros(self.params.nt)
        self.hist.kz    = np.zeros(self.params.nt)
        self.hist.Q_load = np.zeros(self.params.nt)
    
    
    def run(self, vardata, exchange=False):
                
        # Rename variables
        Tw = self.vars.Tw
        rho = self.vars.rho
        kz  = self.vars.kz
        dt    = self.params.dt
        # dz    = self.data.z_range[1] - self.data.z_range[0]
        # eps_w   = self.props.eps_w
        alpha = self.props.alpha
        cp    = self.props.cp
        
        # Read boundary conditions
        self.vardata.Te     = vardata['Te']    # dry-bulb temperature of the outdoor air
        self.vardata.RHe    = vardata['RHe']    # partial water vapor pressure in the air
        self.vardata.v_wind = vardata['v_wind']
        self.vardata.ghi    = vardata['ghi']
        self.vardata.sc     = vardata['sky_cover']
        self.vardata.month  = vardata['month'].astype(int)    
        
        try:
            self.vardata.Q_lw_sky  = vardata['Q_lw_sky']
        except:
            self.vardata.Q_lw_sky  = []

        # Save boundary conditions into hist
        self.hist.Te  = vardata['Te'].values 
        self.hist.RHe  = vardata['RHe'].values 
        self.hist.v_wind = vardata['v_wind'].values 
        self.hist.ghi    = vardata['ghi'].values 
        self.hist.heating_demand = vardata['heating_demand'].values 
        self.hist.cooling_demand = vardata['cooling_demand'].values 
        self.hist.Q_ev   = np.zeros(self.params.nt)
        self.hist.Q_conv = np.zeros(self.params.nt)
        self.hist.Q_lw   = np.zeros(self.params.nt)
        self.hist.Q_sw   = np.zeros(self.params.nt)
        self.hist.Q_sw_tr = np.zeros(self.params.nt)
        self.hist.Q_diff  = np.zeros(self.params.nt)
        self.hist.Tsky  = np.zeros(self.params.nt)
        
        if exchange == True:
            self.vardata.heating_demand = vardata['heating_demand']
            self.vardata.cooling_demand = vardata['cooling_demand']   
            self.vardata.cop    = 3*np.ones(self.params.nt)
            self.vardata.eer    = 3*np.ones(self.params.nt)
            self.vardata.f_cop  = np.divide((self.vardata.cop-1),self.vardata.cop)
            self.vardata.f_eer  = np.divide((self.vardata.eer+1),self.vardata.eer)
            self.vardata.heat_load = np.multiply(self.vardata.heating_demand, self.vardata.f_cop)
            self.vardata.cool_load = np.multiply(self.vardata.cooling_demand, self.vardata.f_eer)
            # Cool load > 0 (charging) and heat load < 0 (discharging)
            self.vardata.Q_load = 1000*(self.vardata.cool_load - self.vardata.heat_load) / 24  # kWh/day --> W 
        else:
            self.vardata.Q_load = np.zeros(self.params.nt)

        
        sigma = 5.67*1e-8 # W/(m2 K4) Stephan-Boltzmann constant for blackbody radiation
        # L_w   = 2260000 # J/kg Latent heat of vaporization of water
        Tw_new = np.zeros(2)
        
        # Simulation
        for t in range(self.params.nt):
            # Shorten variable names
            Te = self.vardata.Te[t]
            v  = self.vardata.v_wind[t] #m/s
            RHe = self.vardata.RHe[t]
            # Cool load > 0 (charging) and heat load < 0 (discharging)
            Q_load = self.vardata.Q_load[t]          
            # calculate density and turbulent diffusivity
            rho = self.calc_dens(Tw)
            kz  = self.eddy_diffusivity(v, rho) 
            T_sky  = self.sky_temperature(Te)
            Psat   = self.saturated_pressure(Tw[0])            
            Pe     = self.saturated_pressure(Te)*RHe/100
            # heat balance of the surface layer (epilymnion)
            # Latent heat flux (W/m2) due to evaporation of surface water (Ryan, 1974)
            Twv = Tw[0]/(1-0.378*Psat/101325)
            Tav = Te/(1-0.378*Pe/101325)
            if Twv>Tav:                
                Q_ev = (0.027*(Twv-Tav)**(0.333)+0.032*v)*(Psat-Pe)  
            else:
                Q_ev = (0.032*v)*(Psat-Pe)
            # Bowen coefficient: ratio between sensible and latent heat exchange at the surface of a water body
            Q_conv = self.bowen()*Q_ev  # W/m2
      
            try:
                Q_lw_lake = 0.97*sigma*((Tw[0]+273.15)**4)
                Q_lw_sky = self.vardata.Q_lw_sky[t]
                Q_lw = Q_lw_lake - Q_lw_sky
            except:
                Q_lw = 0.9*sigma*((Tw[0]+273.15)**4-(T_sky+273.15)**4)      
            
            alpha = self.albedo(self.data.latitude, self.vardata.month[t])
            Q_sw    = (1-alpha)*self.vardata.ghi[t]      # W/m2
            Q_sw_tr = self.data.light_fraction*Q_sw  # W/m2            
            
            if self.data.lake_type == 'shallow':
                Q_diff  = 0
                Tw_new[0] = Tw[0] + (dt*self.data.A_surf)/(rho[0]*cp*self.data.V)*(-Q_ev-Q_conv-Q_lw+Q_sw)
                Tw_new[1] = Tw_new[0]
            else:
                # mixing between layers
                Q_diff  = kz*(Tw[0]-Tw[1])  # W/m2  
                # heat balance of the surface layer                 
                Tw_new[0] = Tw[0] + (dt*self.data.A_surf)/(rho[0]*cp*self.data.V_epi)*(-Q_ev-Q_conv-Q_lw+Q_sw-Q_diff-Q_sw_tr)  
                # heat balance of the bottom layer (hypolimnion)
                Tw_new[1] = Tw[1] + (dt*self.data.A_surf)/(rho[1]*cp*self.data.V_hypo)*(Q_diff+Q_sw_tr+(Q_load/self.data.A_surf))  
            #update temperatures
            Tw[0] = Tw_new[0]
            Tw[1] = Tw_new[1]
            # save temperature, density and turbulent diffusivity
            self.hist.Tw_e[t]  = Tw[0]
            self.hist.Tw_h[t]  = Tw[1]
            self.hist.Psat[t]  = Psat
            self.hist.rho_e[t] = rho[0]
            self.hist.rho_h[t] = rho[1]
            self.hist.kz[t]    = kz
            self.hist.Q_diff[t] = Q_diff
            self.hist.Q_ev[t]   = Q_ev
            self.hist.Q_conv[t] = Q_conv
            self.hist.Q_lw[t]   = Q_lw
            self.hist.Q_sw[t]   = Q_sw
            self.hist.Q_sw_tr[t] = Q_sw_tr
            self.hist.Tsky[t]  = T_sky
            self.hist.Q_load[t] = Q_load
        
        # Take only last year (transient should be over)
        self.hist = self.hist[-int(self.params.nt/self.params.n_years):]
        self.hist = self.hist.reset_index(drop=True)
        # self.hist.Tw_avg = (self.data.V_epi*self.hist.Tw_e+self.data.V_hypo*self.hist.Tw_h)/(self.data.V_epi+self.data.V_hypo)
        # self.hist.Tw_avg = (self.hist.Tw_e+self.hist.Tw_h)/2
            
       

    
    #--------------------------------------------------------------------------    
    # used inside this class -------------------------------------------------------  
    
    def bowen(self):
        # Woolway et al (2018) Geographic and temporal variations in turbulent 
        # heat loss from lakes: a global analysis across 45 lakes
        #
        # data from summer (jul-Sept) 
        # in winter B is higher 
        #
        lat = self.data.latitude
        B   = 0.0501*np.exp(0.0295*lat)
        # B = 0.6
        return B
        
    def thermocline_depth(self, L, W):
        # Hanna M. (1990): Evaluation of Models predicting Mixing Depth. 
        # Can. J. Fish. Aquat. Sci. 47: 940-947
        #
        MEL = max(L,W)/1000
        self.data.MEL = MEL
        z_therm = 10**(0.336*np.log10(MEL-0.245))  # m
        z_therm = 2*z_therm
        return z_therm
    
    def light_extinction(self, ext_coeff, z):
        # z_a = 0.6 # m
        light_fraction = 1 * np.exp(-ext_coeff*(z))
        return light_fraction
    
    def calc_dens(self, wtemp):
        # dens = 999.842594 + (6.793952 * 1e-2 * wtemp) - (9.095290 * 1e-3 *wtemp**2) + (1.001685 * 1e-4 * wtemp**3) - (1.120083 * 1e-6* wtemp**4) + (6.536336 * 1e-9 * wtemp**5)
 
        rho_0 = 999.83311
        a1    = 0.0752
        a2 = -0.0089
        a3 = 7.36413*1e-5
        a4 = 4.74639*1e-7
        a5 = 1.34888*1e-9
        
        dens = np.zeros((2,1))
         
        for idx,wt in enumerate(wtemp):
            if wt >= 4.0:
                dens[idx] = rho_0 + (a1 * wt) + (a2 *wt**2) + (a3 * wt**3) + (a4* wt**4) + (a5 * wt**5)
            else:
                dens[idx] = rho_0 + (a1 * 4) + (a2 *4**2) + (a3 * 4**3) + (a4* 4**4) + (a5 * 4**5) + 0.2
        
        return dens
    
    def sky_temperature(self, Te):
        # conversion °C --> K
        Te = Te + 273.15 
        # Swinbank model (1963): valid for clear sky (overestimation of Q_lw = 85 W/m2)        
        # Tsky = 0.0553*Te**1.5
        # Fuentes model (1987): assumes average cloudiness factor of 0.61 (Q_lw = 70 W/m2)        
        Tsky = 0.037536*Te**1.5 + 0.32*Te
        # conversion K --> °C
        Tsky = Tsky - 273.15
        return Tsky
    
    def albedo(self, lat, month):
        # Cogley 1979 albedo = f(latitude, month)
        albedos_60_90 = np.array([56.2, 37.6, 23.1, 14.9, 10.9, 9.6, 10.3, 13.4, 20.2, 33.1, 52.2, 66.6])
        albedos_30_60 = np.array([15.5, 11.3, 7.9, 6.2, 5.5, 5.4, 5.5, 5.9, 7.3, 10.3, 14.6, 17.2])
        albedos_0_30  = np.array([6.1, 5.4, 4.9, 4.6, 4.7, 4.7, 4.7, 4.6, 4.8, 5.2, 5.9, 6.4])
        if (lat > 0) & (lat <= 30):
            alb = albedos_0_30[month-1]
        elif (lat > 30) & (lat <= 60):
            alb = albedos_30_60[month-1]
        elif lat > 60:
            alb = albedos_60_90[month-1]
        else:
            print('Error: change correlation for southern emisphere!')
        alpha = alb/100
        return alpha

        

    
    #--------------------------------------------------------------------------
    # used outside this class ------------------------------------------------------
   
    def eddy_diffusivity(self, v, rho):
        # 
        # v = u10 = velocity 10 meters above ground surface (m/s)
        #
        # ThreeLayer <- function(t, y, parms)-------------------------------
        Ht      = self.data.thickness_trans* 100 # thermocline thickness (cm)
        # Ht  = self.data.z_therm/2*100
        rho_air = 1.2 # kg/m3 density of the air
        
        if v == 0:
            v = 0.01

        # wind drag coefficient from Wüest & Lorke (2003)
        if v <= 0.1:
            Cd = 6.215e-2
        elif 0.1 < v < 3.85:
            Cd = 4.4e-2*v**(-1.15)
        else:
            Cd = -7.12e-7*v**2 + 7.387e-5*v + 6.605e-4
        
        # water-side shear velocity (m/s)
        v_star2 = Cd*(v**2)*rho_air/rho[0]
        
        # ratio between buoyancy force and wind stress
        Lmax = self.data.MEL
        W = self.props.g*abs(rho[0]-rho[1])/rho[0]*(self.data.z_therm**2)/(Lmax*v_star2)   
        
        # connect to previous parameters
        Ri = W
        a = 7 # constant
        c = 9e4                       # empirical constant
        w0 = np.sqrt(v_star2/(rho[0]/1000)) # rho divided by 1000 because must be in g/cm3
        E0  = c * w0
               
        if (rho[0] > rho[1]):
            kz = 300
        else:
            kz = (E0 / (1 + a*Ri)**(3/2))/(Ht/100) #* (86400/10000)  #m2/s (probabilm lui divide per 10000 per avere cm2/s 

        return kz


    def saturated_pressure(self, air_temp):
        # maximum water vapor pressure (kPa) in the air at air_temp (°C)
        # Tetens equation (1930) adapted to t>0°C from Monteith and Unsworth (2008) 
        if air_temp >= 0:
            Psat_kPa = 0.61078*np.exp((17.27*air_temp)/(air_temp+237.3))
        else:
            Psat_kPa = 0.61078*np.exp((21.875*air_temp)/(air_temp+265.5))
        # Conversion kPa --> Pa
        Psat = 1000*Psat_kPa
        return Psat