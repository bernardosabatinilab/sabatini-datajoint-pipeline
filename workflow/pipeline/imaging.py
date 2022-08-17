import datajoint as dj
import numpy as np
from element_calcium_imaging import scan, imaging_no_curation as imaging
from workflow import db_prefix
from .core import lab, session

from workflow.utils.paths import (
    get_imaging_root_data_dir,
    get_imaging_processed_root_data_dir,
    get_imaging_session_directory,
    get_scan_image_files,
)

__all__ = ["scan", "imaging"]

# ------------- Activate "imaging" schema -------------
Session = session.Session
Equipment = lab.Equipment

@lab.schema
class CCF(dj.Lookup):
    definition = """  # Common Coordinate Framework
    ccf_id            : int             # CCF ID, a.k.a atlas ID
    ---
    ccf_version       : varchar(64)     # Allen CCF Version - e.g. CCFv3
    ccf_resolution    : float           # voxel resolution in micron
    ccf_description='': varchar(255)    # CCFLabel Description
    """

    class Voxel(dj.Part):
        definition = """  # CCF voxel coordinates
        -> master
        x   :  int   # (um)  Anterior-to-Posterior (AP axis)
        y   :  int   # (um)  Superior-to-Inferior (DV axis)
        z   :  int   # (um)  Left-to-Right (ML axis)
        index(y, z)
        """

@lab.schema
class BrainRegion(dj.Manual):
    definition = """
    -> CCF
    acronym: varchar(32)
    ---
    region_name: varchar(128)
    """

Location = BrainRegion

imaging.activate(db_prefix + "imaging", db_prefix + "scan", linking_module=__name__)