from xquant.api import get_universe, rebalance_portfolio

def initialize(context):
	pass

def handle_data(context, data):
	# get the universe
	universe = get_universe(data, context.datetime)
	# compute weights
	weights = {asset: 1. / len(universe) for asset in universe}
	# rebalance portfolio
	rebalance_portfolio(context, data, weights)