import datajoint as dj
import pathlib


def get_raw_root_data_dir():
    data_dir = dj.config.get("custom", {}).get("raw_root_data_dir", None)
    return pathlib.Path(data_dir) if data_dir else None


def get_processed_root_data_dir():
    data_dir = dj.config.get("custom", {}).get("processed_root_data_dir", None)
    return pathlib.Path(data_dir) if data_dir else None


# for element-array-ephys activation
def get_ephys_root_data_dir():
    return get_raw_root_data_dir()


def get_ephys_processed_root_data_dir():
    return get_processed_root_data_dir()


def get_session_directory(session_key: dict) -> str:
    data_dir = get_ephys_root_data_dir()

    from workflow.pipeline import session

    if not (session.SessionDirectory & session_key):
        raise FileNotFoundError(f"No session data directory defined for {session_key}")

    sess_dir = data_dir / (session.SessionDirectory & session_key).fetch1("session_dir")

    return sess_dir.as_posix()


# for element-calcium-imaging activation
def get_imaging_root_data_dir():
    return get_raw_root_data_dir()


def get_scan_image_files(scan_key):
    # Folder structure: root / subject / session / .tif (raw)
    data_dir = get_imaging_root_data_dir()

    from workflow.pipeline import session

    sess_dir = data_dir / (session.SessionDirectory & scan_key).fetch1("session_dir")

    if not sess_dir.exists():
        raise FileNotFoundError(f"Session directory not found ({sess_dir})")

    tiff_filepaths = [fp.as_posix()
                      for fp in (sess_dir / "Imaging" / f"scan{scan_key['scan_id']}").glob("*.tif")
                      if not fp.name.startswith('zstack')]
    if tiff_filepaths:
        return tiff_filepaths
    else:
        raise FileNotFoundError(f"No tiff file found in {sess_dir}")


def get_dlc_root_data_dir():
    return get_raw_root_data_dir()


def get_dlc_processed_data_dir():
    return get_processed_root_data_dir()
