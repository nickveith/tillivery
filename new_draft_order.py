
import requests
import json

###########################################################################

input_data = {
	"body": '{"customer":{"id":5824530511},"line_items":[{"variant_id":"44167873743","quantity":"1"},{"variant_id":"44167847055","quantity":"1"},{"variant_id":"44167851727","quantity":"1"},{"variant_id":"44167843023","quantity":"1"},{"variant_id":"44167852751","quantity":"1"}],"use_customer_default_address":"true"}'
	}
output = {}

parsed_input_data = json.loads(input_data['body'])
customer = parsed_input_data.get('customer',{})
customer_id = customer.get('id')
lineitems = parsed_input_data.get('line_items',[])
use_customer_default_address = parsed_input_data.get('use_customer_default_address')

###########################################################################

# Shopify Credentials
shop_url = 'https://tillivery-test.myshopify.com'
api_key = '5b5447ed911da3f281eebb929efdb092'
password = 'ef67f788a3a1266d4461439684a4a841'
shopify_headers = {'Content-Type': 'application/json'}
debug = False

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

def fetch_draft_orders (shop_url, api_key, password, debug=False):
	headers = shopify_headers
	params = {"status": "open"}

	method = 'GET'
	edge = '/admin/draft_orders.json'
	url = shop_url + edge
	response = request_(method, url, headers, params=params, auth=(api_key, password), debug=debug)
	draft_orders = response['data']['draft_orders']

	return draft_orders

def create_draft_order (customer, lineitems, use_customer_default_address, api_key, password, debug=False):
	headers = shopify_headers
	method = 'POST'
	edge = '/admin/draft_orders.json'
	url = shop_url + edge
	post_data =  {
		"draft_order": {
			"customer": customer,
			"line_items": lineitems,
			"use_customer_default_address": use_customer_default_address
		}
	}
	response = request_(method=method, url=url, headers=headers, json=post_data, auth=(api_key, password), debug=debug)
	return response

def update_draft_order(draft_order_id, customer, lineitems, use_customer_default_address, api_key, password, debug=False):
	headers = shopify_headers
	method = 'PUT'
	edge = '/admin/draft_orders/{draft_order_id}.json'.format(draft_order_id=draft_order_id)
	url = shop_url + edge
	post_data =  {
		"draft_order": {
			"id": draft_order_id,
			"customer": customer,
			"line_items": lineitems,
			"use_customer_default_address": use_customer_default_address
		}
	}
	response = request_(method, url, headers, json=post_data, auth=(api_key, password), debug=debug)
	return response


###########################################################################

draft_order_id = None
draft_orders = fetch_draft_orders(shop_url, api_key, password, debug)

for draft_order in draft_orders:
	draft_order_customer_id = draft_order['customer']['id']
	if draft_order_customer_id == customer_id:
		draft_order_id = draft_order['id']
		break

if draft_order_id:
	response = update_draft_order(draft_order_id, customer, lineitems, use_customer_default_address, api_key, password, debug)
else:
	response = create_draft_order(customer, lineitems, use_customer_default_address, api_key, password, debug)

print response

