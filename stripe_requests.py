
import requests
import urllib
import sys
import datetime

def pretty_print_POST(req):
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

###########################################################################


input_data = {
	'shopify_customer_id': '5824530511',
	'first_name': None,
	'last_name': None,
	'email': 'nick@brightblackbox.com',
	'stripe_token': 'tok_1ALfNPDsSqQm8NKrpwf08iFm',
	'stripe_customer_id': None,
	'stripe_api_key': 'sk_test_7TamteMMGJMRuCgte3bjzCq9'
	}

metafields_new = []

output = {}

##################################################################
### SET STRIPE VALUES

protocol = 'https://'
base_url = 'api.stripe.com/v1/'

api_key = input_data['stripe_api_key']
headers = {
	'Authorization': 'Bearer %s' % (api_key,),
	'content_type': 'application/x-www-form-urlencoded'
	}

##################################################################
### CREATE CUSTOMER IN STRIPE IF NO ID ON CUSTOMER IN SHOPIFY

stripe_customer_id = input_data.get('stripe_customer_id')
stripe_token = input_data.get('stripe_token')

metadata = {
	'first_name': input_data.get('first_name'),
	'last_name': input_data.get('last_name'),
	'email': input_data.get('email'),
	'shopify_customer_id': input_data.get('shopify_customer_id')
	}

for mk in metadata.keys():
	if metadata[mk] is None:
		del metadata[mk]

if stripe_customer_id is None or stripe_customer_id == '':

	params = {
		'description': 'Tillivery Customer'
		}
	if metadata != {}:
		params['metadata'] = metadata

	post_data = urllib.urlencode(list(_api_encode(params or {})))

	edge = 'customers'
	url = ''.join([protocol,base_url,edge])
	print url

	r = requests.Request('POST', url, headers=headers, data=post_data)
	prepared = r.prepare()
	pretty_print_POST(prepared)

	s = requests.Session()
	response = s.send(prepared)
	record = response.json()

	print response
	print record

	stripe_customer_id = record['id']

	metafields_new.append({
			'key': 'stripe-customer',
			'namespace': 'customer_attribute',
			'value': stripe_customer_id,
			'value_type': 'string'
		})

##################################################################
### CREATE CARD FOR CUSTOMER AND SET AS DEFAULT FOR CUSTOMER

if stripe_token and stripe_customer_id is not None and stripe_customer_id != '':
	
	params = {
		'source': stripe_token
		}
	if metadata != {}:
		params['metadata'] = metadata

	post_data = urllib.urlencode(list(_api_encode(params or {})))

	edge = 'customers/{customer_id}/sources'.format(customer_id=stripe_customer_id)
	url = ''.join([protocol,base_url,edge])

	r = requests.Request('POST', url, headers=headers, data=post_data)
	prepared = r.prepare()
	pretty_print_POST(prepared)

	s = requests.Session()
	response = s.send(prepared)
	record = response.json()

	print response
	print record

	card_id = record['id']

	metafields_new.append({
			'key': 'stripe-token',
			'namespace': 'customer_attribute',
			'value': None,
			'value_type': 'string'
		})

	metafields_new.append({
			'key': 'card-id',
			'namespace': 'customer_attribute',
			'value': card_id,
			'value_type': 'string'
		})


	metafields_new.append({
			'key': 'credit-card-provider',
			'namespace': 'customer_attribute',
			'value': record['brand'],
			'value_type': 'string'
		})

	metafields_new.append({
			'key': 'expiration-month',
			'namespace': 'customer_attribute',
			'value': record['exp_month'],
			'value_type': 'string'
		})

	metafields_new.append({
			'key': 'expiration-year',
			'namespace': 'customer_attribute',
			'value': record['exp_year'],
			'value_type': 'string'
		})

	metafields_new.append({
			'key': 'last-four',
			'namespace': 'customer_attribute',
			'value': record['last4'],
			'value_type': 'string'
		})

	### SET DEFAULT SOURCE FOR CUSTOMER

	params = {
		'default_source': card_id
		}
	post_data = urllib.urlencode(list(_api_encode(params or {})))

	edge = 'customers/{customer_id}'.format(customer_id=stripe_customer_id)
	url = ''.join([protocol,base_url,edge])
	print url

	r = requests.Request('POST', url, headers=headers, data=post_data)
	prepared = r.prepare()
	pretty_print_POST(prepared)

	s = requests.Session()
	response = s.send(prepared)
	record = response.json()

	print response
	print record

##################################################################
### UPDATE SHOPIFY CUSTOMER METADATA WITH STRIPE CUSTOMER ID

if metafields_new != []:

	import requests
	import json

	# Shopify Credentials
	shop_url = 'https://tillivery-test.myshopify.com'
	api_key = '5b5447ed911da3f281eebb929efdb092'
	password = 'ef67f788a3a1266d4461439684a4a841'

	# Accept Inputs
	shopify_customer_id = input_data.get('shopify_customer_id')

	### CHECK IF METAFIELD EXISTS
	edge = '/admin/customers/{customer_id}/metafields.json'.format(customer_id=shopify_customer_id)
	response = requests.get(shop_url + edge, headers={'Content-Type': 'application/json'}, auth=(api_key, password))

	print response
	metafields = response.json()['metafields']

	### UPDATE STRIPE DATA ON SHOPIFY CUSTOMER
	edge = '/admin/customers/{customer_id}.json'.format(customer_id=shopify_customer_id)

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
			response = requests.put(shop_url + edge, headers={'Content-Type': 'application/json'}, auth=(api_key, password), json=payload)
			print response
			print response.json()
		elif value is None and metafield_id:
			edge = '/admin/metafields/{metafield_id}.json'.format(metafield_id=metafield_id)
			response = requests.delete(shop_url + edge, headers={'Content-Type': 'application/json'}, auth=(api_key, password))
			print response

	### OUTPUT FOR ZAPIER
	output.update({})