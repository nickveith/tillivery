
import requests
import urllib
import sys
import datetime
import time
from math import ceil

###########################################################################

input_data = {'stripe_api_key': 'sk_live_9gGEH1eSMVAiNj6K9TUXCkKB'}
output = {}

# General Setting
debug = True
currency = 'USD'

# Shopify Setting
shop_url = 'https://tillivery.myshopify.com'
shopify_api_key = '642c1f9c3ed33035ea2a623ad970d52c'
shopify_password = '0e3ea297e2e7ffde0634d0ecb28413ac'
shopify_headers = {'Content-Type': 'application/json'}

# Stripe Setting
base_url = 'https://api.stripe.com/v1/'
stripe_api_key = input_data['stripe_api_key']
stripe_headers = {
	'Authorization': 'Bearer %s' % (stripe_api_key,),
	'content_type': 'application/x-www-form-urlencoded'
	}

###########################################################################

def prettyprint_(req):
	print('{}\n{}\n{}\n\n{}'.format(
		'-----------START-----------',
		req.method + ' ' + req.url,
		'\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
		req.body,
	))

def request_ (method, url, headers, params=None, data=None, json=None, auth=None, debug=False):
	result = {}
	r = requests.Request(method, url, params=params, headers=headers, auth=auth, data=data, json=json)
	prepared = r.prepare()
	
	if debug:
		prettyprint_(prepared)

	s = requests.Session()
	r = s.send(prepared)

	result['status_code'] = r.status_code
	result['error'] = not (r.status_code == requests.codes.ok)

	try:
		result['data'] = r.json()
	except:
		pass

	if debug:
		print result

	return result

def fetch_customer_orders (shop_url, api_key, password, debug):
	headers = shopify_headers

	# Get Count of Orders
	params = {"status": "open", "financial_status": "pending"}
	method = 'GET'
	edge = '/admin/orders/count.json'
	url = shop_url + edge
	response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
	order_count = response.get('data',{}).get('count',0)

	# Get Orders
	params = {"status": "open", "financial_status": "pending"}
	method = 'GET'
	edge = '/admin/orders.json'
	url = shop_url + edge
	orders = []

	limit = 250
	total_pages = max(ceil(order_count/limit),1)
	for page in xrange(1, int(total_pages + 1)):
		params['page'] = page
		params['limit'] = limit
		response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
		orders += response.get('data',{}).get('orders')

	### Set Stripe Customer ID on Orders
	for order in orders:
		customer_id = order.get("customer", {}).get('id')
		order['shopify_customer_id'] = customer_id

		## Get Customer Metadata
		stripe_customer_id = None
		method = 'GET'
		edge = '/admin/customers/{customer_id}/metafields.json'.format(customer_id = customer_id)
		url = shop_url + edge
		response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
		for metafield in response['data']['metafields']:
			namespace = metafield['namespace']
			key = metafield['key']
			if namespace == 'customer_attribute' and key == 'stripe-customer':
				stripe_customer_id = metafield['value']
				break

		time.sleep(.5)

		order['stripe_customer_id'] = stripe_customer_id

	### Collect customer orders
	customer_orders = {}
	for order in orders:
		customer_id = order.get('customer', {}).get('id')
		order_id = order.get('id')
		cust_orders = customer_orders.get(customer_id)
		if cust_orders is None:
			cust_orders = [order]
			customer_orders[customer_id] = cust_orders
		else:
			cust_orders.append(order)
			customer_orders[customer_id] = cust_orders

	return customer_orders

def utf8(value):
    # Note the ordering of these conditionals: `unicode` isn't a symbol in
    # Python 3 so make sure to check version before trying to use it. Python
    # 2to3 will also boil out `unicode`.
    if sys.version_info < (3, 0) and isinstance(value, unicode):
        return value.encode('utf-8')
    else:
        return value

def _encode_nested_dict(key, data, fmt='%s[%s]'):
    d = {}
    for subkey, subvalue in data.iteritems():
        d[fmt % (key, subkey)] = subvalue
    return d

def _api_encode(data):
    for key, value in data.iteritems():
        key = utf8(key)
        if value is None:
            continue
        elif hasattr(value, 'stripe_id'):
            yield (key, value.stripe_id)
        elif isinstance(value, list) or isinstance(value, tuple):
            for sv in value:
                if isinstance(sv, dict):
                    subdict = _encode_nested_dict(key, sv, fmt='%s[][%s]')
                    for k, v in _api_encode(subdict):
                        yield (k, v)
                else:
                    yield ("%s[]" % (key,), utf8(sv))
        elif isinstance(value, dict):
            subdict = _encode_nested_dict(key, value)
            for subkey, subvalue in _api_encode(subdict):
                yield (subkey, subvalue)
        elif isinstance(value, datetime.datetime):
            yield (key, _encode_datetime(value))
        else:
            yield (key, utf8(value))

def create_charge (stripe_customer_id, amount, currency, shopify_customer_id, shopify_order_id, debug=False):

	headers = stripe_headers
	api_key = stripe_api_key

	method = 'POST'
	edge = 'charges'
	url = shop_url + edge
	params = {
		'customer': stripe_customer_id,
		'amount': amount,
		'currency': currency,
		'metadata': {
			'shopify_customer_id': shopify_customer_id,
			'shopify_order_id': shopify_order_id
			}
		}

	post_data = urllib.urlencode(list(_api_encode(params or {})))
	url = base_url + edge
	records = request_(method, url, headers, data=post_data, debug=debug)

	return records

def read_transactions(shop_url, api_key, password, order_id, debug=False):
	headers = shopify_headers
	method = 'GET'
	edge = '/admin/orders/{order_id}/transactions.json'.format(order_id=order_id)
	url = shop_url + edge
	response = request_(method, url, headers, auth=(api_key, password), debug=debug)
	return response

def capture_transaction(shop_url, api_key, password, order_id, debug=False):
	headers = shopify_headers
	method = 'POST'
	edge = '/admin/orders/{order_id}/transactions.json'.format(order_id=order_id)
	url = shop_url + edge
	body = {
	  "transaction": {
	    "kind": "capture"
	  }
	}
	response = request_(method, url, headers, json=body, auth=(api_key, password), debug=debug)
	return response

def update_order(shop_url, api_key, password, order_id, params, debug=False):
	headers = shopify_headers
	method = 'PUT'
	edge = '/admin/orders/{order_id}.json'.format(order_id=order_id)
	url = shop_url + edge
	response = request_(method, url, headers, json=params, auth=(api_key, password), debug=debug)
	return response

def fulfill_order(shop_url, api_key, password, order_id, debug=False):
	headers = shopify_headers
	method = 'POST'
	params = 	{'fulfillment': {
					'tracking_number': None,
					'notify_customer': False
					}
			  	}
	edge = '/admin/orders/{order_id}/fulfillments.json'.format(order_id=order_id)
	url = shop_url + edge
	response = request_(method, url, headers, json=params, auth=(api_key, password), debug=debug)
	return response

def process_customer_orders(shop_url, api_key, password, shopify_customer_id, cust_orders, debug=False):
	headers = shopify_headers

	stripe_customer_id = None
	amount_to_charge = 0
	currency = 'USD'

	charge = None
	error_code = None
	failure_message = None
	status_code = None

	for order in cust_orders:
		
		order_status = order['financial_status']
		
		if order_status != 'paid':
			amount_to_charge += int(100 * float(order['total_price_usd']))
			shopify_order_id = order['id']

		if stripe_customer_id is None:
			stripe_customer_id = order.get('stripe_customer_id')

	if stripe_customer_id and amount_to_charge > 0:
		charge = create_charge(
			stripe_customer_id=stripe_customer_id,
			amount = amount_to_charge,
			currency = currency,
			shopify_customer_id = shopify_customer_id,
			shopify_order_id = shopify_order_id,
			debug = debug)
		error_code = charge.get('data',{}).get('error',{}).get('code')
		if error_code:
			failure_message = error_code.replace('_', ' ').title()
		status_code = charge['status_code']

	### Update Shopify
	for order in cust_orders:
		shopify_order_id = order['id']
		order_body = {'order': {'id': shopify_order_id}}

		if stripe_customer_id is None:
			tags = 'Payment Failed, No Payment Info'
			order_body['order']['tags'] = tags
		elif status_code == requests.codes.ok:
			transaction = capture_transaction(shop_url, api_key, password, shopify_order_id, debug=debug)
			# fulfillment = fulfill_order(shop_url, api_key, password, shopify_order_id, debug=debug)
		else:
			tags = 'Payment Failed'
			if failure_message:
				tags = tags + ', ' + failure_message
			order_body['order']['tags'] = tags

		updated_order = update_order(shop_url, api_key, password, shopify_order_id, order_body, debug=debug)

	return status_code

########################################################################

debug = True
test_customer_ids = []

customer_orders = fetch_customer_orders(shop_url, shopify_api_key, shopify_password, debug=debug)

for customer_id, cust_orders in customer_orders.iteritems():
	if customer_id in test_customer_ids or test_customer_ids == []:
		processed = process_customer_orders(shop_url=shop_url,
										api_key=shopify_api_key,
										password=shopify_password,
										shopify_customer_id=customer_id,
										cust_orders=cust_orders,
										debug=debug)




