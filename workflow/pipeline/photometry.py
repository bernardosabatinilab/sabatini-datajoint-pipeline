import datajoint as dj
import numpy as np
import logging
from .core import session

from . import lab, experiment
from . import get_schema_name

log = logging.getLogger(__name__)

schema = dj.schema(get_schema_name('photometry'))



@schema
class ExcitationWavelength(dj.Lookup):
    definition = """
    wavelength:      smallint 
    """
    contents = [[415], [470], [560]]

@schema
class EmissionColor(dj.Lookup):
    definition = """
    color:      varchar(10) 
    """
    contents = [['green'], ['red']]


@schema
class FiberPhotometrySession(dj.Imported):  
    # Ophys data ingested from fiber photometry recordings
    
    definition = """
    -> session.Session
    ---
    sample_rate:    float   
    """
    
    class ExcitationWavelength(dj.Part):  # Excitation wavelengths used in this session
        definition = """
        -> master
        -> ExcitationWavelength
        ---
        led_state:    smallint   
        """

    class Fiber(dj.Part):   # Meta info for each fiber
        definition = """
        -> master
        fiber_number:   int  # Index of the implanted fibers
        ---
        -> lab.Virus
        -> lab.BrainArea
        -> lab.Hemisphere
        -> lab.SkullReference
        ap_location: decimal(6, 2) # (um) anterior-posterior; ref is 0; more anterior is more positive
        ml_location: decimal(6, 2) # (um) medial axis; ref is 0 ; more right is more positive
        depth:       decimal(6, 2) # (um) manipulator depth relative to surface of the brain (0); more ventral is more negative
        theta:       decimal(5, 2) # (deg) - elevation - rotation about the ml-axis [0, 180] - w.r.t the z+ axis
        phi:         decimal(5, 2) # (deg) - azimuth - rotation about the dv-axis [0, 360] - w.r.t the x+ axis
        implant_note:    varchar(1000)
        """
        
    class ROI(dj.Part): 
        # ROIs in the camera raw image
        definition = """
        -> master.Fiber
        -> EmissionColor
        ---
        header_name:   varchar(30)      # Header name in the csv file
        """
        
    class RawTrace(dj.Part):
        definition = """
        -> master.ROI
        -> master.ExcitationWavelength
        ---
        timestamp:  longblob   # (in seconds)
        raw:        longblob
        """
                

@schema
class TrialEvent(dj.Imported):     
    
    definition = """
    -> experiment.BehaviorTrial
    trial_event_id:     int
    ---
    -> experiment.TrialEventType
    trial_event_time:   decimal(10, 5)    
    """
    
    
@schema    
class ActionEvent(dj.Imported):
    
    definition = """
    -> experiment.BehaviorTrial
    trial_event_id:     int
    ---
    -> experiment.ActionEventType
    action_event_time:   decimal(10, 5)   
    """