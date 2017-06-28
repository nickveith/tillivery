
import requests
import json

###########################################################################

input_data = {
	"body": '{"customer":{"id":5824530511},"order_total":600,"line_items":[{"variant_id":"44167873423","quantity":"1"}],"use_customer_default_address":"true"}'
	}
output = {}

parsed_input_data = json.loads(input_data['body'])
customer = parsed_input_data.get('customer',{})
customer_id = customer.get('id')
order_total = parsed_input_data.get('order_total',"0")
lineitems = parsed_input_data.get('line_items',[])
use_customer_default_address = parsed_input_data.get('use_customer_default_address')

###########################################################################

# Shopify Credentials
shop_url = 'https://tillivery.myshopify.com'
api_key = '642c1f9c3ed33035ea2a623ad970d52c'
password = '0e3ea297e2e7ffde0634d0ecb28413ac'
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

def tag_customer (customer, tag, api_key, password, debug=False):
	shopify_customer_id = customer['id']
	headers = shopify_headers
	method = 'GET'
	edge = '/admin/customers/{customer_id}.json'.format(customer_id=shopify_customer_id)
	url = shop_url + edge
	response = request_(method=method, url=url, headers=headers, auth=(api_key, password), debug=debug)

	customer = response['data']['customer']

	tags = [existing_tag.strip() for existing_tag in customer['tags'].split(',')]
	print tags

	message = 'Tag Exists'

	if tag not in tags:
		tags.append(tag)
		tag_string = ', '.join(tags)
		method = 'PUT'
		edge = '/admin/customers/{customer_id}.json'.format(customer_id=shopify_customer_id)
		url = shop_url + edge
		params = {
				"customer": {
					"id": customer_id,
					"tags": tag_string
					}
				}
		response = request_(method=method, url=url, headers=headers, json=params, auth=(api_key, password), debug=debug)
		message = 'Tag Added'

	return message

###########################################################################

order = create_order(customer, order_total, lineitems, use_customer_default_address, api_key, password, debug)
print order

tag = 'Active Subscriber'
tagged_customer = tag_customer(customer, tag, api_key, password)
print tagged_customer

