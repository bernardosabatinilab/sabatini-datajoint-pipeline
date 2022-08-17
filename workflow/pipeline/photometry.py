import datajoint as dj
import numpy as np
from .core import session
from . import get_schema_name

logger = dj.logger
schema = dj.schema(get_schema_name("photometry"))


@schema
class ExcitationWavelength(dj.Lookup):  # always constant?
    definition = """
    excitation_wavelength:      smallint 
    """

    contents = zip([405, 470])


@schema
class EmissionColor(dj.Lookup):
    definition = """
    emission_color:      varchar(10) 
    ---
    emission_wavelength: smallint
    """

    contents = [("green", 525)]


@schema
class FiberPhotometry(dj.Imported):
    definition = """
    -> session.Session
    fiber_id: in Id of the implanted fibers
    ---t  #
    sample_rate: float (Hz) 
    notes='': varchar(1000)  
    """

    class Trace(dj.Part):
        definition = """ # preprocessed photometry traces
        -> master
        channel_id: int
        ---
        -> ExcitationWavelength
        -> EmissionColor
        timestamps: longblob  # (in seconds) photometry timestamps, already synced to the master clock
        trace: longblob
        """

    class TimeOffset(dj.Part):
        definition = """
        -> master
        ---
        time_offset: float  # (in second) time offset to synchronize the photometry traces to the master clock
        """

    def make():
        # go to session_dir / photometry
        # retrieves all photometry data - determine the number of fibers
        # run through the preprocessing code - for each fiber - should return
        #   - fiber_id
        #   - channels
        #       - excitation wavelength
        #       - emission color
        #       - preprocessed traces
        #       - preprocessed timestamps (timeoffset applied)

        pass
