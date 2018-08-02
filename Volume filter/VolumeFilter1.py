'''
Volume filter strategy 1
Developer: Hoang Nguyen
Source: Oxford strategy (https://oxfordstrat.com/trading-strategies/volume-filters-1/)
Data: 
- Symbol: XBTUSD (Futures)
- Exchange: Bitmex
- Period: 

Rationale:
See strategy design

Version:
- long-only
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt
import backtrader.feeds as btfeeds

class VolumeFilter(bt.Strategy):
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.close = self.datas[0].close
        self.open = self.datas[0].open
        self.high = self.datas[0].high
        self.low = self.datas[0].low
        self.volume = self.datas[0].volume
        
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Price channels
        self.pricechannel = np.zeros(4)

        # Volume channels
        self.volumechannel = np.zeros(4)

        # Volume filter
        self.upvolume = 0
        self.downvolume = 0

        # Setup
        self.long_entry_setup = False
        self.short_entry_setup = False
        self.long_exit_setup = False
        self.short_exit_setup = False

        # Filter
        self.long_entry_filter = False
        self.short_entry_filter = False
        self.long_exit_filter = False
        self.short_exit_filter = False

        # Signal (long)
        self.buy_sig = bt.And(self.long_entry_setup && self.long_entry_filter)
        self.sell_sig = bt.And(self.long_exit_setup && self.long_exit_filter)

        # Signal (short)

        # Signal (stop loss)

    def price_channels(self, entry_lookback, exit_lookback):
        # indexes 0,1,2,3 are the entry up price channel, entry down price channel, exit up price channel and exit down price channel
        entry_high = self.high.rolling(entry_lookback)
        entry_low = self.low.rolling(entry_lookback)
        exit_high = self.high.rolling(exit_lookback)
        exit_low = self.low.rolling(exit_lookback)

        self.pricechannel = [max(entry_high), min(entry_low), max(exit_high), min(exit_low)]

    def volume_channels(self, entry_lookback, exit_lookback):
        # indexes 0,1,2,3 are the entry up volume channel, entry down volume channel, exit up volume channel and exit down volume channel
        entry_up = self.upvolume.rolling(entry_lookback)
        entry_dn = self.downvolume.rolling(entry_lookback)
        exit_up = self.upvolume.rolling(exit_lookback)
        exit_dn = self.downvolume.rolling(exit_lookback)

        self.volumechannel = [max(entry_up), min(entry_dn), max(exit_up), min(exit_dn)]

    def filter(self):
        self.upvolume += max((self.close[0]-self.open[0])*self.volume[0], 0)
        self.downvolume += min((self.close[0]-self.open[0])*self.volume[0], 0)

    def setup(self):
        self.long_entry_setup = self.upvolume[0] > self.entry_up[-1]
        self.short_entry_setup = self.downvolume[0] > self.entry_up[-1]
        self.long_exit_setup = self.upvolume[0] > self.exit_up[-1]
        self.short_exit_setup = self.downvolume[0] > self.exit_up[-1]

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.buy_sig:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        
        else:
            if self.sell_sig:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(RSIStrat)

    data = btfeeds.GenericCSVData(
    dataname='../data/bitmex/XBTUSD.csv',

    fromdate=datetime.datetime(2018, 2, 2, 0, 00, 0),
    todate=datetime.datetime(2018, 7, 7, 23, 00, 0),

    nullvalue=0.0,

    dtformat=('%Y-%m-%d %H:%M:%S'),

    datetime=1, # count index
    open=2,
    high=3,
    low=4,
    close=5,
    volume=6
)


    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    cerebro.plot()