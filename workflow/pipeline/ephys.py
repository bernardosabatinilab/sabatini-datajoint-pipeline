from element_array_ephys import probe
from element_array_ephys import ephys_no_curation as ephys

from workflow import db_prefix
from workflow.pipeline import lab, session
from workflow.utils.paths import (get_ephys_root_data_dir,
                                  get_processed_root_data_dir,
                                  get_session_directory)

__all__ = ['ephys', 'probe']


# ------------- Activate "ephys" schema -------------

SkullReference = lab.SkullReference
Session = session.Session

if not ephys.schema.is_activated():
    ephys.activate(db_prefix + 'ephys', db_prefix + 'probe', linking_module=__name__)


# add a default kilosort2 paramset

default_params = {
    "fs": 30000,
    "fshigh": 150,
    "minfr_goodchannels": 0.1,
    "Th": [10, 4],
    "lam": 10,
    "AUCsplit": 0.9,
    "minFR": 0.02,
    "momentum": [20, 400],
    "sigmaMask": 30,
    "ThPr": 8,
    "spkTh": -6,
    "reorder": 1,
    "nskip": 25,
    "GPU": 1,
    "Nfilt": 1024,
    "nfilt_factor": 4,
    "ntbuff": 64,
    "whiteningRange": 32,
    "nSkipCov": 25,
    "scaleproc": 200,
    "nPCs": 3,
    "useRAM": 0
}

ephys.ClusteringParamSet.insert_new_params(
    clustering_method='kilosort2.5',
    paramset_desc='Default parameter set for Kilosort2.5',
    params=default_params,
    paramset_idx=0)
