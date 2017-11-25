#Zipline-SMA

from zipline.api import order, symbol, record, order_target
import sys
import numpy as np
import pandas as pd


logger = init_logger(__name__)


def initialize(context):
	context.security = symbol('AAPL')

def handle_data(context, data):
	MA1 = data[context.security].mavg(50)	# short MA
	MA2 = data[context.security].mavg(100)	# long MA

	current_price = data[context.security].price
	current_positions = context.portfolio.positions[symbol('AAPL')].amount
	cash = context.portfolio.cash

	if (MA1 > MA2) and (current_positions == 0):
		number_of_shares = int(cash/current_price)
		order(context.security, number_of_shares)	# placing order, with param: asset and size
		logger.info('Buying shares')
	elif (MA1 < MA2) and (current_positions != 0):	# must have stocks for shorting
		order_target(context.security, 0)
		logger.info('Selling shares')

	record(MA1 = MA1, MA2 = MA2, Price = current_price)




