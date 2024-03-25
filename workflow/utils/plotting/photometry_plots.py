import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.stats import sem

from workflow.pipeline import photometry, event

def plot_event_aligned_photometry(session_key, *, trace_name, emission_color, hemisphere, events_OI):
    restr = {
        "trace_name": trace_name,
        "emission_color": emission_color,
        "hemisphere": hemisphere
    }

    time_buffer = (20, 60)  # before and after each event

    trace = (photometry.FiberPhotometrySynced.SyncedTrace & session_key & restr).fetch1("trace")
    timestamps = np.array((photometry.FiberPhotometrySynced & session_key).fetch1("timestamps"))

    fig, axes = plt.subplots(1, len(events_OI), figsize=(23, 3))

    RMS = []
    CI = []
    avg_trace = []
    SEM = []

    for ind, (event_type, ax) in enumerate(zip(events_OI, axes)):

        event_traces = []  # Store traces for this event type

        desired_length = len(trace)
        new_timestamps = np.linspace(timestamps[0], timestamps[-1], desired_length)
        df = pd.DataFrame({"timestamps": new_timestamps, "photometry_trace": trace})

        # Query the event_start_time for the respective event type
        query = event.Event & session_key & f"event_type='{event_type}'"
        event_ts = query.fetch("event_start_time")

        # Iterate over each event time
        for ts in event_ts:
            # Find the corresponding index in the trace for the event time
            index = np.searchsorted(df["timestamps"], ts)

            # Define the time window around the event
            window_start = index - int(time_buffer[0])
            window_end = index + int(time_buffer[1]) + 1

            # Extract the peri-event window
            peri_event_window = df.iloc[window_start:window_end]

            if len(peri_event_window["photometry_trace"]) == len(range(window_start, window_end)):
                event_traces.append(peri_event_window["photometry_trace"].values)

        if event_traces:  # Check if there are event traces
            event_traces = np.array(event_traces)  # trial x time

            # Compute the mean and standard error of the event traces
            mean_trace = np.mean(event_traces, axis=0)
            sem_trace = sem(event_traces, axis=0)
            mean_trace_timestamps = np.arange(-time_buffer[0], time_buffer[1] + 1)
            avg_trace.append(mean_trace)
            SEM.append(sem_trace)

            # compute confidence interval
            from scipy.stats import norm
            confidence = 0.95
            alpha_2 = (1 - confidence) / 2
            critical_value = norm.ppf(1 - alpha_2)

            ci = [(mean_trace - (critical_value * sem_trace)),
                  (mean_trace + (critical_value * sem_trace))]
            CI.append(ci)

            # compute RMS
            rms = np.sqrt(mean_trace ** 2)
            RMS.append(rms)

            # Plot the mean trace with standard error
            ax.plot(mean_trace_timestamps, mean_trace, label=event_type, lw=2)
            ax.fill_between(mean_trace_timestamps, mean_trace - sem_trace, mean_trace + sem_trace, alpha=0.3)

        ax.axvline(x=0, linewidth=0.5, ls='--')
        if ind == 0:
            ax.set_ylabel("Trace Name", fontsize=15)
        ax.set(xlabel='Sample', title=event_type)
        sns.despine()

    return fig, CI, RMS, avg_trace, SEM

