import sys
from datajoint_utilities.dj_worker import parse_args

from workflow.populate.worker import standard_worker, spike_sorting_worker, logger


# -------- Run process(s) --------
configured_workers = {
    'standard_worker': standard_worker,
    'spike_sorting_worker': spike_sorting_worker
}


def run(**kwargs):
    worker = configured_workers[kwargs["worker_name"]]
    if kwargs.get("duration") is not None:
        worker._run_duration = kwargs["duration"]
    if kwargs.get("sleep") is not None:
        worker._sleep_duration = kwargs["sleep"]

    try:
        worker.run()
    except Exception:
        logger.exception(
            "Worker '{}' encountered an exception:".format(kwargs["worker_name"])
        )


def cli():
    """
    Calls :func:`run` passing the CLI arguments extracted from `sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    args = parse_args(sys.argv[1:])
    run(
        worker_name=args.worker_name,
        duration=args.duration,
        sleep=args.sleep
    )


if __name__ == '__main__':
    cli()
