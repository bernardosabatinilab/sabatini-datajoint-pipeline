import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, WorkerLog, ErrorLog
from workflow import db_prefix
from workflow.pipeline import session, ephys, scan, imaging, model as dlc_model, train as dlc_train

logger = dj.logger

__all__ = ["standard_worker", "dlc_worker", "calcium_imaging_worker", \
     "spike_sorting_worker", "WorkerLog", "ErrorLog"]

def auto_generate_probe_insertions():
    for skey in (session.Session - ephys.ProbeInsertion).fetch('KEY'):
        try:
            logger.debug(f"Making {skey} -> {ephys.ProbeInsertion.full_table_name}")
            ephys.ProbeInsertion.auto_generate_entries(skey)
            logger.debug(f"Success making {skey} -> {ephys.ProbeInsertion.full_table_name}")
        except Exception as error:
            logger.debug(f"Error making {skey} -> {ephys.ProbeInsertion.full_table_name} - {str(error)}")
            ErrorLog.log_exception(skey, ephys.ProbeInsertion.auto_generate_entries, error)

def auto_generate_clustering_tasks():
    for rkey in (ephys.EphysRecording - ephys.ClusteringTask).fetch('KEY'):
        try:
            ephys.ClusteringTask.auto_generate_entries(rkey, paramset_idx=0)
        except Exception as error:
            logger.error(str(error))
            ErrorLog.log_exception(rkey, ephys.ClusteringTask.auto_generate_entries, error)

# -------- Define process(s) --------
org_name, workflow_name, _ = db_prefix.split("_")

worker_db_prefix = f"{org_name}_support_{workflow_name}_"
worker_schema_name = worker_db_prefix + "workerlog"
autoclear_error_patterns = ["%FileNotFound%"]

# standard process for non-GPU jobs 
standard_worker = DataJointWorker('standard_worker',
                                  worker_schema_name,
                                  db_prefix=[db_prefix, worker_db_prefix],
                                  run_duration=-1,
                                  sleep_duration=30,
                                  autoclear_error_patterns=autoclear_error_patterns)

standard_worker(auto_generate_probe_insertions)

standard_worker(ephys.EphysRecording, max_calls=5)

standard_worker(auto_generate_clustering_tasks)

standard_worker(ephys.CuratedClustering, max_calls=10)

standard_worker(ephys.WaveformSet, max_calls=1)

standard_worker(ephys.LFP, max_calls=1)


# spike_sorting process for GPU required jobs
spike_sorting_worker = DataJointWorker('spike_sorting_worker',
                                       worker_schema_name,
                                       db_prefix=[db_prefix, worker_db_prefix],
                                       run_duration=-1,
                                       sleep_duration=30,
                                       autoclear_error_patterns=autoclear_error_patterns)

spike_sorting_worker(ephys.Clustering, max_calls=6)

# imaging
standard_worker(scan.ScanInfo, max_calls=5)

standard_worker(imaging.MotionCorrection, max_calls=5)

standard_worker(imaging.Segmentation, max_calls=5)

standard_worker(imaging.Fluorescence, max_calls=5)

standard_worker(imaging.Activity, max_calls=5)

# analysis worker
calcium_imaging_worker = DataJointWorker(
    "calcium_imaging_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

calcium_imaging_worker(imaging.Processing, max_calls=5)

# --- Deeplabcut ---

# GPU worker for DLC
dlc_worker = DataJointWorker(
    "dlc_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)
dlc_worker(dlc_model.RecordingInfo, max_calls=5)
dlc_worker(dlc_model.PoseEstimation, max_calls=5)
