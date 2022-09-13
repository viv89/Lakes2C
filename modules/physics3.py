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
        # self.data.ext_coeff = lake_data['extinction_coeff']
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
        self.data.h       = 3*self.data.V/(self.data.A_surf)
        self.data.z_therm = self.thermocline_depth(self.data.L,self.data.W) # thermocline depth 
        self.data.thickness_trans  = min(5*self.data.z_therm, self.data.h/3)
        self.data.r_surf  = np.sqrt(self.data.A_surf/np.pi)  
        self.data.z_b1    = self.data.z_therm
        self.data.A_b1    = self.data.A_surf*(self.data.h - self.data.z_b1)/self.data.h
        self.data.r_b1    = np.sqrt(self.data.A_b1/np.pi)
        self.data.z_b2    = self.data.z_b1 + self.data.thickness_trans
        self.data.A_b2    = self.data.A_surf*(self.data.h - self.data.z_b2)/self.data.h
        self.data.r_b2    = np.sqrt(self.data.A_b2/np.pi)   
        self.data.V_epi   = np.pi/3*self.data.z_b1*(self.data.r_surf**2 + self.data.r_surf*self.data.r_b1 + self.data.r_b1**2)
        self.data.V_hypo  = self.data.A_b2*(self.data.h-self.data.z_b2)/3
        self.data.V_tran  = self.data.V - self.data.V_epi - self.data.V_hypo
        
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
        self.data.light_fraction = 0.02 #self.light_extinction(self.data.ext_coeff, self.data.z_therm)
        
        # initialize model variables
        self.vars.Tw  = self.data.Tw_init*np.ones(3)
        self.vars.rho = np.zeros(3)
        self.vars.kz  = np.zeros(2) 
        
        self.hist = pd.DataFrame(columns=['Te','RHe','v_wind','ghi',
                                          'Tw_e','Tw_h','Tw_t','Psat','rho_e','rho_h','rho_t','kz_b1','kz_b2',
                                          'Q_ev','Q_conv','Q_lw','Q_sw','Q_sw_tr','Q_diff_b1','Q_diff_b2','Tsky',
                                          'heating_demand','cooling_demand','Q_load'])
        self.hist.Tw_e  = np.zeros(self.params.nt)
        self.hist.Tw_h  = np.zeros(self.params.nt)
        self.hist.Tw_t  = np.zeros(self.params.nt)
        self.hist.rho_e = np.zeros(self.params.nt)
        self.hist.rho_h = np.zeros(self.params.nt)
        self.hist.rho_t = np.zeros(self.params.nt)
        self.hist.kz_b1  = np.zeros(self.params.nt)
        self.hist.kz_b2  = np.zeros(self.params.nt)
        self.hist.Q_load = np.zeros(self.params.nt)
    
    
    def run(self, vardata, exchange):
                
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
        # self.hist.Q_diff  = np.zeros(self.params.nt)
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
            self.vardata.Q_load = 1000*(self.vardata.cool_load - self.vardata.heat_load)   # W 
        else:
            self.vardata.Q_load = np.zeros(self.params.nt)

        
        sigma = 5.67*1e-8 # W/(m2 K4) Stephan-Boltzmann constant for blackbody radiation
        # L_w   = 2260000 # J/kg Latent heat of vaporization of water
        Tw_new = np.zeros(3)
        
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
            Q_lw = 0.9*sigma*((Tw[0]+273.15)**4-(T_sky+273.15)**4)           
            Q_sw    = (1-alpha)*self.vardata.ghi[t]      # W/m2
            Q_sw_tr = self.data.light_fraction*Q_sw  # W/m2
            # mixing between layers
            Q_diff_b1  = kz[0]*(Tw[0]-Tw[1])  # W/m2
            Q_diff_b2  = kz[1]*(Tw[1]-Tw[2])  # W/m2
            #heat balance of the surface layer
            Tw_new[0] = Tw[0] + (dt*self.data.A_surf)/(rho[0]*cp*self.data.V_epi)*(-Q_ev-Q_conv-Q_lw+Q_sw-Q_diff_b1-Q_sw_tr)
            # heat balance of the transition layer 
            Tw_new[1] = Tw[1] + (dt*self.data.A_b1)/(rho[1]*cp*self.data.V_tran)*(Q_diff_b1-Q_diff_b2+Q_sw_tr)  
            # heat balance of the bottom layer (hypolimnion)
            Tw_new[2] = Tw[2] + (dt*self.data.A_b2)/(rho[2]*cp*self.data.V_hypo)*(Q_diff_b2+(Q_load/self.data.A_b2))  
            #update temperatures
            Tw[0] = Tw_new[0]
            Tw[1] = Tw_new[1]
            Tw[2] = Tw_new[2]
            # save temperature, density and turbulent diffusivity
            self.hist.Tw_e[t]  = Tw[0]
            self.hist.Tw_t[t]  = Tw[1]
            self.hist.Tw_h[t]  = Tw[2]
            self.hist.Psat[t]  = Psat
            self.hist.rho_e[t] = rho[0]
            self.hist.rho_t[t] = rho[1]
            self.hist.rho_h[t] = rho[2]
            self.hist.kz_b1[t]    = kz[0]
            self.hist.kz_b2[t]    = kz[1]
            self.hist.Q_diff_b1[t]  = Q_diff_b1
            self.hist.Q_diff_b2[t]  = Q_diff_b2
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
        B = 0.6
        return B
        
    def thermocline_depth(self, L, W):
        # Hanna M. (1990): Evaluation of Models predicting Mixing Depth. 
        # Can. J. Fish. Aquat. Sci. 47: 940-947
        #
        MEL = max(L,W)/1000
        z_therm = 10**(0.336*np.log10(MEL-0.245))  # m
        z_therm = 2*z_therm
        return z_therm
    
    def light_extinction(self, ext_coeff, z):
        # z_a = 0.6 # m
        light_fraction = 1 * np.exp(-ext_coeff*(z))
        return light_fraction
    
    def calc_dens(self, wtemp):
        dens = 999.842594 + (6.793952 * 1e-2 * wtemp) - (9.095290 * 1e-3 *wtemp**2) + (1.001685 * 1e-4 * wtemp**3) - (1.120083 * 1e-6* wtemp**4) + (6.536336 * 1e-9 * wtemp**5)
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
    
    #--------------------------------------------------------------------------
    # used outside this class ------------------------------------------------------
   
    def eddy_diffusivity(self, v, rho):
        # 
        kz = np.zeros(2)
        # ThreeLayer <- function(t, y, parms)-------------------------------
        Ht = self.data.thickness_trans* 100 # thermocline thickness (cm)
        a = 7 # constant

        # # diffusion coefficient
        Cd = 0.00052*v**(0.44)        # unit ok because v is in m/s
        shear = 1.164/1000*Cd*v**2    # unit ok (see above)
        c = 9e4                       # empirical constant
        w0 = np.sqrt(shear/(rho[0]/1000)) # rho divided by 1000 because must be in g/cm3
        E0  = c * w0
        Ri_b1 = ((self.props.g/self.props.rho_0)*(abs(rho[0]-rho[1])/10))/(w0/(self.data.z_b1)**2)
        Ri_b2 = ((self.props.g/self.props.rho_0)*(abs(rho[0]-rho[1])/10))/(w0/(self.data.z_b2)**2)
        if (rho[0] > rho[1]):
            kz[0] = 100
        else:
            kz[0] = (E0 / (1 + a*Ri_b1)**(3/2))/(Ht/100) #* (86400/10000)  #m2/s (probabilm lui divide per 10000 per avere cm2/s 
                 #       e moltiplica per 86400 per passare da W a J/d)
        if (rho[1] > rho[2]):
            kz[1] = 100
        else:
            kz[1] = (E0 / (1 + a*Ri_b2)**(3/2))/(Ht/100) #* (86400/10000)  #m2/s (probabilm lui divide per 10000 per avere cm2/s 
                 #       e moltiplica per 86400 per passare da W a J/d)   
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