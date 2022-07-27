import os
import datajoint as dj
from datajoint_utilities.dj_notification.notifier.slack_notifier import SlackWebhookNotifier
from datajoint_utilities.dj_notification.loghandler import PopulateHandler

from workflow import db_prefix
from workflow.pipeline import session, ephys, scan, imaging, model, train

__all__ = ['logger']
logger = dj.logger

webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

notifiers = []
if webhook_url:
    slack_notifier = SlackWebhookNotifier(webhook_url=webhook_url)
    notifiers.append(slack_notifier)

if notifiers:
    verbose_handler = PopulateHandler(notifiers=notifiers,
                                        full_table_names=[scan.ScanInfo.full_table_name,
                                                        imaging.ProcessingTask.full_table_name,
                                                        imaging.Processing.full_table_name,
                                                        imaging.Activity.full_table_name,
                                                        ephys.ProbeInsertion.full_table_name,
                                                        ephys.EphysRecording.full_table_name,
                                                        ephys.Clustering.full_table_name,
                                                        ephys.CuratedClustering.full_table_name,
                                                        ephys.WaveformSet.full_table_name],
                                        on_start=True, on_success=True, on_error=True)

    verbose_handler.setLevel('DEBUG')

    logger.setLevel('DEBUG')
    logger.addHandler(verbose_handler)
