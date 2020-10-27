"""Defines utility methods for use in methods.py"""

import numpy as np


def xirr_np(dates, amounts, guess=0.05, step=0.05):
    '''Calculates XIRR from a series of cashflows. Requires Pandas, NumPy, and datetime libraries
       Needs a dataframe with columns date and amount, customisable through parameters.'''

    years = np.array(dates - dates[0], dtype='timedelta64[D]')/np.timedelta64(365, 'D')

    epsilon = 0.1
    limit = 100
    residual = 1

    # test
    dex = np.sum(amounts/((1.05+guess)**years)) < np.sum(amounts/((1+guess)**years))
    mul = 1 if dex else -1

    # Calculate XIRR
    for _ in range(limit):
        prev_residual = residual
        residual = np.sum(amounts/((1+guess)**years))
        if abs(residual) > epsilon:
            if residual * prev_residual < 0:
                step /= 2
            guess = guess + step * mul * (-1 if residual < 0 else 1)
        else:
            return guess
    return "XIRR not calculated"
