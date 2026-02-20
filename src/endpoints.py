"""
Salesforce Commerce Cloud (SFCC) API endpoints for Pokemon Center.

Based on manual interception research. The site runs on Demandware/SFCC
with Imperva, Reese84, DataDome, and CloudFront protection layers.
"""

# =============================================================================
# BASE CONFIGURATION
# =============================================================================
BASE_URL = "https://www.pokemoncenter.com"
BASE_API = "/site/en-ca/resourceapi"
LOCALE = "en-ca"

# =============================================================================
# STOCK CHECKING
# =============================================================================
# Product availability endpoint (needs field name verification via DevTools)
# Response structure varies - check actual response for correct field
STOCK_CHECK = f"{BASE_API}/products/{{product_id}}/availability"

# Stock response parsing - UPDATE THESE after DevTools verification
# Possible field names (try each until one works):
#   - data["availability"]["orderable"]
#   - data["inventoryStatus"] == "IN_STOCK"
#   - data["available"] == True
#   - data["inStock"] == True
STOCK_STATUS_KEY = "availability"  # Top-level key (placeholder)
STOCK_IN_STOCK_VALUE = True        # Expected value when in stock


# =============================================================================
# CART OPERATIONS
# =============================================================================
# SFCC uses same endpoint for GET (view) and POST (add)
CART_ADD = f"{BASE_API}/cart"   # POST
CART_VIEW = f"{BASE_API}/cart"  # GET
CART_CLEAR = f"{BASE_API}/cart" # DELETE (if supported)


# =============================================================================
# CHECKOUT FLOW
# =============================================================================
# Standard SFCC checkout sequence
CHECKOUT_INIT = f"{BASE_API}/checkout"
CHECKOUT_SHIPPING = f"{BASE_API}/checkout/shipping"
CHECKOUT_PAYMENT = f"{BASE_API}/checkout/payment"
CHECKOUT_SUBMIT = f"{BASE_API}/checkout/submit"
ORDER_CONFIRM = f"{BASE_API}/orders/{{order_id}}"


# =============================================================================
# REQUIRED COOKIES (for bot protection)
# =============================================================================
# These must all be present from a real browser session
REQUIRED_COOKIES = [
    "auth",           # JWT authentication (JSON object containing access_token)
    "reese84",        # Bot protection token
    "datadome",       # Bot detection
    "visid_incap_2682446",  # Imperva visitor ID
    "nlbi_2682446",         # Imperva load balancer
    # "incap_ses_*",        # Imperva session (wildcard)
    "SSID",           # Salesforce session ID
    "SSSC",           # Salesforce session cookie
    "SSOD",           # Salesforce session data
    "correlationId",  # Request correlation
]


# =============================================================================
# PAYLOAD TEMPLATES
# =============================================================================

def cart_add_payload(product_id: str, size: str = "", quantity: int = 1) -> dict:
    """
    Build add-to-cart payload.

    SFCC typically uses a simple structure. The 'size' field may not be needed
    if it's encoded in the product_id variant.
    """
    payload = {
        "productId": product_id,
        "quantity": quantity,
    }
    # Only add size if provided (some products don't have sizes)
    if size:
        payload["size"] = size
    return payload


def shipping_payload(profile) -> dict:
    """Build shipping address payload for SFCC."""
    return {
        "address": {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "address1": profile.address1,
            "address2": profile.address2 or "",
            "city": profile.city,
            "stateCode": profile.state,
            "postalCode": profile.zip_code,
            "countryCode": profile.country,
            "phone": profile.phone,
        },
        "email": profile.email,
    }


def payment_payload(profile) -> dict:
    """
    Build payment method payload.

    NOTE: SFCC often tokenizes card data via a payment processor.
    This structure may need adjustment based on actual checkout flow.
    """
    return {
        "paymentInstrument": {
            "cardNumber": profile.card_number,
            "expirationMonth": profile.card_exp.split("/")[0] if "/" in profile.card_exp else profile.card_exp[:2],
            "expirationYear": profile.card_exp.split("/")[1] if "/" in profile.card_exp else profile.card_exp[2:],
            "securityCode": profile.card_cvv,
        },
        "billingAddress": {
            "firstName": profile.first_name,
            "lastName": profile.last_name,
            "address1": profile.address1,
            "city": profile.city,
            "stateCode": profile.state,
            "postalCode": profile.zip_code,
            "countryCode": profile.country,
        },
    }


def url(endpoint: str, **kwargs) -> str:
    """Build full URL from endpoint template."""
    return BASE_URL + endpoint.format(**kwargs)


def product_referer(product_id: str, slug: str = "") -> str:
    """Build product page referer URL."""
    if slug:
        return f"{BASE_URL}/en-ca/product/{product_id}/{slug}"
    return f"{BASE_URL}/en-ca/product/{product_id}"
