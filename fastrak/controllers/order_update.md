##Order Update Api Reference:
    ###Available fields to be updated:
        (pickup_address,delivery_address,payment_method,is_pos_payment,
         shipping_fees,money_collected,weight)

####Addresses:
can be edited at any level (on_pickup,on_delivery,on_credit)

#### payment_method (on_pickup,on_delivery,on_credit)
can only be edited as long as the order is not picked-up yet

### is_pos_payment (yes/no):
if order is on_pickup can be edited as long as the order is not picked-up
if order is on_delivery can be edited as long as the order is not yet delivered

### money_collected:
can be edited as long as the money_collection_entry is not created (order is not yet delivered)

the money_collection_entry is created once order is marked as delivered (by calling the api confirm-order-money-collection : collection_type->money_collection)

### weight & shipping_fees & discount:
if order is on_pickup it will be available to edit as long as the order is not yet picked-up
if order is on_delivery or on_credit can be edited as long as the order is not yet delivered

##Important Note:
the payment_method parameter should not be sent to the api once the order is 
picked-up otherwise it will throw validation error and none of the required fields to update will be done

        
