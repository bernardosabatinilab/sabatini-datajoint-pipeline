"""
Created on Tue May 19 20:43:56 2020

@author: celiaberon
"""

import numpy as np
import pandas as pd

"""for first notebook - labeling behavioral features"""


def make_bandit_df(df, fracTimeout):
    """
    makes a dataframe with basic trial info for each session, necessary preprocessing step for DAB version of lick task
        inputs:
        -df: loaded dataTrial in pandas
        -savepath: output path for 2D csv
        -fracTimeout: threshold for fraction of trials with a timeout within a block to flag that block
    """
    df = df.set_index("nTrial")  # will use trial number for indexing
    df = df[
        [
            "Mouse",
            "Date",
            "Session",
            "Condition",
            "sSelection",
            "tSelection",
            "I_anySelect_L",
            "I_anySelect_R",
            "I_giveReward",
            "T_Reward",
            "T_ENL",
            "n_ENL",
            "n_Cue",
            "DAB_I_flipLR_event",
            "DAB_I_flipLR",
            "DAB_I_HighProbSel",
        ]
    ]  # include only columns of interest

    # find block number for each trial
    df["iBlock"] = df.DAB_I_flipLR_event.cumsum().astype("int") + 1
    df["iInBlock"] = df.groupby("iBlock").cumcount()

    # get count ("i") position within each block
    counts = np.unique(df["iBlock"], return_counts=True)[
        1
    ]  # number of trials per block
    idx = counts.cumsum()  # numeric index of each block switch
    # iInBlock = np.ones(idx[-1], dtype=int)                  # initialize array of ones same size as original vector
    # iInBlock[idx[:-1]] = -counts[:-1]+1                     # insert negative of counts-1 per block, then take cumulative sum
    # df['iInBlock'] = iInBlock.cumsum()-1                      # returns matrix that cumsums within each block

    df["blockLength"] = np.repeat(counts, counts)  # array of current block lengths

    df["direction"] = df[
        "I_anySelect_R"
    ]  # make new column called direction where right = 1, left = 0
    df.loc[
        df.sSelection == 3, "direction"
    ] = np.nan  # and no selection is marked by a NaN.

    # flag first and last block, and recursively flag n-1 continuous blocks of timeouts > fracTimeout
    df["flagBlocks"] = False
    df.loc[df.iBlock == df.iBlock.min(), "flagBlocks"] = True  # set first
    df.loc[df.iBlock == df.iBlock.max(), "flagBlocks"] = True  # set last

    blockSearch = df.iBlock.max() - 1
    continueSearch = True
    while continueSearch:
        tmp = df[df.iBlock == blockSearch]
        # if timeouts exceed threshold for timeouts
        if sum(tmp.sSelection == 3) > fracTimeout * tmp["blockLength"].values[0]:
            df.loc[(df.iBlock == blockSearch), "flagBlocks"] = True
            blockSearch = blockSearch - 1
        else:
            continueSearch = False

    # also report on any block with timeouts above threshold
    # ([)code can likely be made more efficient by doing this first and then
    # finding from it flagged blocks instead of doing recursive search...)
    df["timeoutBlocks"] = False
    for i in df.iBlock.unique():
        tmp = df[df.iBlock == i]
        # if timeouts exceed threshold for timeouts
        if len(tmp) == 1:
            continue
        if sum(tmp.sSelection == 3) > fracTimeout * tmp["blockLength"].values[0]:
            df.loc[df.iBlock == i, "timeoutBlocks"] = True

    # record the threshold being used.
    df["timeoutThreshold"] = fracTimeout

    df["timeout"] = df["sSelection"] == 3

    # find trials where decision lick is a switch from previous trial.
    # NOTE on NaNs - NaNs, no selection, are ignored, if a trial has a lick that is switched from the previous trial that had a lick, whether or not
    # it is separated by timeouts, it is counted as a switch. Licks in the same direction separated by timeouts are not treated as switches.

    indNotNaN = (
        np.isnan(df.direction.values) == False
    )  # find elements in direction columns that are NOT NaN
    diffDir = abs(
        np.diff(df.direction[indNotNaN])
    )  # take the difference of consecutive elements, excluding timeouts
    df["Switch"] = 0
    switch = np.insert(diffDir, 0, 0)
    df.loc[
        indNotNaN, "Switch"
    ] = switch  # so switches include direction A->timeout->direction B

    # df['Switch'] = np.abs(np.diff(df.direction, prepend=df.direction.iloc[0])) # previously
    df = df.rename(
        columns={
            "I_giveReward": "Reward",
            "DAB_I_flipLR": "State",
            "DAB_I_HighProbSel": "selHigh",
        }
    )
    df.drop(
        ["I_anySelect_L", "I_anySelect_R", "DAB_I_flipLR_event"], axis=1, inplace=True
    )  # remove redundant columns
    df["State"] = 1 - df["State"]  # flip because 0s and 1s are opposite Decision binary

    return df


def get_direction(df):
    """function that adds columns to report if the mouse made a choice to the right (1) or left (0) port"""

    target = df.iSpout.values
    lickDirection = df.sSelection.values.astype(float)
    choice = np.zeros_like(target)  # default direction is 0, right

    # label left trials as 1
    choice[np.where((lickDirection == 1) & (target == 0))] = 1
    choice[np.where((lickDirection == 2) & (target == 1))] = 1

    # label timeouts
    choice = choice.astype("float")
    choice[lickDirection == 3] = np.nan
    df["direction"] = choice

    return df


def get_previous_event(data, eventName, binarize, nBack):
    """this currently works for any column that has integer values"""

    if binarize:
        previous_event = list(
            (data[eventName[0]].values > 0).astype("int")
        )  # list binary reward outcome
    else:
        previous_event = list((data[eventName[0]].values).astype("float"))

    for trial in np.arange(1, nBack + 1):
        columnName = "-" + str(trial) + eventName[1]
        data[columnName] = np.nan
        data.loc[trial:, columnName] = previous_event[:-trial]
    return data


def get_next_event(data, eventName, binarize, nFor):
    """this currently works for any column that has integer values"""

    if binarize:
        next_event = list(
            (data[eventName[0]].values > 0).astype("int")
        )  # list binary reward outcome
    else:
        next_event = list((data[eventName[0]].values).astype("float"))

    for trial in np.arange(1, nFor + 1):
        columnName = "+" + str(trial) + eventName[1]
        trial_idx = data[-(trial + 1) :].index[0]
        data[columnName] = np.nan
        data.loc[:trial_idx, columnName] = next_event[trial:]
    return data


def get_switch(data, nBack=1):
    """self explanatory, labels switches. may be generalized."""
    # switch=1, stay=0 (Gil uses 2)
    # need to deal with TO still
    # note: Gil uses -1_d for this (& SamePastDirection)

    curr_decision = data.direction[1:].values
    past_decision = data.direction[:-1].values
    switches = (curr_decision != past_decision).astype("int")
    data["Switch"] = [np.nan] + list(switches)

    return data


def label_history_ab(df, history_length=3):
    """this is a little different than I usually use it. The last character is the current trial (not history)."""

    df["h{}".format(history_length)] = np.nan

    for row in np.arange(
        (history_length - 1), df.shape[0]
    ):  # going row by row to label history

        h = (
            "A" if df.loc[row - (history_length - 1)].Reward else "a"
        )  # everything is referenced to the row N before

        for i in np.arange(history_length - 2, -1, -1):
            if (
                df.loc[row - (history_length - 1)].direction
                == df.loc[row - i].direction
            ):

                h += "A" if df.loc[row - i].Reward else "a"

            else:
                h += "B" if df.loc[row - i].Reward else "b"

        df.loc[row, "h{}".format(history_length)] = h

    return df


def get_reward_seq(df):

    df["reward_seq"] = df.Reward.cumsum() - df.Reward.cumsum().where(
        df.Reward == 0
    ).ffill().fillna(0).astype(int)
    df["loss_seq"] = (1 - df.Reward).cumsum() - (df.Reward == 0).cumsum().where(
        df.Reward > 0
    ).ffill().fillna(0).astype(int)

    return df
