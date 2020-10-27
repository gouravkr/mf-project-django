"""This module defines functions for analysing funds"""

import datetime
from dateutil.relativedelta import relativedelta

import pandas as pd
import numpy as np

from django.db import connection

from .utils import xirr_np


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
        for key, value in self.info.items():
            setattr(self, key, value)
        self.nav_hist = None
        self.rr = None

    @property
    def nav_history(self):
        """Fetch the nav history of the fund after checking for cached values"""

        if self.nav_hist is None:
            self.nav_hist = pd.read_sql_query(self.nav_query, connection, params=[self.amfi_code],
                                              index_col='date', parse_dates='date')
        return self.nav_hist

    def latest_returns(self):
        """Fetches the latest 1-3-5 year returns for funds"""

        query = """
            select amfi_code, date, nav
                from nav_history nh
                where amfi_code = %s and date > current_date - '61 month'::interval
                and extract(month from date) between extract(month from current_date)-1 and extract(month from current_date)
                order by date
            """
        with connection.cursor() as cur:
            cur.execute(query, (self.amfi_code,))
            result = cur.fetchall()

        result = np.array(result)

        dates = [datetime.date.today(),
                 datetime.date.today() - relativedelta(years=1),
                 datetime.date.today() - relativedelta(years=3),
                 datetime.date.today() - relativedelta(years=5)]
        data = [result[result[:, 1] <= i][-1] for i in dates]

        returns = []
        for i, j in enumerate(data):
            if i > 0:
                year = (j[1]-data[0][1]).days/-365
                returns.append({'year': int(round(year, 0)), 'return': (data[0][2]/j[2])**(1/year)-1})

        return returns

    def sip_returns(self):
        """Fetches the latest 1-3-5 year SIP returns for funds"""

        sip_schedule_query = """
            with myvars(xamfi_code, xmonths) as (
                values(%s, %s)
            )
            select amfi_code, date, nav, 10000 as amount, round(10000/nav::numeric, 3) as units
                from(
                    select *, row_number() over (partition by xmonth order by date) as rn,
                        row_number() over (order by date) as rno
                        from (
                            select *, TO_CHAR(date, 'YYYY-MM') as xMonth
                                from nav_history, myvars where amfi_code = xamfi_code
                                and extract(day from date) >= 10
                                and date between current_date - (xmonths || ' month')::interval and current_date
                        ) t1
                    ) t2
                    where rn = 1 and rno <> 1
            union
            select amfi_code, date, nav, 0 as amount, 0 as units
                from latest_nav, myvars
                where amfi_code = xamfi_code
            order by date
            """
        months = [60, 36, 12]
        xirrs = []

        with connection.cursor() as cur:
            cur.execute(sip_schedule_query, (self.amfi_code, months[0]+1))
            transactions = cur.fetchall()
        transactions = np.array(transactions)
        transactions[:, 3] = transactions[:, 3].astype(float)
        transactions[:, 4] = transactions[:, 4].astype(float)

        for month in months:
            df_slice = transactions[-(month+1):, :]
            sip_value = sum(df_slice[:-1, 4])*df_slice[-1, 2]
            df_slice[-1, 3] = sip_value * -1
            dates = df_slice[:, 1]
            amounts = df_slice[:, 3]
            xirrs.append({'years': month // 12, 'returns': round(xirr_np(dates, amounts), 6)})

        return xirrs


class FundAdvanced(MutualFund):
    """This class contains functions for advanced analysis of funds.
        It inherits from the basic mutual_fund class."""

    def rolling_returns_old(self, period=1, start_date=None, end_date=None):
        """fetches the rolling returns for the provided period and frequency"""

        nav_hist = self.nav_history
        nav_hist_smooth = nav_hist.asfreq('1D', method='ffill')
        period_in_days = period * 365 + (1 if period >= 3 else 0)
        nav_hist_smooth['growth'] = nav_hist_smooth.pct_change(periods=period_in_days)['nav']
        nav_hist_smooth['growth'] = (nav_hist_smooth['growth']+1)**(1 / period) - 1

        nav_hist_smooth = nav_hist_smooth.loc[start_date:end_date].dropna().reset_index()
        return nav_hist_smooth[['date', 'growth']]

    def rolling_summary(self, period, start_date, end_date):
        """Summary stats like avg, SD based on rolling returns"""

        rolling_returns = self.rolling_returns(period, start_date, end_date)
        rolling_summary = {
            'sd': rolling_returns['growth'].std(),
            'mean': rolling_returns['growth'].mean(),
            'min': rolling_returns['growth'].min(),
            'max': rolling_returns['growth'].max()
        }
        return rolling_summary

    def rolling_returns(self, period=1, start_date=None, end_date=None):
        if self.rr is None:
            self.rr = self._rolling_returns(period=period, start_date=start_date, end_date=end_date)
        return self.rr

    def _rolling_returns(self, period=1, start_date=None, end_date=None):
        query = """
                select t1.*, nh.amfi_code, nh."date", nh.nav, nh2.date as old_date, nh2.nav as old_nav
                from (
                    SELECT dd::date as gen_date
                        FROM generate_series('2005-01-01'::timestamp, current_date::timestamp, '1 day'::interval) dd
                    )  t1
                left join nav_history nh on t1.gen_date = nh.date and nh.amfi_code = %(amfi_code)s
                left join nav_history nh2 on t1.gen_date - %(duration)s::interval = nh2.date and nh2.amfi_code = nh.amfi_code
                order by t1.gen_date
                """
        duration = str(period) + ' year'
        rr_nav = pd.read_sql(query, connection, params={'amfi_code': self.amfi_code, 'duration': duration})
        rr_nav['old_nav'] = rr_nav['old_nav'].ffill()
        rr_nav['growth'] = rr_nav['nav'] / rr_nav['old_nav'] - 1
        return rr_nav[['date', 'growth']].dropna().reset_index(drop=True)


def fund_search(search_string, plan='%', option='%'):
    """Search funds using PostgreSQL TS Query"""

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


def fetch_amc_list():
    """Fetch the entire list of AMCs"""

    with connection.cursor() as cur:
        cur.execute("select * from amc_master")
        amcs = cur.fetchall()
        keys = [i[0] for i in cur.description]

    return [dict(zip(keys, i)) for i in amcs]
