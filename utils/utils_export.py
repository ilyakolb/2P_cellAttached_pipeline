import datajoint as dj
dj.conn()
from pipeline import pipeline_tools,lab, experiment, ephys_cell_attached,ephysanal_cell_attached, imaging, imaging_gt
import numpy as np
import os
import matplotlib.pyplot as plt
import shutil
import pandas as pd
from pathlib import Path
from utils import utils_plot, utils_ephys
#%%
def export_s2f_data_from_datajoint():
    #%% export traces for s2f
    # this script locates the cells with highest snr for each sensor, then exports the first n cells or m movies, whichever comes first
    fig = plt.figure(figsize = [15,5])
    ax_ophys=fig.add_subplot(2,1,1)
    ax_ephys=fig.add_subplot(2,1,2,sharex = ax_ophys)
    #%
    savedir = '/home/rozmar/Data/Calcium_imaging/GCaMP8_exported_ROIs_s2f'
    files_alread_saved = os.listdir(savedir)
    #savedir = '/home/rozmar/Network/rozsam_google_drive/Data_to_share/GCaMP8_exported_ROIs_s2f'
    roi_crit = {'channel_number':1,
                'motion_correction_method':'Suite2P',
                'roi_type':'Suite2P',
                'neuropil_number':1}
    max_sweep_ap_hw_std_per_median =  .2
    min_sweep_ap_snr_dv_median = 10
    ephys_quality_crit_1 = 'sweep_ap_snr_dv_median>={}'.format(min_sweep_ap_snr_dv_median)
    ephys_quality_crit_2 = 'sweep_ap_hw_std_per_median<={}'.format(max_sweep_ap_hw_std_per_median)
    calcium_sensors = np.unique(imaging_gt.SessionCalciumSensor().fetch('session_calcium_sensor'))
    max_cells_to_export = 200 # per sensor
    max_movies_to_export = 2000 #per sensor
    for sensor in calcium_sensors:
        sensor_crit = 'session_calcium_sensor="{}"'.format(sensor)
        movies_all = (ephysanal_cell_attached.SweepAPQC()*imaging_gt.SessionCalciumSensor()*imaging_gt.MovieCalciumWaveSNR() & sensor_crit&ephys_quality_crit_1&ephys_quality_crit_2)
        subject_ids = np.unique(movies_all.fetch('subject_id'))
        median_cell_snr_list = list()
        subject_id_list = list()
        cell_number_list = list()
        movie_number_list = list()
        for subject_id in subject_ids:
            subject_crit = 'subject_id = {}'.format(subject_id)
            cell_numbers = np.unique((movies_all*imaging_gt.ROISweepCorrespondance() & subject_crit).fetch('cell_number'))
            for cell_number in cell_numbers:
                cell_crit = 'cell_number = {}'.format(cell_number)
                cell_snrs = (movies_all*imaging_gt.ROISweepCorrespondance()&subject_crit&cell_crit).fetch('movie_median_cawave_snr_per_ap')
                median_cell_snr_list.append(np.median(cell_snrs))
                movie_number_list.append(len(cell_snrs))
                subject_id_list.append(np.median(subject_id))
                cell_number_list.append(np.median(cell_number))
         #%
        cell_number_list=np.asarray(cell_number_list)
        subject_id_list=np.asarray(subject_id_list)
        median_cell_snr_list=np.asarray(median_cell_snr_list)
        movie_number_list=np.asarray(movie_number_list)
        order = np.argsort(median_cell_snr_list)
        median_cell_snr_list = median_cell_snr_list[order][::-1]
        subject_id_list = subject_id_list[order][::-1]
        cell_number_list = cell_number_list[order][::-1]
        movie_number_list = movie_number_list[order][::-1]
        
        cell_counter = 0
        movie_counter = 0
        for subject_id,cell_number,median_cell_snr in zip(subject_id_list,cell_number_list,median_cell_snr_list):
            if median_cell_snr<np.median(median_cell_snr_list):
                break
            if cell_counter>max_cells_to_export or movie_counter > max_movies_to_export:
                break
            cell_counter+=1
            #%
            subject_crit = 'subject_id = {}'.format(subject_id)
            cell_crit = 'cell_number = {}'.format(cell_number)
            cell_movies = movies_all*imaging_gt.ROISweepCorrespondance() & subject_crit & cell_crit# &'sweep_number = 2'
            snrs,movie_numbers = cell_movies.fetch('movie_median_cawave_snr_per_ap','movie_number')
            order = np.argsort(snrs)[::-1]
            snrs = snrs[order]
            movie_numbers = movie_numbers[order]
            for movie_number, snr in zip(movie_numbers,snrs):
                dj.conn().connect()
                try:
                    filename = 'sensor_{}_subject_{}_cell_{}_movie_{}_snr_{:.2f}'.format(sensor,int(subject_id),int(cell_number),int(movie_number),snr)
                    if filename+'.npz' in files_alread_saved:
                        print('{} already saved'.format(filename))
                        continue
                    else:
                        print('exporting {}'.format(filename))
                    movie_crit = 'movie_number = {}'.format(movie_number)
                    big_table = ephys_cell_attached.SweepMetadata()*imaging.ROI()*imaging.ROITrace()*imaging.ROINeuropilTrace()*imaging.MovieFrameTimes()*cell_movies&movie_crit&roi_crit#*ephysanal_cell_attached.ActionPotential()
                    
                    roi_f,neuropil_f,frame_times,roi_time_offset = big_table.fetch1('roi_f','neuropil_f','frame_times','roi_time_offset') #ap_times
                    ap_max_times = (ephysanal_cell_attached.ActionPotential()*cell_movies&movie_crit&roi_crit).fetch('ap_max_time')
                    cell_recording_start, session_time = (ephys_cell_attached.Cell()*experiment.Session()*cell_movies&movie_crit).fetch1('cell_recording_start', 'session_time')
                    
                    sweep_start_time =  (ephys_cell_attached.Sweep()*cell_movies&movie_crit).fetch1('sweep_start_time')
                    response_trace, sample_rate = (ephys_cell_attached.SweepMetadata()*ephys_cell_attached.SweepResponse()*cell_movies&movie_crit).fetch1('response_trace','sample_rate')
    
                    ephys_time = np.arange(len(response_trace))/sample_rate
                    frame_times = frame_times - ((cell_recording_start-session_time).total_seconds()+float(sweep_start_time)) +roi_time_offset
    
                    roi_f_corr = roi_f-.8*neuropil_f
                    dff = (roi_f_corr-np.percentile(roi_f_corr,10))/np.percentile(roi_f_corr,10)
                    
                    np.savez_compressed(os.path.join(savedir,filename+'.npz'),
                                                                 F=roi_f,
                                                                 Fneu = neuropil_f,
                                                                 framerate = np.median(np.diff(frame_times)),
                                                                 ap_times=ap_max_times,
                                                                 frame_times = frame_times,
                                                                 ephys_time = ephys_time,
                                                                 ephys_raw = response_trace)
                    ax_ophys.cla()
                    ax_ephys.cla()
                    ax_ophys.plot(frame_times,dff,'g-')
                    ax_ophys.plot(np.asarray(ap_max_times,'float'),np.zeros(len(ap_max_times))-.5,'r|')
                    ax_ephys.plot(ephys_time,response_trace,'k-')
                    ax_ephys.set_xlabel('Time (s)')
                    ax_ephys.set_ylabel('ephys')
                    ax_ophys.set_ylabel('dF/F')
                    ax_ephys.set_xlim([0,np.max(ephys_time)])
                    fig.savefig(os.path.join(savedir,filename+'.png'), bbox_inches='tight')
                    movie_counter+=1
                except:
                    print('error with this record')
                    cell_movies&movie_crit&roi_crit
                    
#%%
                    

def plot_movie(key,title = '',filter_sigma = 5):
    cell_recording_start, session_time = (ephys_cell_attached.Cell()*experiment.Session()&key).fetch1('cell_recording_start', 'session_time')

    imaging_table = imaging.MovieFrameTimes()*imaging.ROI()*imaging.ROINeuropilTrace()*imaging.ROITrace()*imaging_gt.ROISweepCorrespondance()
    roi_f,neuropil_f,roi_time_offset,frame_times = (imaging_table&key).fetch1('roi_f','neuropil_f','roi_time_offset','frame_times')
    frame_times = frame_times+ roi_time_offset      
    frame_rate = np.median(np.diff(frame_times))
    if filter_sigma>0:
        roi_f = utils_plot.gaussFilter(roi_f,frame_rate,filter_sigma)
        neuropil_f = utils_plot.gaussFilter(neuropil_f,frame_rate,filter_sigma) 
        
    roi_f_corr = roi_f-neuropil_f*0.8
    f0 = np.percentile(roi_f_corr,10)
    roi_dff = (roi_f_corr-f0)/f0

    sweep_start_time =  (ephys_cell_attached.Sweep()&key).fetch1('sweep_start_time')
    response_trace, sample_rate = (ephys_cell_attached.SweepMetadata()*ephys_cell_attached.SweepResponse()&key).fetch1('response_trace','sample_rate')
    response_trace,stim_idxs,stim_amplitudes = utils_ephys.remove_stim_artefacts_without_stim(response_trace, sample_rate)
    response_trace_filt = utils_plot.hpFilter(response_trace, 50, 1, sample_rate, padding = True)
    response_trace_filt = utils_plot.gaussFilter(response_trace_filt,sample_rate,sigma = .0001)
    
    ephys_time = np.arange(len(response_trace))/sample_rate
    frame_times = frame_times - ((cell_recording_start-session_time).total_seconds()+float(sweep_start_time))

    ap_max_times,ap_max_indices=(ephysanal_cell_attached.ActionPotential()&key).fetch('ap_max_time','ap_max_index')
    
    fig = plt.figure(figsize = [10,10])
    ax_ophys = fig.add_subplot(2,1,1)
    ax_ephys = fig.add_subplot(2,1,2,sharex = ax_ophys)
    ax_ophys.plot(frame_times,roi_dff,'g-')
    ax_ophys.plot(np.asarray(ap_max_times,'float'),np.zeros(len(ap_max_times))-.5,'r|')
    ax_ephys.plot(ephys_time,response_trace_filt,'k-')
    ax_ophys.set_title(title)
    data_dict = {'dff':roi_f_corr,
                'frame_times':frame_times,
                'ephys_trace':response_trace_filt,
                'ephys_time':ephys_time,
                'ap_max_times':np.asarray(ap_max_times,float)}
    return data_dict, fig

def export_high_snr_movies_from_datajoint():
    save_dir = '/home/rozmar/Data/Calcium_imaging/good_snr_movies_for_Ilya'
    
    
    sensors = np.unique(imaging_gt.SessionCalciumSensor().fetch('session_calcium_sensor'))
    for sensor in sensors:
        sensor_df = pd.DataFrame(imaging_gt.ROISweepCorrespondance()*imaging_gt.SessionCalciumSensor()*imaging_gt.MovieCalciumWaveSNR()&'session_calcium_sensor = "{}"'.format(sensor))
        sensor_df = sensor_df.sort_values('movie_median_cawave_snr_per_ap',ascending=False)
        for movie_row in sensor_df[:5].iterrows():
            movie_row = movie_row[1]
            dest_dir = os.path.join(save_dir,
                                    '{sensor}_{subject}_cell{cell}_movie{movie}_snr{snr:.2f}'.format(sensor = sensor,
                                                                                                subject = movie_row['subject_id'],
                                                                                                cell = movie_row['cell_number'],
                                                                                                movie = movie_row['movie_number'],
                                                                                                snr = movie_row['movie_median_cawave_snr_per_ap'] ))
            if os.path.isdir(dest_dir):
                continue
            key = {'subject_id': movie_row['subject_id'],
                   'session':movie_row['session'],
                   'cell_number':movie_row['cell_number'],
                   'sweep_number':movie_row['sweep_number'],  
                   'movie_number':movie_row['movie_number'],
                   'motion_correction_method':"Suite2P",# the second four entries restrict the imaging data (see above)
                   'roi_type':"Suite2P",
                   'channel_number':1,
                   'neuropil_number':1}
            #print(movie_row)
            data_dict,fig = plot_movie(key,title = imaging.Movie()&key)
            reg_movie_file_repository,reg_movie_file_directory,reg_movie_file_name = (imaging.RegisteredMovieFile()&key).fetch('reg_movie_file_repository','reg_movie_file_directory','reg_movie_file_name')
            source_dir = os.path.join(dj.config['locations.{}'.format(reg_movie_file_repository[0])],reg_movie_file_directory[0])
            
            regtiff_dest_dir = os.path.join(dest_dir,'regtiff')
            Path(regtiff_dest_dir).mkdir(parents=True, exist_ok=True)
            for fname in reg_movie_file_name:
                shutil.copy(os.path.join(source_dir,fname),os.path.join(regtiff_dest_dir,fname))
                
            np.savez_compressed(os.path.join(dest_dir,'data.npz'),
                                dff=data_dict['dff'],
                                frame_times = data_dict['frame_times'],
                                ephys_trace = data_dict['ephys_trace'],
                                ephys_time = data_dict['ephys_time'],
                                ap_max_times = data_dict['ap_max_times'])
            fig.savefig(os.path.join(dest_dir,'movie.png'), bbox_inches='tight')