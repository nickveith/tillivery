
import requests
import urllib
import sys
import datetime
from math import ceil

###########################################################################

input_data = {'stripe_api_key': 'sk_test_7TamteMMGJMRuCgte3bjzCq9'}
output = {}

# General Setting
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

def fetch_subscribers (shop_url, api_key, password, params={}, debug=False):
	headers = shopify_headers
	
	method = 'GET'
	edge = '/admin/customers/count.json'
	url = shop_url + edge
	response = request_(method, url, headers, auth=(api_key, password), debug=debug)
	count = response.get('data',{}).get('count',0)

	method = 'GET'
	edge = '/admin/customers/search.json'
	url = shop_url + edge
	params = {'query': 'Active Subscriber'}

	limit = 250
	total_pages = max(ceil(count/limit),1)
	subscribers = []
	for page in xrange(1, int(total_pages + 1)):
		params['page'] = page
		params['limit'] = limit
		response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
		subscribers += response.get('data',{}).get('customers')
	
	return subscribers

def fetch_orders (shop_url, api_key, password, params={"status": "open", "financial_status": "pending"}, debug=False):
	params['page'] = 1
	params['limit'] = 250

	headers = shopify_headers
	method = 'GET'
	edge = '/admin/orders.json'
	url = shop_url + edge
	response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
	orders = response['data']['orders']
	return orders

def fetch_variants (shop_url, api_key, password, params={}, debug=False):
	variants = {}

	headers = shopify_headers

	method = 'GET'
	edge = '/admin/products/count.json'
	url = shop_url + edge
	response = request_(method, url, headers, auth=(api_key, password), debug=debug)
	product_count = response.get('data',{}).get('count',0)

	method = 'GET'
	edge = '/admin/products.json'
	url = shop_url + edge
	products = []

	limit = 250
	total_pages = max(ceil(product_count/limit),1)
	for page in xrange(1, int(total_pages + 1)):
		params['page'] = page
		params['limit'] = limit
		response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
		products += response.get('data',{}).get('products')

	for product in products:
		for v in product['variants']:
			variant_id = v['id']
			variant_dict = dict(product)
			del variant_dict['variants']
			variant_dict['variant'] = v
			variants[variant_id] = variant_dict

	return variants

def create_order (customer, order_total, lineitems, use_customer_default_address, api_key, password, debug=False):
	headers = shopify_headers
	method = 'POST'
	edge = '/admin/orders.json'
	url = shop_url + edge
	amount = 0.00
	if order_total:
		amount = round(float(order_total) / 100,2)
	post_data =  {
		"order": {
			"customer": customer,
			"line_items": lineitems,
			"use_customer_default_address": use_customer_default_address,
			"financial_status": "pending",
			"transactions": [{
				"kind": "authorization",
				"status": "success",
				"amount": amount
				}]
		}
	}
	response = request_(method=method, url=url, headers=headers, json=post_data, auth=(api_key, password), debug=debug)
	return response

def chefs_choice(variant_dict):

	### Define Chef's Choice
	chefs_choice = {}
	added_items = {'entree': 0, 'soup': 0, 'salad': 0, 'bread': 0}
	for variant_id in variant_dict.keys():
		product = variant_dict[variant_id]
		product_type = product['product_type'].lower()
		product_id = product['id']
		tags = product['tags']
		max_items = {'entree': 2, 'soup': 1, 'salad': 1, 'bread': 1}
		if 'chef\'s choice' in tags.lower():
			print added_items
			items_added = added_items[product_type]
			items_max = max_items[product_type]
			if  items_added < items_max:
				items_added += 1
				line_item = { 
					"variant_id": variant_id,
					"quantity": 1,
					"properties": [{"name": "product_type", "value": product_type}]
					}
				key = product_type

				if key == 'entree':
					key = 'entree' + str(items_added)

				chefs_choice[key] = line_item
				added_items[product_type] = items_added
	return chefs_choice

def process_default_order(base_chefs_choice, customer, order_dict, variant_dict):
	chefs_choice = dict(base_chefs_choice)
	email = customer['email']
	customer_id = customer['id']
	max_items = {'entree': 2, 'soup': 1, 'salad': 1, 'bread': 1, 'add-on': 999}
	added_items = {'entree': 0, 'soup': 0, 'salad': 0, 'bread': 0, 'add-on': 0}

	customer_orders = order_dict.get(customer_id, [])

	for customer_order in customer_orders:
		customer_order_id = customer_order['id']
		lineitems = customer_order['line_items']
		for lineitem in lineitems:
			variant_id = lineitem['variant_id']
			product_id = lineitem['product_id']
			variant = variant_dict[variant_id]
			product_type = variant['product_type'].lower()
			variant_id = lineitem['variant_id']
			quantity = lineitem['quantity']
			for i in xrange(1, int(quantity)+1):
				if product_type in ['entree', 'soup', 'salad', 'bread', 'add-on']:
					items_added = added_items[product_type]
					items_max = max_items[product_type]

					items_added += 1
					key = product_type
					if key == 'entree':
						key = 'entree' + str(items_added)

					if key in chefs_choice.keys():
						del chefs_choice[key]

					added_items[product_type] = items_added

		if chefs_choice.keys() == []:
			break

	if chefs_choice == {}:
		customer_default_order = None
	else:
		customer_default_order = chefs_choice

	return customer_default_order

########################################################################

debug = False
test_customer_ids = []

subscribers = fetch_subscribers(shop_url, shopify_api_key, shopify_password, debug=debug)
subscribers = [subscriber for subscriber in subscribers if subscriber['id'] in test_customer_ids or test_customer_ids == []]

print len(subscribers)

orders = fetch_orders(shop_url, shopify_api_key, shopify_password, debug=debug)
variant_dict = fetch_variants(shop_url, shopify_api_key, shopify_password, debug=debug)

print len(variant_dict)

order_dict = {}
for order in orders:
	customer_id =  order['customer']['id']
	customer_orders = order_dict.get(customer_id)
	if customer_orders is None:
		customer_orders = []
	customer_orders.append(order)
	order_dict[customer_id] = customer_orders

base_chefs_choice = chefs_choice(variant_dict)

print base_chefs_choice

# ### Prepare Default Orders
for customer in subscribers:
	customer_id = customer['id']
	print customer_id
	default_order = process_default_order(base_chefs_choice, customer, order_dict, variant_dict)
	print default_order
	if default_order:
		lineitems_dict = {}
		for box_item in default_order.keys():
			variant = default_order[box_item]
			variant_id = variant['variant_id']
			quantity = variant['quantity']
			lineitem_quantity = lineitems_dict.get(variant_id, 0)
			if lineitem_quantity:
				quantity += lineitem_quantity
			lineitems_dict[variant_id] = {'variant_id': variant_id, 'quantity': quantity}

		lineitems = [value for key, value in lineitems_dict.iteritems()]
		use_customer_default_address = True
		order_total = 0

		for lineitem in lineitems:
			variant_id = lineitem['variant_id']
			quantity = lineitem['quantity']
			variant = variant_dict[variant_id]
			default_price = float(variant.get('variant', {}).get('price',0))
			lineitem_price = float(quantity) * default_price
			order_total += lineitem_price

		order_total = int(order_total * 100)

		if lineitems != []:
			order = create_order(customer, 
								order_total, 
								lineitems, 
								use_customer_default_address, 
								shopify_api_key, 
								shopify_password, 
								debug=False)
			print order
























