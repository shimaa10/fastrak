#Order Api Reference:
    ###Create Bol(Order):
        will be called on creating an order with all required fields
        A- new fields to be sent within the request in addition to the old ones
            
        B- changed fields
            1- 'payment_method':
                add new option 'on_credit' which will be for orders created by business customers

    ###confirm order pickup:
        will be called once driver pickup the order
    ###confirm order delivery:
        will be called once driver handle the order to destionation customer

    ###confirm order money collection:
        added new field collection_type:
            'shipping_fees' -> for orders with payment method 'on_delivery' or 'on_pickup'
            'money_collection'-> for orders with payment method 'on_credit'
            
        A- On Pickup Payment:
            api should be called after the order is confirmed
            with collection_type parameter set to 'shipping_fees'
            

        B- On Delivery Payment:
            1- api should be called after the order is delivered
            with collection_type parameter set to 'shipping_fees'
            2- api should be called after delivery if there is money to be collected
            with collection_type parameter set to 'money_collection'

            

        C- On Credit Payment:
            in this case if there is a money collection then the 
            api should be called after the order is delivered
            (ensure that there is a delviery driver else will raise validation error)
            with collection_type parameter set to 'money_collection'
            NOTE: this call is not permitted at the order draft status
            *-* Payment will be a Manual Handling by accountant
        
    