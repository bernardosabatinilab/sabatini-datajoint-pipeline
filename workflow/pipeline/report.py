import datajoint as dj
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from workflow import db_prefix
from workflow.pipeline import session, event, model, photometry

import workflow.utils.photometry_preprocessing as pp
from workflow.utils.paths import get_processed_root_data_dir


schema = dj.schema(db_prefix + "report")

report_figures_dir = get_processed_root_data_dir() / "report_figures"
report_figures_dir.mkdir(exist_ok=True, parents=True)


# Pose estimation plots

@schema
class PoseEstimationPlots(dj.Computed):
    definition = """
    -> model.PoseEstimation
    """

    class BodyPart(dj.Part):
        definition = """
        -> master
        body_part: varchar(64)
        ---
        bodypart_xy_plot: attach
        bodypart_time_plot: attach
        """

    def make(self, key):
        body_parts = (model.PoseEstimation.BodyPartPosition & key).fetch('body_part')

        pose_df = (model.PoseEstimation.BodyPartPosition & key).fetch(format='frame').reset_index()
        pose_df = pose_df.explode(column=["frame_index", "x_pos", "y_pos", "likelihood"])

        self.insert1(key)

        for body_part in body_parts:
            body_part_df = pose_df[pose_df['body_part'] == body_part]
            fig1, ax = plt.subplots(figsize=(12, 6))
            sns.scatterplot(body_part_df, x='x_pos', y='y_pos', hue='frame_index', style='body_part', alpha=0.3, ax=ax)

            fig2, axs = plt.subplots(2, 1, figsize=(12, 6))
            axs[0].plot(body_part_df['frame_index'], body_part_df['x_pos'], 'r', label='x_pos')
            axs[1].plot(body_part_df['frame_index'], body_part_df['y_pos'], 'b', label='y_pos')

            saved_fig_paths = save_figs(
                {"bodypart_xy_plot": fig1, "bodypart_time_plot": fig2},
                save_dir=get_session_figs_dir(key),
                fig_prefix="-".join([str(v) for v in key.values()]) + "-" + body_part,
                extension=".png",
            )
            self.BodyPart.insert1({**key, "body_part": body_part, **saved_fig_paths})

# photometry plots

@schema
class FiberPhotometryPlots(dj.Computed):
    definition = """
    -> photometry.FiberPhotometrySynced
    ---
    demodulated_trace_plot: attach
    event_aligned_plot: attach
    photometry_analysis_summary: longblob
    """

    key_source = photometry.FiberPhotometrySynced & event.BehaviorRecording

    def make(self, key):
        from workflow.utils.plotting.photometry_plots import plot_event_aligned_photometry

        # Demodulated trace plot
        query = photometry.FiberPhotometry.DemodulatedTrace & key
        traces = query.fetch("trace_name", "emission_color", "hemisphere", "trace", as_dict=True)

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

        # event-aligned plot
        events_OI = ['lick', 'water']
        fig1, CI, RMS, avg_trace, SEM = plot_event_aligned_photometry(key, trace_name='photom', emission_color='green',
                                                                      hemisphere='right', events_OI=events_OI)
        analysis_summary = {'mean': avg_trace, 'RMS': RMS, 'SEM': SEM, 'aligned_events': events_OI}

        saved_fig_paths = save_figs(
            {"demodulated_trace_plot": fig0, "event_aligned_plot": fig1},
            save_dir=get_session_figs_dir(key),
            fig_prefix="-".join([str(v) for v in key.values()]),
            extension=".png",
        )

        self.insert1({**key, **saved_fig_paths, "photometry_analysis_summary": analysis_summary})


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
