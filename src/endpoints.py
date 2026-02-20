"""
API endpoint constants.

!! IMPORTANT !!
These are PLACEHOLDER endpoints. They will NOT work until you map
the real API endpoints using Chrome DevTools.

See: docs/ENDPOINT_MAPPING.md for instructions.
"""

# Base URL
BASE_URL = "https://www.pokemoncenter.com"

# =============================================================================
# STOCK CHECKING
# =============================================================================
# This endpoint should return product availability/inventory status.
# Look for requests when viewing a product page.
#
# Expected response structure:
# {
#     "status": "IN_STOCK" | "OUT_OF_STOCK",
#     "quantity": 10,
#     ...
# }
STOCK_CHECK = "/api/product/{product_id}/availability"

# What status value indicates in-stock?
STOCK_STATUS_KEY = "status"
STOCK_IN_STOCK_VALUE = "IN_STOCK"


# =============================================================================
# CART OPERATIONS
# =============================================================================
# Add to cart endpoint (POST)
# Captured when clicking "Add to Cart" button
CART_ADD = "/api/cart/add"

# View cart endpoint (GET)
CART_VIEW = "/api/cart"

# Clear cart (optional)
CART_CLEAR = "/api/cart/clear"


# =============================================================================
# CHECKOUT FLOW
# =============================================================================
# These endpoints are hit sequentially during checkout.

# Initialize checkout session
CHECKOUT_INIT = "/api/checkout"

# Set shipping address
CHECKOUT_SHIPPING = "/api/checkout/shipping"

# Set payment method
CHECKOUT_PAYMENT = "/api/checkout/payment"

# Submit final order
CHECKOUT_SUBMIT = "/api/checkout/submit"

# Order confirmation
ORDER_CONFIRM = "/api/order/{order_id}"


# =============================================================================
# PAYLOAD TEMPLATES
# =============================================================================
# These are example structures. Update based on actual API payloads.

def cart_add_payload(product_id: str, size: str, quantity: int = 1) -> dict:
    """Build add-to-cart payload."""
    return {
        "productId": product_id,
        "size": size,
        "quantity": quantity,
        # Add other required fields here after mapping
    }


def shipping_payload(profile) -> dict:
    """Build shipping address payload."""
    return {
        "address": {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "line1": profile.address1,
            "line2": profile.address2,
            "city": profile.city,
            "state": profile.state,
            "postalCode": profile.zip_code,
            "country": profile.country,
            "phone": profile.phone,
        },
        "email": profile.email,
    }


def payment_payload(profile) -> dict:
    """Build payment method payload."""
    # NOTE: Real sites often tokenize card data.
    # This may need to be adjusted based on how the site handles payments.
    return {
        "payment": {
            "cardNumber": profile.card_number,
            "expirationDate": profile.card_exp,
            "cvv": profile.card_cvv,
        },
        "billingAddress": {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "line1": profile.address1,
            "city": profile.city,
            "state": profile.state,
            "postalCode": profile.zip_code,
            "country": profile.country,
        },
    }


def url(endpoint: str, **kwargs) -> str:
    """Build full URL from endpoint template."""
    return BASE_URL + endpoint.format(**kwargs)
