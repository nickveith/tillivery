import stripe
stripe.api_key = "sk_test_7TamteMMGJMRuCgte3bjzCq9"

# list charges
stripe.Customer.create(description='Generated using Stripe Python Library', metadata={'Name':'Nick'})

# retrieve single charge
# stripe.Charge.retrieve("ch_1A2PUG2eZvKYlo2C4Rej1B9d")