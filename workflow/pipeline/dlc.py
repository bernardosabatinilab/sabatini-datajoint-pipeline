from element_deeplabcut import train, model
from workflow import db_prefix
from workflow.utils.paths import get_dlc_root_data_dir, get_dlc_processed_data_dir
from workflow.pipeline import lab, session, reference
from workflow.pipeline.dlc import ModelVideoSet

import yaml
import re
import numpy as np

__all__ = ["train", "model"]

# ------------- Activate "DeepLabCut" schema -------------
Session = session.Session
Device = reference.Device

train.activate(db_prefix + "train", linking_module=__name__)
model.activate(db_prefix + "model", linking_module=__name__)

def insert_new_dlc_model(project_path, paramset_idx=None, model_prefix="", model_description=""):
    config_file_path = project_path / "config.yaml"
        
    with open(config_file_path, "rb") as f:
        dlc_config = yaml.safe_load(f)

    # Modify the project path and save it to the config.yaml file
    root_data_dir = (
        model.get_dlc_root_data_dir()[0]
        if len(model.get_dlc_root_data_dir()) > 1
        else model.get_dlc_root_data_dir()
    )
    dlc_config["project_path"] = (
        root_data_dir / "dlc_projects" / str(config_file_path).split("/")[-2]
    ).as_posix()

    sample_paths = [f for f in project_path.rglob('dlc-models/*trainset*shuffle*')]
    iterations_dir = project_path / 'dlc-models' 

    iteration_list = [iteration for iteration in iterations_dir.glob('*') if iteration.is_dir()]
    iterations = [x for x in str(sample_paths[0]).split("/") if "iteration" in x]
    for iteration in iterations:
        sample_paths = [f for f in iterations_dir.rglob('*trainset*shuffle*')]            
        sample_path = next(x for x in sample_paths if iteration in str(x))

        trainsetshuffle_piece = next(
            x for x in str(sample_path).split("/") if "trainset" in x
        )

        trainset, shuffle = re.search(
            r"trainset(\d+)shuffle(\d+)", trainsetshuffle_piece
        ).groups()

        model_name = str(project_path).split("/")[-1] + f"_{iteration}"

        trainingsetindex=np.argmin(
                np.abs(
                    np.array(dlc_config["TrainingFraction"]) - float(trainset) / 100
                )
            )

        scorer_legacy = model.str_to_bool(dlc_config.get("scorer_legacy", "f"))
        dlc_scorer = model.GetScorerName(
            cfg=dlc_config,
            shuffle=shuffle,
            trainFraction=dlc_config["TrainingFraction"][int(trainingsetindex)],
            modelprefix=model_prefix,
        )[scorer_legacy]

    if dlc_config["snapshotindex"] == -1:
        dlc_scorer = "".join(dlc_scorer.split("_")[:-1])
        model_dict = {
            "model_name": model_name,
            "model_description": model_description,
            "scorer": dlc_scorer,
            "task": dlc_config["Task"],
            "date": dlc_config["date"],
            "iteration": dlc_config["iteration"],
            "snapshotindex": dlc_config["snapshotindex"],
            "shuffle": shuffle,
            "trainingsetindex": int(trainingsetindex),
            "project_path": project_path.relative_to(root_data_dir).as_posix(),
            "paramset_idx": paramset_idx,
            "config_template": dlc_config,
        }
        model.Model.insert1(model_dict)
