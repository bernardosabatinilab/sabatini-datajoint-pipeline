import datajoint as dj
import numpy as np
import fissa
from element_calcium_imaging import scan, imaging_no_curation as imaging
from workflow import db_prefix
from .core import lab, session
from workflow.utils.imaging_analysis import (
    calculate_dff,
    calculate_zscore,
    combine_trials,
)
from workflow.utils.paths import (
    get_imaging_root_data_dir,
    get_processed_root_data_dir,
    get_nd2_files,
    get_scan_box_files,
    get_scan_image_files,
)

__all__ = ["scan", "imaging"]

# ------------- Activate "imaging" schema -------------
Session = session.Session
Equipment = lab.Equipment

imaging.activate(db_prefix + "imaging", db_prefix + "scan", linking_module=__name__)


# Custom `make()` function for Activity table


def custom_activity_make(self, key):
    # This code estimates the following quantities for each cell:
    # 1) neuropil corrected fluorescence,
    # 2) dff,
    # 3) zscore.
    processing_method, suite2p_dataset = imaging.get_loader_result(
        key, imaging.ProcessingTask
    )

    fissa_params, activity_extraction_paramset_idx = (
        imaging.ActivityExtractionParamSet & key
    ).fetch1("params", "activity_extraction_paramset_idx")

    # processing_output_dir contains the paramset_id. The upload & ingest should be done accordingly.
    output_dir = imaging.find_full_path(
        imaging.get_imaging_root_data_dir(),
        (imaging.ProcessingTask & key).fetch("processing_output_dir", limit=1)[0],
    )

    reg_img_dir = output_dir / "suite2p/plane0/reg_tif"
    fissa_output_dir = output_dir / "FISSA_Suite2p"

    # Required even though the FISSA is not triggered
    iscell = suite2p_dataset.planes[0].iscell
    ncells = len(imaging.Segmentation.Mask & key)
    cell_ids = np.arange(ncells)
    cell_ids = cell_ids[iscell == 1]  # Use only the cells

    # Trigger Condition
    if not any(
        (fissa_output_dir / p).exists() for p in ["separated.npy", "separated.npz"]
    ):
        fissa_output_dir.mkdir(parents=True, exist_ok=True)

        Ly, Lx = (
            (imaging.MotionCorrection.Summary & key)
            .fetch("average_image", limit=1)[0]
            .shape
        )
        stat = suite2p_dataset.planes[0].stat
        num_rois = len(cell_ids)
        rois = [np.zeros((Ly, Lx), dtype=bool) for n in range(num_rois)]

        for i, n in enumerate(cell_ids):
            # i is the position in cell_ids, and n is the actual cell number
            ypix = stat[n]["ypix"][~stat[n]["overlap"]]
            xpix = stat[n]["xpix"][~stat[n]["overlap"]]
            rois[i][ypix, xpix] = 1

        experiment = fissa.Experiment(
            reg_img_dir.as_posix(),
            [rois[:ncells]],
            fissa_output_dir.as_posix(),
            **fissa_params["init"]
        )
        experiment.separate(**fissa_params["exec"])

    # Load the results
    fissa_output_file = list(fissa_output_dir.glob("separated.np*"))[
        0
    ]  # This can be npy or npz.
    fissa_output = np.load(fissa_output_file, allow_pickle=True)

    # Old and new FISSA outputs are stored differently
    # Two versions can be distinguised with the output file suffix.
    trace_list = []
    if fissa_output_file.suffix == ".npy":
        for cell_id, mask in zip(
            cell_ids, fissa_output[3]
        ):  # LuLab uses this the 3rd component.
            trace_list.append(
                dict(
                    **key,
                    mask=cell_id,
                    fluo_channel=0,
                    activity_type="corrected_fluorescence",
                    activity_trace=mask[0][0][0]
                )
            )
            dff = calculate_dff(mask[0][0][0])
            trace_list.append(
                dict(
                    **key,
                    mask=cell_id,
                    fluo_channel=0,
                    activity_type="dff",
                    activity_trace=dff
                )
            )
            trace_list.append(
                dict(
                    **key,
                    mask=cell_id,
                    fluo_channel=0,
                    activity_type="z_score",
                    activity_trace=calculate_zscore(dff)
                )
            )

    else:
        traces = combine_trials(fissa_output)
        for cell_id, mask in zip(cell_ids, traces):
            trace_list.append(
                dict(
                    **key,
                    mask=cell_id,
                    fluo_channel=0,
                    activity_type="Fcorrected",
                    activity_trace=mask
                )
            )
            trace_list.append(
                dict(
                    **key,
                    mask=cell_id,
                    fluo_channel=0,
                    activity_type="z_score",
                    activity_trace=calculate_zscore(mask)
                )
            )

    self.insert1(key)
    self.Trace.insert(trace_list)


imaging.Activity.make = custom_activity_make


# Default FISSA ActivityExtractionParamSet

_default_fissa_paramset = {
    "init": {
        "ncores_preparation": None,
        "ncores_separation": None,
        "nRegions": 4,
        "expansion": 3,
        "alpha": 0.2,
    },
    "exec": {"redo_prep": True, "redo_sep": True},
}


# --- ActivityExtractionParamSet ---
imaging.ActivityExtractionParamSet.insert_new_params(
    activity_extraction_paramset_idx=0,
    extraction_method="FISSA",
    paramset_desc="Default",
    params=_default_fissa_paramset,
)
