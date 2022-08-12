import datajoint as dj
import numpy as np
import pandas as pd
from element_event import event, trial 
from workflow import db_prefix
from workflow.pipeline import lab, session, subject, ephys
from pathlib import Path
from element_array_ephys import ephys_no_curation as ephys

__all__ = ['event', 'trial']

Session = session.Session

# ------------- Activate "event" schema -------------
if not event.schema.is_activated():
    event.activate(db_prefix + 'event', linking_module=__name__)
    
Event = event.Event

# ------------- Activate "trial" schema -------------
if not trial.schema.is_activated():
    trial.activate(db_prefix + 'trial', db_prefix + 'event',linking_module=__name__)
    
Trial = trial.Trial
Block = trial.Block
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
        root_dir = Path(dj.config['custom']['beh_root_data_dir'])
        session_dir = (session.SessionDirectory & key).fetch("session_dir")[0]
        
        beh_data_files = ['events.csv', 'block.csv', 'trial.csv']  # one behavioral session expects these .csv files
        
        assert np.prod([(root_dir / session_dir / file).exists() for file in beh_data_files]), "behavioral data missing!"
        
        for file in beh_data_files:
            if 'events' in file:
                events_df = pd.read_csv(root_dir / session_dir / file)
            elif 'block' in file:
                block_df = pd.read_csv(root_dir / session_dir / file)
                block_df.replace(np.nan, '', regex=True, inplace=True)
            elif 'trial' in file:
                trial_df = pd.read_csv(root_dir / session_dir / file)        

        # Populate EventType
        event.EventType.insert([[event, ''] for event in events_df["event_type"].unique()], skip_duplicates=True)  # should be hard-coded later
        
        # Populate BehaviorRecording
        recording_start_time = ''
        recording_duration = events_df['time'].iloc[-1] 
        event.BehaviorRecording.insert1(
                                    {
                                        **key,
                                        "recording_duration": recording_duration   
                                    },
                                    skip_duplicates=True
                                )
        
        # Populate BehaviorRecording.File
        for file in beh_data_files:
            event.BehaviorRecording.File.insert1({**key, "filepath": session_dir + '/' + file}, skip_duplicates=True)

        # Populate Block
        for block_ind, row in block_df.iterrows(): 
            block_start_trial = row["start_trial"] 
            block_end_trial = row["end_trial"] 
            
            temp_df = events_df.loc[events_df['trial']== block_start_trial]
            block_start_time =  temp_df["time"].values[0]
            temp_df = events_df.loc[events_df['trial']== block_end_trial]
            block_stop_time =  temp_df["time"].values[-1]
            
            Block.insert1(
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
            Block.Attribute.insert(attributes,  allow_direct_insert=True, skip_duplicates=True)
            
        # Populate trial.TrialType
        trial.TrialType.insert1(["None", "None"], skip_duplicates=True)  # not sure if this is needed
        trial_df.rename(columns={"session_position": "trial_id", "block": "block_id"}, inplace=True)
        
        # Populate trial.Trial
        for _, row in trial_df.iterrows(): 
            block_start_trial = row["trial_id"] 
            temp_df = events_df.loc[events_df['trial']== row["trial_id"] ]
            
            Trial.insert1(
                            {
                                **key,
                                "trial_id": row['trial_id'],
                                "trial_type": "None",
                                "trial_start_time": temp_df["time"].values[0],                                
                                "trial_stop_time": temp_df["time"].values[-1]                                
                            },  allow_direct_insert=True, skip_duplicates=True
                        )
            
            attributes = [[*key.values(), row['trial_id'], attr, val] for (attr, val) in zip(row.index, row.values)
                          if attr != 'trial_id' and attr != 'block']
            
            # Populate Trial.Attribute
            Trial.Attribute.insert(attributes)

        # Populate trial.BlockTrial()
        temp_df = trial_df.loc[:, ["trial_id", "block_id"]]
        temp_df["subject"] = subject
        temp_df["session_id"] = session_id
        trial.BlockTrial.insert(temp_df, allow_direct_insert=True, skip_duplicates=True)
        
        ## TODO
        # Populate event.Event
        
        ## TODO : this table depends on event.Event
        # Populate trial.TrialEvent  
        # temp_df = events_df.rename(columns={"time": "event_start_time", "trial": "trial_id"})
        # temp_df["subject"] = subject
        # temp_df["session_id"] = session_id
        # trial.TrialEvent.insert(temp_df, allow_direct_insert=True, skip_duplicates=True)


event.BehaviorIngestion = BehaviorIngestion