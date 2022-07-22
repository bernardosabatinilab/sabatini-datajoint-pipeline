import datajoint as dj

from element_lab import lab
from element_animal import subject
from element_session import session_with_id as session

from workflow import db_prefix

__all__ = ['lab', 'subject', 'session']


# ------------- Activate "lab", "subject", "session" schema -------------

lab.activate(db_prefix + "lab")

Subject = subject.Subject

Subject.definition = Subject.definition.replace("varchar(8)", "varchar(24)")
subject.activate(db_prefix + "subject", linking_module=__name__)

Experimenter = lab.User
session.activate(db_prefix + "session", linking_module=__name__)

# ------------- Declare table Equipment for use in element_calcium_imaging -------------


@lab.schema
class Equipment(dj.Lookup):
    definition = """
    scanner: varchar(32)
    """
    contents = zip(["Nikon A1 plus"])


lab.Equipment = Equipment

# ------------- Declare table Device for use in element_facemap -------------


@lab.schema
class Device(dj.Lookup):
    definition = """
    device_id         : smallint
    ---
    device_name       : varchar(32)  # user-friendly name of the device
    device_description: varchar(256)
    """

    contents = [(0, "face_camera", "Face camera"), (1, "behavior_camera", "Behavior camera")]


lab.Device = Device
