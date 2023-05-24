"""
Created on Fri Apr 15 16:01:51 2022

@author: celiaberon and janetberrios
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from copy import deepcopy
from scipy import signal, stats, optimize
import warnings
import tdt

import warnings
import numpy as np
import pandas as pd
from scipy import stats
from scipy import signal
from scipy import interpolate
from scipy import optimize
from scipy.signal.windows import hamming
from copy import deepcopy


def gen_sine(x, timepoints=None):

    tmp = x[0] * np.sin(2 * np.pi * timepoints * x[1] + x[2]) + x[3]
    return tmp


def gen_cosine(x, timepoints=None):

    tmp = x[0] * np.cos(2 * np.pi * timepoints * x[1] + x[2]) + x[3]
    return tmp


def get_residuals(x, signal, **kwargs):

    return signal - gen_sine(x, **kwargs)


def is_filter_stable(coeffs):
    # check the stability of sos coefficients
    z, p, k = signal.sos2zpk(coeffs)

    # if all the poles lie in the unit circle we're good
    return np.all(np.abs(p) <= 1.0)


def bandpass_signal(
    x, center_fs, fs=6103.515625, order=4, bw=50, attenuation=40, ripple=0.1
):

    sos = signal.ellip(
        order,
        ripple,
        attenuation,
        [center_fs - (bw // 2), center_fs + (bw // 2)],
        btype="bandpass",
        fs=fs,
        output="sos",
    )

    if not is_filter_stable(sos):
        raise ValueError(
            "Bandpass filter is unstable, change your design specifications"
        )

    cleaned_signal = deepcopy(x)
    cleaned_signal = signal.sosfiltfilt(sos, cleaned_signal)
    return cleaned_signal


def get_baseline(x, win_samples, percentile=10):
    x = pd.Series(x)
    return (
        x.rolling(win_samples, center=True, min_periods=1)
        .quantile(percentile / 100)
        .to_numpy()
    )


def downsample(x, fs, new_fs, method="polyphase"):

    x[np.isnan(x)] = 0

    if method.lower()[0] == "f":
        total_secs = len(x) / fs
        new_total = int(new_fs * total_secs)
        new_signal = signal.resample(x, new_total)
    elif method.lower()[0] == "p":
        import fractions

        frac = fractions.Fraction(new_fs / fs).limit_denominator()
        p, q = frac.numerator, frac.denominator
        new_signal = signal.resample_poly(x, p, q)
    else:
        raise ValueError("Did not understand downsample method {}".format(method))

    return new_signal


# currently does not work properly for non-integer downsampling
def downsample2(x, fs, new_fs):
    """This downsample does not introduce smoothing artifacts"""
    warnings.warn("downsample2 does not work properly for non-integer downsampling")
    assert new_fs < fs, "new fs must be lower"
    time = np.arange(len(x))
    time2 = np.linspace(0, len(x) - 1, int(len(x) * new_fs / fs))
    x = deepcopy(x)
    x2 = interpolate_signal(time, x, time2, method="nearest")
    return x2


def sync_to_clock(sync, threshold=0.5):

    clock = np.zeros_like(sync.astype("float"))
    clock[:] = np.nan

    idx = np.arange(len(sync) - 1)

    crossings = np.sort(
        np.where(np.logical_and(sync[idx] <= threshold, sync[idx + 1] >= threshold))[0]
    )
    place_idx = np.cumsum(np.ones_like(crossings))
    smooth_vec = np.linspace(
        place_idx[0], place_idx[-1], len(np.arange(crossings[0], crossings[-1]))
    )
    clock[crossings[0] : crossings[-1]] = smooth_vec

    return clock


def interpolate_signal(x, y, xx, method="nearest", extrapolate=False):

    if extrapolate:
        warnings.warn("Interpolating clock signal, out of range...")
        f = interpolate.interp1d(x, y, method, fill_value="extrapolate")
    else:
        f = interpolate.interp1d(x, y, method)

    return f(xx)


def detect_fs(x, tstep):

    """
    use FFT to get carrier frequency from input sine wave
    INPUTS:
        x: input sine wave from tdt
        tstep: time points along x
    OUTPUTS:
        maximum frequency band from FFT
    """
    cmp_fft = np.fft.fft(x - np.mean(x))
    mx_fs = np.argmax(np.abs(cmp_fft))
    hz = np.fft.fftfreq(x.size, tstep)
    return np.abs(hz[mx_fs])


def fit_reference(
    x, timestamps, expected_fs=None, mod_bandpass=True, bandpass_kwargs={}
):

    """
    Fit parameters for reference wave
    INPUTS:
        x: snippet of freq modulated signal measured with photodiode
        timestamps: corresponding snippet of time points for x
        expected_fs: detected carrier freq
    OUTPUTS:
        new_params: [amplitude, frequency, phase, offset] for sine wave
        sine wave snippet created with new_params
        ref: bandpass filtered reference wave for snippet
    """

    tstep = np.nanmean(np.diff(timestamps))  # length of each timestep

    ref = deepcopy(x)
    fs = 1 / tstep  # sampling frequency

    # bandpass signal around carrier frequency
    if mod_bandpass:
        ref = bandpass_signal(ref, center_fs=expected_fs, fs=fs, **bandpass_kwargs)

    ### fft on bp filtered signal to make sure matches input freq
    cmp_fft = np.fft.fft(ref)
    mx_fs = np.argmax(np.abs(cmp_fft))
    hz = np.fft.fftfreq(ref.size, tstep)
    detected_fs = np.abs(hz[mx_fs])

    if np.abs(detected_fs - expected_fs) > 100:
        warnings.warn(
            "FFT detected center frequency {} while supplied frequency {}".format(
                hz, expected_fs
            )
        )

    # initialize best guesses of new params
    init_vec = [np.nanstd(ref), expected_fs, 0, np.nanmean(ref)]

    # calculate phase offset from input and reference signals and fill into init_vec
    init_fit_angle = np.angle(
        signal.hilbert(stats.zscore(gen_sine(init_vec, timestamps)))
    )
    data_angle = np.angle(signal.hilbert(ref.astype("float")))
    phase_diff = -np.angle(np.mean(np.exp(1j * (init_fit_angle - data_angle))))
    init_vec[2] = phase_diff

    # fit params to bp filtered signal by minimizing SSE
    obj_fun = lambda p: np.sum(get_residuals(p, signal=ref, timepoints=timestamps) ** 2)
    new_params = optimize.fmin(obj_fun, init_vec, disp=False)

    return new_params, gen_sine(new_params, timestamps), ref


def spec_demodulate(z1_trace_list, calc_carry_list, sampling_Hz, num_perseg, n_overlap):
    demodulated_trace_list = []
    for z1_trace in z1_trace_list:
        f, t, sxx = signal.spectrogram(
            z1_trace, 
            fs=sampling_Hz, 
            nperseg=num_perseg, 
            noverlap=n_overlap
        )
        freq_ind = np.argmin(np.abs(f - calc_carry_list))
        demodulated_trace = sxx[freq_ind, :]
        demodulated_trace_list.append(demodulated_trace)
    return demodulated_trace_list
            
def calc_carry(raw_carrier_list, sampling_Hz):
                calc_carry_list = []
                points_2_process = 2**14
                for i in range(len(raw_carrier_list)):
                    fft_carrier = abs(np.fft.fft(raw_carrier_list[i][0:points_2_process]))
                    P2 = fft_carrier/points_2_process
                    P1 = abs(P2/2+1)
                    P1[1:-1] = 2*P1[1:-1]
                    f = sampling_Hz * np.arange(points_2_process // 2) / points_2_process
                    ind = np.argmax(P1, axis=None)
                    processed_carrier = round(f[ind])
                    calc_carry_list.append(processed_carrier)
                return calc_carry_list

def four(z1_trace_list):
                return [np.fft.fft(trace) for trace in z1_trace_list] 

def bandpass_demod(demodulated_trace_list, calc_carry_list, sampling_Hz, bp_bw):
    return [
        bandpass_signal(
            trace, 
            center_fs=calc_carry,
            fs=sampling_Hz,
            attenuation=40,
            bw=bp_bw)
        for trace, calc_carry in zip(demodulated_trace_list, calc_carry_list)]

def process_trace(raw_photom_list, calc_carry_list,
                                sampling_Hz, window1,
                                num_perseg, n_overlap):
                z1_trace_list = [] ##create a dict for each step of the process
                ##create a dict for each step of the process   
                for i in range(len(raw_photom_list)):
                    z_trace = rolling_z(raw_photom_list[i], window1)
                    z1_trace_list.append(z_trace)
                    power_spectra_list, t_list = rolling_demodulation(z1_trace_list,
                                                                      calc_carry_list,
                                                                    sampling_Hz, num_perseg, n_overlap)
                    spect_power_list = spect_power(power_spectra_list)
                return z1_trace_list, power_spectra_list, t_list, spect_power_list

def rolling_demodulation(z1_trace_list, calc_carry_list, sampling_Hz, nperseg, noverlap):
    power_spectra_list = []
    t_list = []
    win = signal.hamming(nperseg, 'periodic')
    calc_carry_list = np.array(calc_carry_list)
    for x in z1_trace_list:
        power_spectra = []
        t = []
        for ii in range(0, len(x) - nperseg + 1, noverlap):
            f, t_, Zxx = signal.spectrogram(x[ii:ii+nperseg], sampling_Hz, window=win, nperseg=nperseg, noverlap=noverlap)
            power_spectra.append(np.abs(Zxx))
            t.append(t_)
        t = np.concatenate(t)
        power_spectra = np.concatenate(power_spectra, axis=1)
        freq_ind = np.argmin(np.abs(f - calc_carry_list.reshape((-1, 1))), axis=0)
        rolling_demod = power_spectra[freq_ind, :]
        power_spectra_list.append(rolling_demod)
        t_list.append(t)
    power_spectra_list = np.array(power_spectra_list)
    t_list = np.array(t_list)
    return power_spectra_list, t_list

def spect_power(power_spectra_list):
    spect_power_list = []
    for i in range(len(power_spectra_list)):
        spect_power = np.mean(power_spectra_list[i], axis=0)
        spect_power_list.append(spect_power)
    return spect_power_list
              

def demodulate(
    x,
    center_fs,
    ref_x=None,
    ref_y=None,
    demod_tau=0.5,
    demod_filter_order=3,
    mod_bandpass=True,
    fs=6103.515625,
    attenuation=40,
    downsample_fs=500,
    downsample_filter_order=3,
    downsample_method="polyphase",
    downsample_antialias=True,
    pre_downsample=True,
    bandpass_bw=50,
):

    assert downsample_fs < fs, "Downsample fs must be lower than original fs"

    if ref_x is None or ref_y is None:
        raise RuntimeError("Need references")

    demod_fs = 1 / demod_tau
    demod_samples = int(demod_tau * downsample_fs)

    # get the product operators, then integrate and combine
    sig = deepcopy(x)

    if mod_bandpass:
        sig = bandpass_signal(
            sig, center_fs=center_fs, fs=fs, attenuation=attenuation, bw=bandpass_bw
        )

    # get rms for x and y, downsample before r, multiply nyquist by .8 so we have headroom

    mult_x = np.square(sig * ref_x)
    mult_y = np.square(sig * ref_y)

    if pre_downsample:
        if downsample_antialias:
            sos = signal.butter(
                downsample_filter_order,
                0.8 * (downsample_fs / 2),
                btype="low",
                fs=fs,
                output="sos",
            )
            if not is_filter_stable(sos):
                raise ValueError(
                    "Downsample filter unstable, change your filter specifications"
                )
            mult_x = signal.sosfiltfilt(sos, mult_x)
            mult_y = signal.sosfiltfilt(sos, mult_y)

            mult_x = downsample(mult_x, fs, downsample_fs, method=downsample_method)
            mult_y = downsample(mult_y, fs, downsample_fs, method=downsample_method)

    # final round of filtering
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)

        sos = signal.ellip(
            demod_filter_order,
            0.1,
            40,
            demod_fs,
            btype="low",
            fs=downsample_fs,
            output="sos",
        )

        if not is_filter_stable(sos):
            raise ValueError(
                "Integration filter is not stable, change your design specifications"
            )

        int_x = np.sqrt(signal.sosfiltfilt(sos, mult_x))
        int_y = np.sqrt(signal.sosfiltfilt(sos, mult_y))
        r = np.hypot(int_x, int_y)

    r[:demod_samples] = np.nan
    r[-demod_samples:] = np.nan
    int_y[:demod_samples] = np.nan
    int_y[-demod_samples:] = np.nan
    int_x[:demod_samples] = np.nan
    int_x[-demod_samples:] = np.nan

    return int_x, int_y, r, downsample_fs


def rolling_z(x, wn):
    x = pd.Series(x)
    xbar = x.rolling(wn, center=True).mean()
    xstd = x.rolling(wn, center=True).std()

    z = (x - xbar) / xstd
    z[: wn // 2] = 0
    z[-wn // 2 :] = 0
    return z.values



def offline_demodulation(data, metadata, tau=20, z=True, z_window=60, downsample_fs=600, 
                         bandpass_bw=50, **kwargs):
        
    # use a short snippet of the signal to fit our offline reference
    use_points = int(1e4)     
            
    tstamps, ref, demod_sig = {}, {}, {}
        
    if metadata.task_ID.values[0].startswith('hf'):
        threshold = 0.5# ... # 0.5?
        toBeh = (downsample(data['toBeh'], metadata.sampling_freq.values[0], downsample_fs, 
                            method='polyphase') > threshold).astype('int')
        froG = (downsample(data['froG'], metadata.sampling_freq.values[0], downsample_fs, 
                             method='polyphase') > threshold)
    
    demod_df = pd.DataFrame(data={'toBehSys':toBeh, 
                                  'fromBehSys':froG})
    
    for fiber in [col for col in data.columns if col.startswith('fiber')]:
    
        sig = data[fiber].values # photometry signal
        ref_fs = metadata.loc[fiber, 'carrier_freq']
        fs = metadata.loc[fiber, 'sampling_freq']
        if z:
            sig = rolling_z(sig, wn=round(z_window*fs))
            print('applying first z-score with a 60s rolling window')
             
        tstamps = np.arange(len(sig)) / fs # CB: timestamps to track samples

        results = fit_reference(sig[int(z_window*fs):int(z_window*fs)+use_points],  # jump over z-score window tails (or equivalent to match)
                                tstamps[int(z_window*fs):int(z_window*fs)+use_points], 
                                expected_fs=ref_fs) # CB: TBD but think this is fitting sine measured wave in raw data
                                                       # and comparing to input sine wave parameters for driver; outputs fit params
        ref["params_x"], _, _ = results # CB: deconstruct above into fit params and bp filtered data
        # remember y has a 90 degree phase shift
        ref["params_y"] = (ref["params_x"][0], #
                           ref["params_x"][1],
                           ref["params_x"][2] + np.pi / 2,
                           ref["params_x"][3])
        ref["ref_x"] = gen_sine(ref["params_x"], tstamps) # CB: generate new reference sine using fit params for data
        ref["ref_y"] = gen_sine(ref["params_y"], tstamps) # CB: same but for shifted 90 deg

        _, _, demod_sig, _ = demodulate(sig, 
                                         ref_fs, #is this the center_fs? and what is the center_fs
                                         ref_x=ref["ref_x"],
                                         ref_y=ref["ref_y"],
                                         demod_tau=tau,
                                         downsample_fs=downsample_fs,
                                         bandpass_bw=bandpass_bw)
              
        demod_sig[:int(z_window*downsample_fs)] = np.nan
        demod_sig[-int(z_window*downsample_fs):] = np.nan
        demod_df[fiber.replace('fiber', 'detrend')] = demod_sig
            
    start_idx = demod_df[fiber.replace('fiber', 'detrend')].first_valid_index()
    end_idx = demod_df[fiber.replace('fiber', 'detrend')].last_valid_index()
    demod_df = demod_df[start_idx:end_idx].reset_index(drop=True)
                     
    if z:
        raw = offline_demodulation(data, metadata, tau, z=False,
                                   downsample_fs=downsample_fs, 
                                   bandpass_bw=bandpass_bw, **kwargs)
        print(raw.columns)
        assert(demod_df[['toBehSys','fromBehSys']].equals(raw[['toBehSys','fromBehSys']]))
        for fiber in [col for col in data.columns if col.startswith('fiber')]:
            side = fiber[len('fiber_'):]
            demod_df[fiber.replace('fiber', 'raw')] = raw[f'detrend_{side}']
    
    return demod_df