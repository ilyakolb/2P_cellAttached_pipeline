#These scripts are used during the experiment to quickly visualize the quality of the ephys and the tuning of the cell
#You can also use the datajoint database
#
from utils_ephys import extract_tuning_curve
from utils import utils_ephys
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import re
try:
    import datajoint as dj
    dj.conn()
    from pipeline import pipeline_tools
    from pipeline import lab, experiment, ephys_cell_attached,ephysanal_cell_attached #, ephysanal, imaging
except:
    print('could not connect to datajoint')
#%%

# onlne analysis during the experiment
ephys_basedir = '/home/rozmar/Network/Genie2Prig/imaging_ephys/rozsam'
vis_stim_basedir = '/home/rozmar/Network/Genie2Prig/visual_stim/Visual stim'

#analysis on marton's PC
ephys_basedir = '/home/rozmar/Data/Wavesurfer/Genie_2p_rig'
vis_stim_basedir = '/home/rozmar/Data/Visual_stim/raw/Genie_2P_rig'
suite2p_basedir = '/home/rozmar/Data/Calcium_imaging/suite2p/Genie_2P_rig'

# =============================================================================
# # set folder for analysis on dm11
# #ephys_basedir = '/home/rozmar/Network/dm11/genie/rozsam/raw/movies_ephys'
# vis_stim_basedir = '/home/rozmar/Network/dm11/genie/rozsam/raw/visual_stim'
# suite2p_basedir = '/home/rozmar/Network/dm11/genie/rozsam/suite2p'
# =============================================================================

# =============================================================================
# # parameters
# session = '20200813' #688
# subject = '472181'
# cell = '7'
# runnum = [10]#range(1,20)#[3]#[2] #range(3,20)#[4] # visual stimulus number needed
# roi_num = [3] # suite2p roi number
# =============================================================================
# =============================================================================
# session = '20200814' #686
# subject = '472180'
# cell = '4'
# runnum = [3]#range(1,20)#[3]#[2] #range(3,20)#[4] # visual stimulus number needed
# roi_num = [2] # suite2p roi number
# # parameters
# =============================================================================
session = '20200702'
subject = '478406'
cell = '1'
runnum = [2]#range(1,20)#[3]#[2] #range(3,20)#[4] # visual stimulus number needed
roi_num = [0] # suite2p roi number


# =============================================================================
# sensor = 'GCaMP7f'
# savedir = '/home/rozmar/Data/Calcium_imaging/exported_ROIs_for_Ziqiang'
# 
# =============================================================================




plot_suite2p_output = True
F0win = 80 #s
F_filter_sigma = .001 #seconds
neu_r =.7


uniqueAngles = [ 45,  90, 135, 180, 225, 270, 315, 360]
stim_ap_dict =  {key: list() for key in [str(i) for i in uniqueAngles]} 
baseline_ap_dict = {key: list() for key in [str(i) for i in uniqueAngles]} 
#%
sessions = os.listdir(ephys_basedir)
sessiondir = os.path.join(ephys_basedir,'{}-anm{}'.format(session,subject))
cells = os.listdir(sessiondir)
for celldir in cells:
    if 'cell{}'.format(cell) == celldir.lower():
        break
celldir = os.path.join(sessiondir,celldir)
ephysfiles = os.listdir(celldir)
ephysfiles_real = list()
stimnums=list()
stimidxs = list()
for ephysfile in ephysfiles:
    if '.h5' in ephysfile:
        
        separators = [m.start() for m in re.finditer('_| |-', ephysfile)]
        if int(re.findall(r'\d+', ephysfile[separators[0]+1:separators[1]])[0]) in runnum:
            ephysfiles_real.append(ephysfile)
            stimnums.append(ephysfile[separators[0]+1:separators[1]])
            stimidxs.append(int(re.findall(r'\d+', ephysfile[separators[0]+1:separators[1]])[0]))
ephysfiles_real  = np.asarray(ephysfiles_real)[np.argsort(stimidxs)]       
stimnums = np.asarray(stimnums)[np.argsort(stimidxs)]
vstimdirs=os.listdir(vis_stim_basedir)
data_dicts = list()
for stim,ephysfile in zip(stimnums,ephysfiles_real):  
    #try:
    stimnum = re.findall(r'\d+', stim)[0]
    dirnow_needed = '{}-anm{}'.format(session,subject)
    if dirnow_needed in vstimdirs:
        sessiondir_vstim = os.path.join(vis_stim_basedir,dirnow_needed)
        stimdirs = os.listdir(sessiondir_vstim)
        stimdirs_cellnum=list()
        stimdirs_runnum=list()
        for stimdir_now in stimdirs:
            sepidx = stimdir_now.find('_')
            try:
                stimdirs_cellnum.append(int(stimdir_now[4:sepidx]))
            except:
                stimdirs_cellnum.append(np.nan)
            try:
                stimdirs_runnum.append(int(stimdir_now[sepidx+4:]))
            except:
                stimdirs_runnum.append(np.nan)
            
        stimdirnow_needed = 'cell{}_Run{}'.format(cell,stimnum)
        if any((np.asarray(stimdirs_cellnum)==float(cell)) & (np.asarray(stimdirs_runnum)==float(stimnum))):
            stimdirnow_needed = stimdirs[np.argmax((np.asarray(stimdirs_cellnum)==float(cell)) & (np.asarray(stimdirs_runnum)==float(stimnum)))]
            vstimdir_now = os.path.join(sessiondir_vstim,stimdirnow_needed)
            vstimfile= os.listdir(vstimdir_now)[0]
            #try:
            try: # get ephys data from datajoint
                #%
                key = {'subject_id':int(subject),
                       'session':1,
                       'protocol_name':ephysfile[:-3]}
                sweep_needed = ephys_cell_attached.Sweep()&key
                #%
                sample_rate = (ephys_cell_attached.SweepMetadata()&sweep_needed).fetch1('sample_rate')
                ephys_v_filt = (ephys_cell_attached.SweepResponse&sweep_needed).fetch1('response_trace')
                ephys_t = np.arange(len(ephys_v_filt))/sample_rate
                ap_idx,ap_snr_dv,ap_amplitude,ap_ahp_amplitude,ap_isi,ap_halfwidth,ap_full_width = (ephysanal_cell_attached.ActionPotential()&sweep_needed).fetch('ap_max_index','ap_snr_dv','ap_amplitude','ap_ahp_amplitude','ap_isi','ap_halfwidth','ap_full_width')
                ap_idx = np.asarray(ap_idx,int)
                ap_max_times = ephys_t[ap_idx]
                frame_times = (ephysanal_cell_attached.SweepFrameTimes()&sweep_needed).fetch1('frame_sweep_time')
                data_now = dict()
                data_now['ephys_v_filt'] = ephys_v_filt
                data_now['ephys_t'] = ephys_t
                data_now['ap_idx'] = ap_idx
                data_now['frame_times'] = frame_times
                #%
                fig = plt.figure()
                ax_ephys = fig.add_subplot(311)
                ax_ephys.plot(ephys_t,ephys_v_filt,'k-')
                ax_ephys.plot(ap_max_times,ephys_v_filt[ap_idx],'ro')
                ax_snr = fig.add_subplot(312,sharex = ax_ephys)
                ax_snr.semilogy(ap_max_times,ap_snr_dv,'ro')
                ax_snr.set_ylabel('SNR')
                ax_snr.set_ylim([1,ax_snr.get_ylim()[1]])
                ax_ahp = fig.add_subplot(313)
                ax_ahp.semilogx(ap_isi,ap_ahp_amplitude/ap_amplitude,'ko')
                #%
            except:
                data_now = extract_tuning_curve(WS_path = os.path.join(celldir,ephysfile),vis_path = os.path.join(vstimdir_now,vstimfile),plot_data=True,plot_title = 'anm{}-cell{}-{}'.format(subject,cell,stim))
            
            if plot_suite2p_output:
                #%
                suite2p_cell_path = suite2p_basedir +celldir[len(ephys_basedir):]
                movie_dirs = os.listdir(suite2p_cell_path)
                for movie_dir in movie_dirs:
                    separators = [m.start() for m in re.finditer('_| |-', movie_dir)]
                    if 'cell' not in movie_dir.lower() and len(separators)==1: # HOTFIX first recordings the movie name doesn't include the cell identity
                        separators=[0]+separators
                    elif len(separators)==1:
                        separators=separators + [len(movie_dir)]
                    if 'stack' not in movie_dir and len(re.findall(r'\d+', movie_dir[separators[0]+1:separators[1]]))>0 and int(re.findall(r'\d+', movie_dir[separators[0]+1:separators[1]])[0]) == int(stimnum):
                        #%
                        suite2p_movie_path = os.path.join(suite2p_cell_path,movie_dir,'plane0')
                        F_all = np.load(os.path.join(suite2p_movie_path,'F.npy'))
                        Fneu_all = np.load(os.path.join(suite2p_movie_path,'Fneu.npy'))
                        framerate = int(1/np.mean(np.diff(data_now['frame_times'])))
                        ROI_idx = roi_num[runnum==int(stimnum)]
                        F = F_all[ROI_idx]
                        Fneu = Fneu_all[ROI_idx]
                        
                        
                        F0step= int(F0win/np.mean(np.diff(data_now['frame_times'])))
                        
                        
                        
                        F_orig = F.copy()
                        Fneu_orig = Fneu.copy()
                        #%
                        # - ------ calculate r
                        try:
                            AP_times = data_now['ephys_t'][data_now['ap_idx']]
                            frametimes = data_now['frame_times']
                            decay_time = 4 #s
                            decay_step = int(decay_time*framerate)
                            F_activity = np.zeros(len(frametimes))
                            for ap_time in AP_times:
                                F_activity[np.argmax(frametimes>ap_time)] = 1
                            F_activitiy_conv= np.convolve(F_activity,np.concatenate([np.zeros(decay_step),np.ones(decay_step)]),'same')
                            F_activitiy_conv[:decay_step]=1
                            needed =F_activitiy_conv==0
                            F_orig_filt = utils_ephys.gaussFilter(F_orig,framerate,sigma = F_filter_sigma)
                            Fneu_orig_filt = utils_ephys.gaussFilter(Fneu_orig,framerate,sigma = F_filter_sigma)
                            p=np.polyfit(Fneu_orig_filt[needed],F_orig_filt[needed],1)
                            neu_r = p[0] 
                            if neu_r>1:
                                neu_r = 1
                        except: # fast spiking cells always fire
                            neu_r = .7
                        
# =============================================================================
#                                 neuropilvals = np.asarray([np.min(Fneu_orig_filt[needed]),np.max(Fneu_orig_filt[needed])])
#                                 fittedvals = np.polyval(p,neuropilvals)
#                                 
#                                 plt.plot(Fneu_orig_filt[needed],F_orig_filt[needed],'ko')
#                                 plt.plot(neuropilvals,fittedvals,'r-')
#                                 plt.title(p)
#                                 plt.ylabel('F')
#                                 plt.xlabel('neuropil')
# =============================================================================
                        # - ------ calculate r
                        
                        
                        F = utils_ephys.gaussFilter(F,framerate,sigma = F_filter_sigma)
                        Fneu = utils_ephys.gaussFilter(Fneu,framerate,sigma = F_filter_sigma)
                        F_corr = F-Fneu*neu_r
                        p=np.polyfit(F_corr,utils_ephys.gaussFilter(F,framerate,sigma = F_filter_sigma),1)
                        F_corr =F_corr +p[1]
                        # correct neuropil fluctuations
                        
                        
                        F0 = utils_ephys.rollingfun(F_corr, window = F0step, func = 'min')
                        F0 = utils_ephys.rollingfun(F0, window = int(F0step*1), func = 'max')
                        dFF = (F_corr-F0)/F0
                        #s2p_metadata = np.load(os.path.join(suite2p_movie_path,'ops.npy')).tolist()
                        #%
                        xlims= [np.min(data_now['ephys_t']),np.max(data_now['ephys_t'])]
                        #xlims=[104,105]
                        fig = plt.figure(figsize = [15,10])
                        ax_raw = fig.add_subplot(411)
                        ax_img = fig.add_subplot(412, sharex=ax_raw)
                        ax_dff = fig.add_subplot(413, sharex=ax_raw)
                        ax_ephys = fig.add_subplot(414, sharex=ax_raw)
                        ax_rate = ax_ephys.twinx()
                        ax_raw.plot(data_now['frame_times'],F_orig,'k-')
                        ax_raw.plot(data_now['frame_times'],Fneu_orig,'r-')
                        
                        ax_img.plot(data_now['frame_times'],F_corr,'g-',lw=2)
                        ax_img.plot(data_now['frame_times'],F0,'k-')
                        #ax_img.plot(data_now['ephys_t'][data_now['ap_idx']],np.ones(len(data_now['ap_idx']))*np.min(F),'r|')
                        
                        ax_dff.plot(data_now['frame_times'],dFF,'g-',linewidth=1)
                        ax_dff.plot(data_now['ephys_t'][data_now['ap_idx']],np.ones(len(data_now['ap_idx']))*np.max(dFF)*-0.1,'r|')
                        ax_ephys.plot(data_now['ephys_t'],data_now['ephys_v_filt'],'k-')
                        
                        fr_e, fr_bincenters = utils_ephys.AP_times_to_rate(data_now['ephys_t'][data_now['ap_idx']],firing_rate_window=1)
                        ax_rate.plot(fr_bincenters,fr_e,'r-')
                        
                        
                        ax_raw.set_xlim(xlims)
                        ax_img.set_xlim(xlims)
                        ax_dff.set_xlim(xlims)
                        ax_ephys.set_xlim(xlims)
                        plt.show()
                        
# =============================================================================
#                         np.savez_compressed(os.path.join(savedir,'sensor_{}_subject_{}_cell_{}_run_{}.npz'.format(sensor,subject,cell,runnum[0])),
#                                                                      F=F,
#                                                                      Fneu = Fneu,
#                                                                      framerate = framerate,
#                                                                      ap_times=ap_max_times,
#                                                                      frame_times = frame_times,
#                                                                      neuropil_r = neu_r)
#                         fig.savefig(os.path.join(savedir,'sensor_{}_subject_{}_cell_{}_run_{}.png'.format(sensor,subject,cell,runnum[0])), bbox_inches='tight')
# =============================================================================
                    
                        
                    
                #%
            if type(data_now)==dict:
                data_dicts.append(data_now)
                for a in uniqueAngles:
                    idx = data_now['uniqueAngles'] == a
                    if any(idx):
                        stim_ap_dict[str(a)].extend(data_now['allSpikes'][idx][0])
                        baseline_ap_dict[str(a)].extend(data_now['allSpikes_baseline'][idx][0])
# =============================================================================
#                 except ValueError:
#                     pass
# =============================================================================
        else:
            print(stimdirnow_needed+' not found')
# =============================================================================
#     except:
#         pass
# =============================================================================
#%
stim_ap_dict_orig = stim_ap_dict.copy()        
baseline_ap_dict_orig = baseline_ap_dict.copy()   
#%


#%%
plt.figure()
stim_ap_dict = stim_ap_dict_orig.copy()        
baseline_ap_dict = baseline_ap_dict_orig.copy()        
maxlength = 0
for keynow in stim_ap_dict.keys():
    maxlength = np.max([len(stim_ap_dict[keynow]),maxlength])
    #%
    
for keynow in stim_ap_dict.keys():
    if maxlength>len(stim_ap_dict[keynow]):
        stim_ap_dict[keynow] = stim_ap_dict[keynow].extend(np.zeros(maxlength - len(stim_ap_dict[keynow]))*np.nan)
        baseline_ap_dict[keynow] = baseline_ap_dict[keynow].extend(np.zeros(maxlength - len(baseline_ap_dict[keynow]))*np.nan)
        
df_stim = pd.DataFrame(stim_ap_dict)
df_baseline = pd.DataFrame(baseline_ap_dict)
df_apdiff = df_stim-df_baseline
df_apdiff_div = df_stim/df_baseline
df_apdiff_div = df_apdiff_div.replace(np.inf, np.nan)
#%
sns.swarmplot(data=df_apdiff,color='k')
plt.errorbar(df_apdiff.keys(),df_apdiff.mean(skipna=True),df_apdiff.std(skipna=True),color='red',linewidth=4)
plt.xlabel('Angle')
plt.ylabel('Firing rate change')
plt.show()


plt.figure()
#plt.yscale('log')
sns.swarmplot(data=df_apdiff_div,color='k')
plt.errorbar(df_apdiff_div.keys(),df_apdiff_div.mean(skipna=True),df_apdiff_div.std(skipna=True),color='red',linewidth=4)
plt.xlabel('Angle')
plt.ylabel('Firing rate fold-change')

#plt.ylim([.01,100])
plt.show()

#%%