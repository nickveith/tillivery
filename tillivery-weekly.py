

import datetime
from chefs_choice import run_chefs_choice, remove_customer_tag
from process_orders import run_process_orders, cancel_failed_payments_orders, fulfill_last_weeks_orders

############################################################
# Weekly Tillivery Process
############################################################

# Is Today the Day?
today_is_the_day = False
current_weekday = datetime.datetime.today().weekday()
if current_weekday == 3: # Only run on Thursdays
    today_is_the_day = True


canceled_orders = False
fulfilled_orders = False
chefs_choice = False
processed_orders = True

if today_is_the_day:

    # ## Clear Failed Payment Orders by Cancelling and Refunding orders that are OPEN and UNPAID and TAGGED WITH PAYMENT FAILED -  Payment Failed view in Orders
    # canceled_orders = cancel_failed_payments_orders()
    # print 'canceled_orders', canceled_orders

    # ## Fulfill any orders that are OPEN and PAID and not FULFILLED - Ready to Fulfill view in Orders
    # fulfilled_orders = fulfill_last_weeks_orders()
    # print 'fulfilled_orders', fulfilled_orders

    # ## Verify that Chef's Choice options have been set - Chef's Choice view in products
    # #### This is still manual

    # ## Run Chef's Choice to create default orders for any ACTIVE SUBSCRIBERS that do not have a full box
    # if canceled_orders and fulfilled_orders:
    #     chefs_choice = run_chefs_choice()
    #     print 'chefs_choice', chefs_choice

    # ## Run Process Orders script to aggregate balance per customer and create a charge in stripe
    # if chefs_choice:
    #     processed_orders = run_process_orders()
    #     print 'processed_orders', processed_orders

    # ## Remove Skip Tag from all customers
    if processed_orders:
        tagged_customers = remove_customer_tag(tag='Skip')
        print 'tagged_customers', tagged_customers

## On Friday Retry Payment for Failed Payment Orders