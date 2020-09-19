import numpy as np
import matplotlib.pyplot as plt
import datajoint as dj
import pandas as pd
import scipy.signal as signal
import scipy.ndimage as ndimage
from pipeline import pipeline_tools, lab, experiment, ephys_cell_attached#, ephysanal
#dj.conn()
#%%
schema = dj.schema(pipeline_tools.get_schema_name('ephys-anal'),locals())

#%%

# =============================================================================
# @schema
# class ActionPotential(dj.Computed):
#     definition = """
#     -> ephys_patch.Sweep
#     ap_num : smallint unsigned # action potential number in sweep
#     ---
#     ap_max_index=null : int unsigned # index of AP max on sweep
#     ap_max_time=null : decimal(8,4) # time of the AP max relative to recording start
#     """
#     def make(self, key):
#         
#         #%%
#         #key = {'subject_id': 454263, 'session': 1, 'cell_number': 1, 'sweep_number': 62}
#         #print(key)
#         keynow = key.copy()
#         counter = 0
#         if len(ActionPotential()&keynow) == 0:
#             #%%
#             pd_sweep = pd.DataFrame((ephys_patch.Sweep()&key)*(SweepResponseCorrected()&key)*(ephys_patch.SweepStimulus()&key)*(ephys_patch.SweepMetadata()&key))
#             if len(pd_sweep)>0:
#                 dj.conn().ping()
#                 trace = pd_sweep['response_trace_corrected'].values[0]
#                 sr = pd_sweep['sample_rate'][0]
#                 si = 1/sr
#                 msstep = int(.0005/si)
#                 sigma = .00005
#                 trace_f = ndimage.gaussian_filter(trace,sigma/si)
#                 d_trace_f = np.diff(trace_f)/si
#                 peaks = d_trace_f > 40
#                 sp_starts,sp_ends =(SquarePulse()&key).fetch('square_pulse_start_idx','square_pulse_end_idx') 
#                 squarepulses = np.concatenate([sp_starts,sp_ends])
#                 for sqidx in squarepulses:
#                     peaks[sqidx-msstep:sqidx+msstep] = False
#                 peaks = ndimage.morphology.binary_dilation(peaks,np.ones(int(round(.002/si))))
#                 spikemaxidxes = list()
#                 while np.any(peaks):
#                     if counter ==0:
#                         print('starting ap detection')
#                     if counter%2==0:
#                         dj.conn().ping()
#                     if counter%20==0:
#                         print('pingx10')
#                     
#                     counter +=1
#                     spikestart = np.argmax(peaks)
#                     spikeend = np.argmin(peaks[spikestart:])+spikestart
#                     if spikestart == spikeend:
#                         if sum(peaks[spikestart:]) == len(peaks[spikestart:]):
#                             spikeend = len(trace)
#                     try:
#                         sipeidx = np.argmax(trace[spikestart:spikeend])+spikestart
#                     except:
#                         print(key)
#                         sipeidx = np.argmax(trace[spikestart:spikeend])+spikestart
#                     spikemaxidxes.append(sipeidx)
#                     peaks[spikestart:spikeend] = False
#                     #%
#                 if len(spikemaxidxes)>0:
#                     spikemaxtimes = spikemaxidxes/sr + float(pd_sweep['sweep_start_time'].values[0])
#                     spikenumbers = np.arange(len(spikemaxidxes))+1
#                     keylist = list()
#                     for spikenumber,spikemaxidx,spikemaxtime in zip(spikenumbers,spikemaxidxes,spikemaxtimes):
#                         keynow =key.copy()
#                         keynow['ap_num'] = spikenumber
#                         keynow['ap_max_index'] = spikemaxidx
#                         keynow['ap_max_time'] = spikemaxtime
#                         keylist.append(keynow)
#                         #%
#                     try:
#                         self.insert(keylist,skip_duplicates=True)
#                     except:
#                         print(key)
#                         self.insert(keylist,skip_duplicates=True)
# @schema
# class ActionPotentialDetails(dj.Computed):
#     definition = """
#     -> ActionPotential
#     ---
#     ap_real                : tinyint # 1 if real AP
#     ap_threshold           : float # mV
#     ap_threshold_index     : int #
#     ap_baseline_value      : float # mV average of 10 ms right before the threshold
#     ap_halfwidth           : float # ms
#     ap_amplitude           : float # mV
#     ap_dv_max : float # mV/ms
#     ap_dv_max_voltage : float # mV
#     ap_dv_min : float # mV/ms
#     ap_dv_min_voltage : float # mV    
#     """
#     def make(self, key):
#         counter = 0
#         #%%
#         sigma = .00003 # seconds for filering
#         step_time = .0001 # seconds
#         threshold_value = 5 # mV/ms
#         baseline_length = .01 #s back from threshold
#         #%%
# # =============================================================================
# #         key = {'subject_id': 454263, 'session': 1, 'cell_number': 1, 'sweep_number': 56, 'ap_num': 30}
# #         print(key)
# # =============================================================================
#         keynow = key.copy()
#         del keynow['ap_num']
#         pd_sweep = pd.DataFrame((ephys_patch.Sweep()&key)*(SweepResponseCorrected()&key)*(ephys_patch.SweepStimulus()&key)*(ephys_patch.SweepMetadata()&key))
#         pd_ap = pd.DataFrame(ActionPotential()&keynow)
#         #%%
#         if len(pd_ap)>0 and len(ActionPotentialDetails()&dict(pd_ap.loc[0])) == 0:
#             #%%
#             #print(key)
#             trace = pd_sweep['response_trace_corrected'].values[0]
#             sr = pd_sweep['sample_rate'][0]
#             si = 1/sr
#             step_size = int(np.round(step_time/si))
#             ms5_step = int(np.round(.005/si))
#             trace_f = ndimage.gaussian_filter(trace,sigma/si)
#             d_trace_f = np.diff(trace_f)/si
#             tracelength = len(trace)
#             baseline_step = int(np.round(baseline_length/si))
#             #%%
#             keylist = list()
#             for ap_now in pd_ap.iterrows():
#                 counter += 1
#                 if counter%2==0:
#                     dj.conn().ping()
#                 ap_now = dict(ap_now[1])
#                 ap_max_index = ap_now['ap_max_index']
#                 dvmax_index = ap_max_index
#                 while dvmax_index>step_size*2 and trace_f[dvmax_index]>0:
#                     dvmax_index -= step_size
#                 while dvmax_index>step_size*2 and dvmax_index < tracelength-step_size and  np.max(d_trace_f[dvmax_index-step_size:dvmax_index])>np.max(d_trace_f[dvmax_index:dvmax_index+step_size]):
#                     dvmax_index -= step_size
#                 if dvmax_index < tracelength -1:
#                     dvmax_index = dvmax_index + np.argmax(d_trace_f[dvmax_index:dvmax_index+step_size])
#                 else:
#                     dvmax_index = tracelength-2
#                     
#                 
#                 dvmin_index = ap_max_index
#                 #%
#                 while dvmin_index < tracelength-step_size and  (trace_f[dvmin_index]>0 or np.min(d_trace_f[np.max([dvmin_index-step_size,0]):dvmin_index])>np.min(d_trace_f[dvmin_index:dvmin_index+step_size])):
#                     dvmin_index += step_size
#                     #%
#                 dvmin_index -= step_size
#                 dvmin_index = dvmin_index + np.argmin(d_trace_f[dvmin_index:dvmin_index+step_size])
#                 
#                 thresh_index = dvmax_index
#                 while thresh_index>step_size*2 and (np.min(d_trace_f[thresh_index-step_size:thresh_index])>threshold_value):
#                     thresh_index -= step_size
#                 thresh_index = thresh_index - np.argmax((d_trace_f[np.max([0,thresh_index-step_size]):thresh_index] < threshold_value)[::-1])
#                 ap_threshold = trace_f[thresh_index]
#                 ap_amplitude = trace_f[ap_max_index]-ap_threshold
#                 hw_step_back = np.argmax(trace_f[ap_max_index:np.max([ap_max_index-ms5_step,0]):-1]<ap_threshold+ap_amplitude/2)
#                 hw_step_forward = np.argmax(trace_f[ap_max_index:ap_max_index+ms5_step]<ap_threshold+ap_amplitude/2)
#                 ap_halfwidth = (hw_step_back+hw_step_forward)*si
#                 
#                 
#                 
#                 if ap_amplitude > .01 and ap_halfwidth>.0001:
#                     ap_now['ap_real'] = 1
#                 else:
#                     ap_now['ap_real'] = 0
#                 ap_now['ap_threshold'] = ap_threshold*1000
#                 ap_now['ap_threshold_index'] = thresh_index
#                 if thresh_index>10:
#                     ap_now['ap_baseline_value'] = np.mean(trace_f[np.max([thresh_index - baseline_step,0]) : thresh_index])*1000
#                 else:
#                     ap_now['ap_baseline_value'] = ap_threshold*1000
#                 ap_now['ap_halfwidth'] =  ap_halfwidth*1000
#                 ap_now['ap_amplitude'] =  ap_amplitude*1000
#                 ap_now['ap_dv_max'] = d_trace_f[dvmax_index]
#                 ap_now['ap_dv_max_voltage'] = trace_f[dvmax_index]*1000
#                 ap_now['ap_dv_min'] =  d_trace_f[dvmin_index]
#                 ap_now['ap_dv_min_voltage'] = trace_f[dvmin_index]*1000
#                 del ap_now['ap_max_index']
#                 del ap_now['ap_max_time']
#                 keylist.append(ap_now)
#                 #%%
#             self.insert(keylist,skip_duplicates=True)
# # =============================================================================
# #             fig=plt.figure()
# #             ax_v = fig.add_axes([0,0,.8,.8])
# #             ax_dv = fig.add_axes([0,-1,.8,.8])
# #             ax_v.plot(trace[ap_max_index-step_size*10:ap_max_index+step_size*10],'k-')
# #             ax_v.plot(trace_f[ap_max_index-step_size*10:ap_max_index+step_size*10])
# #             ax_dv.plot(d_trace_f[ap_max_index-step_size*10:ap_max_index+step_size*10])
# #             dvidx_now = dvmax_index - ap_max_index + step_size*10
# #             ax_dv.plot(dvidx_now,d_trace_f[dvmax_index],'ro')
# #             ax_v.plot(dvidx_now,trace_f[dvmax_index],'ro')
# #             dvminidx_now = dvmin_index - ap_max_index + step_size*10
# #             ax_dv.plot(dvminidx_now,d_trace_f[dvmin_index],'ro')
# #             ax_v.plot(dvminidx_now,trace_f[dvmin_index],'ro')
# #             threshidx_now = thresh_index - ap_max_index + step_size*10
# #             ax_dv.plot(threshidx_now,d_trace_f[thresh_index],'ro')
# #             ax_v.plot(threshidx_now,trace_f[thresh_index],'ro')
# #             plt.show()
# #             break
# # =============================================================================
#         #%%
# =============================================================================
    
# =============================================================================
# 
# @schema       
# class SweepResponseCorrected(dj.Computed):
#     definition = """
#     -> ephys_patch.Sweep
#     ---
#     response_trace_corrected  : longblob #
#     """
#     def make(self, key):
#        
#         try:
#              #%
#            # key={'subject_id': 463291, 'session': 1, 'cell_number': 0, 'sweep_number': 64}#{'subject_id': 466769, 'session': 1, 'cell_number': 2, 'sweep_number': 45}
#             junction_potential = 13.5/1000 #mV
#             e_sr= (ephys_patch.SweepMetadata()&key).fetch1('sample_rate')
#             uncompensatedRS =  float((SweepSeriesResistance()&key).fetch1('series_resistance_residual'))
#             v = (ephys_patch.SweepResponse()&key).fetch1('response_trace')
#             i = (ephys_patch.SweepStimulus()&key).fetch1('stimulus_trace')
#             tau_1_on =.1/1000
#             t = np.arange(0,.001,1/e_sr)
#             f_on = np.exp(t/tau_1_on) 
#             f_on = f_on/np.max(f_on)
#             kernel = np.concatenate([f_on,np.zeros(len(t))])[::-1]
#             kernel  = kernel /sum(kernel )  
#             i_conv = np.convolve(i,kernel,'same')
#             v_comp = (v - i_conv*uncompensatedRS*10**6) - junction_potential
#             key['response_trace_corrected'] = v_comp
#             #%
#             self.insert1(key,skip_duplicates=True)
#         except:
#             print(key)
# # =============================================================================
# #         downsample_factor = int(np.round(e_sr/downsampled_rate))
# #         #%downsampling
# #         v_out = moving_average(v_comp, n=downsample_factor)
# #         v_out = v_out[int(downsample_factor/2)::downsample_factor]
# #         i_out = moving_average(i, n=downsample_factor)
# #         i_out = i_out[int(downsample_factor/2)::downsample_factor]
# #         t_out = moving_average(trace_t, n=downsample_factor)
# #         t_out = t_out[int(downsample_factor/2)::downsample_factor]
# # =============================================================================
# =============================================================================
    

@schema
class SweepFrameTimes(dj.Computed):
    definition = """
    -> ephys_cell_attached.Sweep
    ---
    frame_idx : longblob # index of positive square pulses
    frame_sweep_time : longblob  # time of exposure relative to sweep start in seconds
    frame_time : longblob  # time of exposure relative to recording start in seconds
    """    
    def make(self, key):
        #%%
       # key = {'subject_id': 471997, 'session': 1, 'cell_number': 1,'sweep_number':0}#{'subject_id':456462,'session':1,'cell_number':3,'sweep_number':24}
        exposure = (ephys_cell_attached.SweepImagingExposure()&key).fetch('imaging_exposure_trace')
        if len(exposure)>0:
            si = 1/(ephys_cell_attached.SweepMetadata()&key).fetch('sample_rate')[0]
            sweeptime = float((ephys_cell_attached.Sweep()&key).fetch('sweep_start_time')[0])
            exposure = np.diff(exposure[0])
            peaks = signal.find_peaks(exposure,height = 1)
            peaks_idx = peaks[0]
            #%
            difi = np.diff(peaks_idx)
            #difi[-1]=1500
            median_dif = np.median(difi)
            if sum(difi>10*median_dif)>0:
                needed_idx_end = np.argmax(np.concatenate([[0],difi])>2*median_dif)
                peaks_idx=peaks_idx[:needed_idx_end]
            key['frame_idx']= peaks_idx 
            key['frame_sweep_time']= peaks_idx*si
            key['frame_time']= peaks_idx*si + sweeptime
            #%%
            self.insert1(key,skip_duplicates=True)
    
    
    
    
# =============================================================================
#     step = 100
#     key = {
#            'subject_id' : 453476,
#            'session':29,
#            'cell_number':1,
#            'sweep_number':3,
#            'square_pulse':0}
#     sqstart = trace[start_idx-step:start_idx+step]
#     sqend = trace[end_idx-step:end_idx+step]
#     time = np.arange(-step,step)/sr*1000
#     fig=plt.figure()
#     ax_v=fig.add_axes([0,0,.8,.8])
#     ax_v.plot(time,sqstart)    
#     ax_v.plot([time_back/2*-1*1000,(time_forward/2+time_capacitance)*1000],[v0_start,vrs_start],'o')    
#     ax_v.plot(time,sqend)    
#     ax_v.plot([time_back/2*-1*1000,(time_forward/2+time_capacitance)*1000],[v0_end,vrs_end],'o')    
# =============================================================================

