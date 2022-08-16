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
class BrainRegion(dj.Manual):
    definition = """
    -> master
    acronym: varchar(32)
    ---
    region_name: varchar(128)
    """

Location = BrainRegion

imaging.activate(db_prefix + "imaging", db_prefix + "scan", linking_module=__name__)