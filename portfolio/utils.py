import pandas as pd
import numpy as np
import datetime


def xirr(df, guess=0.05, step=0.05, date_column='date', amount_column='amount'):
    '''Calculates XIRR from a series of cashflows. Requires Pandas, NumPy, and datetime libraries
       Needs a dataframe with columns date and amount, customisable through parameters.'''

    df = df.sort_values(by=date_column).reset_index(drop=True)

    amounts = df[amount_column].values
    dates = df[date_column].values
    years = np.array(dates - dates[0], dtype='timedelta64[D]').astype(int) / 365

    epsilon = 0.1
    limit = 1000
    residual = 1

    #test
    disc_val_1 = np.sum(amounts/((1+guess)**years))
    disc_val_2 = np.sum(amounts/((1.05+guess)**years))
    mul = 1 if disc_val_2 < disc_val_1 else - 1

    # Calculate XIRR
    for _ in range(limit):
        prev_residual = residual
        disc_val = amounts/((1+guess)**years)
        residual = np.sum(disc_val)

        if abs(residual) > epsilon:
            if np.sign(residual) != np.sign(prev_residual):
                step /= 2
            guess = guess + step * np.sign(residual) * mul
        else:
            return guess


def init_guess(df):
    neg_dates = df.loc[df['amount'] < -0.1,
                       'trx_date'].values.astype('datetime64[D]')
    neg_amts = df.loc[df['amount'] < -0.1, 'amount'].values
    neg_dates_mean = np.average(neg_dates.view(
        'i8'), weights=neg_amts)  # .astype('datetime64[D]')

    pos_dates = df.loc[df['amount'] > 0.1,
                       'trx_date'].values.astype('datetime64[D]')
    pos_amts = df.loc[df['amount'] > 0.1, 'amount'].values
    pos_dates_mean = np.average(pos_dates.view(
        'i8'), weights=pos_amts)  # .astype('datetime64[D]')

    avg_holding = (neg_dates_mean - pos_dates_mean)/365

    abs_return = abs(np.sum(neg_amts)/np.sum(pos_amts))

    return abs_return ** (1/avg_holding) - 1
