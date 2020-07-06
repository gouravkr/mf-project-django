from django.db import connection

import pandas as pd

from .utils import xirr

class User:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_folios(self, amfi_code):
        query = """select uf.user_id, uf.folio, uf.amc_id, uf.is_primary 
                    from user_folios uf 
                    join fund_master fm on uf.amc_id = fm.amc_id 
                    where fm.amfi_code = %s and user_id = %s
                """
        folios = pd.read_sql_query(query, connection, params=[amfi_code, self.user_id])
        if len(folios) == 0:
            return({"message": "No folios found"})
        return folios.to_dict(orient='records')

    def get_bank_list(self):
        query = "select * from bank_details where user_id = %s"
        banks = pd.read_sql_query("select * from bank_details where user_id = %s", connection, [self.user_id])
        return banks.to_dict(orient='records')


class UserInvestmentManager(User):
    """get_folio, create_folio, add_transaction, add_bank"""

    def add_past_transaction(self, **kwargs):
        insert_query = """
            insert into transaction_history 
            (user_id, amfi_code, folio, trx_type, trx_date, nav, amount, units)
            values (%(user_id)s, %(amfi_code)s, %(folio)s, 'INV', %(date)s, %(nav)s, %(amount)s, %(units)s)
        """
        nav_query = """select * from nav_history 
                        where amfi_code = %s and date > %s
                        order by date limit 1
                    """
        with connection.cursor() as cur:
            cur.execute(nav_query, [kwargs['amfi_code'], kwargs['date']])
            records = cur.fetchall()
            kwargs['nav'] = records[0][2]
        if 'amount' not in kwargs:
            kwargs['amount'] = round(nav*kwargs['units'], 2)
        if 'units' not in kwargs:
            kwargs['units'] = round(kwargs['amount']/kwargs['nav'], 4)
        folios = self.get_folios(kwargs['amfi_code'])
        for i in folios:
            if i['is_primary']:
                kwargs['folio'] = i['folio']
        kwargs['user_id'] = self.user_id
        with connection.cursor() as conn:
            conn.execute(insert_query, kwargs)
        return("success")

    def create_folio(self, amc_id, folio, primary=False):
        create_query = """
            insert into user_folios values(
                %(user_id)s, %(folio)s, %(amc_id)s, %(primary)s
            )
            """
        folio = str(np.random.randint(100000000)) if folio is None else folio
        params = {'user_id': self.userid, 'folio': folio,
                  'amc_id': amc_id, 'primary': primary}
        with connection.conect() as cursor:
            cursor.execute(create_query, params)


class UserPortfolio(User):
    '''Functions related to building and fetching a user's portfolio'''

    def __init__(self, user_id):
        User.__init__(self, user_id)
        self.trx_hist = None
        self.navs = None

    trx_hist_query = """
        select th.trans_id, th.user_id, am.amc, fm.amfi_code, fm.fund_name, th.folio, th.trx_type, 
                th.trx_date, th.amount, th.nav, th.units, lnav.nav, lnav.nav*th.units as value,
                fm.cg_category, current_date-trx_date as holding_period
            from transaction_history th
                join fund_master fm on th.amfi_code = fm.amfi_code
                join amc_master am on fm.amc_id = am.amc_id 
                join latest_nav lnav on fm.amfi_code = lnav.amfi_code
                where th.user_id = %s"""

    all_navs_query = """select amfi_code, date, nav 
                    from latest_nav 
                    where amfi_code in (
                        select distinct amfi_code from transaction_history th where user_id = %s
                    )"""

    @property
    def transaction_history(self):
        if self.trx_hist is None:
            self.trx_hist = pd.read_sql_query(self.trx_hist_query, connection, params=[self.user_id], parse_dates='trx_date')
        return self.trx_hist

    def fetch_portfolio(self, with_xirr=False):
        trx = self.transaction_history
        trx.loc[trx['trx_type'] == 'RED', 'units'] *= -1
        trx.loc[trx['trx_type'] == 'RED', 'amount'] *= -1
        portfolio_summary = trx.groupby(['amfi_code', 'fund_name']).agg(
            {'units': 'sum', 'amount': 'sum'}).reset_index()
        nav = self.all_navs
        portfolio_summary = portfolio_summary.merge(nav)
        portfolio_summary = portfolio_summary.eval('value = units*nav')
        portfolio_summary = portfolio_summary.eval('profit = value-amount')
        if with_xirr:
            xirr = self.calc_fund_xirr()
            portfolio_summary = portfolio_summary.merge(xirr)
        portfolio_summary = portfolio_summary.dropna()
        return portfolio_summary

    @property
    def all_navs(self):
        if self.navs is None:
            self.navs = pd.read_sql_query(self.all_navs_query, connection,
                                          params=[self.user_id], parse_dates='date')
        return self.navs

    def portfolio_xirr(self):
        trx = self.transaction_history
        current_value = trx['value'].sum()*-1
        current_date = pd.Timestamp.today()
        trx = trx.append({'trx_date': current_date, 'amount': current_value}, ignore_index=True)
        trx = trx.sort_values(by='trx_date')
        xirr_perc = xirr(trx[['trx_date', 'amount']], date_column='trx_date')
        return xirr_perc

    def calc_fund_xirr(self):
        trx = self.transaction_history[['amfi_code', 'trx_date', 'trx_type', 'amount', 'units']]
        trx.loc[trx['trx_type'] == 'RED', 'units'] *= -1
        trx.loc[trx['trx_type'] == 'RED', 'amount'] *= -1
        values = trx.groupby('amfi_code').sum().round(4).reset_index()
        values = values.merge(self.all_navs).eval("value = units*nav*-1").round(2)
        values = values[['amfi_code', 'date', 'value']]
        values['trx_type'] = "cur_val"
        values.columns = ['amfi_code', 'trx_date', 'amount', 'trx_type']
        trx_with_val = trx.append(values)
        fund_xirr = trx_with_val.groupby('amfi_code').apply(lambda x: xirr(x, date_column='trx_date'))
        fund_xirr = pd.DataFrame(fund_xirr).reset_index()
        fund_xirr.columns = ['amfi_code', 'xirr']
        return fund_xirr

    def investment_summary(self):
        portfolio_summary = self.fetch_portfolio()
        investment_summary = {
            'xirr': self.portfolio_xirr(),
            'investment': portfolio_summary['amount'].sum(),
            'value': portfolio_summary['value'].sum(),
            'num_funds': sum(portfolio_summary['value'] > 0.5)
        }
        return investment_summary
