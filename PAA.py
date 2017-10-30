"""
PAA - montly - v5

P. Falter 
8/26/2016

Modified implementation of Protective Asset Allocation
based on Keller and Keuning (April 25, 2016)
"Protective Asset Allocation (PAA): A simple momentum-based alternative for term deposits"
http://papers.ssrn.com/sol3/papers.cfm?abstract_id=2759734

Strategy goal:
- Average, unleveraged return better than SP500
- Significantly reduced drawdown vs SP500
subject to constraints:
- Monthly rebalancing

PAA strategy summary
1. consider a proxy set of N assets
2. select a protection factor (see below) and maximum number of assets to hold (TopN)
3. count the number (n) of these with positive prior month MOM (see MOM definition below)
4. compute the bond fraction (BF): BF = (N-n)/(N-n1). (see n1 definition below)
5. Invest a fraction BF of the portfolio into the safe set (bonds)
6. Invest the remaining fraction (1-BF) in the top n_eq equities sorted on MOM
7. Hold for one month and then repeat to rebalance

definition of terms used by Keller
Keller defines the following:
- momentum (MOM): to be MOM = (last month's close)/(SMA over lookback period) - 1
- lookback period (L): L is measured in months
- protection factor (a): a = [0, 1, or 2] is used to adjust the BF gain: n1 = a*N/4
- number of equities to be purchased (n_eq): n_eq = min(n,topM)

"""
"""
Significant changes vs Keller and Keunig:
a) bond fraction is forced to fall on n_levels discrete values from 0.0 to 1.0
b) safe set = [IEF, TLT]
c) the author's original equity set is used for market proxy, but a separate equity set is defined for investing

If you want to approximate the author's original results then
- set context.n_levels to a large value, perhaps 100, 
    or comment out "bond_fraction = np.floor(bond_fraction*n_steps)/n_steps"
- set context.equities = context.proxies
- set context.safe = [sid(23870)] #IEF

More comments at bottom of file
"""
"""

PAA - monthly - v5
Study of separate investment and proxy sets



Changes to PAA - monthly - v0: 
a) bond fraction is forced to fall on n_levels discrete values from 0.0 to 1.0
b) daily sampling
c) unweighted filter with 4 month lookback
d) safe harbor = [IEF and TLT]
e) separate investment and proxy sets


"""

import numpy as np

 
def initialize(context):
    """
    Define proxy set, equity set and safe set
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
    
    """
    Define other parameters
    """    
    context.lookback = 4         # lookback in months
    context.protection = 2       # protection factor = 0(low), 1, 2 (high)
    context.topM = 6             # topM is max number of equities
    context.n_levels = 2         # number of discrete levels for bond_fraction (>=2)
    context.b_frac = 0           # initialize to avoid recording error message
    
    """
    Define structures to count how frequently each equity is held
    """    
    context.eq_list = [stock.symbol for stock in context.equities]
    context.safe_list = [stock.symbol for stock in context.safe]

    context.times_held = dict.fromkeys(context.eq_list,0)
    context.cum_safe = dict.fromkeys(context.safe_list,0)   
    
    # Rebalance monthly
    schedule_function(func=PAA_rebalance, date_rule=date_rules.month_end(days_offset=0), time_rule=time_rules.market_open(), half_days=True)   
     
    # Record tracking variables at the end of each day.
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())

def PAA_rebalance(context,data):
    """
    Select optimal portfolio and implement it
    """    
    N_safe = len(context.safe)
    N_eq = len(context.equities)
    lookback = context.lookback
    topM = context.topM
    prot = context.protection
    
    #
    # poll the proxy set to determine the number of assets with positive momentum
    #
    n = 0
    for eq in context.proxies:
        sym = eq.symbol        
        if data.can_trade(eq):
            price_hist = data.history(eq, 'price', 21*lookback, '1d')
            price = price_hist[-1]
            prices = price_hist #.resample('M', how='last')
            w_SMA = np.ones(len(prices))
            MA = np.average(prices, weights=w_SMA,axis=0)
            if price>MA: n += 1
    
    # Calculate the bond fraction based on N_eq, prot, and n
    # This is the portion to be invested in safe harbor
    # Calculate equity fraction and weight per equity (frac_eq, w_eq) 
    # Limit bond_fraction to a discrete number of levels (n_levels >=2)
    
    n1 = prot*N_eq/4.0
    bond_fraction = min( 1.0, (N_eq - n)/(N_eq-n1) )
    n_steps = context.n_levels - 1.0
    bond_fraction = np.floor(bond_fraction*n_steps)/n_steps
    
    frac_safe = bond_fraction    
    w_safe = frac_safe/N_safe
    context.b_frac = bond_fraction

    
    #
    # calculate the MOM for each equity
    # determine the number of equities to be purchases
    #
    MOM = {}
    n = 0
    for eq in context.equities:
        sym = eq.symbol
        
        if data.can_trade(eq):
            price_hist = data.history(eq, 'price', 21*lookback, '1d')
            price = price_hist[-1]
            prices = price_hist #.resample('M', how='last')
            w_SMA = np.ones(len(prices))
            MA = np.average(prices, weights=w_SMA,axis=0)
            MOM[sym] = (price/MA) - 1
            if MOM[sym]>0.0: n+= 1            
    
    frac_eq = 1.0-bond_fraction
    n_eq = min(n,topM)
    w_eq = 0.0
    if n>0: w_eq = frac_eq/n_eq
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
    
    

"""
=======================================================================================
Base model: PAA - monthly - v0
Implementing per Keller's recommendation
    baseline equity set with IEF as safe harbor
    Lookback = 12 months, protection = 2, 
    Data sampled monthly
    moving average based on triangular filter

Total Returns    92.3%
Alpha         0.08            Beta    0.04        Sharpe    0.94
Volatility    0.09    Max Drawdown    9.6%

SPY held 68 times
QQQ held 75 times
IWM held 53 times
VGK held 46 times
EWJ held 30 times
EEM held 42 times
IYR held 59 times 
GSG held 22 times
GLD held 45 times
HYG held 31 times
LQD held 32 times
TLT held 48 times
IEF held 101 times

Observations
1. This delivered the low volatily and good drawdown protection
2. A quick check of protection values shows that 2 is better than 0 or 1
3. Overall CAGR is 7.5%
4. The method results in long (6 to 18 mo) periods of no net growth
5. Portfolio value may drop as market is recovering from a drawdown
6. GSG, EWJ, HYG, and LQD were held much less often than other equities

Thoughts
1. Observations 1 and 2 support Keller's claims
2. The CAGR is good for a conservative portfolio
3. Observations 4 and 5 would be frustrating to investors
4. Bonds are held at high levels too long after stocks start recovery
5. Why is the the investment set the same as the proxy set?
6. Why is this a good proxy set?
7. Are there better investment and safe sets?
8. Are the good results due to sound logic or overfitting? Is there sound rationale for picking the proxy set other than that it produced good results in the back test?
9. How brittle is this strategy? Can it handle small changes to the proxy set? Is it strongly affected by day of month at which polling occurs? or at which rebalancing occurs?

"""
"""
=======================================================================================
PAA - monthly - v1
Study of bond fraction calculation and day of month sensitivity
Conclusions:
1. Returns benefit from forcing BF to fall on a small number of discrete values. This keeps the portfolio more heavily invested in stocks, except when polling strongly supports bonds
2. There is a significant day-of-month sensitivity


Base model: PAA - monthly - v0
Changes: 
a) bond fraction is forced to fall on n_levels discrete values from 0.0 to 1.0

For baseline presented in PAA-monthly-v0: standard resample
n_levels =  12    Returns    93.6%    Alpha    0.08 Sharpe    0.92    Drawdown    9.6%
n_levels =   8    Returns    95.9%    Alpha    0.09 Sharpe    0.97    Drawdown    9.4%
n_levels =   6    Returns    94.8%    Alpha    0.08 Sharpe    0.88    Drawdown   10.9%
n_levels =   4    Returns    96.6%    Alpha    0.09 Sharpe    0.92    Drawdown   10.9%
n_levels =   3    Returns    97.6%    Alpha    0.09 Sharpe    0.87    Drawdown   10.9%
n_levels =   2    Returns   124.6%    Alpha    0.11 Sharpe    1.03    Drawdown   10.9%

For n_levels = 2 given the following offsets relative to month_end: standard resample
days_offset= 0    Returns   124.6%    Alpha    0.11 Sharpe    1.03    Drawdown   10.9%
days_offset= 1    Returns   133.4%    Alpha    0.12 Sharpe    1.13    Drawdown   12.2%
days_offset= 2    Returns   106.8%    Alpha    0.09 Sharpe    0.86    Drawdown   16.8%
days_offset= 3    Returns    78.2%    Alpha    0.06 Sharpe    0.58    Drawdown   17.3%
days_offset= 5    Returns    64.9%    Alpha    0.05 Sharpe    0.46    Drawdown   18.0%
days_offset= 7    Returns    96.5%    Alpha    0.08 Sharpe    0.74    Drawdown   17.1%
days_offset=13    Returns    97.7%    Alpha    0.09 Sharpe    0.81    Drawdown   16.1%

For n_levels = 12 given the following offsets relative to month_end: standard resample
days_offset= 0    Returns    93.6%    Alpha    0.08 Sharpe    0.92    Drawdown    9.6%
days_offset= 1    Returns    82.7%    Alpha    0.07 Sharpe    0.80    Drawdown   11.4%
days_offset= 2    Returns    69.3%    Alpha    0.06 Sharpe    0.62    Drawdown   15.6%
days_offset= 3    Returns    46.0%    Alpha    0.03 Sharpe    0.34    Drawdown   17.7%
days_offset= 5    Returns    51.5%    Alpha    0.04 Sharpe    0.41    Drawdown   17.0%
days_offset= 7    Returns    65.9%    Alpha    0.05 Sharpe    0.57    Drawdown   16.1%
days_offset=13    Returns    78.8%    Alpha    0.07 Sharpe    0.77    Drawdown   12.3%

For n_levels = 2 given the following offsets relative to month_end: no resampling
days_offset= 0    Returns   130.7%    Alpha    0.12 Sharpe    1.08    Drawdown   10.9%
days_offset= 1    Returns   107.4%    Alpha    0.09 Sharpe    0.88    Drawdown   10.9%
days_offset= 2    Returns   127.4%    Alpha    0.12 Sharpe    1.07    Drawdown   15.0%
days_offset= 3    Returns    88.2%    Alpha    0.07 Sharpe    0.67    Drawdown   17.3%
days_offset= 5    Returns    73.8%    Alpha    0.06 Sharpe    0.54    Drawdown   18.3%
days_offset= 7    Returns   118.2%    Alpha    0.10 Sharpe    0.96    Drawdown   13.7%
days_offset=13    Returns   113.9%    Alpha    0.10 Sharpe    0.96    Drawdown   12.9%

Weekly test
For n_levels = 2 given the following offsets relative to week_end: no resampling
days_offset= 0    Returns    96.1%    Alpha    0.08 Sharpe    0.80    Drawdown   14.6%
days_offset= 1    Returns   106.4%    Alpha    0.10 Sharpe    0.91    Drawdown   12.4%
days_offset= 2    Returns   110.6%    Alpha    0.10 Sharpe    0.94    Drawdown   10.9%
days_offset= 3    Returns    86.0%    Alpha    0.07 Sharpe    0.69    Drawdown   13.9%


Observations
1. Between n_levels 3 to 12 there is little effect on performance (slightly better return and slightly worse volatility)
2. For n_levels = 2 the performance is very different (returns increase much faster than volatility)
3. Behavior is strongly affected by the days_offset from month_end
"""

"""
=======================================================================================
PAA - monthly - v2
Study of lookback period, 
Conclusions:
1. A lookback period of 4 or 5 months is better than much longer ones
2. Protection factor = 2 gives the best results
3. Limiting the maximum number of equities (TopM) to 5 or 6 provides good return vs volatility

=======================================================================================
Lookback for simple moving average (unweighted)

Prot = 2; TopM = 6; n_levels = 2
MA = SMA based on daily data:  6/1/2017 through 6/3/2016

12 month lookback:             Total Returns    72.7%
Alpha         0.05            Beta    0.19        Sharpe    0.53
Volatility    0.12    Max Drawdown    16.0%"

9 month lookback:             Total Returns    114.5%
Alpha         0.10            Beta    0.18        Sharpe    0.93
Volatility    0.12    Max Drawdown    11.6%""

7 month lookback:             Total Returns    116.7%
Alpha         0.10            Beta    0.16        Sharpe    0.94
Volatility    0.12    Max Drawdown    11.9%"

6 month lookback:             Total Returns    130.8%
Alpha         0.12            Beta    0.16        Sharpe    1.06
Volatility    0.12    Max Drawdown    10.1%"

5 month lookback:             Total Returns    154.7%
Alpha         0.15            Beta    0.14        Sharpe    1.28
Volatility    0.12    Max Drawdown    10.9%"

4 month lookback:             Total Returns    158.1%
Alpha         0.15            Beta    0.13        Sharpe    1.32
Volatility    0.12    Max Drawdown    10.9%" 

3 month lookback:             Total Returns    84.2%
Alpha         0.07            Beta    0.17        Sharpe    0.60
Volatility    0.13    Max Drawdown    14.0%" 
 
==> the 4 and 5 month lookbacks give similar results ==> use either

=======================================================================================
Protection factor for simple moving average (unweighted)

TopM = 6; MA = 4 month SMA based on daily data:  6/1/2017 through 6/3/2016

Protection factor = 2:             Total Returns    158.1%
Alpha         0.15            Beta    0.13        Sharpe    1.32
Volatility    0.12    Max Drawdown    10.9%

Protection factor = 1:             Total Returns    137.4%
Alpha         0.12            Beta    0.25        Sharpe    1.06
Volatility    0.13    Max Drawdown    18%

Protection factor = 0:             Total Returns    81%
Alpha         0.06            Beta    0.28        Sharpe    0.5
Volatility    0.14    Max Drawdown    33.5%

==> Protection factor = 2 is the clear winner
Note: both 0 and 1 resulted in deeper and wider drawdowns in addition to lower overall yield

=======================================================================================
Max number of equities (TopM) for simple moving average (unweighted)

Prot = 2; MA = SMA based on daily data:  6/1/2017 through 6/3/2016

TopM = 12 (no limit): Total Returns    132.4%
Alpha         0.12            Beta    0.10        Sharpe    1.25
Volatility    0.10    Max Drawdown    10.3%

TopM = 8:             Total Returns    142.7%
Alpha         0.14            Beta    0.12        Sharpe    1.24
Volatility    0.11    Max Drawdown    11.3%
 
TopM = 6:             Total Returns    158.1%
Alpha         0.15            Beta    0.13        Sharpe    1.32
Volatility    0.12    Max Drawdown    10.9%

TopM = 5:             Total Returns    154.8%
Alpha         0.15            Beta    0.14        Sharpe    1.23
Volatility    0.13    Max Drawdown    10.7%

TopM = 4:             Total Returns    158.1%
Alpha         0.13            Beta    0.14        Sharpe    1.03
Volatility    0.13    Max Drawdown    12.4%

TopM = 3:             Total Returns    153.3%
Alpha         0.14            Beta    0.14        Sharpe    1.12
Volatility    0.14    Max Drawdown    12.8%

 
==> I'll use TopM = 5 or 6. Similar returns are had for TopM = 3, 4, 5, o4 6. TopM = 5 or 6 appear to be a good balance of preserving return and reducing risk (drawdown, volatility)

"""
"""
=======================================================================================
PAA - monthly - v3
Study of various asset weighting schemes
Conclusions:
1. Strategy returns were surprisingly unaffected by the weighting schemes used.

Note: The code for implementing this stucy has been removed from this file for clarity.

Base model: PAA - monthly - v0
Changes: 
a) bond fraction is forced to fall on n_levels discrete values from 0.0 to 1.0
b) daily sampling
c) unweighted filter with 4 month lookback
d) various asset weighting methods

Picking best weighting scheme

Prot = 2; TopM = 12; n_levels = 2
MA = 4 mon SMA based on daily data:  6/1/2017 through 6/3/2016

Equal weighting
Total Returns    132.4%
Alpha         0.12            Beta    0.10        Sharpe    1.25
Volatility    0.10    Max Drawdown    10.3%

proportional to expected return (10 days), if > 0:             
Total Returns    156.2%
Alpha         0.15            Beta    0.09        Sharpe    1.30
Volatility    0.12    Max Drawdown    13.0%

proportional to expected return (21 days), if > 0:             
Total Returns    156.5%
Alpha         0.15            Beta    0.10        Sharpe    1.27
Volatility    0.12    Max Drawdown    12.9%

proportional to expected return (31 days), if > 0:             
Total Returns    132.5%
Alpha         0.12            Beta    0.11        Sharpe    1.08
Volatility    0.12    Max Drawdown    16.0%

proportional to expected return (42 days), if > 0:             
Total Returns    138.9%
Alpha         0.13            Beta    0.13        Sharpe    1.13
Volatility    0.12    Max Drawdown    13.1%

proportional to expected return/variance (21 days), if > 0:             
Total Returns    149.7%
Alpha         0.15            Beta    0.04        Sharpe    1.54
Volatility    0.10    Max Drawdown    11.8%

proportional to expected return/sqrt(variance) (21 days), if > 0:             
Total Returns    154.5%
Alpha         0.15            Beta    0.08        Sharpe    1.41
Volatility    0.11    Max Drawdown    12.3%

proportional to expected return*sqrt(variance) (21 days), if > 0:             
Total Returns    154.2%
Alpha         0.15            Beta    0.13        Sharpe    1.13
Volatility    0.14    Max Drawdown    13.6%
Total Returns

proportional to expected return/variance (42 days), if > 0:             
Total Returns    119.7%
Alpha         0.11            Beta    0.06        Sharpe    1.20
Volatility    0.10    Max Drawdown    9.4%

proportional to expected return/sqrt(variance) (42 days), if > 0:             
Total Returns    130.6%
Alpha         0.12            Beta    0.10        Sharpe    1.17
Volatility    0.11    Max Drawdown    11.7%

proportional to expected return*sqrt(variance) (42 days), if > 0:             
Total Returns    141.9%
Alpha         0.13            Beta    0.16        Sharpe    1.05
Volatility    0.13    Max Drawdown    13.6% 

==> the return is suprisingly independent of wildly different schemes

"""
"""
=======================================================================================
PAA - monthly - v4
Study of safe set
Conclusions:
1. 50% IEF/50% TLT provides better yield tha IEF or TLT alone and volatility similar to IEF. 


Base model: PAA - monthly - v0
Changes: 
a) bond fraction is forced to fall on n_levels discrete values from 0.0 to 1.0
b) daily sampling
c) unweighted filter with 4 month lookback
d) various safe sets

Prot = 2; TopM = 6; n_levels = 2
MA = 4 mon SMA based on daily data:  6/1/2017 through 6/3/2016

100% IEF
Total Returns    158.1%
Alpha         0.15            Beta    0.13        Sharpe    1.32
Volatility    0.12    Max Drawdown    10.9%

50% IEF and 50% SHY
Total Returns    124.7%
Alpha         0.11            Beta    0.17        Sharpe    1.08
Volatility    0.11    Max Drawdown    10.9%

50% IEF and 50% TLT
Total Returns    199.4%
Alpha         0.20            Beta    0.08        Sharpe    1.54
Volatility    0.13    Max Drawdown    13.3%

100% TLT
Total Returns    157.7%
Alpha         0.16            Beta    0.05        Sharpe    1.07
Volatility    0.15    Max Drawdown    18.8%

33% IEF, 33%SHY and 33% TLT
Total Returns    159.5%
Alpha         0.15            Beta    0.12        Sharpe    1.31
Volatility    0.12    Max Drawdown    11.0%

33% IEF, 33%IAU and 33% TLT
Total Returns    191%
Alpha         0.19            Beta    0.12        Sharpe    1.46
Volatility    0.13    Max Drawdown    16.8%

==> 50/50 IEF/TLT is much better than IEF or TLT alone
"""
"""
=======================================================================================
PAA - monthly - v5
Study of separate equity and proxy set
Conclusions:
1. Separate proxy and equity sets work fine.
2. The proxy set does not outperform a naively selected equity set
3. Others can have fun playing with this


Base model: PAA - monthly - v4
Changes: 
a) various equity sets

Proxy set same as Keller:
- SPY, QQQ, IWM (US equities: S&P500, Nasdaq100 and Russell2000 Small Cap)
- VGK, EWJ (Developed International Market equities: Europe and Japan)
- EEM (Emerging Market equities)
- IYR, GSG, GLD (alternatives: REIT, Commodities, Gold)
- HYG, LQD and TLT (High Yield, Investment Grade Corporate and Long Term US Treasuries)

Equity sets as shown below

Equity set 0 = Proxy set = original set
Equity set = [SPY, QQQ, IWN, VGK, EWJ, EEM, IYR, GSG, GLD, HYG, LQD, TLT]

Total Returns    199%
Alpha         0.20            Beta    0.08        Sharpe    1.54
Volatility    0.13    Max Drawdown    13%

Equity Set 1 = Set 0, except 9 SPDR sector ETFs replace the 9 non-bond ETFs
Equity Set = [XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, HYG, LQD, TLT]
Total Returns    192%
Alpha         0.19            Beta    0.10        Sharpe    1.50
Volatility    0.13    Max Drawdown    14%
Set 1 results were similar to Set 0 results throughout the back test

Equity Set 2 = Set 1, except bonds are replaced by [RWR, GSG, IAU]
Equity Set = [XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, RWR, GSG, IAU]
Total Returns    219%
Alpha         0.22            Beta    0.10        Sharpe    1.60
Volatility    0.14    Max Drawdown    17%
This set may give somewhat better return and Sharpe ratio with slightly degraded drawdown. 
 
Equity Set 3 = Set 2, except most volatile ETFs [XLE, XLF, GSG, IAU] are replaced by [IWM, VGK, EWJ, TLT]
[XLF, GSG, IAU] each have at least 1.5x the volatility of the SP500
Equity Set = [XLB, XLE, XLI, XLK, XLP, XLU, XLV, XLY, RWR, VGK, EWJ, EEM]
Total Returns    220%
Alpha         0.22            Beta    0.09        Sharpe    1.73
Volatility    0.13    Max Drawdown    14%
Sets 1, 2, and 3 have are significantly different in composition, but not in result.
TLT was held only 12 times as an equity. This is about 1/4 as often as others. This is expected since the equity set should be purchased when bonds are not in favor.

 
Equity Set 4 = Set 3, except TLT is replaced by EWH
[XLF, GSG, IAU] each have at least 1.5x the volatility of the SP500
Equity Set = [XLB, XLE, XLI, XLK, XLP, XLU, XLV, XLY, RWR, VGK, EWJ, EWH]
Total Returns    218%
Alpha         0.22            Beta    0.10        Sharpe    1.63
Volatility    0.14    Max Drawdown    14%
EWH was held 41 times, but Set 4 results looks just about the same as the others.


"""

"""
=======================================================================================

Open issues:
a) Entry/exit logic (resolved)
unmodified:
The logic appears to function as desired by forcing exit from stocks during past periods of poor returns
Resolution: bond_fraction is modified so that the result must fall on n_level levels from 0 to 1
This adjustment improve performance by forcing a clearer "in or out" decision.
This discrete nature the investor reduces the likelihood of very small holdings or or changes in an asset.

b) Proxy set (no study yet)
Keller used:
- SPY, QQQ, IWM (US equities: S&P500, Nasdaq100 and Russell2000 Small Cap)
- VGK, EWJ (Developed International Market equities: Europe and Japan)
- EEM (Emerging Market equities)
- IYR, GSG, GLD (alternatives: REIT, Commodities, Gold)
- HYG, LQD and TLT (High Yield, Investment Grade Corporate and Long Term US Treasuries)
What is the technical rationale for selecting the set of assets that are polled for determining when to be in stocks vs bonds? 
If this set is near optimal, then why? 
Might the asset set merely be fortunately correlated with past good results?

c) Equity set (resolved. further optimization may be done)
Keller used the same equity set as proxy set
Why limit the equity set to be the same as the proxy set that is polled to determine entry/exit?
It should be more profitable to have separate investment and proxy sets
Resolution: Separate equity set works fine with the original proxy set

d) Safe harbor set (resolved)
Keller used: IEF
He stated a preference for low volatility (IEF, SHY) vs others (BIL, SHV, IEI, TLT, AGG)
The safe set results may be different since I modified the entry/exit logic
Resolution: IEF/TLT provided better results than IEF alone

d) Day of month sensitivity (still open)
As shown in PAA - monthly - v1 above there is a significant sensitivity.
How can this be mitigated?

"""
