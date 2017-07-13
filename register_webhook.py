
import requests
import json

# Shopify Credentials
shop_url = 'https://tillivery.myshopify.com'
api_key = '642c1f9c3ed33035ea2a623ad970d52c'
password = '0e3ea297e2e7ffde0634d0ecb28413ac'


## DELETE 
# edge = '/admin/webhooks/{webhook_id}.json'.format(webhook_id='507839951')
# response = requests.delete(shop_url + edge , headers={'Content-Type': 'application/json'}, auth=(api_key, password))
# print response


## CREATE
payload = {
    "webhook": {
        "topic": "customers/update",
        "address": "https://hooks.zapier.com/hooks/catch/2280294/52b9ri/",
        "format": "json",
        "metafield_namespaces": ["customer_attribute"]
        }
    }

edge = '/admin/webhooks.json'
response = requests.post(shop_url + edge, headers={'Content-Type': 'application/json'}, auth=(api_key, password), json=payload)
print response
print response.json()

# {u'webhook': {u'metafield_namespaces': [u'customer_attribute'], u'format': u'json', u'fields': [], u'created_at': u'2017-05-18T02:11:20-04:00', u'updated_at': u'2017-05-18T02:11:20-04:00', u'topic': u'customers/update', u'address': u'https://hooks.zapier.com/hooks/catch/2238730/9u3gwn/', u'id': 486299535}}