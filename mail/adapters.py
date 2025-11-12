from django.conf import settings

def get_buyer_email(order):
    return order.email

def get_buyer_name(order):
    name = f"{order.first_name} {order.last_name}".strip()
    return name or order.email

def get_order_number(order):
    return str(order.id)

def get_total_display(order):
    total = order.get_total_cost()
    # Pretty currency (2 decimals, thousands comma)
    return f"${float(total):,.2f}"

def get_seller_recipients(order):
    # Send to ops / store inbox; customize if you have vendor per product
    return [getattr(settings, "ORDERS_SELLER_EMAIL", settings.DEFAULT_FROM_EMAIL)]
