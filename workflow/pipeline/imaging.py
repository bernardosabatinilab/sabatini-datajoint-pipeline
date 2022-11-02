import datajoint as dj
import numpy as np
from element_calcium_imaging import scan, imaging_no_curation as imaging
from workflow import db_prefix
from workflow.pipeline import lab, session, reference

from workflow.utils.paths import (
    get_imaging_root_data_dir,
    get_processed_root_data_dir,
    get_scan_image_files,
)

__all__ = ["scan", "imaging"]

# ------------- Activate "imaging" schema -------------
Session = session.Session
Equipment = reference.Equipment
Location = reference.BrainRegion

imaging.activate(db_prefix + "imaging", db_prefix + "scan", linking_module=__name__)
