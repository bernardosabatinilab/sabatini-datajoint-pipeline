import datajoint as dj
import json
import os
import pandas as pd
import numpy as np
import seaborn as sns
import scipy.signal
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from element_interface.utils import find_full_path

from workflow import db_prefix
from workflow.pipeline import session, event, model, photometry, ephys
from workflow.utils.plotting import ephys_plots, photometry_plots

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

@schema
class EphysPlots(dj.Computed):
    definition = """
    -> ephys.EphysRecording
    ---
    summary_plot: attach
    driftmap_plot: attach
    raster_plot: attach
    peak_waveforms_plot: attach
    periodogram_plot: attach
    power_spectrum_plot: attach
    """
    key_source = ephys.EphysRecording

    def make(self, key):
        #get data dir
        session_id = (session.Session & key).fetch1("session_id")
        session_dir = (session.SessionDirectory & key).fetch1("session_dir")
        session_full_dir: Path = find_full_path(get_raw_root_data_dir(), session_dir)
        report_dir = session_full_dir / "Report_figures"
        report_dir.mkdir(exist_ok=True, parents=True)

        #fetch lfp_key
        lfp_key = (ephys.LFP & key).fetch1("KEY")
        probe_key = (ephys.CuratedClustering & key).fetch1("KEY")
        freq_bands = [(0.5, 4), (4, 8), (8, 13), (13, 30), (30, 50)] #delta, theta, alpha, beta, gamma

        # Begin summary plot
        good_units = ephys.CuratedClustering.Unit & probe_key & "cluster_quality_label='good'"
        noise_units = ephys.CuratedClustering.Unit & probe_key & "cluster_quality_label='noise'"
        fig1=ephys_plots.plot_counts(good_units, noise_units, probe_key)
        fig1.savefig(report_dir / f"{session_id}_summary_plot.png")
        summary_plot = os.path.join(report_dir, f"{session_id}_summary_plot.png")
        # End summary plot

        # Begin driftmap plot
        units = ephys.CuratedClustering.Unit & probe_key & "cluster_quality_label='good'"
        table = units * ephys.ProbeInsertion * probe.ProbeType.Electrode
        spike_times, spike_depths = table.fetch("spike_times", "spike_depths", order_by="unit")
        fig2 = ephys_plots.plot_driftmap(spike_times, spike_depths, colormap="gist_heat_r")
        fig2.savefig(report_dir / f"{session_id}_driftmap_plot.png")
        driftmap_plot = os.path.join(report_dir, f"{session_id}_driftmap_plot.png")
        # End driftmap plot

        # Begin raster plot
        units, unit_spiketimes = (ephys.CuratedClustering.Unit & probe_key & "cluster_quality_label='good'").fetch("unit", "spike_times")
        fig3 = ephys_plots.plot_raster(units, unit_spiketimes, probe_key)
        fig3.savefig(report_dir / f"{session_id}_raster_plot.png")
        raster_plot = os.path.join(report_dir, f"{session_id}_raster_plot.png")
        # End raster plot

        # Begin peak waveforms plot
        unit_key = (ephys.CuratedClustering.Unit & probe_key & "cluster_quality_label='good'").fetch("KEY")
        unit_data = (ephys.CuratedClustering.Unit * ephys.WaveformSet.PeakWaveform & unit_key).fetch()
        fig4=ephys_plots.plot_peak_waveforms(unit_data, probe_key)
        fig4.savefig(report_dir / f"{session_id}_peak_waveforms_plot.png")
        peak_waveforms_plot = os.path.join(report_dir, f"{session_id}_peak_waveforms_plot.png")
        # End peak waveforms plot

        # Begin periodogram plot
        from scipy.signal import welch
        lfp_channels = (ephys.LFP.Electrode & lfp_key).fetch("electrode")
        lfp_signals = (ephys.LFP.Electrode & lfp_key).fetch("lfp")
        lfp_fs = (ephys.LFP & lfp_key).fetch1("lfp_sampling_rate")

        power_spectral_density = []
        frequencies = []

        for i, (channel, signal) in enumerate(zip(lfp_channels, lfp_signals)):
            f, Pxx = welch(signal, fs=lfp_fs, nperseg=lfp_fs*2)
            power_spectral_density.append(Pxx)
            frequencies.append(f)

        #grab first 200 points for each channel
        power_spectral_density_filt = np.array(power_spectral_density)[:, :200]
        frequencies_filt = np.array(frequencies)[:, :200]

        import seaborn as sns
        fig5, ax = plt.subplots(figsize=(10, 5))
        for i, (channel, psd) in enumerate(zip(lfp_channels, power_spectral_density_filt)):
            ax.plot(frequencies_filt[i], np.log(psd))
        ax.set(xlabel="Frequency (Hz)", ylabel="Power log(\u03bcV^2/Hz)")
        ax.set_title(f"Welch's periodgram for {key['subject']} per channel ({len(lfp_channels)} total)")
        sns.despine()
        fig5.savefig(report_dir / f"{session_id}_periodogram_plot.png")
        periodogram_plot = os.path.join(report_dir, f"{session_id}_periodogram_plot.png")
        # End periodogram plot

        # Begin power spectra plot
        idx_delta = np.logical_and(frequencies_filt[0] >= freq_bands[0][0], frequencies_filt[0] <= freq_bands[0][1])
        idx_theta = np.logical_and(frequencies_filt[0] >= freq_bands[1][0], frequencies_filt[0] <= freq_bands[1][1])
        idx_alpha = np.logical_and(frequencies_filt[0] >= freq_bands[2][0], frequencies_filt[0] <= freq_bands[2][1])
        idx_beta = np.logical_and(frequencies_filt[0] >= freq_bands[3][0], frequencies_filt[0] <= freq_bands[3][1])
        idx_gamma = np.logical_and(frequencies_filt[0] >= freq_bands[4][0], frequencies_filt[0] <= freq_bands[4][1])

        #seperate out the power spectral density for each frequency band
        delta_psd = power_spectral_density_filt[:, idx_delta]
        theta_psd = power_spectral_density_filt[:, idx_theta]
        alpha_psd = power_spectral_density_filt[:, idx_alpha]
        beta_psd = power_spectral_density_filt[:, idx_beta]
        gamma_psd = power_spectral_density_filt[:, idx_gamma]
        #calculate abosulte power for each frequency band
        from scipy.integrate import simps
        delta_freq_res = frequencies_filt[0][1] - frequencies_filt[0][0]
        delta_power = simps(delta_psd, dx=delta_freq_res)

        theta_freq_res = frequencies_filt[0][1] - frequencies_filt[0][0]
        theta_power = simps(theta_psd, dx=theta_freq_res)

        alpha_freq_res = frequencies_filt[0][1] - frequencies_filt[0][0]
        alpha_power = simps(alpha_psd, dx=alpha_freq_res)

        beta_freq_res = frequencies_filt[0][1] - frequencies_filt[0][0]
        beta_power = simps(beta_psd, dx=beta_freq_res)

        gamma_freq_res = frequencies_filt[0][1] - frequencies_filt[0][0]
        gamma_power = simps(gamma_psd, dx=gamma_freq_res)
        #Match channels to their respective depths
        table = ephys.ProbeInsertion * probe.ProbeType.Electrode & lfp_key
        site, depths = table.fetch("shank_row", "y_coord", order_by="shank_row")
        depths = [depths[i] for i in lfp_channels]
        #map depths to each frequency band power in a dataframe
        power_df = pd.DataFrame({"depth": depths, "delta_power": delta_power, "theta_power": theta_power, "alpha_power": alpha_power, "beta_power": beta_power, "gamma_power": gamma_power})
        power_df.sort_values(by="depth", inplace=True)
        fig6 = ephys_plots.plot_power_spectrum(power_df)
        fig6.savefig(report_dir / f"{session_id}_power_spectrum_plot.png")
        power_spectrum_plot = os.path.join(report_dir, f"{session_id}_power_spectrum_plot.png")
        # End power spectra plot

        self.insert1({**lfp_key, "summary_plot": summary_plot, "driftmap_plot": driftmap_plot, "raster_plot": raster_plot,
                      "peak_waveforms_plot": peak_waveforms_plot, "periodogram_plot": periodogram_plot,
                      "power_spectrum_plot": power_spectrum_plot})
        

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
