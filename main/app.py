import os
import nest_asyncio
import sqlite3
import requests
import aiohttp
import asyncio
import investpy
import json
import datetime
import time
from collections import defaultdict
from flask import Flask, flash, jsonify, redirect, render_template, request, session, g
from flask_session import Session
from tempfile import mkdtemp

# USD to SGD conversion rate
er_token = os.getenv("exchange_rate_token") # From https://app.exchangerate-api.com/
# er_token = keys.exchangeRate_token
temp = requests.get(f"https://v6.exchangerate-api.com/v6/{er_token}/latest/USD")
res = temp.json()
conv_rate = float(res['conversion_rates']['SGD'])

token = os.getenv("finnhub_api_key") # From https://finnhub.io/
# token = keys.finnhub_token

user_id = "demo" # Choose how you want the database to identify you // I don't think you need to have more than one user


# Configure application
app = Flask(__name__)

# Auto-reload templates
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# No cached responses
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# configure database
print(f"\ncurrent directory: {os.getcwd()}\n")
conn = sqlite3.connect("../main/main.db", timeout=5.0, check_same_thread=False)
c = conn.cursor()
conn.row_factory = sqlite3.Row


###################################HELPER FUNCTIONS####################################################
nest_asyncio.apply()
# GET DATA FOR ALL USD STOCKS
async def get_data():
    c.execute("SELECT ticker FROM stocks WHERE user_id = ? AND status = 'hold' AND currency = 'USD' AND NOT sector = 'ETF' ORDER BY date_open", (user_id,))
    holdings = c.fetchall()
    tickers = [holding[0] for holding in holdings]

    async def f(ticker, token):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={token}')
            return await resp.json()

    responses = await asyncio.gather(*[f(ticker, token) for ticker in tickers])
    return responses
loop = asyncio.get_event_loop()

# FUNCTION THAT UPDATES PORTFOLIO ONLY WHEN YOU VISIT THE APP
def update_portfolio():
    # get time now
    now = int(datetime.datetime.now().timestamp()) * 1000
    c.execute("SELECT timing FROM portfolio WHERE user_id = ? AND timing = (SELECT MAX(timing) FROM portfolio WHERE user_id = ?)", (user_id, user_id,))
    temp = c.fetchall()
    prev = temp[0][0]
    # get capital
    c.execute("SELECT remarks from portfolio WHERE user_id = ?", (user_id,))
    temp = c.fetchall()
    capital = sum([_[0] for _ in temp])
    # get cash
    c.execute("SELECT price FROM stocks WHERE user_id = ? AND currency = ?", (user_id, "cash",))
    try:
        cash = c.fetchall()[0][0]
    except IndexError:
        cash = 0
    # if time now - prev > 24hours update portfolio
    if now - prev > 86400000:
        holdings_us, holdings_sg, sectors, equity_val = getholdings()
        port_val = equity_val + cash
        p_change = round((port_val-capital)*100/capital, 2)
        c.execute("INSERT INTO portfolio VALUES (?,?,?,?,?)", (user_id, now, port_val, p_change,0))
        conn.commit()

############################################################################################
@app.route("/", methods=["GET"])
def get_index():
    return redirect("/home")


# OVERVIEW (home page)
@app.route("/home", methods=["GET"])
def get_home():
    g.active_item = 'overview'
    # get cash
    c.execute("SELECT price FROM stocks WHERE user_id = ? AND currency = ?", (user_id, "cash",))
    try:
        cash = c.fetchall()[0][0]
    except IndexError:
        cash = 0
    # porfolio data should update everyday after market closes
    c.execute("SELECT port_val FROM portfolio WHERE user_id = ? AND timing = (SELECT MAX(timing) FROM portfolio WHERE user_id = ?)", (user_id, user_id,))
    temp = c.fetchall()
    try:
        latest_val = temp[0][0]
    except IndexError:
        latest_val = 0
    # at the end of every day, update the database for portfolio
    c.execute("SELECT timing, port_val, pctg_change FROM portfolio WHERE user_id = ?", (user_id,))
    d = c.fetchall()
    portfolio = [[i[0], i[1]] for i in d]
    returns = [[i[0], i[2]] for i in d]

    data_sectors = []
    holdings_us, holdings_sg, sectors, equity_val = getholdings()
    usd = sum([stock[11] for stock in holdings_us])
    sgd = sum([stock[9] for stock in holdings_sg])
    day_gains = round(sum([stock[7]*stock[4] for stock in holdings_us]), 2)
    try:
        p_change = round(day_gains*100/latest_val,2)
    except:
        p_change = 0
    for sector, exposure in sectors.items():
        data_sectors.append([sector, round(exposure / equity_val * 100, 2)])
    return render_template("home.html", portfolio=portfolio, returns=returns, cash=cash, holdings_us=holdings_us, holdings_sg=holdings_sg, day_gains=day_gains, data_sectors=data_sectors, equity_val=equity_val, p_change=p_change, conv_rate=conv_rate, usd=usd, sgd=sgd/conv_rate)

# DETAILED PAGE
@app.route("/detailed", methods=["GET"])
def get_detailed():
    g.active_item = 'detailed'
    c.execute("SELECT instrument, ticker, sector, date_open, qty, price, status, price_sold, currency FROM stocks WHERE user_id = ? ORDER BY date_open", (user_id,))
    temp = c.fetchall()
    # get cash
    c.execute("SELECT price FROM stocks WHERE user_id = ? AND currency = ?", (user_id, "cash",))
    try:
        cash = c.fetchall()[0][0]
    except IndexError:
        cash = 0
    holdings_us, holdings_sg, sectors, equity_val = getholdings()

    sold_usd = []
    sold_sgd = []
    for i in range(len(temp)):
        if temp[i][6] == 'sold' and temp[i][8] == 'USD':
            sold_usd.append(temp[i])
        if temp[i][6] == 'sold' and temp[i][8] == 'SGD':
            sold_sgd.append(temp[i])
    # get capital
    c.execute("SELECT remarks from portfolio WHERE user_id = ?", (user_id,))
    temp = c.fetchall()
    capital = sum([_[0] for _ in temp])
    # THIS IS TEMPORARY (I THINK)
    if capital == 0:
        earnings = 0
    else:
        earnings = equity_val+cash - capital
    return render_template("detailed.html", sold_usd=sold_usd, sold_sgd=sold_sgd, holdings_us=holdings_us, holdings_sg=holdings_sg, equity_val=equity_val, cash=cash, earnings=earnings, capital=capital, conv_rate=conv_rate)


# EDIT POSITIONS
@app.route("/edit-positions", methods=["GET"])
def add_pos():
    g.active_item = 'editpos'
    # Pretty much nothing to do here, since this just renders the page
    holdings_us, holdings_sg, sectors, equity_val = getholdings()

    return render_template("editpos.html", holdings_us=holdings_us, holdings_sg=holdings_sg, conv_rate=conv_rate)

@app.route("/editpos", methods=["POST"])
def editpos():
    if request.method == "POST":
        if not request.form.get("action"):
            flash("Please Specify Action")
            return redirect("/edit-positions")
        action = request.form.get("action")
        currency = request.form.get("currency")
        ticker = (request.form.get("ticker")).upper()
        sector = request.form.get("sector")
        date_open = request.form.get("date")
        try:
            qty = int(request.form.get("qty"))
            price = float(request.form.get("price"))
        except (TypeError, ValueError) as e:
            if action == "edit" and qty == 0:
                price = None
            else:
                flash(f"Failed to make changes to your portfolio. Check that you have entered all the necessary fields.")
                return redirect("/edit-positions")
        # flash(f"received: {action=} {currency=} {ticker=} {sector=} {date_open=} {qty=} {price=}")
        # ADDING POSITIONS
        if action == "add":
            # FOR US STOCKS
            # User has to supply ticker, date_open, qty_bought, price, currency
            if currency == "USD" and ticker and date_open and qty and price:
                # BEFORE DOING ANYTHING, CHECK IF TICKER HAS BEEN BOUGHT BY USER BEFORE + "hold"
                c.execute("SELECT date_open, qty, price FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency ='USD'", (user_id,ticker,))
                check = c.fetchall() # check = [(previous qty, price)]
                # IF YES:
                if len(check) == 1:
                    # Retrieve price * previous qty, add with new_price * new_qty and find the average cost
                    prev_date, prev_qty, prev_price = check[0]
                    new_qty = prev_qty + qty
                    ave_price = round((qty * price + prev_qty * prev_price)/new_qty, 2)
                    # get the oldest value
                    date = min(date_open, prev_date)
                    # update the same row with new price, new quantity
                    c.execute("UPDATE stocks SET date_open = ?, qty = ?, price = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = 'USD'", (date, new_qty, ave_price, user_id, ticker))
                # IF NO:
                elif len(check) == 0:
                    # Before adding of positions, we need to once again req finnhub to get the name of the ticker as well as the sector
                    temp = requests.get(f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={token}')
                    res = temp.json()
                    if len(res) == 0:
                        flash(f"Invalid ticker {ticker} provided, check again and contact me if issue persists")
                        return redirect("/edit-positions")
                    instrument = res['name']
                    sector = res['finnhubIndustry']
                    # Then we insert into stocks user_id, instrument, ticker, sector, date_open, qty_bought, price, "hold", currency
                    c.execute("INSERT INTO stocks (user_id, instrument, ticker, sector, date_open, qty, price, status, currency) VALUES (?,?,?,?,?,?,?,?,?) ",
                              (user_id, instrument, ticker, sector, date_open, qty, price, 'hold', currency))

                c.execute("UPDATE stocks SET price = price - ? WHERE user_id = ? and currency = ?", (qty*price, user_id, "cash",))
                conn.commit()
                flash(f"Added {qty} {ticker} to your portfolio")
                return redirect("/edit-positions")

            # FOR SG STOCKS
            # User has to supply name, ticker, sector, date_open, qty, price
            if currency == "SGD" and ticker and sector and date_open and qty and price:
                # BEFORE DOING ANYTHING, CHECK IF TICKER HAS BEEN BOUGHT BY USER BEFORE + "hold"
                c.execute("SELECT date_open, qty, price FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND currency ='SGD'",(user_id, ticker,))
                check = c.fetchall()  # check = [(previous qty, price)]
                # IF YES:
                if len(check) == 1:
                    # Retrieve price * previous qty, add with new_price * new_qty and find the average cost
                    prev_date, prev_qty, prev_price = check[0]
                    new_qty = prev_qty + qty
                    ave_price = round((qty * price + prev_qty * prev_price)/new_qty, 2)
                    # set oldest date
                    date = min(date_open, prev_date)
                    # update the same row with new price, new quantity
                    c.execute("UPDATE stocks SET date_open = ?, qty = ?, price = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND currency = 'SGD'", (date, new_qty, ave_price, user_id, ticker,))
                # IF NO:
                elif len(check) == 0:
                    # use investpy to get the instrumment name for SG stocks
                    try:
                        res = investpy.search_quotes(text=ticker, products=['stocks'], countries=['singapore'], n_results=1)
                    except RuntimeError:
                        flash(f"{ticker} does not exist. Contact me if problem persists.")
                        return redirect("/edit-positions")
                    instrument = json.loads(str(res))['name']
                    curr_price = res.retrieve_information()['prevClose']
                    # Then we insert into stocks user_id, instrument, ticker, sector, date_open, qty, price, "hold", currency
                    c.execute("INSERT INTO stocks (user_id, instrument, ticker, sector, date_open, qty, price, status, currency, currentprice) VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (user_id, instrument, ticker, sector, date_open, qty, price, "hold", currency, curr_price,))

                c.execute("UPDATE stocks SET price = price - ? WHERE user_id = ? and currency = ?", (qty * price/conv_rate, user_id, "cash",))
                conn.commit()
                flash(f"Added {qty} {ticker} to your portfolio")
                return redirect("/edit-positions")

        elif action == "sell":
            # FOR SELL POSITIONS
            # User has to supply ticker, qty_sold, price, currency
            if ticker and qty and price and currency:
                # Check if ticker exists in db and qty > qty_sold
                c.execute("SELECT instrument, ticker, sector, date_open, qty, price, currency FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?", (user_id, ticker, currency,))
                check = c.fetchall() # check = [(instrument, ticker, sector, dateopen, qty, price, currency)]
                if len(check) > 0:
                    checkinstrument, checkticker, checksector, checkdate, prev_qty, ave_price, currency = check[0]

                    if currency == "USD":
                        c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? and currency = ?",
                                  (qty * price, user_id, "cash",))
                    else:
                        c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? and currency = ?",
                                  (qty * price / conv_rate, user_id, "cash",))

                    # IF YES
                    prev_qty = int(prev_qty)
                    if prev_qty > qty:
                        # update row of ticker (decrement qty by qty_sold)
                        c.execute("UPDATE stocks SET qty = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?", (prev_qty-qty, user_id, ticker, currency,))
                        # insert into db user_id, instrument, ticker, sector, date_opened, qty_sold, price_opened, "sold", price_sold, currency
                        c.execute("INSERT INTO stocks (user_id, instrument, ticker, sector, date_open, qty, price, status, price_sold, currency) VALUES (?,?,?,?,?,?,?,?,?,?) ",
                                  (user_id, checkinstrument, ticker, checksector, checkdate, qty, ave_price, 'sold', price, currency,))
                        conn.commit()
                        flash(f"Sold {qty} {ticker} from your {currency} portfolio.")
                        return redirect("/edit-positions")
                    elif prev_qty == qty:
                        # sell all
                        c.execute("UPDATE stocks SET status = ?, price_sold = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?", ('sold', price, user_id, ticker, currency,))
                        conn.commit()
                        flash(f"Sold {qty} {ticker} from your {currency} portfolio.")
                        return redirect("/edit-positions")
                    else:
                        flash(f"You do not have {qty} {ticker} in your {currency} portfolio. Check again.")
                        return redirect("/edit-positions")
                # IF NO:
                else:
                    flash(f"You do not have {qty} {ticker} in your {currency} portfolio. Check again.")
                    return redirect("/edit-positions")

        elif action == "edit":
            c.execute("SELECT * FROM stocks WHERE user_id = ? and ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?",
                      (user_id, ticker, currency))
            check = c.fetchall()
            if len(check) == 0:
                flash(f"You do not have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            # if qty is 0, delete the holding
            if currency and ticker and qty == 0:
                try:
                    c.execute("SELECT qty, price, from stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?", (user_id, ticker, currency,))
                    q1,p1 = c.fetchall()[0]
                    if currency == "USD":
                        c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? and currency = ?",
                                  (q1*p1, user_id, "cash",))
                    else:
                        c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? and currency = ?",
                                  (q1*p1 / conv_rate, user_id, "cash",))
                    c.execute("DELETE FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?", (user_id, ticker, currency,))
                    conn.commit()
                    flash(f"Removed {ticker} from your {currency} portfolio.")
                except sqlite3.IntegrityError:
                    flash(f"You do not seem to have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            # if qty > 0, edit the holding
            elif currency and ticker and date_open and price and qty > 0:
                try:
                    c.execute("UPDATE stocks SET date_open = ?, qty = ?, price = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND NOT sector = 'ETF' AND currency = ?",
                        (date_open, qty, price, user_id, ticker, currency,))
                    conn.commit()
                    flash(f"Updated {ticker} from your {currency} portfolio.")
                except sqlite3.IntegrityError:
                    flash(f"You do not seem to have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            else:
                flash("Failed to update your portfolio, do check you have entered all the necessary fields.")
                return redirect("/edit-positions")

    flash("Something went wrong, if issue persists, contact me.")
    return redirect("/edit-positions")

@app.route("/editetfpos", methods=["POST"])
def editetfpos():
    if request.method == "POST":
        if not request.form.get("action"):
            flash("Please specify action")
            return redirect("/edit-positions")
        action = request.form.get("action")
        currency = request.form.get("currency")
        ticker = (request.form.get("ticker")).upper()
        sector = "ETF"
        date_open = request.form.get("date")
        try:
            qty = int(request.form.get("qty"))
            price = float(request.form.get("price"))
        except (TypeError, ValueError) as e:
            if action == "edit" and qty == 0:
                price = None
            else:
                flash(
                    f"Failed to make changes to your portfolio. Check that you have entered all the necessary fields.")
                return redirect("/edit-positions")
        # flash(f"received: {action=} {currency=} {ticker=} {sector=} {date_open=} {qty=} {price=}")
        # ADDING POSITIONS
        if action == "add":
            # User has to supply name, ticker, sector, date_open, qty, price
            if currency and ticker and date_open and qty and price:
                # BEFORE DOING ANYTHING, CHECK IF TICKER HAS BEEN BOUGHT BY USER BEFORE + "hold"
                c.execute(
                    "SELECT date_open, qty, price FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency ='SGD'",
                    (user_id, ticker,))
                check = c.fetchall()  # check = [(previous qty, price)]
                # IF YES:
                if len(check) == 1:
                    # Retrieve price * previous qty, add with new_price * new_qty and find the average cost
                    prev_date, prev_qty, prev_price = check[0]
                    new_qty = prev_qty + qty
                    ave_price = round((qty * price + prev_qty * prev_price) / new_qty, 2)
                    # set oldest date
                    date = min(date_open, prev_date)
                    # update the same row with new price, new quantity
                    c.execute(
                        "UPDATE stocks SET date_open = ?, qty = ?, price = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = 'SGD'",
                        (date, new_qty, ave_price, user_id, ticker,))
                # IF NO:
                elif len(check) == 0:
                    # use investpy to get etf name
                    if currency == "USD":
                        try:
                            res = investpy.search_quotes(text=ticker, products=['etfs'], countries=["united states"], n_results=1)
                        except:
                            flash(f"ETF {ticker} does not exist in the US market. Contact me if problem persists.")
                            return redirect("/edit-positions")
                    else:
                        try:
                            res = investpy.search_quotes(text=ticker, products=['etfs'], countries=["singapore"], n_results=1)
                        except:
                            flash(f"ETF {ticker} does not exist in the SG market. Contact me if problem persists.")
                            return redirect("/edit-positions")

                    instrument = json.loads(str(res))['name']
                    curr_price = res.retrieve_information()['prevClose']
                    # Then we insert into stocks user_id, instrument, ticker, sector, date_open, qty, price, "hold", currency
                    c.execute(
                        "INSERT INTO stocks (user_id, instrument, ticker, sector, date_open, qty, price, status, currency, currentprice) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (user_id, instrument, ticker, sector, date_open, qty, price, "hold", currency, curr_price,))

                c.execute("UPDATE stocks SET price = price - ? WHERE user_id = ? and currency = ?", (qty * price / conv_rate, user_id, "cash",))
                conn.commit()
                flash(f"Added {qty} {ticker} to your portfolio")
                return redirect("/edit-positions")

        elif action == "sell":
            # FOR SELL POSITIONS
            # User has to supply ticker, qty_sold, price, currency
            if ticker and qty and price and currency:
                # Check if ticker exists in db and qty > qty_sold
                c.execute(
                    "SELECT instrument, ticker, sector, date_open, qty, price, currency FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                    (user_id, ticker, currency,))
                check = c.fetchall()  # check = [(instrument, ticker, sector, dateopen, qty, price, currency)]
                if len(check) > 0:
                    checkinstrument, checkticker, checksector, checkdate, prev_qty, ave_price, currency = check[0]
                    # IF YES
                    prev_qty = int(prev_qty)
                    if prev_qty > qty:
                        # update row of ticker (decrement qty by qty_sold)
                        c.execute(
                            "UPDATE stocks SET qty = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                            (prev_qty - qty, user_id, ticker, currency,))
                        # insert into db user_id, instrument, ticker, sector, date_opened, qty_sold, price_opened, "sold", price_sold, currency
                        c.execute(
                            "INSERT INTO stocks (user_id, instrument, ticker, sector, date_open, qty, price, status, price_sold, currency) VALUES (?,?,?,?,?,?,?,?,?,?) ",
                            (user_id, checkinstrument, ticker, checksector, checkdate, qty, ave_price, 'sold', price, currency,))
                        conn.commit()
                        flash(f"Sold {qty} {ticker} from your {currency} portfolio.")
                        return redirect("/edit-positions")
                    elif prev_qty == qty:
                        # sell all
                        c.execute(
                            "UPDATE stocks SET status = ?, price_sold = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                            ('sold', price, user_id, ticker, currency,))
                        c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? and currency = ?",
                                  (qty * price / conv_rate, user_id, "cash",))
                        conn.commit()
                        flash(f"Sold {qty} {ticker} from your {currency} portfolio.")
                        return redirect("/edit-positions")
                    else:
                        flash(f"You do not have {qty} {ticker} in your {currency} portfolio. Check again.")
                        return redirect("/edit-positions")
                # IF NO:
                else:
                    flash(f"You do not have {qty} {ticker} in your {currency} portfolio. Check again.")
                    return redirect("/edit-positions")

        elif action == "edit":
            c.execute("SELECT * FROM stocks WHERE user_id = ? and ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                      (user_id, ticker, currency,))
            check = c.fetchall()
            if len(check) == 0:
                flash(f"You do not have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            # if qty is 0, delete the holding
            if currency and ticker and qty == 0:
                try:
                    c.execute(
                        "DELETE FROM stocks WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                        (user_id, ticker, currency))
                    conn.commit()
                    flash(f"Removed {ticker} from your {currency} portfolio.")
                except sqlite3.IntegrityError:
                    flash(f"You do not seem to have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            # if qty > 0, edit the holding
            elif currency and ticker and date_open and price and qty > 0:
                try:
                    c.execute(
                        "UPDATE stocks SET date_open = ?, qty = ?, price = ? WHERE user_id = ? AND ticker = ? AND status = 'hold' AND sector = 'ETF' AND currency = ?",
                        (date_open, qty, price, user_id, ticker, currency,))
                    conn.commit()
                    flash(f"Updated {ticker} from your {currency} portfolio.")
                except sqlite3.IntegrityError:
                    flash(f"You do not seem to have {ticker} in your {currency} portfolio. Check again.")
                return redirect("/edit-positions")
            else:
                flash("Failed to update your portfolio, do check you have entered all the necessary fields.")
                return redirect("/edit-positions")

    flash("Something went wrong, if issue persists, contact me.")
    return redirect("/edit-positions")

@app.route("/editcap", methods=["POST"])
def editcap():
    if request.method == "POST":
        if not request.form.get("action"):
            flash("Please specify action")
            return redirect("/edit-positions")
        action = request.form.get("action")
        currency = request.form.get("currency")
        amount = float(request.form.get("amount"))
        date = request.form.get("date")
        today = int(datetime.datetime.now().timestamp()) * 1000
        # get the latest portfolio value
        c.execute("SELECT port_val FROM portfolio WHERE user_id = ? AND timing = (SELECT MAX(timing) FROM portfolio WHERE user_id = ?)", (user_id, user_id,))
        temp = c.fetchall()
        try:
            latest_val = temp[0][0]
        except IndexError:
            latest_val = 0
        # get capital
        c.execute("SELECT remarks from portfolio WHERE user_id = ?", (user_id,))
        temp = c.fetchall()
        capital = sum([_[0] for _ in temp])
        # convert to usd if currency is sgd
        if currency == 'SGD':
            amount = round(amount/conv_rate, 2)

        # See if user has deposited before
        c.execute("SELECT *  FROM portfolio where user_id = ? ORDER BY timing DESC LIMIT 1", (user_id, ))
        check = c.fetchall()

        if action == 'deposit':
            # user hasn't deposited before
            if len(check) == 0:
                if not date:
                    timestamp = 1546272000000 # 2019-01-01
                else:
                    timestamp = int(time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())) * 1000
                c.execute("INSERT INTO portfolio VALUES (?,?,?,?,?)", (user_id, timestamp, amount, 0, amount,))
                c.execute("INSERT INTO stocks (user_id, price, currency) VALUES (?,?,?)", (user_id, amount, "cash",))
            else:
                if not date:
                    if latest_val == capital:
                        pctg_change = 0
                    else:
                        pctg_change = latest_val * 100 / (capital - amount)
                    c.execute("INSERT INTO portfolio VALUES (?,?,?,?,?)",
                              (user_id, today, latest_val + amount, pctg_change, amount,))
                else:
                    timestamp = int(time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())) * 1000
                    c.execute("UPDATE portfolio SET port_val = port_val + ?, remarks = ?, WHERE user_id = ? AND timing < ? ORDER BY timing DESC  LIMIT 1", (amount, amount, user_id, timestamp,))
                c.execute("UPDATE stocks SET price = price + ? WHERE user_id = ? AND currency = ?", (amount, user_id, "cash",))
        # if withdrawal, then we just subtract amount from portfolio value from the nearest date / default to today
        elif action == 'withdraw':
            # user hasn't deposited before
            if len(check) == 0 or check[0][2] < amount:
                flash(f"You do not have enough cash to withdraw {amount}USD ({round(amount * conv_rate,2)}SGD)")
                return redirect("/edit-positions")
            else:
                if not date:
                    if latest_val == capital:
                        pctg_change = 0
                    else:
                        pctg_change = latest_val*100/(capital - amount)
                    c.execute("INSERT INTO portfolio VALUES (?,?,?,?,?)", (user_id, today, latest_val-amount, pctg_change, -amount,))
                else:
                    timestamp = int(time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple())) * 1000
                    c.execute("UPDATE portfolio SET port_val = port_val - ?, remarks = ? WHERE user_id = ? AND timing < ? ORDER BY timing DESC LIMIT 1", (amount, -amount, user_id, timestamp,))
                c.execute("UPDATE stocks SET price = price - ? WHERE user_id = ? AND currency = ?", (amount, user_id, "cash",))
        conn.commit()
        flash(f"'{action} {amount}USD ({round(amount * conv_rate,2)} SGD)' has been recorded in your portfolio.")
        return redirect("/edit-positions")

    flash("Something went wrong, if issue persists, contact me.")
    return redirect("/edit-positions")

# CONTACT
@app.route("/about", methods=["GET"])
def about_me():
    g.active_item = 'about'
    return render_template("about.html", conv_rate=conv_rate)


# HELPER FUNCTIONS
def getholdings():
    holdings_us = []
    holdings_sg = []

    # getting current holdings for US STOCKS
    c.execute("SELECT instrument, ticker, sector, date_open, qty, price FROM stocks WHERE user_id = ? AND status = 'hold' AND currency = 'USD' AND NOT sector = 'ETF' ORDER BY date_open", (user_id,))
    stocks_us = c.fetchall()
    # getting current holdings for US ETFS
    c.execute("SELECT instrument, ticker, sector, date_open, qty, price FROM stocks WHERE user_id = ? AND status = 'hold' AND currency = 'USD' AND sector = 'ETF' ORDER BY date_open", (user_id,))
    etf_us = c.fetchall()
    # getting current holdings for SG STOCKS
    c.execute("SELECT instrument, ticker, sector, date_open, qty, price FROM stocks WHERE user_id = ? AND status = 'hold' AND currency = 'SGD' AND NOT sector = 'ETF'ORDER BY date_open", (user_id,))
    stocks_sg = c.fetchall()
    c.execute("SELECT instrument, ticker, sector, date_open, qty, price FROM stocks WHERE user_id = ? AND status = 'hold' AND currency = 'SGD' AND sector = 'ETF'ORDER BY date_open", (user_id,))
    etf_sg = c.fetchall()

    sectors = defaultdict(lambda: 0)
    equity_val = 0
    # this is for US STOCKS ONLY
    responses = loop.run_until_complete(get_data())
    for i in range(len(responses)):
        instrument, ticker, sector, date, qty, price = [stocks_us[i][j] for j in range(len(stocks_us[0]))]
        curr = responses[i]['c']
        prev = responses[i]['pc']
        day_c = curr - prev
        p_day_c = (curr - prev) / prev * 100
        p_tot_c = (curr - price) / price * 100
        p_l = (curr - price) * qty
        m_v = curr * qty
        stock = [instrument,  # name
                 ticker,  # ticker
                 sector,  # sector
                 date,  # date opened
                 qty,  # quantity/shares
                 price,  # dollar averaged cost per share
                 curr,  # current price
                 round(day_c, 2),  # day change
                 round(p_day_c, 2),  # % day change
                 round(p_tot_c, 2),  # % total change
                 round(p_l, 2),  # profit/loss
                 round(m_v, 2)]  # market value
        if stock not in holdings_us:
            holdings_us.append(stock)
        sectors[sector] += round(m_v, 2)
        equity_val += round(m_v, 2)

    # this is for US ETFS
    for item in etf_us:
        instrument, ticker, sector, date, qty, price = item
        info = investpy.search_quotes(text=ticker, products=['etfs'], countries=['united states'], n_results=1)
        curr = float(info.retrieve_information()['prevClose'])
        p_tot_c = (curr - price) / price * 100
        p_l = (curr - price) * qty
        m_v = curr * qty
        stock = [instrument,  # name
                 ticker,  # ticker
                 sector,  # sector
                 date,  # date opened
                 qty,  # quantity/shares
                 price,  # dollar averaged cost per share
                 curr,  # current price
                 -1,  # day change
                 -1,  # % day change
                 round(p_tot_c, 2),  # % total change
                 round(p_l, 2),  # profit/loss
                 round(m_v, 2)]  # market value
        if stock not in holdings_us:
            holdings_us.append(stock)
        sectors[sector] += round(m_v, 2)
        equity_val += round(m_v, 2)

    # this is for SG STOCKS ONLY
    for item in stocks_sg:
        instrument, ticker, sector, date, qty, price = item
        info = investpy.search_quotes(text=ticker, products=['stocks'], countries=['singapore'], n_results=1)
        curr = float(info.retrieve_information()['prevClose'])
        p_tot_c = (curr - price) / price * 100
        p_l = (curr - price) * qty
        m_v = curr * qty
        stock = [instrument,  # name
                 ticker,  # ticker
                 sector,  # sector
                 date,  # date opened
                 qty,  # quantity/shares
                 price,  # dollar averaged cost per share
                 curr,  # current price
                 # day change
                 # % day change
                 round(p_tot_c, 2),  # % total change
                 round(p_l, 2),  # profit/loss
                 round(m_v, 2)]  # market value
        if stock not in holdings_sg:
            holdings_sg.append(stock)
        sectors[sector] += round(m_v / conv_rate, 2)
        equity_val += round(m_v / conv_rate, 2)

    # this is for SG ETF
    for item in etf_sg:
        instrument, ticker, sector, date, qty, price = item
        info = investpy.search_quotes(text=ticker, products=['etfs'], countries=['singapore'], n_results=1)
        curr = float(info.retrieve_information()['prevClose'])
        p_tot_c = (curr - price) / price * 100
        p_l = (curr - price) * qty
        m_v = curr * qty
        stock = [instrument,  # name
                 ticker,  # ticker
                 sector,  # sector
                 date,  # date opened
                 qty,  # quantity/shares
                 price,  # dollar averaged cost per share
                 curr,  # current price
                 # day change
                 # % day change
                 round(p_tot_c, 2),  # % total change
                 round(p_l, 2),  # profit/loss
                 round(m_v, 2)]  # market value
        if stock not in holdings_sg:
            holdings_sg.append(stock)
        sectors[sector] += round(m_v / conv_rate, 2)
        equity_val += round(m_v / conv_rate, 2)

    return holdings_us, holdings_sg, sectors, equity_val
############################################################################################

if __name__ == '__main__':
    # this is for updating only when you visit the app
    try:
        update_portfolio()
    except:
        pass
    app.run()
