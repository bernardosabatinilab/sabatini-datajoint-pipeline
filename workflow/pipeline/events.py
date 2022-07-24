from element_event import event, trial 

from workflow import db_prefix
from workflow.pipeline import lab, session
from workflow.utils.paths import (get_ephys_root_data_dir,
                                  get_processed_root_data_dir,
                                  get_session_directory)

__all__ = ['event', 'trial']

# ------------- Activate "event" schema -------------
Session = session.Session

if not event.schema.is_activated():
    event.activate(db_prefix + 'event', linking_module=__name__)

# ------------- Activate "trial" schema -------------
Event = event.Event

if not trial.schema.is_activated():
    trial.activate(db_prefix + 'trial', db_prefix + 'event',linking_module=__name__)

