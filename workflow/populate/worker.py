import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, WorkerLog, ErrorLog
from workflow import db_prefix
from workflow.pipeline import (
    session,
    ephys,
    scan,
    photometry,
    imaging,
    model as dlc_model,
    ingestion,
)
from workflow.pipeline.dlc import ingest_behavior_videos
logger = dj.logger

__all__ = [
    "standard_worker",
    "dlc_worker",
    "calcium_imaging_worker",
    "spike_sorting_worker",
    "WorkerLog",
    "ErrorLog",
]


def auto_generate_probe_insertions():
    for skey in (session.Session - ephys.ProbeInsertion).fetch("KEY"):
        try:
            logger.debug(f"Making {skey} -> {ephys.ProbeInsertion.full_table_name}")
            ephys.ProbeInsertion.auto_generate_entries(skey)
            logger.debug(
                f"Success making {skey} -> {ephys.ProbeInsertion.full_table_name}"
            )
        except Exception as error:
            logger.debug(
                f"Error making {skey} -> {ephys.ProbeInsertion.full_table_name} - {str(error)}"
            )
            ErrorLog.log_exception(
                skey, ephys.ProbeInsertion.auto_generate_entries, error
            )


def auto_generate_clustering_tasks():
    for rkey in (ephys.EphysRecording - ephys.ClusteringTask).fetch("KEY"):
        try:
            ephys.ClusteringTask.auto_generate_entries(rkey, paramset_idx=0)
        except Exception as error:
            logger.error(str(error))
            ErrorLog.log_exception(
                rkey, ephys.ClusteringTask.auto_generate_entries, error
            )

def auto_generate_dlc_videorecordings():
    for skey in (session.Session - dlc_model.VideoRecording).fetch("KEY"):
        try: 
            ingest_behavior_videos(skey)
        except Exception as error:
            logger.error(str(error))
            ErrorLog.log_exception(
                skey, ingest_behavior_videos, error
            )    


# -------- Define process(s) --------
worker_schema_name = db_prefix + "workerlog"
autoclear_error_patterns = ["%FileNotFound%"]

# standard process for non-GPU jobs
standard_worker = DataJointWorker(
    "standard_worker",
    worker_schema_name,
    db_prefix=[db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

standard_worker(ingestion.BehaviorIngestion, max_calls=5)
standard_worker(auto_generate_probe_insertions)
standard_worker(ephys.EphysRecording, max_calls=5)
standard_worker(auto_generate_clustering_tasks)
standard_worker(ephys.CuratedClustering, max_calls=5)
standard_worker(ephys.WaveformSet, max_calls=5)
standard_worker(ephys.LFP, max_calls=5)

# photometry
standard_worker(photometry.FiberPhotometry, max_calls=5)
standard_worker(photometry.FiberPhotometrySynced, max_calls=5)

# spike_sorting process for GPU required jobs
spike_sorting_worker = DataJointWorker(
    "spike_sorting_worker",
    worker_schema_name,
    db_prefix=[db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

spike_sorting_worker(ephys.Clustering, max_calls=6)

# imaging
standard_worker(scan.ScanInfo, max_calls=5)
standard_worker(imaging.MotionCorrection, max_calls=5)
standard_worker(imaging.Segmentation, max_calls=5)
standard_worker(imaging.Fluorescence, max_calls=5)
standard_worker(imaging.Activity, max_calls=5)

# calcium imaging worker
calcium_imaging_worker = DataJointWorker(
    "calcium_imaging_worker",
    worker_schema_name,
    db_prefix=[db_prefix],
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
    db_prefix=[db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

# dlc_worker(dlc_model.RecordingInfo, max_calls=5)
# dlc_worker(auto_generate_dlc_videorecordings)
# dlc_worker(dlc_model.PoseEstimation, max_calls=5)
