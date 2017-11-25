#Risk-adjusted momentum strategy

'''
Note:
- Please adjust the codes and the assets in accordance with the platform and the market
- This is a one instrument strategy, will modify to include multiple instruments later on

Data specification:
- Day data is required for moving average strategy

Strategy summary:
1. Calculate log return
2. Calculate volatility of log return
3. Calculate weighted return
4. 

'''

from zipline.api import order, symbol, record, order_target
import sys
import numpy as np
import pandas as pd
import scipy

logger = init_logger(__name__)

def initialize(context):
	#--- init asset
	context.security = symbol('AAPL')
	context.asset = []
	context.futures = []
	context.bond = []
	context.lookback = 12
	context.period = 25	# equivalent to a business month
	context.lda = 0.94	# standard lambda value, can be adjusted when backtesting

	#--- init signal
	context.df = pd.DataFrame()
	context.weight = [1 for i in range(self.lookback)]	# we set equal weight by default, backtesters can adjust the weights later.

def risk_adjusted_ma(context, ret, lookback = self.lookback, lda):
	#--- calculate adjusted volatility
	volatility = numpy.std(data[context.security])
	self.df["volatility"].append(lda*volatility**2 + (1-lda)*self.df["ret"].iloc[-1]**2)

	#--- calculate momentum
	for i in range(lookback):
		self.df["mom"].append((ret.rolling(lookback))*np.transpose(weight))
	while length(df["mom"]) > lookback:
		self.df["risk_adjusted_mom"].append(sum(self.df["mom"].rolling(lookback)))

	ramom_ret = np.sign(df["risk_adjusted_mom"].rolling(k2))*(np.expm1(self.df["ret"].iloc[-1])/self.df["volatility"].iloc[-1])
	return risk_adjusted_mom

def strat(context, data, weight):
	self.df["ret"] = np.log(data[context.security]/data[context.security].shift(1))
	ma = data[context.security].rolling(length)*np.transpose(weight)	# EWMA

	#--- signal calculation
	risk_adjusted_ma = risk_adjusted_ma(ret, self.lookback, lda = self.lda)
	

	return