import os
import datajoint as dj
from datajoint_utilities.dj_notification.notifier.email_notifier import MailgunEmailNotifier
from datajoint_utilities.dj_notification.notifier.slack_notifier import SlackWebhookNotifier
from datajoint_utilities.dj_notification.loghandler import PopulateHandler

from workflow import db_prefix
from workflow.pipeline import session, scan, imaging, model, train, fbe as facemap
from workflow.support import imaging_support, facemap_support

__all__ = ['logger']

logger = dj.logger

org_name, workflow_name, _ = db_prefix.split('_')
org_vm = dj.create_virtual_module('org_vm', f'{org_name}_admin_workflow')

workflow_key = (org_vm.Workflow & {'wf_db_prefix': db_prefix}).fetch1('KEY')

if hasattr(org_vm, 'WorkflowNotification') and (org_vm.WorkflowNotification & workflow_key):
    notifiers = []
    for notif in (org_vm.WorkflowNotification & workflow_key).proj('notif_type').fetch(as_dict=True):
        if notif['notif_type'] == 'mailgun':
            mailgun_api_key, mailgun_domain_name, sender_name, sender_email = (
                    org_vm.WorkflowNotification.MailGun & workflow_key).fetch1(
                'mailgun_api_key',
                'mailgun_domain_name',
                'mailgun_sender_name',
                'mailgun_sender_email')
            receiver_emails = (org_vm.WorkflowNotification.ReceiverEmail & workflow_key).fetch('receiver_email')
            email_notifier = MailgunEmailNotifier(mailgun_api_key=mailgun_api_key,
                                                  mailgun_domain_name=mailgun_domain_name,
                                                  sender_name=sender_name,
                                                  sender_email=sender_email,
                                                  receiver_emails=receiver_emails)
            notifiers.append(email_notifier)
        elif notif['notif_type'] == 'slack_webhook':
            webhook_url = (org_vm.WorkflowNotification.SlackWebhook & workflow_key).fetch1('slack_webhook_url')
            slack_notifier = SlackWebhookNotifier(webhook_url=webhook_url)
            notifiers.append(slack_notifier)

    if notifiers:
        verbose_handler = PopulateHandler(notifiers=notifiers,
                                          full_table_names=[scan.ScanInfo.full_table_name,
                                                            imaging.ProcessingTask.full_table_name,
                                                            imaging.Processing.full_table_name,
                                                            imaging.Activity.full_table_name,
                                                            facemap.RecordingInfo.full_table_name,
                                                            facemap.FacemapTask.full_table_name,
                                                            facemap.FacemapProcessing.full_table_name,
                                                            facemap.FacialSignal.full_table_name],
                                          on_start=True, on_success=True, on_error=True)

        verbose_handler.setLevel('DEBUG')

        logger.setLevel('DEBUG')
        logger.addHandler(verbose_handler)
