import json
import urlparse

input_data = {
    "body": '{"customer":{"id":5824530511},"line_items":[{"variant_id":"44167873743","quantity":"1"},{"variant_id":"44167847055","quantity":"1"},{"variant_id":"44167851727","quantity":"1"},{"variant_id":"44167843023","quantity":"1"},{"variant_id":"44167852751","quantity":"1"}],"use_customer_default_address":"true"}'
    }
output = {}

###########################################################################

parsed_input_data = json.loads(input_data['body'])

customer = parsed_input_data.get('customer')
lineitems = parsed_input_data.get('line_items')
use_customer_default_address = parsed_input_data.get('use_customer_default_address')

# for base_key in body_dict.keys():
#     value = body_dict[base_key]
#     if '[' in base_key:
#         # item is list
#         key_array = base_key.split('[')
#         parent_key = key_array[0]
#         if parent_key == 'line_items':
#             position = int(key_array[1].strip(']'))
#             child_key = key_array[2].strip(']')
#             line_items = parsed_input_data.get('line_items')
#             if line_items is None:
#                 parsed_input_data['line_items'] = []
#                 line_items = parsed_input_data['line_items']
#             if position > len(line_items):
#                 line_items.append({child_key: value})
#     else:
#         parsed_input_data[base_key] = body_dict[base_key][0]

# print parsed_input_data