from django.db import connection

import pandas as pd
import datetime

class MutualFund:
    """defines a class for a specific mutual fund"""

    query = """select fm.fund_name, fm.amc, fm.fund_plan, fm.option, fm.primary_fund_name, 
            fm.primary_fund_code, fm.category, fm.sub_category, fm.amc_id, lnav.nav
            from fund_master fm
            join latest_nav lnav on fm.amfi_code = lnav.amfi_code
            where fm.amfi_code = %s
            """

    nav_query = """select amfi_code, date, nav from nav_history 
                    where amfi_code = %s order by date"""
                    
    def __init__(self, amfi_code):
        self.amfi_code = amfi_code
        result = pd.read_sql_query(self.query, connection, params=[amfi_code])
        self.info = result.to_dict(orient='records')[0]
        for k, v in self.info.items():
            setattr(self, k, v)
        self.nav_hist = None

    @property
    def nav_history(self):
        if self.nav_hist is None:
            self.nav_hist = pd.read_sql_query(self.nav_query, connection,
                                              params=[self.amfi_code], index_col='date', parse_dates='date')
        return self.nav_hist

    def returns(self, c_date=datetime.datetime.today()):
        nav_hist = self.nav_history
        current_date = nav_hist.loc[:c_date].tail(1).index[0]
        c_date = nav_hist.loc[current_date].name
        year1 = nav_hist.loc[:c_date+DateOffset(years=-1)].tail(1).index[0]
        year3 = nav_hist.loc[:c_date+DateOffset(years=-3)].tail(1).index[0]
        year5 = nav_hist.loc[:c_date+DateOffset(years=-5)].tail(1).index[0]
        nav_hist = nav_hist.loc[[c_date, year1, year3, year5]].reset_index()

        nav_hist['years'] = round((nav_hist['date'][0] - nav_hist['date']).dt.days/365, 1)
        nav_hist['returns'] = (nav_hist['nav'][0]/nav_hist['nav']) ** (1/nav_hist['years']) - 1
        returns = nav_hist.loc[1:, ['years', 'returns']].to_dict(orient='records')
        return returns

class FundAdvanced(MutualFund):
    """This class contains functions for advanced analysis of funds.
        It inherits from the basic mutual_fund class."""

    def rolling_returns(self, period=1, start_date=None, end_date=None):
        nav_hist = self.nav_history
        nav_hist_smooth = nav_hist.asfreq('1D', method='ffill')
        period_in_days = period * 365 + (1 if period >= 3 else 0)
        nav_hist_smooth['growth'] = nav_hist_smooth.pct_change(periods=period_in_days)['nav']**(1 / period) - 1

        nav_hist_smooth = nav_hist_smooth.loc[start_date:end_date].dropna().reset_index()
        return nav_hist_smooth[['date', 'growth']]

    def rolling_summary(self, period, start_date, end_date):
        rolling_returns = self.rolling_returns(period, start_date, end_date)
        rolling_summary = {
            'sd': rolling_returns['growth'].std(),
            'mean': rolling_returns['growth'].mean(),
            'min': rolling_returns['growth'].min(),
            'max': rolling_returns['growth'].max()
        }
        return rolling_summary


def fund_search(search_string, plan='%', option='%'):
    fund_name = search_string.replace(" ", "%").replace("%-", " & !")
    fund_name = fund_name.replace('cap', '%cap').replace('fund', '')
    fund_name = f"{fund_name}:*"  # enables partial match in tsquery
    sql_query = """select lnav.*, fm.sub_category from latest_nav lnav 
                    join fund_master fm on lnav.amfi_code = fm.amfi_code   
                    where lnav.fts_doc @@ to_tsquery(%s)
                    and fm.fund_plan ilike %s and fm.option ilike %s order by lnav.fund_name
                """
    results = pd.read_sql_query(sql_query, connection, params=[fund_name, plan, option])
    return results


def amc_list():
    amcs = pd.read_sql_query("select * from amc_master", connection)
    return amcs.to_dict(orient='records')
