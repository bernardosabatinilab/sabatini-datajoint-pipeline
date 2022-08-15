import datajoint as dj
import numpy as np
import pandas as pd
from element_event import event, trial 
from workflow import db_prefix
from workflow.pipeline import lab, session, subject, ephys
from pathlib import Path
# from element_array_ephys import ephys_no_curation as ephys
from datetime import datetime 

__all__ = ['event', 'trial']

Session = session.Session

# ------------- Activate "event" schema -------------
if not event.schema.is_activated():
    event.activate(db_prefix + 'event', linking_module=__name__)
    
# ------------- Activate "trial" schema -------------
if not trial.schema.is_activated():
    trial.activate(db_prefix + 'trial', db_prefix + 'event', linking_module=__name__)
    

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
        
        subject, session_id = key["subject"], key["session_id"]
        
        session_dir = ephys.get_ephys_session_directory(key)
        beh_data_files = ['events.csv', 'block.csv', 'trial.csv']  # one behavioral session expects these .csv files
        
        assert all([(session_dir / Path(file)).exists() for file in beh_data_files]), "behavioral data missing!"
        
        events_df = pd.read_csv(session_dir / 'events.csv', keep_default_na=False)
        block_df = pd.read_csv(session_dir / 'block.csv', keep_default_na=False)
        trial_df = pd.read_csv(session_dir / 'trial.csv', keep_default_na=False)        

        # Populate EventType
        event.EventType.insert([[event, ''] for event in events_df["event_type"].unique()], skip_duplicates=True)  # can be hard-coded later
        
        # Populate BehaviorRecording
        recording_duration = events_df['time'].iloc[-1] 
        event.BehaviorRecording.insert1(
                                    {
                                        **key,
                                        "recording_duration": recording_duration   
                                    },
                                    skip_duplicates=True
                                )
        
        # Populate BehaviorRecording.File
        behavioral_recording_file_list = [[*key.values(), f"{session_dir}/{file}"] for file in beh_data_files]
        event.BehaviorRecording.File.insert(behavioral_recording_file_list, skip_duplicates=True)

        # Populate Block
        # TODO: trial block dict
        
        for block_ind, row in block_df.iterrows(): 
            
            block_start_trial = row["start_trial"] 
            block_end_trial = row["end_trial"] 
            
            events_block_df = events_df.loc[events_df['trial']== block_start_trial]
            block_start_time =  events_block_df["time"].values[0]
            events_block_df = events_df.loc[events_df['trial']== block_end_trial]
            block_stop_time =  events_block_df["time"].values[-1]
            
            trial.Block.insert1(
                            {
                                **key,
                                "block_id": block_ind + 1,
                                "block_start_time": block_start_time,
                                "block_stop_time": block_stop_time
                            },  
                            allow_direct_insert=True, skip_duplicates=True
                        )
            
            attributes = [[*key.values(), block_ind + 1, attr, val] for (attr, val) in zip(row.index, row.values) if attr != 'session']
            
            # Populate Block.Attribute
            trial.Block.Attribute.insert(attributes,  allow_direct_insert=True, skip_duplicates=True)
            
        # Populate trial.TrialType
        trial.TrialType.insert1(["None", "None"], skip_duplicates=True)  # not sure if this is needed
        trial_df.rename(columns={"session_position": "trial_id", "block": "block_id"}, inplace=True)
        
        # Populate trial.Trial
        for _, row in trial_df.iterrows(): 
            block_start_trial = row["trial_id"] 
            events_trial_df = events_df.loc[events_df['trial']== row["trial_id"] ]
            
            trial.Trial.insert1(
                            {
                                **key,
                                "trial_id": row['trial_id'],
                                "trial_type": "None",
                                "trial_start_time": events_trial_df["time"].values[0],                                
                                "trial_stop_time": events_trial_df["time"].values[-1]                                
                            },  allow_direct_insert=True, skip_duplicates=True
                        )
            
            attributes = [[*key.values(), row['trial_id'], attr, val] for (attr, val) in zip(row.index, row.values)
                          if attr != 'trial_id' and attr != 'block']
            
            # Populate Trial.Attribute
            trial.Trial.Attribute.insert(attributes)

        # Populate trial.BlockTrial()
        trial_df["subject"] = subject
        trial_df["session_id"] = session_id
        trial.BlockTrial.insert(trial_df, ignore_extra_fields=True, allow_direct_insert=True, skip_duplicates=True)
        
        # Populate event.Event
        event_table_df = events_df.rename(columns={"time": "event_start_time"})  # populate the table with this dataframe
        event_table_df["subject"] = subject
        event_table_df["session_id"] = session_id
        event.Event.insert(event_table_df, ignore_extra_fields=True, allow_direct_insert=True, skip_duplicates=True)
        
        # Populate trial.TrialEvent  
        event_table_df.rename(columns={"trial": "trial_id"}, inplace=True)
        trial.TrialEvent.insert(event_table_df, allow_direct_insert=True, skip_duplicates=True)
        
        # Populate event.BehaviorIngestion  
        self.insert1({**key, "ingestion_time": datetime.now()})

event.BehaviorIngestion = BehaviorIngestion