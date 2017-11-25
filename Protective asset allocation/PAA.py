#Protective asset allocation

'''
Note:
- Please adjust the codes and the assets in accordance with the platform and the market



PAA strategy summary
1. consider a proxy set of N assets
2. select a protection factor (see below) and maximum number of assets to hold (TopN)
3. count the number (n) of these with positive prior month MOM (see MOM definition below)
4. compute the bond fraction (BF): BF = (N-n)/(N-n1). (see n1 definition below)
5. Invest a fraction BF of the portfolio into the safe set (bonds)
6. Invest the remaining fraction (1-BF) in the top n_eq equities sorted on MOM
7. Hold for one month and then repeat to rebalance
'''

from zipline.api import order, symbol, record, order_target
import sys
import numpy as np
import pandas as pd

logger = init_logger(__name__)

def initialize(context):
	context.security = symbol('AAPL') # change stock symbol here
	context.asset = []
	"""
    Define proxy set, equity set and safe set. These are only examples and subjected to change
    """   
    context.proxies = [  
            sid(8554),  #SPY                      
            sid(19920), #QQQ
            sid(21519), #IWM
            sid(27100), #VGK
            sid(14520), #EWJ
            sid(24705), #EEM
            sid(21652), #IYR
            sid(32406), #GSG
            sid(26807), #GLD
            sid(33655), #HYG
            sid(23881), #LQD
            sid(23921)  #TLT
                        ]

    context.equities = [
            sid(19654), #XLB
            sid(19657), #XLI
            sid(19658), #XLK
            sid(19659), #XLP
            sid(19660), #XLU
            sid(19661), #XLV
            sid(19662), #XLY
            sid(26981), #IAU 
            sid(21519), #IWM
            sid(27100), #VGK
            sid(14520), #EWJ
            sid(14519), #EWH
    ]
    
    context.safe = [sid(23870), #IEF
                    sid(23921),  #TLT
                    ] 
    
	context.lookback = 4
	context.protection = 2            # protection factor = 0(low), 1, 2 (high)
	context.topM = 6                  # topM is max number of equities


def strat(context, data):
	N_safe = len(context.safe)
    N_eq = len(context.equities)
	lookback = context.lookback
	prot = context.protection
	topM = context.topM
	bf = (N-n)/(N-n1)                 # bond fraction, we will invest this fraction in risk-free bonds
	frac_eq = 1 - bf

	# calculate the momentum and sort the assets
	MOM = {}
	n = 0
    for eq in context.equities:
        sym = eq.symbol
        
        if data.can_trade(eq):
            price_hist = data.history(eq, 'price', 21*lookback, '1d')
            price = price_hist[-1]
            prices = price_hist #.resample('M', how='last')
            # calculate SMA
            w_SMA = np.ones(len(prices))
            MA = np.average(prices, weights=w_SMA,axis=0)
            MOM[sym] = (price/MA) - 1
            if MOM[sym] > 0.0: 
            	n+= 1                 # count positive trending assets
    
    frac_eq = 1.0-bond_fraction
    n_eq = min(n,topM)
    w_eq = 0.0
    if n>0: 
    	w_eq = frac_eq/n_eq

    MOM_threshold = sorted(MOM.values(),reverse=True)[n_eq-1]    

    #
    # order assets from safe set
    #
    for eq in context.safe:
        sym = eq.symbol
        if data.can_trade(eq):
            order_target_percent(eq, w_safe)
            context.cum_safe[sym] = context.cum_safe[sym] + (1 if w_safe > 0 else 0)
    #
    # order assets from equity set
    #            
    for eq in context.equities:
        sym = eq.symbol
        if get_open_orders(eq): return
        if data.can_trade(eq):
            if MOM[sym]>=MOM_threshold:
                order_target_percent(eq, w_eq) 
                context.times_held[sym] = context.times_held[sym] + 1
            else:
                order_target_percent(eq,0.0)  
    #
    # log summary results on last trading day
    #    
    env = get_environment('*')
    first_trading_date  = env['start'].date()    
    last_trading_date  = env['end'].date()
    this_trading_date = get_datetime('US/Eastern').date()
    days_remaining = (last_trading_date - this_trading_date).days
    days_traded = (last_trading_date - first_trading_date).days
    if days_remaining < 20:        
        log.info("------------------------------------------------------------------")
        for eq in context.equities:
            sym = eq.symbol
            msg = "{0} held {1} times".format(sym,context.times_held[sym])
            log.info(msg)
        for eq in context.safe:
            sym = eq.symbol
            msg = "{0} held {1} times".format(sym,context.cum_safe[sym])
#            log.info(msg)
        daily_prices = data.history(sid(8554),'price',days_traded,'1d')
        monthly_prices = daily_prices.resample('1M', how='last', 
                                               closed='left', label='left')
        diffs = monthly_prices.pct_change().dropna().values  
        vlt_SPY = np.std(diffs,axis=0)
        for eq in context.equities:
            sym = eq.symbol
            daily_prices = data.history(eq,'price',days_traded,'1d')
            monthly_prices = daily_prices.resample('1M', how='last', 
                                                   closed='left', label='left')
            diffs = monthly_prices.pct_change().dropna().values  
            rel_vlt = np.std(diffs,axis=0)/vlt_SPY
            monthly_nona = daily_prices.resample('1M', how='last', 
                                                   closed='left', label='left').dropna().values
            ret = monthly_nona[-1]/monthly_nona[0] - 1.0
            msg = "{0} has return of {1:0.1%} and relative volatility of {2:.1%} % ".format(sym,ret, rel_vlt)
#            log.info(msg)
#
# record leverage and bond fraction
#
def my_record_vars(context, data):
    record(leverage=context.account.leverage, b_frac=context.b_frac) 







