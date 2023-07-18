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
                (f for f in session_full_dir.rglob("*events*.csv") if f.is_file()), None
            )
            if event_file is None:
                event_file = next(
                    (f for f in session_full_dir.rglob("*event*.parquet") if f.is_file()), None
                )
            
            block_file = next(
                (f for f in session_full_dir.rglob("*block*.csv") if f.is_file()), None
            )
            if block_file is None:
                block_file = next(
                    (f for f in session_full_dir.rglob("*block*.parquet") if f.is_file()), None
                )

            trial_file = next(
                (f for f in session_full_dir.rglob("*trial*.csv") if f.is_file()), None
            )
            if trial_file is None:
                trial_file = next(
                    (f for f in session_full_dir.rglob("*trial*.parquet") if f.is_file()), None
                )

            if event_file is None or block_file is None or trial_file is None:
                raise FileNotFoundError(
                    f"Missing event or trial or block csv/parquet file in {session_full_dir}"
                )
        except StopIteration:
            raise FileNotFoundError(
                f"Missing event or trial or block csv/parquet file in {session_full_dir}"
                )

        # Load .csv into pandas dataframe
        if event_file.suffix == ".csv":
            events_df = pd.read_csv(event_file, keep_default_na=False)
        else:
            events_df = pd.read_parquet(event_file, engine='fastparquet')

        if block_file.suffix == ".csv":
            block_df = pd.read_csv(block_file, keep_default_na=False)
        else:
            block_df = pd.read_parquet(block_file, engine='fastparquet')

        if trial_file.suffix == ".csv":
            trial_df = pd.read_csv(trial_file, keep_default_na=False)
        else:
            trial_df = pd.read_parquet(trial_file, engine='fastparquet')

        beh_data_files = [event_file, block_file, trial_file]

        # Populate EventType
        event.EventType.insert(
            [[e, ""] for e in events_df["event"].unique()],
            skip_duplicates=True,
        )  # can be hard-coded later

        # Populate BehaviorRecording
        recording_duration = events_df["time"].iloc[-1]
        event.BehaviorRecording.insert1(
            {**key, "recording_duration": recording_duration}
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
            if "start_trial" in row:
                block_start_trial = row["start_trial"]
            elif "firstTrial" in row:
                block_start_trial = row["firstTrial"]
            else:
                # Handle the case when both column names are missing
                block_start_trial = None

            if "end_trial" in row:
                block_end_trial = row["end_trial"]
            elif "lastTrial" in row:
                block_end_trial = row["lastTrial"]
            else:
                # Handle the case when both column names are missing
                block_end_trial = None

            events_block_df = events_df.loc[(events_df["trial"] >= block_start_trial) & (events_df["trial"] <= block_end_trial)]
            block_start_time = events_block_df["time"].values[0]
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

        # Populate trial.Trial & trial.Trial.Attribute
        trial_df.rename(
            columns={"session_position": "trial_id", "block": "block_id"}, inplace=True
        )
        trial_trial_list = []  # list of dictionaries
        attribute_list = []  # list of lists

        # create a copy of the events_df if inTrial exists
        for _, row in trial_df.iterrows():
            if "inTrial" in events_df.columns:
                df = events_df[events_df["inTrial"] == 1].copy()
            else:
                df = events_df.copy()

            block_start_trial = row["trial_id"]
            events_trial_df = df.loc[df["trial"] == block_start_trial]

            if not events_trial_df.empty:
                trial_start_time = events_trial_df["time"].values[0]
                trial_stop_time = events_trial_df["time"].values[-1]
            else:
                trial_start_time = float("0")
                trial_stop_time = float("0")


            trial_trial_list.append(
                {
                    **key,
                    "trial_id": row["trial_id"],
                    "trial_start_time": trial_start_time,
                    "trial_stop_time": trial_stop_time,
                }
            )

            attribute_list.extend(
                [
                    [*key.values(), row["trial_id"], attr, val, None]
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
            columns={"event": "event_type", "time": "event_start_time"}
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
        trial.TrialEvent.insert(
            event_table_df,
            ignore_extra_fields=True,
            allow_direct_insert=True,
            skip_duplicates=True,
        )

        # Populate event.BehaviorIngestion
        self.insert1({**key, "ingestion_time": datetime.now()})
