
import requests
import urllib
import sys
import datetime
import json

def prettyprint_(req):
	"""
	At this point it is completely built and ready
	to be fired; it is "prepared".

	However pay attention at the formatting used in 
	this function because it is programmed to be pretty 
	printed and may differ from the actual request.
	"""
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

def remove_empty_keys(dict_):
	for key in dict_.keys():
		if dict_[key] is None:
			del dict_[key]
	return dict_

def create_stripe_customer(input_data, debug=False):
	
	first_name = input_data.get('first_name')
	last_name = input_data.get('last_name')
	email = input_data.get('email')

	metadata = {
		'first_name': first_name,
		'last_name': last_name,
		'email': email,
		'shopify_customer_id': input_data.get('shopify_customer_id')
		}		
	params = {'description': '{first_name} {last_name}'.format(first_name=first_name, last_name=last_name).strip(),
	         	'email': email
	         }

	params['metadata'] = remove_empty_keys(metadata)
	post_data = urllib.urlencode(list(_api_encode(params or {})))

	edge = 'customers'
	url = ''.join([base_url,edge])

	record = request_('POST', url, headers=headers, data=post_data, debug=debug)

	try:
		stripe_customer_id = record['data']['id']
		return stripe_customer_id
	except:
		print record
		return None

def set_default_payment(stripe_customer_id, stripe_token, debug=False):
	params = {'source': stripe_token}
	post_data = urllib.urlencode(list(_api_encode(params or {})))
	edge = 'customers/{customer_id}'.format(customer_id=stripe_customer_id)
	url = ''.join([base_url,edge])
	record = request_('POST', url, headers=headers, data=post_data)
	return record

def get_metafields(shopify_customer_id, debug=False):
	edge = '/admin/customers/{shopify_customer_id}/metafields.json'.format(shopify_customer_id=shopify_customer_id)
	record = request_('GET', shopify_store_url + edge, headers={'Content-Type': 'application/json'}, auth=(shopify_api_key, shopify_password),debug=debug)
	
	try:
		metafields = record['data']['metafields']
		return metafields
	except:
		print record
		return None

def update_metafields(shopify_customer_id, metafields_new, debug=False):
	metafields = get_metafields(shopify_customer_id)

	for metafield_new in metafields_new:
		metafield_id = None
		namespace = metafield_new['namespace']
		key = metafield_new['key']
		value = metafield_new['value']

		for metafield in metafields:
			namespace_new = metafield['namespace']
			key_new = metafield['key']
			if namespace == namespace_new and key == key_new:
				metafield_id = metafield['id']
				metafield_new['id'] = metafield_id
				break
				
		payload = {
			"customer": {
				"id": shopify_customer_id,
				"metafields": [metafield_new]
				}
			}

		if value:
			edge = '/admin/customers/{shopify_customer_id}.json'.format(shopify_customer_id=shopify_customer_id)
			response = request_('PUT', shopify_store_url + edge, headers={'Content-Type': 'application/json'}, auth=(shopify_api_key, shopify_password), json=payload, debug=debug)
		elif value is None and metafield_id:
			edge = '/admin/metafields/{metafield_id}.json'.format(metafield_id=metafield_id)
			response = request_('DELETE', shopify_store_url + edge, headers={'Content-Type': 'application/json'}, auth=(shopify_api_key, shopify_password), debug=debug)

	return True

###########################################################################


# input_data = {
# 	'shopify_customer_id': '6404866508',
# 	'first_name': 'Nick',
# 	'last_name': 'Veith',
# 	'email': 'nick@brightblackbox.com',
# 	'stripe_token': 'tok_visa',
# 	'stripe_customer_id': 'cus_AlsRHFTysjW5aj',
# 	'stripe_api_key': 'sk_test_AJT45IWyJqkWpSLnxICAWAb2',
# 	'shopify_store_url': 'https://tillivery.myshopify.com',
# 	'shopify_api_key': '642c1f9c3ed33035ea2a623ad970d52c',
# 	'shopify_password': '0e3ea297e2e7ffde0634d0ecb28413ac'
# 	}
output = {}

##################################################################
### SET CREDENTIALS
##################################################################

# STRIPE
base_url = 'https://api.stripe.com/v1/'

stripe_api_key = input_data['stripe_api_key']
headers = {
	'Authorization': 'Bearer %s' % (stripe_api_key,),
	'content_type': 'application/x-www-form-urlencoded'
	}

# SHOPIFY
shopify_store_url = input_data['shopify_store_url']
shopify_api_key = input_data['shopify_api_key']
shopify_password = input_data['shopify_password']

debug = True

##################################################################
##################################################################

### LOGIC

stripe_customer_id = input_data.get('stripe_customer_id')
stripe_token = input_data.get('stripe_token')
shopify_customer_id = input_data.get('shopify_customer_id')

### CREATE CUSTOMER IN STRIPE IF NO ID ON CUSTOMER IN SHOPIFY
if stripe_customer_id is None:	
	stripe_customer_id = create_stripe_customer(input_data, debug)
	shopify_customer_meta = []
	shopify_customer_meta.append({
			'key': 'stripe-customer',
			'namespace': 'customer_attribute',
			'value': stripe_customer_id,
			'value_type': 'string'
		})
	### UPDATE SHOPIFY CUSTOMER METADATA WITH STRIPE CUSTOMER ID
	response = update_metafields(shopify_customer_id, shopify_customer_meta, debug=debug)

### OTHERWISE UPDATE DEFAULT PAYMENT METHOD FOR CUSTOMER
if stripe_token and stripe_customer_id:
	stripe_customer = set_default_payment(stripe_customer_id, stripe_token)
	print stripe_customer