from __future__ import annotations
import datajoint as dj
import pandas as pd
import numpy as np
import warnings
from pathlib import Path
import tomli
import tdt
import scipy.io as spio
from scipy import signal
from scipy.fft import fft, ifft, rfft
from copy import deepcopy

from element_interface.utils import find_full_path
from workflow import db_prefix
from workflow.pipeline import session, subject, lab, reference
from workflow.utils.paths import get_raw_root_data_dir
import workflow.utils.photometry_preprocessing as pp
from workflow.utils import demodulation


logger = dj.logger
schema = dj.schema(db_prefix + "photometry")


@schema
class SensorProtein(dj.Lookup):
    definition = """            
    sensor_protein_name : varchar(16)  # (e.g., GCaMP, dLight, etc)
    """


@schema
class LightSource(dj.Lookup):
    definition = """
    light_source_name   : varchar(16)
    """
    contents = zip(["Plexon LED", "Laser"])


@schema
class ExcitationWavelength(dj.Lookup):
    definition = """
    excitation_wavelength   : smallint  # (nm)
    """


@schema
class EmissionColor(dj.Lookup):
    definition = """
    emission_color     : varchar(10) 
    ---
    wavelength=null    : smallint  # (nm)
    """

@schema
class CarrierFrequency(dj.Lookup):
    definition = """
    carrier_frequency     : smallint 
    ---
    wavelength=null    : smallint  # (nm)
    """


@schema
class FiberPhotometry(dj.Imported):
    definition = """
    -> session.Session
    ---
    -> [nullable] LightSource
    raw_sample_rate         : float         # sample rate of the raw data (in Hz) 
    beh_synch_signal=null   : longblob      # signal for behavioral synchronization from raw data
    """

    class Fiber(dj.Part):
        definition = """ 
        -> master
        fiber_id            : tinyint unsigned
        -> reference.Hemisphere
        ---
        notes=''             : varchar(1000)  
        """

    class DemodulatedTrace(dj.Part):
        definition = """ # demodulated photometry traces
        -> master.Fiber
        trace_name          : varchar(8)  # (e.g., raw, detrend)
        -> EmissionColor
        ---
        -> [nullable] SensorProtein          
        -> [nullable] ExcitationWavelength
        -> [nullable] CarrierFrequency
        demod_sample_rate   : float       # sample rate of the demodulated data (in Hz) 
        trace               : longblob    # demodulated photometry traces
        """

    def make(self, key):
        
        # Find data dir
        #first determine data type e.g. raw matlab, processed matlab, or tdt
        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
        photometry_dir = session_full_dir / "Photometry"

        # Read from the meta_info.toml in the photometry folder if exists
        meta_info_file = list(photometry_dir.glob("*.toml"))[0]
        meta_info = {}
        try:
            with open(meta_info_file, "rb") as f:
                meta_info = tomli.load(f)
        except FileNotFoundError:
            logger.info("meta info is missing")
        light_source_name = meta_info.get("Fiber", {}).get("light_source", "")

        # Scan directory for data format
        # If there is a .tdt file, then it is a tdt data and enter tdt_data mode
        # If there is a data*.mat file, then it is a matlab data and enter matlab_data mode
        # If there is a timeseries2.mat file, then it is demux matlab data and enter demux_matlab_data mode  
        if len(list(photometry_dir.glob("data*.mat"))) > 0:
            data_format = "matlab_data"
            matlab_data: dict = spio.loadmat(
            next(photometry_dir.glob("data*.mat")), simplify_cells=True)
            matlab_data=matlab_data["data"]
        elif len(list(photometry_dir.glob("*timeseries_2.mat"))) > 0:
            data_format = "demux_matlab_data"
            demux_matlab_data: list[dict] = spio.loadmat(
                next(photometry_dir.glob("*timeseries_2.mat")), simplify_cells=True
            )["timeSeries"]
        elif len(list(photometry_dir.glob("*.t*"))) > 0:
            data_format = "tdt_data"
            tdt_data: tdt.StructType = tdt.read_block(photometry_dir)      
        
        ## Enter into different data format mode
        if data_format == "matlab_data":
            #matlab_data
            raw_sample_rate = meta_info.get("Processing_Parameters").get("sampling_frequency")

            #Get index of traces
            trace_indices = meta_info.get("Signal_Indices")
            carrier_g_right = matlab_data[trace_indices.get("right").get("carrier_g", None)]
            carrier_r_right =matlab_data[trace_indices.get("right").get("carrier_r", None)]
            photom_g_right = matlab_data[trace_indices.get("right").get("photom_g", None)]
            photom_r_right = matlab_data[trace_indices.get("right").get("photom_r", None)]
            carrier_g_left = matlab_data[trace_indices.get("left").get("carrier_g", None)]
            carrier_r_left = matlab_data[trace_indices.get("left").get("carrier_r", None)]
            photom_g_left = matlab_data[trace_indices.get("left").get("photom_g", None)]
            photom_r_left = matlab_data[trace_indices.get("left").get("photom_r", None)]

            raw_photom_list: list[dict]=[photom_g_right, photom_r_right, 
                                         photom_g_left, photom_r_left]
            raw_carrier_list: list[dict]=[carrier_g_right, carrier_r_right,
                                            carrier_g_left, carrier_r_left]

            # Get processing parameters
            processing_parameters = meta_info.get("Processing_Parameters")
            beh_synch_signal = processing_parameters.get("behavior_offset", 0)
            window = processing_parameters.get("z_window", 60)
            #process_z = processing_parameters.get("z", False)
            set_carrier_g_right = processing_parameters.get("left").get("carrier_frequency_g", 0)
            set_carrier_r_right = processing_parameters.get("left").get("carrier_frequency_r", 0)
            set_carrier_g_left = processing_parameters.get("right").get("carrier_frequency_g", 0)
            set_carrier_r_left = processing_parameters.get("right").get("carrier_frequency_r", 0)
            bp_bw = processing_parameters.get("bandpass_bandwidth", 0.5)
            sampling_Hz = processing_parameters.get("sampling_frequency", None)
            downsample_Hz = processing_parameters.get("downsample_frequency", 200)
            transform = processing_parameters.get("transform", {})
            num_perseg = processing_parameters.get("no_per_segment", 216)
            n_overlap = processing_parameters.get("noverlap", 108)

            window1 = round(window * sampling_Hz)

            set_carrier_list: list[dict]=[set_carrier_g_right, set_carrier_r_right,
                                            set_carrier_g_left, set_carrier_r_left]
            
            # Get calculated carrier freqeuncy from matlab_data
            calc_carry_list = demodulation.calc_carry(raw_carrier_list, sampling_Hz)
            for i in range(len(set_carrier_list)):
                    if calc_carry_list[i] != (set_carrier_list[i] >= calc_carry_list[i]+5 or set_carrier_list[i] <= calc_carry_list[i]-5):
                        warnings.warn("Calculated carrier frequency does not match set carrier frequency. Using calculated carrier frequency.")
                        set_carrier_list = calc_carry_list
                    else:
                        calc_carry_list = calc_carry_list
            
            four_list = demodulation.four(raw_photom_list)
            #demodulate photometry data
            z1_trace_list, power_spectra_list, t_list, spect_power_list = demodulation.process_trace(
                                raw_photom_list, calc_carry_list,
                                sampling_Hz, window1, num_perseg, n_overlap)
            
            # Store data in this list for ingestion
            fiber_list: list[dict] = []
            demodulated_trace_list: list[dict] = []

            fibers: list[str] = [ "right", "left"]

            side_to_fiber_id_mapping = {"right": 1, "left": 2}
            color_mapping = {"g": "green", "r": "red", "b": "blue"}

        # Get photometry traces for each fiber
            for fiber in fibers:
                 
                fiber_notes = meta_info.get("Fiber").get("implantation").get(f'{fiber}').get("notes", None)
                #fiber_diam = meta_info.get("Fiber").get("fiber_diameter", None)
                #hemisphere = meta_info.get("Experiment").get("hemisphere")
                fiber_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "notes": fiber_notes,
                    }
                    )
            
            trace_names = meta_info.get("Signal_Indices").get(f'{fiber}')
            for trace_name in trace_names:

                # Populate EmissionColor if present
                emission_color = color_mapping[trace_name.split("_")[1][0]]

                emission_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("emission_wavelength", {})
                    .get(emission_color, None)
                )

                EmissionColor.insert1(
                    {
                        "emission_color": emission_color,
                        "wavelength": emission_wavelength,
                    },
                    skip_duplicates=True,
                )

                # Populate SensorProtein if present
                sensor_protein = (
                    meta_info.get("VirusInjection", {})
                    .get(f'{fiber}', {})
                    .get("sensor_protein", {})
                    .get(emission_color, None)
                )
                if sensor_protein:
                    logger.info(
                        f"{sensor_protein} is inserted into {__name__}.SensorProtein"
                    )
                    SensorProtein.insert1(
                        {"sensor_protein_name": sensor_protein}, skip_duplicates=True
                    )

                # Populate ExcitationWavelength if present
                excitation_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("excitation_wavelength", {})
                    .get(emission_color, None)
                )

                if excitation_wavelength:
                    logger.info(
                        f"{excitation_wavelength} is inserted into {__name__}.ExcitationWavelength"
                    )
                    ExcitationWavelength.insert1(
                        {"excitation_wavelength": excitation_wavelength},
                        skip_duplicates=True,
                    )
                
                raw_photom_list: list[dict]=[photom_g_right, photom_r_right, 
                                         photom_g_left, photom_r_left]
                raw_carrier_list: list[dict]=[carrier_g_right, carrier_r_right,
                                            carrier_g_left, carrier_r_left]
                carrier_ind = {"g_right":0, "r_right":1, "g_left":2, "r_left":3}
                carrier_frequency = calc_carry_list[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

                demod_trace = spect_power_list[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

                if carrier_frequency:
                    logger.info(
                        f"{carrier_frequency} is inserted into {__name__}.CarrierFrequency"
                    )
                    CarrierFrequency.insert1(
                        {"carrier_frequency": carrier_frequency},
                        skip_duplicates=True,
                    )
                    
                demodulated_trace_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": emission_color,
                        "sensor_protein_name": sensor_protein,
                        "excitation_wavelength": excitation_wavelength,
                        "carrier_frequency": carrier_frequency,
                        "trace": demod_trace,
                    }
                )

            # Populate FiberPhotometry
            logger.info(f"Populate {__name__}.FiberPhotometry")
            self.insert1(
                {
                    **key,
                    "light_source_name": light_source_name,
                    "raw_sample_rate": raw_sample_rate,
                    "beh_synch_signal": beh_synch_signal,
                }
            )

            # Populate FiberPhotometry.Fiber
            logger.info(f"Populate {__name__}.FiberPhotometry.Fiber")
            self.Fiber.insert(fiber_list)

            # Populate FiberPhotometry.DemodulatedTrace
            logger.info(f"Populate {__name__}.FiberPhotometry.DemodulatedTrace")
            self.DemodulatedTrace.insert(demodulated_trace_list)
            

            del matlab_data
            #matlab_data
            
        elif data_format == "demux_matlab_data":
            #demux_matlab_data
            
            raw_sample_rate = None
            beh_synch_signal = demux_matlab_data[0]["time_offset"]

            #Get index of traces
            trace_indices = meta_info.get("Signal_Indices")
            carrier_g_right = trace_indices.get("right").get("carrier_g", None)
            carrier_r_right =trace_indices.get("right").get("carrier_r", None)
            photom_g_right = trace_indices.get("right").get("photom_g", None)
            photom_r_right = trace_indices.get("right").get("photom_r", None)
            carrier_g_left = trace_indices.get("left").get("carrier_g", None)
            carrier_r_left = trace_indices.get("left").get("carrier_r", None)
            photom_g_left = trace_indices.get("left").get("photom_g", None)
            photom_r_left = trace_indices.get("left").get("photom_r", None)

            # Get demodulated sample rate
            demod_sampling: list[float] = []
            for demod in demux_matlab_data:
                demod_sample_rate_g_left = demux_matlab_data[carrier_g_left]["demux_freq"]
                demod_sample_rate_r_left = demux_matlab_data[carrier_r_left]["demux_freq"]
                demod_sample_rate_g_right = demux_matlab_data[carrier_g_right]["demux_freq"]
                demod_sample_rate_r_right = demux_matlab_data[carrier_r_right]["demux_freq"]
            demod_sampling.append(demod_sample_rate_g_right)
            demod_sampling.append(demod_sample_rate_r_right)
            demod_sampling.append(demod_sample_rate_g_left)
            demod_sampling.append(demod_sample_rate_r_left)
            
            
            # Store data in this list for ingestion
            fiber_list: list[dict] = []
            demodulated_trace_list: list[dict] = []

            fiber_list: list[dict] = []
            demodulated_trace_list: list[dict] = []

            fibers: list[str] = [ "right", "left"]

            side_to_fiber_id_mapping = {"right": 1, "left": 2}
            color_mapping = {"g": "green", "r": "red", "b": "blue"}

            # Get photometry traces for each fiber
            for fiber in fibers:
                 
                fiber_notes = meta_info.get("Fiber").get("implantation").get(f'{fiber}').get("notes", None)
                #fiber_diam = meta_info.get("Fiber").get("fiber_diameter", None)
                #hemisphere = meta_info.get("Experiment").get("hemisphere")
                fiber_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "notes": fiber_notes,
                    }
                    )
                
            trace_names = meta_info.get("Signal_Indices").get(f'{fiber}')
            for trace_name in trace_names:

                # Populate EmissionColor if present
                emission_color = color_mapping[trace_name.split("_")[1][0]]

                emission_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("emission_wavelength", {})
                    .get(emission_color, None)
                )

                EmissionColor.insert1(
                    {
                        "emission_color": emission_color,
                        "wavelength": emission_wavelength,
                    },
                    skip_duplicates=True,
                )

                # Populate SensorProtein if present
                sensor_protein = (
                    meta_info.get("VirusInjection", {})
                    .get(f'{fiber}', {})
                    .get("sensor_protein", {})
                    .get(emission_color, None)
                )
                if sensor_protein:
                    logger.info(
                        f"{sensor_protein} is inserted into {__name__}.SensorProtein"
                    )
                    SensorProtein.insert1(
                        {"sensor_protein_name": sensor_protein}, skip_duplicates=True
                    )

                # Populate ExcitationWavelength if present
                excitation_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("excitation_wavelength", {})
                    .get(emission_color, None)
                )

                if excitation_wavelength:
                    logger.info(
                        f"{excitation_wavelength} is inserted into {__name__}.ExcitationWavelength"
                    )
                    ExcitationWavelength.insert1(
                        {"excitation_wavelength": excitation_wavelength},
                        skip_duplicates=True,
                    )

                ##pull out the data from the matlab file
            for sensor_protein in ["g_left", "r_left", "g_right", "r_right"]:
                    if sensor_protein == "g_left":
                        photometry_demux_g_left = demux_matlab_data[photom_g_left]['data']
                    elif sensor_protein == "r_left":
                        photometry_demux_r_left = demux_matlab_data[photom_r_left]['data']
                    elif sensor_protein == "g_right":
                        photometry_demux_g_right = demux_matlab_data[photom_g_right]['data']
                    elif sensor_protein == "r_right":
                        photometry_demux_r_right = demux_matlab_data[photom_r_right]['data']
                    else:
                        raise ValueError("Sensor Protein must be g or r")
            demux_trace_list: list[dict] = []
            demux_trace_list.append(photometry_demux_g_right)
            demux_trace_list.append(photometry_demux_r_right)
            demux_trace_list.append(photometry_demux_g_left)
            demux_trace_list.append(photometry_demux_r_left)

            carrier_ind = {"g_right":0, "r_right":1, "g_left":2, "r_left":3}
            carrier_frequency = demod_sampling[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

            demod_trace = demux_trace_list[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

            if carrier_frequency:
                logger.info(
                    f"{carrier_frequency} is inserted into {__name__}.CarrierFrequency"
                )
                CarrierFrequency.insert1(
                    {"carrier_frequency": carrier_frequency},
                    skip_duplicates=True,
                )
            
                            
            demodulated_trace_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": emission_color,
                        "sensor_protein_name": sensor_protein,
                        "excitation_wavelength": excitation_wavelength,
                        "carrier_frequency": carrier_frequency,
                        "trace": demod_trace,
                    }
                )
                    
                # Populate FiberPhotometry
            logger.info(f"Populate {__name__}.FiberPhotometry")
            self.insert1(
                        {
                            **key,
                            "light_source_name": light_source_name,
                            "raw_sample_rate": sampling_Hz,
                            "beh_synch_signal": beh_synch_signal,
                        }
                    )

                    # Populate FiberPhotometry.Fiber
            logger.info(f"Populate {__name__}.FiberPhotometry.Fiber")
            self.Fiber.insert(fiber_list)

                    # Populate FiberPhotometry.DemodulatedTrace
            logger.info(f"Populate {__name__}.FiberPhotometry.DemodulatedTrace")
            self.DemodulatedTrace.insert(demodulated_trace_list)

            del demux_matlab_data
            #demux_matlab_data


        elif data_format == "tdt_data":
            #tdt_data             
                        
            # Get trace indices from meta_info
            trace_indices = meta_info.get("Signal_Indices")
            carrier_g_right = tdt_data.streams.Fi1r.data[trace_indices.get("right").get("carrier_g", None)]
            carrier_r_right =tdt_data.streams.Fi1r.data[trace_indices.get("right").get("carrier_r", None)]
            photom_g_right = tdt_data.streams.Fi1r.data[trace_indices.get("right").get("photom_g", None)]
            photom_r_right = tdt_data.streams.Fi1r.data[trace_indices.get("right").get("photom_r", None)]
            carrier_g_left = tdt_data.streams.Fi2r.data[trace_indices.get("left").get("carrier_g", None)]
            carrier_r_left = tdt_data.streams.Fi2r.data [trace_indices.get("left").get("carrier_r", None)]
            photom_g_left = tdt_data.streams.Fi2r.data[trace_indices.get("left").get("photom_g", None)]
            photom_r_left = tdt_data.streams.Fi2r.data[trace_indices.get("left").get("photom_r", None)]

            #Get trace names and store in this list for ingestion
            raw_photom_list: list[dict]=[photom_g_right, photom_r_right, 
                                         photom_g_left, photom_r_left]
            raw_carrier_list: list[dict]=[carrier_g_right, carrier_r_right,
                                            carrier_g_left, carrier_r_left]

            
            # Get processing parameters
            processing_parameters = meta_info.get("Processing_Parameters")
            beh_synch_signal = processing_parameters.get("behavior_offset", 0)
            window = processing_parameters.get("z_window", 60)
            process_z = processing_parameters.get("z", False)
            set_carrier_g_right = processing_parameters.get("left").get("carrier_frequency_g", 0)
            set_carrier_r_right = processing_parameters.get("left").get("carrier_frequency_r", 0)
            set_carrier_g_left = processing_parameters.get("right").get("carrier_frequency_g", 0)
            set_carrier_r_left = processing_parameters.get("right").get("carrier_frequency_r", 0)
            bp_bw = processing_parameters.get("bandpass_bandwidth", 0.5)
            sampling_Hz = processing_parameters.get("sampling_frequency", None)
            downsample_Hz = processing_parameters.get("downsample_frequency", 200)
            demod_sample_rate = processing_parameters.get("demod_sample_rate", 200)
            transform = processing_parameters.get("transform", {})
            num_perseg = processing_parameters.get("no_per_segment", 216)
            n_overlap = processing_parameters.get("noverlap", 108)

            set_carrier_list: list[dict]=[set_carrier_g_right, set_carrier_r_right,
                                            set_carrier_g_left, set_carrier_r_left]
            
            calc_carry_list = demodulation.calc_carry(raw_carrier_list, sampling_Hz)

            for i in range(len(set_carrier_list)):
                    if calc_carry_list[i] != (set_carrier_list[i] >= calc_carry_list[i]+5 or set_carrier_list[i] <= calc_carry_list[i]-5):
                        warnings.warn("Calculated carrier frequency does not match set carrier frequency. Using calculated carrier frequency.")
                        set_carrier_list = calc_carry_list
            else:
                    calc_carry_list = calc_carry_list         

            #change window to reflect the sampling rate/downsample rate
            window1 = round(window * sampling_Hz)

            # Process traces
            if transform == "spectogram":
                calc_carry_list = demodulation.calc_carry(raw_carrier_list, sampling_Hz)
                for i in range(len(set_carrier_list)):
                    if calc_carry_list[i] != (set_carrier_list[i] >= calc_carry_list[i]+5 or set_carrier_list[i] <= calc_carry_list[i]-5):
                        warnings.warn("Calculated carrier frequency does not match set carrier frequency. Using calculated carrier frequency.")
                        set_carrier_list = calc_carry_list
                else:
                    calc_carry_list = calc_carry_list

                four_list = demodulation.four(raw_photom_list)
                z1_trace_list, power_spectra_list, t_list, spect_power_list = demodulation.process_trace(
                                raw_photom_list, calc_carry_list,
                                sampling_Hz, window1, num_perseg, n_overlap)                 
            elif transform == "hilbert":
                fiber_to_side_mapping = {1: "right", 2: "left"}
                color_mapping = {"g": "green", "r": "red", "b": "blue"}
                synch_signal_names = ["toBehSys", "fromBehSys"]
                demod_sample_rate = 600
                photometry_df, fibers, raw_sample_rate = demodulation.offline_demodulation(
                tdt_data, z=True, tau=0.05, downsample_fs=demod_sample_rate, bandpass_bw=20
                )

            #loop through each trace in raw_photom_list and raw_carrier_list
            #return the demodulated traces
            
          
        # Store data in this list for ingestion
            fiber_list: list[dict] = []
            demodulated_trace_list: list[dict] = []
                   
            fibers: list[str] = [ "right", "left"]

            side_to_fiber_id_mapping = {"right": 1, "left": 2}
            color_mapping = {"g": "green", "r": "red", "b": "blue"}

        # Get photometry traces for each fiber
            for fiber in fibers:
                 
                fiber_notes = meta_info.get("Fiber").get("implantation").get(f'{fiber}').get("notes", None)
                #fiber_diam = meta_info.get("Fiber").get("fiber_diameter", None)
                #hemisphere = meta_info.get("Experiment").get("hemisphere")
                fiber_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "notes": fiber_notes,
                    }
                    )
            
            trace_names = meta_info.get("Signal_Indices").get(f'{fiber}')
            for trace_name in trace_names:

                # Populate EmissionColor if present
                emission_color = color_mapping[trace_name.split("_")[1][0]]

                emission_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("emission_wavelength", {})
                    .get(emission_color, None)
                )

                EmissionColor.insert1(
                    {
                        "emission_color": emission_color,
                        "wavelength": emission_wavelength,
                    },
                    skip_duplicates=True,
                )

                # Populate SensorProtein if present
                sensor_protein = (
                    meta_info.get("VirusInjection", {})
                    .get(f'{fiber}', {})
                    .get("sensor_protein", {})
                    .get(emission_color, None)
                )
                if sensor_protein:
                    logger.info(
                        f"{sensor_protein} is inserted into {__name__}.SensorProtein"
                    )
                    SensorProtein.insert1(
                        {"sensor_protein_name": sensor_protein}, skip_duplicates=True
                    )

                # Populate ExcitationWavelength if present
                excitation_wavelength = (
                    meta_info.get("Fiber", {})
                    .get("implantation")
                    .get(f'{fiber}')
                    .get("excitation_wavelength", {})
                    .get(emission_color, None)
                )

                if excitation_wavelength:
                    logger.info(
                        f"{excitation_wavelength} is inserted into {__name__}.ExcitationWavelength"
                    )
                    ExcitationWavelength.insert1(
                        {"excitation_wavelength": excitation_wavelength},
                        skip_duplicates=True,
                    )
                
                raw_photom_list: list[dict]=[photom_g_right, photom_r_right, 
                                         photom_g_left, photom_r_left]
                raw_carrier_list: list[dict]=[carrier_g_right, carrier_r_right,
                                            carrier_g_left, carrier_r_left]
                carrier_ind = {"g_right":0, "r_right":1, "g_left":2, "r_left":3}
                carrier_frequency = calc_carry_list[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

                demod_trace = spect_power_list[carrier_ind[trace_name.split("_")[1]+ f"_{fiber}"]]

                if carrier_frequency:
                    logger.info(
                        f"{carrier_frequency} is inserted into {__name__}.CarrierFrequency"
                    )
                    CarrierFrequency.insert1(
                        {"carrier_frequency": carrier_frequency},
                        skip_duplicates=True,
                    )
                    
                demodulated_trace_list.append(
                    {
                        **key,
                        "fiber_id": side_to_fiber_id_mapping[fiber],
                        "hemisphere": fiber,
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": emission_color,
                        "sensor_protein_name": sensor_protein,
                        "excitation_wavelength": excitation_wavelength,
                        "carrier_frequency": carrier_frequency,
                        "trace": demod_trace,
                    }
                )
            
            # Populate FiberPhotometry
            logger.info(f"Populate {__name__}.FiberPhotometry")
            self.insert1(
                {
                    **key,
                    "light_source_name": light_source_name,
                    "raw_sample_rate": sampling_Hz,
                    "beh_synch_signal": beh_synch_signal,
                }
            )

            # Populate FiberPhotometry.Fiber
            logger.info(f"Populate {__name__}.FiberPhotometry.Fiber")
            self.Fiber.insert(fiber_list)

            # Populate FiberPhotometry.DemodulatedTrace
            logger.info(f"Populate {__name__}.FiberPhotometry.DemodulatedTrace")
            self.DemodulatedTrace.insert(spect_power_list)
            
            del tdt_data
            #tdt_data

@schema
class FiberPhotometrySynced(dj.Imported):
    definition = """
    -> FiberPhotometry
    ---
    timestamps   : longblob
    time_offset  : float     # time offset to synchronize the photometry traces to the master clock (in second)  
    sample_rate  : float     # target downsample rate of synced data (in Hz) 
    """

    class SyncedTrace(dj.Part):
        definition = """ # demodulated photometry traces
        -> master
        -> FiberPhotometry.Fiber
        trace_name          : varchar(8)  # (e.g., raw, detrend)
        -> EmissionColor
        ---
        trace      : longblob  
        """

    def make(self, key):

        if transform == "hilbert":

            # Parameters
            get_fiber_id = (
                lambda side: 1 if side.lower().startswith("r") else 2
            )  # map hemisphere to fiber id
            get_color = (
                lambda s: "green"
                if s.lower().startswith("g")
                else "red"
                if s.lower().startswith("r")
                else None
            )
            color_mapping = {"green": "grn"}
            synch_signal_names = ["toBehSys", "fromBehSys"]
            behavior_sample_rate = 200  # original behavioral sampling freq (Hz)
            target_downsample_rate = 50  # (Hz)
            downsample_factor = behavior_sample_rate / target_downsample_rate

            # Find data dir
            subject_id, session_dir = (session.SessionDirectory & key).fetch1(
                "subject", "session_dir"
            )
            session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
            behavior_dir = session_full_dir / "Behavior"

            # Fetch demodulated photometry traces from FiberPhotometry table
            query = (FiberPhotometry.Fiber * FiberPhotometry.DemodulatedTrace) & key

            photometry_dict = {}

            for row in query:
                trace_name = (
                    "_".join([row["trace_name"], color_mapping[row["emission_color"]]])
                    + row["hemisphere"][0].upper()
                )
                trace = row["trace"]
                photometry_dict[trace_name] = trace

            photometry_df = pd.DataFrame(
                (FiberPhotometry & key).fetch1("beh_synch_signal") | photometry_dict
            )
            # Get trace names e.g., ["detrend_grnR", "raw_grnR"]
            trace_names: list[str] = photometry_df.columns.drop(synch_signal_names).tolist()

            # Update df to start with first trial pulse from behavior system
            photometry_df = pp.handshake_behav_recording_sys(photometry_df)

            analog_df: pd.DataFrame = pd.read_csv(
                behavior_dir / f"{subject_id}_analog_filled.csv", index_col=0
            )
            analog_df["session_clock"] = analog_df.index * 0.005

            # Resample the photometry data and align to 200 Hz state transition behavioral data (analog_df)
            behavior_df: pd.DataFrame = pd.read_csv(
                behavior_dir / f"{subject_id}_behavior_df_full.csv", index_col=0
            )

            aligned_behav_photo_df, time_offset = pp.resample_and_align(
                analog_df, photometry_df, channels=trace_names
            )
            del analog_df

            # One more rolling z-score over the window length (60s * sampling freq (200Hz))
            win = round(60 * 200)

            for channel in trace_names:
                if "detrend" in channel:
                    aligned_behav_photo_df[
                        f'z_{channel.split("_")[-1]}'
                    ] = demodulation.rolling_z(aligned_behav_photo_df[channel], wn=win)
            aligned_behav_photo_df = aligned_behav_photo_df.iloc[win:-win].reset_index(
                drop=True
            )  # drop edges that now contain NaNs from rolling window

            # Drop unnecessary columns that we don't need to save
            photo_columns = trace_names + [
                f'z_{channel.split("_")[-1]}' for channel in trace_names[::3]
            ]  # trace_names[::((len(trace_names)//2)+1)]]]

            cols_to_keep = [
                "nTrial",
                "iBlock",
                "Cue",
                "ENL",
                "Select",
                "Consumption",
                "iSpout",
                "stateConsumption",
                "ENLP",
                "CueP",
                "nENL",
                "nCue",
                "session_clock",
            ]
            cols_to_keep.extend(photo_columns)

            timeseries_task_states_df: pd.DataFrame = deepcopy(
                aligned_behav_photo_df[cols_to_keep]
            )
            timeseries_task_states_df["trial_clock"] = (
                timeseries_task_states_df.groupby("nTrial").cumcount() * 5 / 1000
            )

            # This has to happen AFTER alignment between photometry and behavior because first ENL triggers sync pulse
            _split_penalty_states(timeseries_task_states_df, behavior_df, penalty="ENLP")
            _split_penalty_states(timeseries_task_states_df, behavior_df, penalty="CueP")

            n_bins, remainder = divmod(
                len(timeseries_task_states_df), downsample_factor
            )  # get number of bins to downsample into
            bin_ids = [
                j for i in range(int(n_bins)) for j in np.repeat(i, downsample_factor)
            ]  # define ids of bins at downsampling rate [1,1,1,1,2,2,2,2,...]
            bin_ids.extend(
                np.repeat(bin_ids[-1] + 1, remainder)
            )  # tag on incomplete bin at end
            timeseries_task_states_df[
                "bin_ids"
            ] = bin_ids  # new column to label new bin_ids

            downsampled_states_df: pd.DataFrame = deepcopy(timeseries_task_states_df)

            # Apply aggregate function to each column
            col_fcns = {
                col: np.max
                for col in downsampled_states_df.columns
                if col not in photo_columns
            }
            [col_fcns.update({col: np.mean}) for col in photo_columns]

            # Handle penalties. Label preceding states as different from those without penalties
            downsampled_states_df = downsampled_states_df.groupby("bin_ids").agg(col_fcns)
            downsampled_states_df = downsampled_states_df.reset_index(drop=True)
            downsampled_states_df = downsampled_states_df.drop(columns=["bin_ids"])

            # Get new
            trace_names = list(downsampled_states_df.columns[-6:])
            # Populate FiberPhotometrySynced
            self.insert1(
                {
                    **key,
                    "timestamps": downsampled_states_df["session_clock"].values,
                    "time_offset": time_offset,
                    "sample_rate": target_downsample_rate,
                }
            )

            # Populate FiberPhotometry
            synced_trace_list: list[dict] = []

            for trace_name in trace_names:

                synced_trace_list.append(
                    {
                        **key,
                        "fiber_id": get_fiber_id(trace_name[-1]),
                        "hemisphere": {"R": "right", "L": "left"}[trace_name[-1]],
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": get_color(trace_name.split("_")[1][0]),
                        "trace": downsampled_states_df[trace_name].values,
                    }
                )

            self.SyncedTrace.insert(synced_trace_list)

        elif transform == "spectrogram":
             # Parameters
            get_fiber_id = (
                lambda side: 1 if side.lower().startswith("r") else 2
            )  # map hemisphere to fiber id
            get_color = (
                lambda s: "green"
                if s.lower().startswith("g")
                else "red"
                if s.lower().startswith("r")
                else None
            )
            # Read from the meta_info.toml in the photometry folder if exists
            meta_info_file = list(photometry_dir.glob("*.toml"))[0]
            meta_info = {}
            try:
                with open(meta_info_file, "rb") as f:
                    meta_info = tomli.load(f)
            except FileNotFoundError:
                logger.info("meta info is missing")

            sampling_Hz = meta_info.get("Processing_Parameters").get("sampling_frequency", 2000)
            behavior_sync_signal = meta_info.get("Processing_Parameters").get("behavior_offset", 0)
            behavior_sampling = meta_info.get("Processing_Parameters").get("behavior_sampling", 200)
            target_downsample_rate = meta_info.get("Processing_Parameters").get("downsample_frequency", 50)
            downsample_factor = round(behavior_sampling // target_downsample_rate)
            beh_ds_factor = round(sampling_Hz // behavior_sampling)

            # Find data dir
            subject_id, session_dir = (session.SessionDirectory & key).fetch1(
                "subject", "session_dir"
            )
            session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
            behavior_dir = session_full_dir / "Behavior"

            # Fetch demodulated photometry traces from FiberPhotometry table
            query = (FiberPhotometry.Fiber * FiberPhotometry.DemodulatedTrace) & key

            photometry_dict = {}

            for row in query:
                trace_name = (
                    "_".join([row["trace_name"], color_mapping[row["emission_color"]]])
                    + row["hemisphere"][0].upper()
                )
                trace = row["trace"]
                photometry_dict[trace_name] = trace

            photometry_sync = pd.DataFrame(
                (FiberPhotometry & key).fetch1("beh_synch_signal") | photometry_dict
            )
            # Get trace names e.g., ["detrend_grnR", "raw_grnR"]
            trace_names: list[str] = photometry_sync.columns.drop(synch_signal_name).tolist()

            #sync to behavior offset and downsample to behavior sampling rate
            sessionStart = behavior_sync_signal
            sessionEnd = len(spect_power_list[0]) ##will spect_power_list carry over? switch to trace_names?
            syncedData = []

            for spect_power_array in spect_power_list:
                data = pd.DataFrame(spect_power_array)
                data1 = data.loc[sessionStart:sessionEnd].reset_index(drop=True)
                syncedData.append(data1)
            
            #one more z-score over the window length
            alignedData = []
            win = round(meta_info.get("Processing_Parameters").get("z_window", 60)*behavior_sampling)
            for ii in range(len(syncedData)):
                    data = syncedData[ii]
                    np_dsPhotom = data.to_numpy()
                    np_dsPhotom = np_dsPhotom.flatten()
                    aligned_photom = demodulation.rolling_z(np_dsPhotom, wn=win)
                    alignedData.append(aligned_photom)

            # get timestamps from matlab data
            if len(list(behavior_dir.glob("*.parquet"))) > 0:
                data_format = "matlab_data"
                matlab_data: list[dict] = pd.read_parquet(
                    next(behavior_dir.glob("*.parquet")), engine='fastparquet'
                )

            # Populate FiberPhotometrySynced
            self.insert1(
                {
                    **key,
                    "timestamps": matlab_data["time"].values,
                    "time_offset": behavior_sync_signal,
                    "sample_rate": target_downsample_rate,
                }
            )

            # Populate FiberPhotometry
            synced_trace_list: list[dict] = []

            for trace_name in trace_names:

                synced_trace_list.append(
                    {
                        **key,
                        "fiber_id": get_fiber_id(trace_name[-1]),
                        "hemisphere": {"R": "right", "L": "left"}[trace_name[-1]],
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": get_color(trace_name.split("_")[1][0]),
                        "trace": alignedData[trace_name].values,
                    }
                )

            self.SyncedTrace.insert(synced_trace_list)


    def _split_penalty_states(
        df: pd.DataFrame, behavior_df: pd.DataFrame, penalty: str = "ENLP"
        ) -> None:
        """Handle penalties. Label preceding states as different from those without penalties"""
        penalty_trials = df.loc[df[penalty] == 1].nTrial.unique()

        if len(penalty_trials) > 1:
            penalty_groups = df.loc[df.nTrial.isin(penalty_trials)].groupby(
                "nTrial", as_index=False
            )

            mask = penalty_groups.apply(
                lambda x: x[f"n{penalty[:-1]}"]
                < behavior_df.loc[behavior_df.nTrial == x.nTrial.iloc[0].squeeze()][
                    f"n_{penalty[:-1]}"
                ].squeeze()
            )

        else:
            mask = (
                df.loc[df.nTrial.isin(penalty_trials), f"n{penalty[:-1]}"]
                < behavior_df.loc[behavior_df.nTrial.isin(penalty_trials)][
                    f"n_{penalty[:-1]}"
                ].squeeze()
            )

        # Label pre-penalty states as penalties
        df[f"state_{penalty}"] = 0
        df.loc[df.nTrial.isin(penalty_trials), f"state_{penalty}"] = (
            mask.values * df.loc[df.nTrial.isin(penalty_trials), f"{penalty[:-1]}"]
        )

        # Remove pre-penalty states from true states
        df.loc[df.nTrial.isin(penalty_trials), f"{penalty[:-1]}"] = (
            1 - mask.values
        ) * df.loc[df.nTrial.isin(penalty_trials), f"{penalty[:-1]}"]
        
   

