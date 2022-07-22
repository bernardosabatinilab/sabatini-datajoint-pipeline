import datajoint as dj
from datajoint_utilities.dj_worker import DataJointWorker, WorkerLog, ErrorLog
from workflow import db_prefix
from workflow.pipeline import session, scan, imaging, model, train, fbe as facemap
from workflow.support import imaging_support, facemap_support, dlc_model_support
from .ingest_tasks import generate_processing_task, generate_facemap_task

logger = dj.logger

__all__ = ["standard_worker", "analysis_worker", "WorkerLog", "ErrorLog"]


def auto_generate_processing_tasks():
    for scan_key in (scan.ScanInfo - imaging.ProcessingTask).fetch("KEY"):
        try:
            logger.debug(
                f"Making {scan_key} -> {imaging.ProcessingTask.full_table_name}"
            )
            generate_processing_task(scan_key)
        except Exception as error:
            logger.debug(
                f"Error making {scan_key} -> {imaging.ProcessingTask.full_table_name} - {str(error)}"
            )
            ErrorLog.log_exception(scan_key, generate_processing_task, error)
        else:
            logger.debug(
                f"Success making {scan_key} -> {imaging.ProcessingTask.full_table_name}"
            )


def auto_generate_facemap_tasks():
    for session_key in (session.Session - facemap.FacemapTask).fetch("KEY"):
        try:
            logger.debug(
                f"Making {session_key} -> {facemap.FacemapTask.full_table_name}"
            )
            generate_facemap_task(session_key)
        except Exception as error:
            logger.debug(
                f"Error making {session_key} -> {facemap.FacemapTask.full_table_name} - {str(error)}"
            )
            ErrorLog.log_exception(session_key, generate_facemap_task, error)
        else:
            logger.debug(
                f"Success making {session_key} -> {facemap.FacemapTask.full_table_name}"
            )


# -------- Define process(s) --------
org_name, workflow_name, _ = db_prefix.split("_")

worker_db_prefix = f"{org_name}_support_{workflow_name}_"
worker_schema_name = worker_db_prefix + "workerlog"
autoclear_error_patterns = ["%FileNotFound%"]

# standard worker for non-GPU jobs
standard_worker = DataJointWorker(
    "standard_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

# imaging
standard_worker(imaging_support.PreScanInfo, max_calls=1)
standard_worker(scan.ScanInfo, max_calls=5)
standard_worker(imaging_support.PreScanInfo.clean_up)

standard_worker(auto_generate_processing_tasks)

standard_worker(imaging_support.PreMotionCorrection, max_calls=2)
standard_worker(imaging.MotionCorrection, max_calls=5)
standard_worker(imaging_support.PreMotionCorrection.clean_up)

standard_worker(imaging_support.PreSegmentation, max_calls=2)
standard_worker(imaging.Segmentation, max_calls=5)
standard_worker(imaging_support.PreSegmentation.clean_up)

standard_worker(imaging_support.PreFluorescence, max_calls=2)
standard_worker(imaging.Fluorescence, max_calls=5)
standard_worker(imaging_support.PreFluorescence.clean_up)

standard_worker(imaging_support.PreActivity, max_calls=3)
standard_worker(imaging.Activity, max_calls=5)
standard_worker(imaging_support.PreActivity.clean_up)

# facemap
standard_worker(auto_generate_facemap_tasks)

standard_worker(facemap_support.PreRecordingInfo, max_calls=2)
standard_worker(facemap.RecordingInfo, max_calls=5)
standard_worker(facemap_support.PreRecordingInfo.clean_up)

standard_worker(facemap_support.PreFacialSignal, max_calls=4)
standard_worker(facemap.FacialSignal, max_calls=5)
standard_worker(facemap_support.PreFacialSignal.clean_up)

# analysis worker
analysis_worker = DataJointWorker(
    "analysis_worker",
    worker_schema_name,
    db_prefix=[db_prefix, worker_db_prefix],
    run_duration=-1,
    sleep_duration=30,
    autoclear_error_patterns=autoclear_error_patterns,
)

analysis_worker(imaging_support.PreProcessing, max_calls=3)
analysis_worker(imaging.Processing, max_calls=5)
analysis_worker(imaging_support.PostProcessing, max_calls=3)
analysis_worker(imaging_support.PreProcessing.clean_up)

analysis_worker(facemap_support.PreFacemapProcessing, max_calls=3)
analysis_worker(facemap.FacemapProcessing, max_calls=5)
analysis_worker(facemap_support.PostFacemapProcessing, max_calls=3)
analysis_worker(facemap_support.PreFacemapProcessing.clean_up)

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
