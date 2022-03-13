from Robinhood import Robinhood
import shelve
import json
import argparse
import csv
from login_data import collect_login_data

parser = argparse.ArgumentParser(
    description='Export Robinhood trades to a CSV file')
parser.add_argument(
    '--debug', action='store_true', help='store raw JSON output to debug.json')
parser.add_argument(
    '--username', default='', help='your Robinhood username')
parser.add_argument(
    '--password', default='', help='your Robinhood password')
parser.add_argument(
    '--mfa_code', help='your Robinhood mfa_code')
parser.add_argument(
    '--device_token', help='your device token')


mfa_required = False	
args = parser.parse_args()
username = args.username
password = args.password
mfa_code = args.mfa_code
if bool(mfa_code):
    mfa_required = True
device_token = args.device_token

logged_in = False

def get_symbol_from_instrument_url(rb_client, url, db):
    instrument = {}
    if type(url) != str:
        url = url.encode('utf8')
    if url in db:
        instrument = db[url]
    else:
        db[url] = fetch_json_by_url(rb_client, url)
        instrument = db[url]
    return instrument['symbol']


def fetch_json_by_url(rb_client, url):
    return rb_client.session.get(url).json()


def order_item_info(order, rb_client, db):
    #side: .side,  price: .average_price, shares: .cumulative_quantity, instrument: .instrument, date : .last_transaction_at
    symbol = get_symbol_from_instrument_url(rb_client, order['instrument'], db)
    return {
        'Transaction Type': order['side'],
        'Purchase price per share': order['average_price'],
        'Shares': order['cumulative_quantity'],
        'Symbol': symbol,
        'Date Purchased': order['last_transaction_at'],
        'Commission': order['fees']
    }


def get_all_history_orders(rb_client):
    orders = []
    past_orders = rb_client.order_history()
    orders.extend(past_orders['results'])
    while past_orders['next']:
        print("{} order fetched".format(len(orders)))
        next_url = past_orders['next']
        past_orders = fetch_json_by_url(rb_client, next_url)
        orders.extend(past_orders['results'])
    print("{} order fetched".format(len(orders)))
    return orders

robinhood = Robinhood()

# login to Robinhood
logged_in = collect_login_data(robinhood_obj=robinhood, username=username, password=password, device_token=device_token, mfa_code=mfa_code, mfa_required=mfa_required)

# fetch order history and related metadata from the Robinhood API
past_orders = get_all_history_orders(robinhood)

instruments_db = shelve.open('instruments.db')
orders = [order_item_info(order, robinhood, instruments_db) for order in past_orders]
keys = ['Purchase price per share', 'Date Purchased', 'Commission', 'Shares', 'Symbol', 'Transaction Type']
with open('orders.csv', 'w',newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(orders)
