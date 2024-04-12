## Ephys plotting functions

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy.stats import sem
import plotly.graph_objects as go

from workflow.pipeline import ephys, probe, event 

def plot_driftmap(
    spike_times: np.ndarray, spike_depths: np.ndarray, colormap="gist_heat_r"
) -> matplotlib.figure.Figure:
    """Plot drift map of unit activity for all units recorded in a given shank of a probe.

    Args:
        spike_times (np.ndarray): Spike timestamps in seconds.
        spike_depths (np.ndarray): The depth of the electrode where the spike was found in μm.
        colormap (str, optional): Colormap. Defaults to "gist_heat_r".

    Returns:
        matplotlib.figure.Figure: matplotlib figure object for showing population activity for all units over time (x-axis in seconds) according to the spatial depths of the spikes (y-axis in μm).
    """

    spike_times = np.hstack(spike_times)
    spike_depths = np.hstack(spike_depths)

    # Time-depth 2D histogram
    time_bin_count = 1000
    depth_bin_count = 200

    spike_bins = np.linspace(0, spike_times.max(), time_bin_count)
    depth_bins = np.linspace(0, np.nanmax(spike_depths), depth_bin_count)

    spk_count, spk_edges, depth_edges = np.histogram2d(
        spike_times, spike_depths, bins=[spike_bins, depth_bins]
    )
    spk_rates = spk_count / np.mean(np.diff(spike_bins))
    spk_edges = spk_edges[:-1]
    depth_edges = depth_edges[:-1]

    # Canvas setup
    fig = plt.figure(figsize=(12, 5), dpi=200)
    grid = plt.GridSpec(15, 12)

    ax_cbar = plt.subplot(grid[0, 0:10])
    ax_driftmap = plt.subplot(grid[2:, 0:10])
    ax_spkcount = plt.subplot(grid[2:, 10:])

    # Plot main
    im = ax_driftmap.imshow(
        spk_rates.T,
        aspect="auto",
        cmap=colormap,
        extent=[spike_bins[0], spike_bins[-1], depth_bins[-1], depth_bins[0]],
    )
    # Cosmetic
    ax_driftmap.invert_yaxis()
    ax_driftmap.set(
        xlabel="Time (s)",
        ylabel="Distance from the probe tip ($\mu$m)",
        ylim=[depth_edges[0], depth_edges[-1]],
    )

    # Colorbar for firing rates
    cb = fig.colorbar(im, cax=ax_cbar, orientation="horizontal")
    cb.outline.set_visible(False)
    cb.ax.xaxis.tick_top()
    cb.set_label("Firing rate (Hz)")
    cb.ax.xaxis.set_label_position("top")

    # Plot spike count
    ax_spkcount.plot(spk_count.sum(axis=0) / 10e3, depth_edges, "k")
    ax_spkcount.set_xlabel("Spike count (x$10^3$)")
    ax_spkcount.set_yticks([])
    ax_spkcount.set_ylim(depth_edges[0], depth_edges[-1])
    sns.despine()

    return fig