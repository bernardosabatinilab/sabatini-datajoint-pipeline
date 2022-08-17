import datajoint as dj
import numpy as np
from .core import session
from . import get_schema_name
from workflow import db_prefix
from element_interface.utils import find_full_path
from workflow.utils.paths import get_raw_root_data_dir
import scipy.io as spio
from pathlib import Path

logger = dj.logger
schema = dj.schema(db_prefix + "photometry")


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
    fiber_id: int  # id of the implanted fibers
    ---
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

    def make(self, key):

        sample_rate = 50
        time_offset = 67.94
        excitation_wavelength = 405
        emission_color = "green"

        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        photometry_dir = (
            find_full_path(get_raw_root_data_dir(), session_dir) / "photometry"
        )

        for fiber in photometry_dir.iterdir:

            fiber_id = fiber.stem

            self.insert1([*key.values(), fiber_id, sample_rate])

            for channel in photometry_dir.rglob("*.csv"):

                channel_id = channel.stem[-1]
                trace = spio.loadmat(channel, simplify_cells=True)[f"ch{channel_id}"]
                duration = len(trace) / sample_rate
                timestamps = np.arange(
                    time_offset, duration, (1 / sample_rate), dtype=np.float32
                )
                self.Trace.insert1(
                    [
                        *key.values(),
                        channel_id,
                        excitation_wavelength,
                        emission_color,
                        timestamps,
                        trace,
                    ]
                )

        self.TimeOffset.insert1([*key.values(), time_offset])
