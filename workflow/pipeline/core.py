import datajoint as dj
from element_animal import subject
from element_lab import lab
from element_session import session_with_id as session

from workflow import db_prefix

__all__ = ['lab', 'subject', 'session']

# ------------- Activate "lab" schema -------------
lab.activate(db_prefix + 'lab')
    
Source = lab.Source
Lab = lab.Lab
Protocol = lab.Protocol
User = lab.User
Location = lab.Location
Project = lab.Project

# Declare SkullReference table for use in element-array-ephys
@lab.schema
class SkullReference(dj.Lookup):
    definition = """
    skull_reference   : varchar(60)
    """
    contents = zip(['Bregma', 'Lambda'])

lab.SkullReference = SkullReference 

# Declare Equipment table for use in element_calcium_imaging 
@lab.schema
class Equipment(dj.Lookup):
    definition = """
    scanner: varchar(32)
    """
    contents = zip(["Nikon A1 plus"])

lab.Equipment = Equipment

# ------------- Activate "subject" schema -------------
subject.activate(db_prefix + 'subject', linking_module=__name__)
Subject = subject.Subject

Experimenter = lab.User

# ------------- Activate "session" schema -------------
session.activate(db_prefix + 'session', linking_module=__name__)


