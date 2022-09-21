"""
Created on Tue May 19 20:53:07 2020

@author: celiaberon
"""

import pandas as pd
import numpy as np
import typing as T


def set_analog_headers(analog_df: pd.DataFrame):

    if analog_df[
        analog_df.columns[-1]
    ].min():  # analog values are not zero...want to confirm
        analog_df.columns = [
            "nTrial",
            "iBlock",
            "iTrial",
            "iOccurrence",
            "iState_start",
            "iState_end",
            "analog1",
            "analog2",
        ]
    else:  # there will be a 0.0 value in nTrial somewhere
        analog_df.columns = [
            "iBlock",
            "iTrial",
            "iOccurrence",
            "iState_start",
            "iState_end",
            "analog1",
            "analog2",
            "nTrial",
        ]

    # now let's to to where the session really starts (block=0)
    if analog_df["iOccurrence"][0] > 1:  # just in case it doesn't already start at 0
        first_trial = analog_df[analog_df["iOccurrence"] == 0]
        analog_df = analog_df[first_trial.index[0] :].reset_index(drop=True)

    return analog_df


def handshake_behav_recording_sys(data: pd.DataFrame) -> pd.DataFrame:
    """now from the perspective of the photometry data, find first incoming and outgoing pulses"""

    data = data.loc[
        data[data["toBehSys"] == 1].index[0] :
    ]  # confirm recording system is sending signal to behavior

    data = data.loc[data[data["fromBehSys"] == 0].index[0] :].reset_index(
        drop=True
    )  # confirm behavior system sends signal back at trial starts
    # further trim to start when first trial signaled

    return data


def bins_per_trial_behavior(analog_df: pd.DataFrame):

    trial_starts = (
        analog_df[analog_df.ENL == 1].groupby("nTrial").head(1).index.tolist()
    )

    trial_lengths = np.diff(trial_starts).tolist()
    trial_lengths.append(len(analog_df) - trial_starts[-1])  # last trial for length

    return trial_lengths, trial_starts


def bins_per_trial_photo(photo_df: pd.DataFrame):

    trial_starts = photo_df[photo_df.fromBehSys.diff() == -1].index.tolist()
    trial_starts = np.insert(trial_starts, 0, 0)

    trial_lengths = np.diff(trial_starts).tolist()
    trial_lengths.append(len(photo_df) - trial_starts[-1])

    return trial_lengths, trial_starts


def resample_and_align(
    beh_df, photo_df, channels=["grnR", "redR", "grnL", "redL"], by_trial=False
) -> T.Tuple[pd.DataFrame, float]:

    """resamples photometry data and aligns with behavior data"""

    import scipy.signal as sp_signal

    behavior_trial_lengths, beh_bin_idx = bins_per_trial_behavior(
        beh_df
    )  # get trial starts (enl pulses) for analog
    photo_trial_lengths, photo_bin_idx = bins_per_trial_photo(
        photo_df
    )  # get enl pulses for trial starts from photometry

    # use beh_binslist to iterate or photo_binslist depending on what is shorter. (this depends what was
    # shutdown first - the photometry system or the behavior system)
    shorterList = min(len(photo_bin_idx), len(beh_bin_idx)) - 1

    # find offset between photometry and behavior (number of trials between starts)
    corr_lst = []

    for i in range(-30, 30):  # (makes assumption behavior started first)

        if i < 0:
            corr_lst.append(
                np.corrcoef(
                    photo_trial_lengths[np.abs(i) : shorterList],
                    behavior_trial_lengths[: shorterList - np.abs(i)],
                )[1, 0]
            )

        if i >= 0:
            corr_lst.append(
                np.corrcoef(
                    photo_trial_lengths[: shorterList - i],
                    behavior_trial_lengths[i:shorterList],
                )[1, 0]
            )

    offset = range(-30, 30)[np.argmax(corr_lst)]

    # print(np.corrcoef(photo_trial_lengths[np.max((0, -offset)) : shorterList - np.max((0, offset))],
    #               behavior_trial_lengths[np.max((0, offset)) : shorterList - np.max((0, -offset))]))

    assert (
        np.corrcoef(
            photo_trial_lengths[
                np.max((0, -offset)) : shorterList - np.max((0, offset))
            ],
            behavior_trial_lengths[
                np.max((0, offset)) : shorterList - np.max((0, -offset))
            ],
        )[1, 0]
        > 0.99999
    )  # need to set threshold better

    if by_trial:
        raise NotImplementedError

    else:
        # print("full session resampling")
        photo_session_trimmed = photo_df[
            photo_bin_idx[np.max((0, -offset))] : photo_bin_idx[
                shorterList - np.max((0, offset))
            ]
        ]
        behavior_session_trimmed = beh_df[
            beh_bin_idx[np.max((0, offset))] : beh_bin_idx[
                shorterList - np.max((0, -offset))
            ]
        ].reset_index(drop=True)

        # print(
        #     "downsampling by factor of ",
        #     len(photo_session_trimmed) / len(behavior_session_trimmed),
        # )

        photo_resample = pd.DataFrame(
            sp_signal.resample(
                photo_session_trimmed[channels], len(behavior_session_trimmed)
            ),
            columns=channels,
        )

        aligned_df = pd.concat(
            [behavior_session_trimmed, photo_resample], axis=1
        ).reset_index()
        time_offset = (
            behavior_session_trimmed["session_clock"].iloc[0]
            - beh_df["session_clock"].iloc[0]
        )  # in seconds
        # print(f"shift into behavior by {time_offset} seconds")

    return aligned_df, time_offset


def normalize(x, window):

    r = x.rolling(window=window, center=True)

    lower_bound = r.min()
    upper_bound = r.max()
    # lower_bound = r.quantile(0.05) # instead of .min()
    # upper_bound = r.quantile(0.95) # instead of .max()

    return (x - lower_bound) / (upper_bound - lower_bound)


def zscore(x, window, rolling=False):
    # z score options: full distribution or sliding window

    if rolling:
        r = x.rolling(window=window, center=True)
    else:
        r = x.copy()

    m = r.mean()
    s = r.std()

    z = (x - m) / s
    return z
