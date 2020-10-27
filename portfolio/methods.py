"""Method for user portfolios"""

import pandas as pd
import numpy as np

from django.db import connection
from django.db import IntegrityError

from .utils import xirr_np


class UserInfo:
    """This is the basic user info class from which other classes inherit"""

    def __init__(self, user_id):
        self.user_id = user_id

    def info(self):
        """Get all information about a user"""

        info_query = """select id, username, first_name, last_name, email, date_joined,
                    ui.mobile, ui.alt_email, ui.alt_mobile, ui.d_o_b, ui.pan
                    from auth_user au
                    join user_info ui on au.id = ui.user_id
                    where id = %s
                    """
        with connection.cursor() as cur:
            cur.execute(info_query, (self.user_id,))
            result = cur.fetchone()
            keys = [i[0] for i in cur.description]
        return dict(zip(keys, result))

    def create_user(self, **kwargs):
        """Create a user"""

        query = """insert into user_info(user_id, mobile, alt_mobile, alt_email, pan, d_o_b)
                values(%(user_id)s, %(mobile)s, %(alt_mobile)s, %(alt_email)s, %(pan)s, %(d_o_b)s) """

        kwargs['user_id'] = self.user_id
        try:
            with connection.cursor() as cur:
                cur.execute(query, kwargs)
        except Exception as error:
            print(error)
            return False
        return True

    def get_folios(self, amfi_code=None):
        """Get all folios of a user"""

        query = """select * from user_folios uf
                    join amc_master am on am.amc_id = uf.amc_id
                    where uf.user_id = %s
                """
        params = [self.user_id]
        if amfi_code is not None:
            params.append(amfi_code)
            query += 'and am.amc_id = (select amc_id from fund_master fm where amfi_code = %s)'
        folios = pd.read_sql_query(query, connection, params=params)
        if len(folios) == 0:
            return "No folios found"
        return folios.to_dict(orient='records')

    def get_banks(self):
        """Get all banks of a user"""

        banks = pd.read_sql_query("select * from bank_details where user_id = %s", connection, params=[self.user_id])
        return banks.to_dict(orient='records')


class UserInvestmentManager(UserInfo):
    """get_folio, create_folio, add_transaction, add_bank"""

    def add_transaction(self, **kwargs):
        """Add a transaction. Creates a folio if one doesn't exist. Errors out if there's no bank"""

        insert_query = """
            insert into transaction_history
            (user_id, amfi_code, folio, trx_type, trx_date, nav, amount, units)
            values (%(user_id)s, %(amfi_code)s, %(folio)s, %(trx_type)s, %(trx_date)s, %(nav)s, %(amount)s, %(units)s)
            returning trans_id, amfi_code, folio, amount, nav, units
        """
        nav_query = """select * from nav_history
                        where amfi_code = %s and date > %s
                        order by date limit 1
                    """
        with connection.cursor() as cur:
            cur.execute(nav_query, [kwargs['amfi_code'], kwargs['trx_date']])
            records = cur.fetchall()
            kwargs['nav'] = records[0][2]

        if 'trx_type' not in kwargs:
            kwargs['trx_type'] = 'INV'

        if 'amount' not in kwargs:
            kwargs['amount'] = round(kwargs['nav']*kwargs['units'], 2)

        if 'units' not in kwargs:
            kwargs['units'] = round(kwargs['amount'] / kwargs['nav'], 4)

        folios = self.get_folios(kwargs['amfi_code'])
        if folios == "No folios found":
            created_folios = self.create_folio(amfi_code=kwargs['amfi_code'])
            if created_folios['status'] == 201:
                folios = kwargs['folio'] = created_folios['folio'][1]
            else:
                return {"message": 'Transaction creation failed', 'status': 400}
        else:
            for i in folios:
                if i['is_primary']:
                    kwargs['folio'] = i['folio']

        kwargs['user_id'] = self.user_id
        try:
            with connection.cursor() as cur:
                cur.execute(insert_query, kwargs)
                result = cur.fetchone()
            return {'message': 'Transaction created successfully', 'status': 201, 'transaction': result}
        except Exception as error:
            print(error)
            return {'message': 'Transaction creation failed', 'status': 400}

    def create_folio(self, amc_id=None, amfi_code=None, folio=None, primary=None, bank_id=None):
        """Create a folio. Links to the primary bank by default. As of now, assigns a random number as folio"""

        if amc_id is None:
            if amfi_code is None:
                return {"message": "Provide either AMC Id or AMFI Code", "status": 400}
            else:
                with connection.cursor() as cur:
                    cur.execute("select amc_id from fund_master where amfi_code = %s", (amfi_code,))
                    result = cur.fetchone()
                amc_id = result[0]

        if bank_id is None:
            with connection.cursor() as cur:
                cur.execute("select id from bank_details where user_id = %s and is_primary", (self.user_id,))
                result = cur.fetchone()
            if result:
                bank_id = result[0]
            else:
                return {'message': "No banks found", "status": 400}

        if primary is None:
            folio_count_query = "select count(*) from user_folios where user_id = %s and amc_id = %s and is_primary"
            with connection.cursor() as cur:
                cur.execute(folio_count_query, (self.user_id, amc_id,))
                count = cur.fetchone()
            primary = bool(not count[0])

        create_query = """insert into user_folios values(
                            %(user_id)s, %(folio)s, %(amc_id)s, %(primary)s, %(bank_id)s
                        ) returning user_id, folio"""
        folio = str(np.random.randint(100000000)) if folio is None else folio

        params = {'user_id': self.user_id, 'folio': folio,
                  'amc_id': amc_id, 'primary': primary, 'bank_id': bank_id}
        try:
            with connection.cursor() as cursor:
                cursor.execute(create_query, params)
                folio = cursor.fetchone()
            return {'message': "Folio created successfully", "status": 201, "folio": folio}
        except Exception as error:
            print(error)
            return {'message': "Could not create folio", "status": 400}

    def create_bank(self, bank_name, account_number, ifsc):
        """Add a bank account for a user"""

        insert_query = """
                       insert into bank_details(user_id, bank_name, account_number, ifsc, is_primary)
                           values(%s, %s, %s, %s, %s)
                           returning id
                       """
        with connection.cursor() as cur:
            cur.execute("select count(*) from bank_details where user_id = %s", (self.user_id,))
            count = cur.fetchone()
        is_primary = bool(not count[0])

        try:
            with connection.cursor() as cur:
                cur.execute(insert_query, (self.user_id, bank_name, account_number, ifsc, is_primary))
                bank_id = cur.fetchone()
            return {'message': "Bank addition successful", 'status': 201, 'bank_id': bank_id[0]}
        except IntegrityError as error:
            print(error)
            return {'message': "Bank already exists", 'status': 409}
        except Exception as error:
            print(error)
            return {'message': "Bank could not be added", 'status': 400}


class UserPortfolio(UserInfo):
    '''Functions related to building and fetching a user's portfolio'''

    def __init__(self, user_id):
        UserInfo.__init__(self, user_id)
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

    holdings_query = """
            with holdings as (
                select th.amfi_code, lnav.fund_name, trx_date as date, amount, th.nav, lnav.nav as latest_nav, units
                    from transaction_history th
                    join latest_nav lnav on th.amfi_code = lnav.amfi_code
                    where user_id = %s
                )
            select * from (
                select amfi_code, fund_name, current_date -1 as date,
                    latest_nav as nav, -sum(units) as units, -(sum(units)*latest_nav)::float as amount
                    from holdings
                    group by amfi_code, fund_name, latest_nav
                ) t1 where abs(units) > 0.1
            union
            select amfi_code, fund_name, date, nav, units::float, amount from holdings
            order by amfi_code, date
            """

    @property
    def transaction_history(self):
        """Fetch the transaction history for a user"""

        if self.trx_hist is None:
            with connection.cursor() as cur:
                cur.execute(self.trx_hist_query, (self.user_id,))
                results = cur.fetchall()
                keys = [i[0] for i in cur.description]
            all_trx = []
            for i in results:
                all_trx.append(dict(zip(keys, i)))
            self.trx_hist = all_trx
        return self.trx_hist

    def fetch_portfolio(self):
        """Fetch the portfoio for a user with XIRR"""

        with connection.cursor() as cur:
            cur.execute(self.holdings_query, (self.user_id,))
            holdings = cur.fetchall()

        holdings = np.array(holdings)
        keys = ['amfi_code', 'fund_name', 'date', 'nav', 'units', 'value', 'cost', 'xirr', 'profit']

        all_xirrs = []
        for i in np.unique(holdings[:, 0]):
            holdings_slice = holdings[holdings[:, 0] == i]
            cur_xirr = xirr_np(holdings_slice[:, 2], holdings_slice[:, 5])
            cur_holdings = list(holdings_slice[-1, :])
            cur_holdings[4] *= -1
            cur_holdings[5] *= -1
            cost = sum(holdings_slice[:-1, 5])
            cur_holdings.append(cost)
            cur_holdings.append(cur_xirr)

            profit = cur_holdings[5]-cur_holdings[6]
            cur_holdings.append(profit)
            all_xirrs.append(dict(zip(keys, cur_holdings)))

        return all_xirrs

    @property
    def all_navs(self):
        """Fetch NAVs of all funds held by the user"""

        if self.navs is None:
            self.navs = pd.read_sql_query(self.all_navs_query, connection,
                                          params=[self.user_id], parse_dates='date')
        return self.navs

    def portfolio_xirr(self):
        """Fetch the portfolio XIRR"""

        with connection.cursor() as cur:
            cur.execute(self.holdings_query, (self.user_id,))
            holdings = cur.fetchall()
        holdings = np.array(holdings)
        xirr_perc = xirr_np(holdings[:, 2], holdings[:, 5])
        return xirr_perc

    def investment_summary(self):
        """Fetch the investment summary for a user"""

        portfolio_summary = self.fetch_portfolio()
        investment_summary = {
            'xirr': self.portfolio_xirr(),
            'investment': sum([i['cost'] for i in portfolio_summary]),
            'value': sum([i['value'] for i in portfolio_summary]),
            'num_funds': len(portfolio_summary)
        }
        return investment_summary
