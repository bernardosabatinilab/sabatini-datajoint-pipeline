## Ephys plotting functions

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib
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

def plot_peak_waveforms(unit_data, probe_key):
    import matplotlib.pyplot as plt
    import numpy as np

    n_units = len(unit_data)
    n_cols = 5
    n_rows = int(np.ceil(n_units / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 3 * n_rows))

    for i, (ax, waveform) in enumerate(zip(axes.flat, unit_data["peak_electrode_waveform"])):
        ax.plot(waveform)
        ax.set_title(f"Unit {i+1}")
        ax.set_ylabel("Voltage (uV)")

    # Hide the empty subplots
    for i in range(n_units, n_rows * n_cols):
        axes.flat[i].axis("off")

    #add master title
    fig.suptitle(f"Peak Waveforms for Good Units {probe_key['subject'], probe_key['session_id']}",
                fontsize=20, y=1.0)
    plt.tight_layout()

    return fig

def plot_counts(good_units, noise_units, probe_key):
    #Create pie chart for good and noise units
    good_units = len(good_units)
    noise_units = len(noise_units)
    labels = ['Good', 'Noise']
    sizes = [good_units, noise_units]
    colors = ['lightcoral', 'lightskyblue']
    explode = (0.1, 0)  # explode 1st slice

    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.text(-1, 1, f"Total Units: {good_units + noise_units}", fontsize=12, color='black')
    ax1.axis('equal')
    plt.title(f"Quality labels for {probe_key['subject'], probe_key['session_id']}")

    return fig1

def plot_raster(units, unit_spiketimes, probe_key):
    plt.figure(figsize=(20, 20))

    # Plot all units on the same raster plot
    for unit, spiketimes in zip(units, unit_spiketimes):
        plt.plot(spiketimes, np.full_like(spiketimes, unit), '|', color='steelblue')  # Use a single color for all units

    plt.xlabel('Time (s)', fontsize=22)
    plt.ylabel('Unit', fontsize=22)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.title(f'Raster Plot for {probe_key["subject"], probe_key["session_id"]}', fontsize=26)
    plt.tight_layout()
    
    return plt

def plot_power_spectrum(df):
    import seaborn as sns
    import matplotlib.pyplot as plt

    #find min and max values for color scaling
    power_data = df.drop(columns=['depth'])

    fig, axs = plt.subplots(1, 5, figsize=(20, 10), sharey='row')

    # Iterate through each column and create a heatmap with its own color bar
    for i, col in enumerate(power_data.columns):
        sns.heatmap(np.log(df[[col, 'depth']].set_index('depth')), cmap='magma', ax=axs[i], cbar=True)
        axs[i].set_title(f'{col}')
        axs[i].set_ylabel('Depth (\u03bcM)')  
        cbar = axs[i].collections[0].colorbar  
        cbar.set_label('log(\u03bc$V^2$/Hz)')  

    plt.subplots_adjust(wspace=1, hspace=1, top=0.9, bottom=0.1)

    return fig
