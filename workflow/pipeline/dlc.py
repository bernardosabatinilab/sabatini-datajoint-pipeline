from element_deeplabcut import train, model
from workflow import db_prefix
from workflow.utils.paths import get_dlc_root_data_dir, get_dlc_processed_data_dir
from workflow.pipeline import lab, session, reference

import yaml
import re
import numpy as np
from pathlib import Path
import os

__all__ = ["train", "model"]

# ------------- Activate "DeepLabCut" schema -------------
Session = session.Session
Device = reference.Device

train.activate(db_prefix + "train", linking_module=__name__)
model.activate(db_prefix + "model", linking_module=__name__)


def ingest_behavior_videos(key, device_id, recording_id=0):
    rel_path = (session.SessionDirectory & key).fetch1("session_dir")
    dlc_beh_path = model.get_dlc_root_data_dir()[0] / rel_path / "dlc_behavior_videos"
    beh_vid_files = [
        beh_file for beh_file in dlc_beh_path.glob("*.avi") if beh_file.is_file()
    ]
    vid_recs = []
    vid_recs_files = []
    for file_idx, bfile in enumerate(beh_vid_files):
        vid_recs.append(
            dict(
                subject=key["subject"],
                session_id=key["session_id"],
                recording_id=recording_id,
                device_id=device_id,
            )
        )

        vid_recs_files.append(
            dict(
                subject=key["subject"],
                session_id=key["session_id"],
                recording_id=recording_id,
                file_id=file_idx,
                file_path=bfile.relative_to(model.get_dlc_root_data_dir()[0]),
            )
        )

    model.VideoRecording.insert(vid_recs, skip_duplicates=True)
    model.VideoRecording.File.insert(vid_recs_files, skip_duplicates=True)


def insert_new_dlc_model(
    project_path, paramset_idx=None, model_prefix="", model_description="", prompt=True
):
    from deeplabcut.utils.auxiliaryfunctions import GetScorerName

    config_file_path = Path(project_path) / "config.yaml"

    with open(config_file_path, "rb") as f:
        dlc_config = yaml.safe_load(f)

    # Modify the project path and save it to the config.yaml file
    root_data_dir = model.get_dlc_root_data_dir()[0]
    # Used to
    dlc_config["project_path"] = config_file_path.parent.as_posix()

    sample_paths = [
        d for d in project_path.rglob(r"iteration*/*trainset*shuffle*") if d.is_dir()
    ]

    for sample_path in sample_paths:
        iteration = re.search(r"iteration-(\d+)", sample_path.parent.name).groups()[0]

        trainset, shuffle = re.search(
            r"trainset(\d+)shuffle(\d+)", sample_path.name
        ).groups()

        model_name = project_path.name + f"_i{iteration}_t{trainset}_s{shuffle}"

        trainingsetindex = np.argmin(
            np.abs(np.array(dlc_config["TrainingFraction"]) - float(trainset) / 100)
        )

        scorer_legacy = model.str_to_bool(dlc_config.get("scorer_legacy", "f"))
        dlc_scorer = GetScorerName(
            cfg=dlc_config,
            shuffle=shuffle,
            trainFraction=dlc_config["TrainingFraction"][int(trainingsetindex)],
            modelprefix=model_prefix,
        )[scorer_legacy]

        if dlc_config["snapshotindex"] == -1:
            dlc_scorer = "".join(dlc_scorer.split("_")[:-1])

        model.Model.insert_new_model(
            model_name=model_name,
            dlc_config=dlc_config,
            shuffle=shuffle,
            trainingsetindex=trainingsetindex,
            project_path=project_path.relative_to(root_data_dir).as_posix(),
            model_description=model_description,
            model_prefix=model_prefix,
            paramset_idx=paramset_idx,
            prompt=prompt,
            params=None,
        )
