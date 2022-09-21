import datajoint as dj
from .core import session, subject, lab
from workflow import db_prefix
from element_interface.utils import find_full_path
import pandas as pd
import numpy as np
from workflow.utils.paths import get_raw_root_data_dir
import typing as T

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
class FiberPhotometry(dj.Imported):
    definition = """
    -> session.Session
    fiber_id            : tinyint unsigned    
    ---
    sample_rate         : float     # (in Hz) 
    timestamps          : longblob  # (in seconds) photometry timestamps, already synced to the master clock
    -> [nullable] LightSource
    time_offset         : float     # (in second) time offset to synchronize the photometry traces to the master clock
    notes=''            : varchar(1000)  
    """

    class Trace(dj.Part):
        definition = """ # preprocessed photometry traces
        -> master
        trace_name       : varchar(8)  # (e.g., raw, detrend, z)
        -> EmissionColor
        ---
        -> lab.Hemisphere
        -> [nullable] SensorProtein          
        -> [nullable] ExcitationWavelength
        trace           : longblob
        """

    def make(self, key):

        from pathlib import Path
        import tomli
        import workflow.utils.photometry_preprocessing as pp
        from workflow.utils import demodulation
        import tdt
        from copy import deepcopy

        # Parameters
        fiber_to_side_mapping = {1: "right", 2: "left"}
        color_mapping = {"g": "green", "r": "red", "b": "blue"}
        behavior_sample_rate = 200  # original behavioral sampling freq (Hz)
        target_downsample_rate = 50  # (Hz)
        downsample_factor = behavior_sample_rate / target_downsample_rate

        # Find data dir
        subject_id = (session.Session & key).fetch1("subject")
        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
        photometry_dir = session_full_dir / "Photometry"

        tdt_data: tdt.StructType = tdt.read_block(photometry_dir)

        photometry_df: pd.DataFrame = demodulation.offline_demodulation(
            tdt_data, z=True, tau=0.05, downsample_fs=600, bandpass_bw=20
        )

        # List working fibers
        fibers = [
            i for i in [1, 2] if np.std(tdt_data.streams[f"Fi{i}r"].data[0][5:] > 0.05)
        ]
        del tdt_data

        channels: T.List[str] = photometry_df.columns.drop(
            ["toBehSys", "fromBehSys"]
        ).tolist()

        # Update df to start with first trial pulse from behavior system
        photometry_df = pp.handshake_behav_recording_sys(photometry_df)

        # Resample the photometry data and align to 200 Hz state transition behavioral data (analog_df)
        behavior_df: pd.DataFrame = pd.read_csv(
            photometry_dir / f"{subject_id}_behavior_df_full.csv", index_col=0
        )
        analog_df: pd.DataFrame = pd.read_csv(
            photometry_dir / f"{subject_id}_analog_filled.csv", index_col=0
        )
        analog_df["session_clock"] = analog_df.index * 0.005

        aligned_behav_photo_df, time_offset = pp.resample_and_align(
            analog_df, photometry_df, channels=channels
        )
        del analog_df

        # One more rolling z-score over the window length (60s * sampling freq (200Hz))
        win = round(60 * 200)

        for channel in channels:
            if "detrend" in channel:
                aligned_behav_photo_df[
                    f'z_{channel.split("_")[-1]}'
                ] = demodulation.rolling_z(aligned_behav_photo_df[channel], wn=win)
        aligned_behav_photo_df = aligned_behav_photo_df.iloc[win:-win].reset_index(
            drop=True
        )  # drop edges that now contain NaNs from rolling window

        # Drop unnecessary columns that we don't need to save
        photo_columns = channels + [
            f'z_{channel.split("_")[-1]}' for channel in channels[::3]
        ]  # channels[::((len(channels)//2)+1)]]]

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

        downsampled_states_df = downsampled_states_df.groupby("bin_ids").agg(col_fcns)
        downsampled_states_df = downsampled_states_df.reset_index(drop=True)
        downsampled_states_df = downsampled_states_df.drop(columns=["bin_ids"])

        # Read from the meta_info.toml in the photometry folder if exists
        meta_info_file = list(photometry_dir.glob("*.toml"))[0]
        try:
            with open(meta_info_file.as_posix()) as f:
                meta_info: T.Dict = tomli.loads(f.read())
        except FileNotFoundError:
            print("meta info is missing")

        # Populate FiberPhotometry
        fiber_photometry_list: T.List[T.Dict[str, T.Any]] = []
        implantation_list: T.List[T.Dict[str, T.Any]] = []
        trace_names: T.List[str] = list(downsampled_states_df.columns[-6:])
        trace_names: T.Set[str] = set([name[:-1] for name in trace_names])
        trace_list: T.List[T.Dict[str, T.Any]] = []

        for fiber_id in fibers:
            hemisphere = fiber_to_side_mapping[fiber_id]

            try:
                light_source = meta_info["Fiber"]["light_source"]
                fiber_notes = meta_info["Fiber"]["implantation"][hemisphere]["notes"]
            except:
                light_source = fiber_notes = ""

            fiber_photometry_list.append(
                {
                    **key,
                    "fiber_id": fiber_id,
                    "sample_rate": target_downsample_rate,
                    "timestamps": (
                        np.linspace(
                            0, len(downsampled_states_df), len(downsampled_states_df)
                        )
                        / target_downsample_rate
                    ),
                    "light_source_name": light_source,
                    "time_offset": time_offset,
                    "notes": fiber_notes,
                }
            )

            try:  # if meta info exists populate here

                brain_region = meta_info["Fiber"]["implantation"][hemisphere]["region"]
                implantation_list.append(
                    {
                        **key,
                        **meta_info["Fiber"]["implantation"][hemisphere],
                        "fiber_id": fiber_id,
                        "implant_date": meta_info["Fiber"]["implantation"]["date"],
                        "implant_type": "fiber",
                        "brain_region": brain_region,
                        "hemisphere": hemisphere,
                        "surgeon": meta_info["Fiber"]["implantation"]["surgeon"],
                    }
                )

                lab.BrainRegion.insert1(
                    {"region_name": brain_region}, skip_duplicates=True
                )

            except:
                pass

            # Populate FiberPhotometry.Trace
            # ['detrend_grn', 'raw_grn', 'z_grn']
            for trace_name in trace_names:

                sensor_protein = meta_info["VirusInjection"][hemisphere][
                    "sensor_protein"
                ]
                SensorProtein.insert1([sensor_protein], skip_duplicates=True)

                emission_color = color_mapping[trace_name.split("_")[1][0]]

                emission_wavelength = meta_info["Fiber"]["emission_wavelength"][
                    emission_color
                ]
                EmissionColor.insert1(
                    [emission_color, emission_wavelength], skip_duplicates=True
                )
                excitation_wavelength = meta_info["Fiber"]["excitation_wavelength"][
                    emission_color
                ]
                ExcitationWavelength.insert1(
                    [excitation_wavelength], skip_duplicates=True
                )

                trace_list.append(
                    {
                        **key,
                        "fiber_id": fiber_id,
                        "trace_name": trace_name.split("_")[0],
                        "emission_color": emission_color,
                        "hemisphere": hemisphere,
                        "sensor_protein_name": sensor_protein,
                        "excitation_wavelength": excitation_wavelength,
                        "trace": downsampled_states_df[
                            trace_name + hemisphere[0].upper()
                        ].values,
                    }
                )

        # Populate Subject.Implantation if not populated already
        if len(implantation_list):
            subject.Implantation.insert(
                implantation_list, ignore_extra_fields=True, skip_duplicates=True
            )

        self.insert(fiber_photometry_list)
        self.Trace.insert(trace_list)


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
