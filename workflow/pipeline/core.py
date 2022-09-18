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

# ------------- Activate "subject" schema -------------
subject.activate(db_prefix + 'subject', linking_module=__name__)
Subject = subject.Subject

Experimenter = lab.User

# ------------- Activate "session" schema -------------
session.activate(db_prefix + 'session', linking_module=__name__)


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

# Declare Device table for use in element_deeplabcut
@lab.schema
class Device(dj.Lookup):
    definition = """
    device_id           : smallint
    ---
    device_name         : varchar(32)  # user-friendly name of the device
    device_description  : varchar(256)
    """

lab.Device = Device


@lab.schema
class Virus(dj.Lookup):
    definition = """            
    name                : varchar(32)  # (e.g., AAV9-DIO-GCaMP6s)
    ---
    notes=''            : varchar(64)  
    """
    
lab.Virus = Virus

@lab.schema
class BrainAtlas(dj.Lookup):
    definition = """  # Common Coordinate Framework
    atlas_id                : int             # CCF ID, a.k.a atlas ID
    ---
    atlas_version=''        : varchar(64)     # Allen CCF Version - e.g. CCFv3
    atlas_description=''    : varchar(255)    # CCFLabel Description
    """

lab.BrainAtlas = BrainAtlas

@lab.schema
class BrainRegion(dj.Lookup):
    definition = """
    -> BrainAtlas
    acronym                 : varchar(32)
    ---
    region_name             : varchar(128)
    region_id=null          : int
    color_code=null         : varchar(6)  # hexcode of the color code of this region
    """
    
lab.BrainRegion = BrainRegion


@lab.schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(32)
    """

    contents = zip(["left", "right", "middle"])

lab.Hemisphere = Hemisphere

@lab.schema
class ImplantationType(dj.Lookup):
    definition = """
    implant_type: varchar(16)
    """

    contents = zip(["ephys", "fiber"]) 
    

lab.ImplantationType = ImplantationType

@lab.schema
class Implantation(dj.Manual):  # may not necessarily be a fiber here
    definition = """
    -> subject.Subject
    implant_date  : date   # surgery date
    -> ImplantationType
    -> BrainRegion
    -> Hemisphere
    ---
    -> lab.User.proj(surgeon='user')        # surgeon
    ap            : decimal(3, 2)           # (um) anterior-posterior; ref is 0
    -> lab.SkullReference.proj(ap_ref='skull_reference')
    ml            : decimal(3, 2)           # (um) medial axis; ref is 0 
    -> lab.SkullReference.proj(ml_ref='skull_reference')
    dv            : decimal(3, 2)           # (um) dorso-ventral axis; ref is 0; more ventral is more negative
    -> lab.SkullReference.proj(dv_ref='skull_reference')
    theta=null    : decimal(3, 2)           # (deg) rotation about the ml-axis [0, 180] - w.r.t the z+ axis
    phi=null      : decimal(3, 2)           # (deg) rotation about the dv-axis [0, 360] - w.r.t the x+ axis
    beta=null     : decimal(3, 2)           # (deg) rotation about the shank of the fiber [-180, 180] - clockwise is increasing in degree - 0 is the probe-front facing anterior
    """
    
lab.Implantation = Implantation
 
@lab.schema
class VirusInjection(dj.Manual):
    definition = """
    -> subject.Subject
    injection_id        : tinyint unsigned
    ---
    -> lab.Virus
    -> lab.User
    injection_volume        : float                         # injection volume
    injection_time=null     : datetime                      # injection time
    rate_of_injection=null  : float                         # rate of injection
    wait_time=null          : float                         # wait time after injection
    target_region           : varchar(16)
    -> Hemisphere
    notes=''                : varchar(1000)
    """

    class Coordinate(dj.Part):
        definition = """
        -> master
        ---
        -> lab.SkullReference                   # (e.g., bregma or lambda)
        ap            : decimal(6, 2)           # (um) anterior-posterior; ref is 0
        ml            : decimal(6, 2)           # (um) medial axis; ref is 0 
        dv            : decimal(6, 2)           # (um) dorso-ventral axis; ref is 0; more ventral is more negative
        dv_reference  : enum("skull", "dura")   # (um) refence (0) for the dorso-ventral axis; (e.g., 'skull' or 'dura') - should be <=0
        theta=null    : decimal(5, 2)           # (deg) rotation about the ml-axis [0, 180] - w.r.t the z+ axis
        phi=null      : decimal(5, 2)           # (deg) rotation about the dv-axis [0, 360] - w.r.t the x+ axis
        beta=null     : decimal(5, 2)           # (deg) rotation about the shank of the fiber [-180, 180] - clockwise is increasing in degree - 0 is the probe-front facing anterior
        """
 
lab.VirusInjection = VirusInjection
 
 
@subject.schema
class Perfusion(dj.Manual):
    definition = """
    -> subject.Subject
    ---
    -> lab.User.proj(experimenter='user')  # person who performed perfusion
    date                : date          # perfusion date
    reagent             : varchar(16)   # (e.g., PFA)
    """
    
subject.Perfusion = Perfusion
    