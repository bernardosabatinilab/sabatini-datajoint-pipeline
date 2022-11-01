from element_deeplabcut import train, model

from workflow import db_prefix
from workflow.utils.paths import get_dlc_root_data_dir, get_dlc_processed_data_dir

from . import lab, session, reference

__all__ = ["train", "model"]

# ------------- Activate "DeepLabCut" schema -------------
Session = session.Session
Device = reference.Device

train.activate(db_prefix + "train", linking_module=__name__)
model.activate(db_prefix + "model", linking_module=__name__)
