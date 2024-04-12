import datajoint as dj
import json
import os
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from element_interface.utils import find_full_path

from workflow import db_prefix
from workflow.pipeline import session, event, model, photometry

import workflow.utils.photometry_preprocessing as pp
from workflow.utils.paths import get_raw_root_data_dir


schema = dj.schema(db_prefix + "report")

#report_figures_dir = find_full_path(get_processed_root_data_dir(), "outbox/report_figures")
#report_figures_dir.mkdir(exist_ok=True, parents=True)

# Pose estimation plots

@schema
class PoseEstimationPlots(dj.Computed):
    definition = """
    -> model.PoseEstimation
    """

    class Summary(dj.Part):
        definition = """
        -> master
        ---
        bodypart_xy_plot: attach
        bodypart_time_plot: longblob
        """

    def make(self, key):
        #get data dir
        session_id = (session.Session & key).fetch1("session_id")
        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
        report_dir = session_full_dir / "Report_figures"
        report_dir.mkdir(exist_ok=True, parents=True)

        body_parts = (model.PoseEstimation.BodyPartPosition & key).fetch('body_part')

        pose_df = (model.PoseEstimation.BodyPartPosition & key).fetch(format='frame').reset_index()
        pose_df = pose_df.explode(column=["frame_index", "x_pos", "y_pos", "likelihood"])

        self.insert1(key)

        fig1, ax = plt.subplots(figsize=(12, 6))
        for_title = key['subject'], key['session_id']
        for_title = " ".join([str(i) for i in for_title])
        for body_part in body_parts:
            body_part_df = pose_df[pose_df['body_part'] == body_part]
            sns.scatterplot(data=body_part_df, x='x_pos', y='y_pos', label=body_part, ax=ax).set_title(f'Body part positions for {for_title}')

        fig2 = make_subplots(rows=2, cols=1)
        for body_part in body_parts:
            body_part_df = pose_df[pose_df['body_part'] == body_part]

            # Plot line plot for likelihood over time using Plotly
            fig2.add_trace(go.Scatter(x=body_part_df['frame_index'], y=body_part_df['likelihood'], mode='lines', name=body_part), row=1, col=1)

        # Update subplot titles and axis labels for Plotly figure
        fig2.update_layout(title='All body parts over time (e.g. frames)', height=800, width=1200)
        fig2.update_xaxes(title_text='Frame Index', row=1, col=1)
        fig2.update_yaxes(title_text='Likelihood', row=1, col=1)

        fig1.savefig(report_dir / f"{session_id}_bodypart_xy_plot.png")
        fig2.write_html(report_dir / f"{session_id}_bodypart_ll_plot.html")

        bodypart_xy_plot = os.path.join(report_dir, f"{session_id}_bodypart_xy_plot.png")

        self.Summary.insert1({**key, 
                                'bodypart_xy_plot': bodypart_xy_plot, 
                                'bodypart_time_plot': json.loads(fig2.to_json())})

# photometry plots

@schema
class FiberPhotometryPlots(dj.Computed):
    definition = """
    -> photometry.FiberPhotometrySynced.SyncedTrace
    ---
    demodulated_trace_plot: attach
    event_aligned_plot: attach
    photometry_analysis_summary: longblob
    """

    key_source = photometry.FiberPhotometrySynced.SyncedTrace & event.BehaviorRecording

    def make(self, key):
        from workflow.utils.plotting.photometry_plots import plot_event_aligned_photometry_combined, plot_event_aligned_photometry
        #get data dir
        session_id = (session.Session & key).fetch1("session_id")
        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
        report_dir = session_full_dir / "Report_figures"
        report_dir.mkdir(exist_ok=True, parents=True)

        # Demodulated trace plot
        query = photometry.FiberPhotometry.DemodulatedTrace & key
        traces = query.fetch("trace_name", "emission_color", "hemisphere", "trace", as_dict=True)
        trace_names = [trace["trace_name"] for trace in traces]

        i = 8
        inc_height = -1.5
        window_start = 1000
        window_stop = 3000
        n_colors = len(query)
        fig0, ax = plt.subplots(figsize=(10, 3))
        sns.set_palette('deep', n_colors)

        for j, trace in enumerate(traces):
            name = '_'.join([trace["trace_name"], trace["emission_color"], trace["hemisphere"]])
            ax.plot(pp.normalize(pd.DataFrame(trace["trace"]), window=500)[window_start:window_stop] + i,
                    label=name)
            i += inc_height
            ax.text(x=window_stop + 2, y=i - inc_height, s=name, fontsize=12, va="bottom", color=sns.color_palette()[j])

        ax.set_title(f"{key}")
        ax.set_xlabel("Time (s)")
        ax.set_yticks([])
        sns.despine(left=True)

        fig0.savefig(report_dir / f"{session_id}_demodulated_trace_plot.png")
        demod_trace_plot= os.path.join(report_dir, f"{session_id}_demodulated_trace_plot.png")

        #event-aligned plot for each emission color and hemisphere
        #cycle through traces that = photom
        for trace_name in trace_names:
            if trace_name == 'photom':
                key_source = (photometry.FiberPhotometrySynced.SyncedTrace & key & {"trace_name": trace_name}).fetch1("KEY")
                #cycle through unique combinations of emission color and hemisphere and plot event-aligned photometry
                unique_combinations = (photometry.FiberPhotometrySynced.SyncedTrace & key_source).fetch("emission_color", "hemisphere", as_dict=True, order_by="emission_color, hemisphere")
                for combination in unique_combinations:
                    key = {**key_source, **combination}
                    fig1, CI, RMS, avg_trace, SEM = plot_event_aligned_photometry(key, trace_name='photom', emission_color='green',
                                                                      hemisphere='right', events_OI=events_OI)
                    analysis_summary = {'mean': avg_trace, 'RMS': RMS, 'SEM': SEM, 'aligned_events': events_OI}
                    fig1.savefig(report_dir / f"{session_id}_event_aligned_plot_{trace_name}_{combination['emission_color']}_{combination['hemisphere']}.png")
                    event_aligned_plot = os.path.join(report_dir, f"{session_id}_event_aligned_plot_{trace_name}_{combination['emission_color']}_{combination['hemisphere']}.png")
                    self.insert1({**key, "demodulated_trace_plot": demod_trace_plot,
                                    "event_aligned_plot": event_aligned_plot,
                                    "photometry_analysis_summary": analysis_summary})



# ---- Helper functions ----

def save_figs(
    fig_dict, save_dir, fig_prefix, extension=".png"
):
    """
    Save figures in fig_dict to save_dir with the specified prefix and extension
    Returns a dictionary of saved figure paths with the same keys as fig_dict
    """
    save_dir.mkdir(exist_ok=True, parents=True)
    saved_fig_paths = {}
    for fig_name, fig in fig_dict.items():
        if fig:
            fig_filepath = save_dir / (fig_prefix + "_" + fig_name + extension)
            saved_fig_paths[fig_name] = fig_filepath.as_posix()
            fig.tight_layout()
            fig.savefig(fig_filepath)
            plt.close(fig)

    return saved_fig_paths


def get_session_figs_dir(key):
    """
    Get the directory to save figures for a given session key
    """
    session_key = (session.Session & key).fetch1("KEY")
    return report_figures_dir / "-".join([str(v) for v in session_key.values()])
