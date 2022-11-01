from element_event import event, trial

from workflow import db_prefix
from workflow.pipeline import session


__all__ = ["event", "trial"]

Session = session.Session

# ------------- Activate "trial" schema -------------
if not trial.schema.is_activated():
    trial.activate(db_prefix + "trial", db_prefix + "event", linking_module=__name__)
