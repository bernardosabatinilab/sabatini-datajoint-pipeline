import datajoint as dj
import pandas as pd
from element_event import event, trial
from element_interface.utils import find_full_path
from workflow import db_prefix
from workflow.pipeline import session
from pathlib import Path
from datetime import datetime
from workflow.utils.paths import get_raw_root_data_dir

__all__ = ["event", "trial"]

Session = session.Session

# ------------- Activate "trial" schema -------------
if not trial.schema.is_activated():
    trial.activate(db_prefix + "trial", db_prefix + "event", linking_module=__name__)


@event.schema
class BehaviorIngestion(dj.Imported):
    definition = """
    -> Session
    ---
    ingestion_time: datetime        # Stores the start time of behavioral data ingestion
    """

    def make(self, key):
        """
        Insert behavioral event, trial and block data into corresponding schema tables
        """

        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir = find_full_path(get_raw_root_data_dir(), session_dir)

        beh_data_files = [
            "events.csv",
            "block.csv",
            "trial.csv",
        ]  # one behavioral session expects these .csv files

        assert all(
            [(session_full_dir / Path(file)).exists() for file in beh_data_files]
        ), "behavioral data missing!"

        events_df = pd.read_csv(session_full_dir / "events.csv", keep_default_na=False)
        block_df = pd.read_csv(session_full_dir / "block.csv", keep_default_na=False)
        trial_df = pd.read_csv(session_full_dir / "trial.csv", keep_default_na=False)

        # Populate EventType
        event.EventType.insert(
            [[event, ""] for event in events_df["event_type"].unique()],
            skip_duplicates=True,
        )  # can be hard-coded later

        # Populate BehaviorRecording
        recording_duration = events_df["time"].iloc[-1]
        event.BehaviorRecording.insert1(
            {**key, "recording_duration": recording_duration},
        )

        # Populate BehaviorRecording.File
        behavioral_recording_file_list = [
            [*key.values(), f"{session_dir}/{file}"] for file in beh_data_files
        ]
        event.BehaviorRecording.File.insert(behavioral_recording_file_list)

        # Populate trial.Block & trial.Block.Attribute
        trial_block_list = []  # list of dictionaries
        attribute_list = []  # list of lists

        for block_ind, row in block_df.iterrows():

            block_start_trial = row["start_trial"]
            block_end_trial = row["end_trial"]

            events_block_df = events_df.loc[events_df["trial"] == block_start_trial]
            block_start_time = events_block_df["time"].values[0]
            events_block_df = events_df.loc[events_df["trial"] == block_end_trial]
            block_stop_time = events_block_df["time"].values[-1]

            trial_block_list.append(
                {
                    **key,
                    "block_id": block_ind + 1,
                    "block_start_time": block_start_time,
                    "block_stop_time": block_stop_time,
                }
            )

            attribute_list.extend(
                [
                    [*key.values(), block_ind + 1, attr, val]
                    for (attr, val) in zip(row.index, row.values)
                    if attr != "session"
                ]
            )

        trial.Block.insert(trial_block_list, allow_direct_insert=True)
        trial.Block.Attribute.insert(attribute_list, allow_direct_insert=True)

        # Populate trial.Trial & trial.Trial.Attribute
        trial_df.rename(
            columns={"session_position": "trial_id", "block": "block_id"}, inplace=True
        )
        trial_trial_list = []  # list of dictionaries
        attribute_list = []  # list of lists

        for _, row in trial_df.iterrows():
            block_start_trial = row["trial_id"]
            events_trial_df = events_df.loc[events_df["trial"] == row["trial_id"]]

            trial_trial_list.append(
                {
                    **key,
                    "trial_id": row["trial_id"],
                    "trial_start_time": events_trial_df["time"].values[0],
                    "trial_stop_time": events_trial_df["time"].values[-1],
                }
            )

            attribute_list.extend(
                [
                    [*key.values(), row["trial_id"], attr, val]
                    for (attr, val) in zip(row.index, row.values)
                    if attr != "trial_id" and attr != "block"
                ]
            )

        trial.Trial.insert(trial_trial_list, allow_direct_insert=True)
        trial.Trial.Attribute.insert(attribute_list)

        # Populate trial.BlockTrial
        trial_df["subject"] = key["subject"]
        trial_df["session_id"] = key["session_id"]
        trial.BlockTrial.insert(
            trial_df, ignore_extra_fields=True, allow_direct_insert=True
        )

        # Populate event.Event
        event_table_df = events_df.rename(
            columns={"time": "event_start_time"}
        )  # populate the table with this dataframe
        event_table_df["subject"] = key["subject"]
        event_table_df["session_id"] = key["session_id"]
        event.Event.insert(
            event_table_df,
            ignore_extra_fields=True,
            allow_direct_insert=True,
            skip_duplicates=True,
        )

        # Populate trial.TrialEvent
        event_table_df.rename(columns={"trial": "trial_id"}, inplace=True)
        trial.TrialEvent.insert(event_table_df, allow_direct_insert=True)

        # Populate event.BehaviorIngestion
        self.insert1({**key, "ingestion_time": datetime.now()})


event.BehaviorIngestion = BehaviorIngestion
