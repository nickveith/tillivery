
import requests
import urllib
import sys
import datetime

###########################################################################

input_data = {'stripe_api_key': 'sk_test_7TamteMMGJMRuCgte3bjzCq9'}
output = {}

# General Setting
debug = True
currency = 'USD'

# Shopify Setting
shop_url = 'https://tillivery-test.myshopify.com'
shopify_api_key = '5b5447ed911da3f281eebb929efdb092'
shopify_password = 'ef67f788a3a1266d4461439684a4a841'
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
	result['error'] = r.status_code == requests.codes.ok

	records = None
	try:
		result['data'] = r.json()
	except:
		pass

	if debug:
		print result

	return result

def fetch_draft_orders (shop_url, api_key, password, debug):
	headers = shopify_headers
	params = {"status": "open"}

	method = 'GET'
	edge = '/admin/draft_orders.json'
	url = shop_url + edge
	response = request_(method, url, headers, params=params, auth=(api_key, password), debug=True)
	draft_orders = response['data']['draft_orders']

	### Set Stripe Customer ID on Orders
	for draft in draft_orders:
		customer_id = draft.get("customer", {}).get('id')
		draft['shopify_customer_id'] = customer_id

		## Get Customer Metadata
		stripe_customer_id = None
		method = 'GET'
		edge = '/admin/customers/{customer_id}/metafields.json'.format(customer_id = customer_id)
		url = shop_url + edge
		response = request_(method, url, headers, params=params, auth=(api_key, password), debug=True)
		for metafield in response['data']['metafields']:
			namespace = metafield['namespace']
			key = metafield['key']
			if namespace == 'customer_attribute' and key == 'stripe-customer':
				stripe_customer_id = metafield['value']
				break

		draft['stripe_customer_id'] = stripe_customer_id

	return draft_orders

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

def create_charge (stripe_customer_id, amount, currency, shopify_customer_id, shopify_draft_order_id, debug=False):

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
			'shopify_draft_order_id': shopify_draft_order_id
			}
		}

	post_data = urllib.urlencode(list(_api_encode(params or {})))
	url = base_url + edge
	records = request_(method, url, headers, data=post_data, debug=debug)

	return records

def update_draft_order(draft_order_id, params):
	headers = shopify_headers
	method = 'PUT'
	edge = '/admin/draft_orders/{draft_order_id}.json'.format(draft_order_id=draft_order_id)
	url = shop_url + edge
	response = request_(method, url, headers, json=params, auth=(api_key, password), debug=debug)
	return response

def complete_draft_order(shop_url, api_key, password, draft_order_id, failure_message, debug=False):
	headers = shopify_headers
	payment_pending = False

	# Tag orders with payment issues
	if failure_message:
		params = {"tags": 'Failed Payment, ' + failure_message}
		response = update_draft_order(draft_order_id, params)

	method = 'PUT'
	edge = '/admin/draft_orders/{draft_order_id}/complete.json'.format(draft_order_id=draft_order_id)
	url = shop_url + edge
	params = {
		"payment_pending": payment_pending
	}
	response = request_(method, url, headers, json=params, auth=(api_key, password), debug=debug)	
	return response 

def process_order (shop_url, api_key, password, draft_order, debug=False):
	headers = shopify_headers
	params = {"status": "open"}

	stripe_customer_id = draft_order['stripe_customer_id']
	amount = int(100 * float(draft_order['total_price']))
	currency = 'USD'
	shopify_customer_id = draft_order['shopify_customer_id']
	shopify_draft_order_id = draft_order['id']

	charge = create_charge(
		stripe_customer_id=stripe_customer_id,
		amount = amount,
		currency = currency,
		shopify_customer_id = shopify_customer_id,
		shopify_draft_order_id = shopify_draft_order_id,
		debug = debug)

	failure_message = charge['data']['failure_message']

	# method = 'GET'
	# edge = '/admin/draft_orders.json'
	# url = shop_url + edge
	# response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)

########################################################################

# draft_orders = fetch_draft_orders(shop_url, shopify_api_key, shopify_password, debug)

# for draft_order in draft_orders:
# 	print draft_order
# 	close_order = process_order(shop_url, shopify_api_key, shopify_password, draft_order, debug)
# 	break

print complete_draft_order(
	shop_url,
	shopify_api_key,
	shopify_password,
	draft_order_id='67900367',
	failure_message=None,
	debug=False)








