#Risk-adjusted momentum strategy

'''
Note:
- Please adjust the codes and the assets in accordance with the platform and the market
- This is a one instrument strategy, will modify to include multiple instruments later on
- For future replications, it is recommended to use Fama-French portfolio to backtest the strategy

Data specification:
- Day data is required for moving average strategy

Strategy summary:
1. Calculate log return (done)
2. Calculate volatility of log return
3. Calculate weighted return
4. 

Strategy strengths:
- Have negative correlation with Fama-French factors
- Outperforms TSMOM when the factors deliver good returns

'''

from zipline.api import order, symbol, record, order_target
import sys
import numpy as np
import pandas as pd
import scipy

logger = init_logger(__name__)

def initialize(context):
	#--- init asset
	context.data = data.history(symbol('AAA'), 'adj_close', 10, '1d')
	context.lookback = 12
	context.period = 25																													# equivalent to a business month
	context.lda = [0.94, 0.87, 0.5]																										# standard lambda values correspond to 30-day, 15-day, 5-day realized volatility

	#--- init signal
	context.df = pd.DataFrame()
	context.volatility = pd.DataFrame()
	context.weight = [1 for i in range(self.lookback)]																					# we set equal weight by default, backtesters can adjust the weights later.

def weighted_volatility(context, ret, lookback = self.lookback, lda):																	# this need to be re-evaluated
	sigma = pd.DataFrame()
	sigma = numpy.std(self.data)																										# need to be re-evaluated on how we calculate volatility
	return np.sqrt(lda * sigma ** 2 + (1 - lda) * self.df["ret"].shift[1] ** 2)															# from (3.2)

def h_ret(context, h = self.lookback):																									# standard momentum with h periods is just h_ret(h)
	h_ret = pd.DataFrame()
	h_ret = np.log(self.data/self.data.shift(h))
	return h_ret

def standard_mom_returns(context, data, weight):
	ret = h_ret(1)
	lookback = length(weight)
	return ret.rolling(lookback) * np.transpose(weight)

def risk_adjusted_returns(context, data, h, lda):																						# for (3.3) calculations
	rar = pd.DataFrame()
	rar = h_ret(ret, h = 12)/weighted_volatility(ret = h_ret(1), lda = lda)
	return pd.DataFrame(np.sum(rar.rolling(h)))

def r_tsmom(context, k1, k2):																											# for (3.4)
	position = 0
	weight = [1 for i in range(25*k1)]
	for c in range(k2):
		position += np.sign(standard_mom_returns(data = h_ret(1).iloc[-25*c], weight = weight))
	return position * np.expm1(h_ret(1))/weighted_volatility(ret = h_ret(1), lda = 0.94)

def r_ramom(context, k1, k2):																											# for (3.5)
	position = 0
	for c in range(k2):
		position += np.sign(risk_adjusted_returns(data = h_ret(1).iloc[-25*c], h = 25*k1 - 11, lda = 0.94))
	return position * np.expm1(h_ret(1))/weighted_volatility(ret = h_ret(1), lda = 0.94)

def strat(context):																														# main trading signals here
	return