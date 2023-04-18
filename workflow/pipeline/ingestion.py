import datajoint as dj
import pandas as pd
from element_interface.utils import find_full_path
from datetime import datetime

from workflow import db_prefix
from workflow.utils.paths import get_raw_root_data_dir
from workflow.pipeline import session, event, trial


logger = dj.logger
schema = dj.schema(db_prefix + "ingestion")


@schema
class BehaviorIngestion(dj.Imported):
    definition = """
    -> session.Session
    ---
    ingestion_time: datetime        # Stores the start time of behavioral data ingestion
    """

    key_source = session.Session & session.SessionDirectory

    def make(self, key):
        """
        Insert behavioral event, trial and block data into corresponding schema tables
        """

        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir = find_full_path(get_raw_root_data_dir(), session_dir)

        # Expecting data in session_full_dir / Behavior /
        # But handles if data is located in a different folder within the session dir
        try:
            event_file = next(
                f for f in session_full_dir.rglob("*events*.csv") if f.is_file()
            )
            block_file = next(
                f for f in session_full_dir.rglob("*block*.csv") if f.is_file()
            )
            trial_file = next(
                f for f in session_full_dir.rglob("*trial*.csv") if f.is_file()
            )
        except StopIteration:
            raise FileNotFoundError(
                f"Missing event or trial or block csv file in {session_full_dir}"
            )

        # Load .csv into pandas dataframe
        events_df = pd.read_csv(event_file, keep_default_na=False)
        block_df = pd.read_csv(block_file, keep_default_na=False)
        trial_df = pd.read_csv(trial_file, keep_default_na=False)

        beh_data_files = [event_file, block_file, trial_file]

        # Populate EventType
        event.EventType.insert(
            [[e, ""] for e in events_df["event_type"].unique()],
            skip_duplicates=True,
        )  # can be hard-coded later

        # Populate BehaviorRecording
        recording_duration = events_df["time"].iloc[-1]
        event.BehaviorRecording.insert1(
            {**key, "recording_duration": recording_duration},
        )

        # Populate BehaviorRecording.File
        behavioral_recording_file_list = [
            [*key.values(), file.relative_to(get_raw_root_data_dir())]
            for file in beh_data_files
        ]
        event.BehaviorRecording.File.insert(behavioral_recording_file_list)

        # Populate trial.Block & trial.Block.Attribute
        trial_block_list = []  # list of dictionaries
        attribute_list = []  # list of lists

        for block_ind, row in block_df.iterrows():
            block_start_trial = row["start_trial"]
            block_end_trial = row["end_trial"]

            ## if events_df has column "inTrial" then isolate events with "inTrial" == 1; this handles Bernardo's pipeline
            ## else isolate events with "trial" == block_start_trial
            if "inTrial" in events_df.columns:
                events_block_df = events_df.loc[events_df["inTrial"] == 1]
            else:
                events_block_df = events_df.loc[events_df["trial"] == block_start_trial]

            # if events_block_df["trial"] is not sequential, then fill with NaN
            #if not events_block_df["trial"].is_monotonic_increasing:
            #    events_block_df["trial"] = events_block_df["trial"].fillna(
            #        method="ffill"
            #    )

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
                    [*key.values(), block_ind + 1, attr, val, None]
                    for (attr, val) in zip(row.index, row.values)
                    if attr != "session"
                ]
            )

        trial.Block.insert(trial_block_list, allow_direct_insert=True)
        trial.Block.Attribute.insert(attribute_list, allow_direct_insert=True)

        # Populate trial.Trial & trial.Trial.Attribute # Why are these renamed?
        #trial_df.rename(
        #    columns={"session_position": "trial_id", "block": "block_id"}, inplace=True
        #)
        trial_trial_list = []  # list of dictionaries
        attribute_list = []  # list of lists

        for _, row in trial_df.iterrows():
            block_start_trial = row["session_position"]
            events_trial_df = events_df.loc[events_df["trial"] == row["session_position"]]

            trial_trial_list.append(
                {
                    **key,
                    "trial_id": row["session_position"],
                    "trial_start_time": events_trial_df["time"].values[0],
                    "trial_stop_time": events_trial_df["time"].values[-1],
                }
            )

            attribute_list.extend(
                [
                    [*key.values(), row["session_position"], attr, val, None]
                    for (attr, val) in zip(row.index, row.values)
                    if attr != "session_position" and attr != "block"
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
        #event_table_df.rename(columns={"trial": "trial_id"}, inplace=True)
        trial.TrialEvent.insert(
            event_table_df,
            ignore_extra_fields=True,
            allow_direct_insert=True,
            skip_duplicates=True,
        )

        # Populate event.BehaviorIngestion
        self.insert1({**key, "ingestion_time": datetime.now()})




