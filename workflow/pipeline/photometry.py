import datajoint as dj
import numpy as np
from .core import session, lab, subject
from workflow import db_prefix
from element_interface.utils import find_full_path
from workflow.utils.paths import get_raw_root_data_dir
from element_array_ephys import ephys_precluster

logger = dj.logger
schema = dj.schema(db_prefix + "photometry")


@schema
class Sensor(dj.Lookup):
    definition = """            
    name                : varchar(16)  # (e.g., GCaMP, dLight, etc)
    ---
    notes=''            : varchar(64)  
    """


@schema
class Virus(dj.Lookup):
    definition = """            
    name                : varchar(32)  # (e.g., AAV9-DIO-GCaMP6s)
    ---
    notes=''            : varchar(64)  
    """


@schema
class ExcitationWavelength(dj.Lookup):
    definition = """
    excitation_wavelength : smallint 
    """


@schema
class EmissionColor(dj.Lookup):
    definition = """
    emission_color      : varchar(10) 
    ---
    light_source=''     : varchar(16)  # (e.g., Plexon LED, Laser, etc)
    emission_wavelength : smallint
    """


@schema
class Coordinate(dj.Manual):
    definition = """
    -> lab.SkullReference                   # (e.g., bregma or lambda)
    ap            : decimal(6, 2)           # (um) anterior-posterior; ref is 0
    ml            : decimal(6, 2)           # (um) medial axis; ref is 0 
    dv            : decimal(6, 2)           # (um) dorso-ventral axis; ref is 0; more ventral is more negative
    dv_reference  : enum("skull", "dura")   # (um) refence (0) for the dorso-ventral axis; (e.g., 'skull' or 'dura') - should be <=0
    theta=null    : decimal(5, 2)           # (deg) rotation about the ml-axis [0, 180] - w.r.t the z+ axis
    phi=null      : decimal(5, 2)           # (deg) rotation about the dv-axis [0, 360] - w.r.t the x+ axis
    beta=null     : decimal(5, 2)           # (deg) rotation about the shank of the fiber [-180, 180] - clockwise is increasing in degree - 0 is the probe-front facing anterior
    """


@schema
class Injection(dj.Manual):
    definition = """
    injection_id        : tinyint unsigned
    -> subject.Subject
    -> lab.User
    -> Virus
    ---
    injection_volume    : float                         # injection volume
    injection_time=null : datetime                      # injection time
    rate_of_injection   : float                         # rate of injection
    wait_time           : float                         # wait time after injection
    target_region       : varchar(16)
    hemisphere=''       : enum("left", "right", "")
    notes=''            : 
    """
    @schema
    class Coordinate(dj.Part):
        definition="""
        -> Coorindate
        """


@schema
class FiberPhotometry(dj.Imported):
    definition = """
    -> session.Session
    fiber_id            : int    # id of the implanted fibers
    ---
    sample_rate         : float  # (in Hz) 
    notes=''            : varchar(1000)  
    """

    @schema
    class Implantation(dj.Part):
        definition = """
        # Fiber implantation for a subject
        -> master
        date                : date                          # surgery date
        target_region       : varchar(16)
        hemisphere=''       : enum("left", "right", "")
        ---
        -> lab.User                                         # surgeon
        -> Coordinate
        """
        
    class Trace(dj.Part):
        definition = """ # preprocessed photometry traces
        -> master
        channel_id: int
        ---
        -> Sensor          
        -> ExcitationWavelength
        -> EmissionColor
        timestamps      : longblob  # (in seconds) photometry timestamps, already synced to the master clock
        trace           : longblob
        """

    class TimeOffset(dj.Part):
        definition = """
        -> master
        ---
        time_offset     : float  # (in second) time offset to synchronize the photometry traces to the master clock
        """

    def make(self, key):

        # Meta info hard-coded for now
        sample_rate = 50
        time_offset = 67.94
        excitation_wavelength = 405
        emission_color = "green"
        notes = ""

        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        photometry_dir = (
            find_full_path(get_raw_root_data_dir(), session_dir) / "photometry"
        )

        for fiber in photometry_dir.iterdir():

            fiber_id = fiber.stem

            # Populate FiberPhotometry
            self.insert1([*key.values(), fiber_id, sample_rate, notes])

            for channel in photometry_dir.rglob("*.csv"):

                channel_id = channel.stem[-1]
                trace = np.genfromtxt(channel, delimiter=",")
                timestamps = (
                    np.linspace(0, len(trace), len(trace)) / sample_rate
                ) + time_offset

                # Populate FiberPhotometry.Trace
                self.Trace.insert1(
                    [
                        *key.values(),
                        fiber_id,
                        channel_id,
                        excitation_wavelength,
                        emission_color,
                        timestamps,
                        trace,
                    ]
                )

        # Populate FiberPhotometry.TimeOffset
        self.TimeOffset.insert1([*key.values(), fiber_id, time_offset])
