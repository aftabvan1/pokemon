"""
Pokemon Center API endpoints (TPCI E-commerce).

Discovered via browser DevTools interception. The site uses a custom
TPCI (The Pokemon Company International) e-commerce API layer.

Bot protection: Imperva, Reese84, DataDome, CloudFront
"""

# =============================================================================
# BASE CONFIGURATION
# =============================================================================
BASE_URL = "https://www.pokemoncenter.com"
TPCI_API = "/tpci-ecommweb-api"  # The actual e-commerce API
LOCALE = "en-ca"
STORE_SCOPE = "pokemon-ca"

# =============================================================================
# PRODUCT DATA
# =============================================================================
# Product page URL format
PRODUCT_PAGE = "/en-ca/product/{product_id}"

# The product page likely has JSON data embedded with the encoded variant ID
# This encoded ID (e.g., 'qgqvhkjxgazs2ojwgm4dc=') is needed for cart operations

# =============================================================================
# STOCK CHECKING
# =============================================================================
# TODO: Find actual stock check endpoint via DevTools
# The product page likely fetches availability from somewhere
STOCK_CHECK = f"{TPCI_API}/product/{{product_id}}/availability"

# =============================================================================
# CART OPERATIONS (VERIFIED via DevTools intercept)
# =============================================================================
# Cart-add: POST /tpci-ecommweb-api/cart/add-product/{encoded_product_id}
# Returns 201 Created on success
CART_ADD = f"{TPCI_API}/cart/add-product"  # Append /{product_id} at runtime
CART_VIEW = f"{TPCI_API}/cart"
CART_CLEAR = f"{TPCI_API}/cart/clear"


# =============================================================================
# CHECKOUT FLOW
# =============================================================================
# TODO: These endpoints need to be discovered via DevTools
# May use TPCI_API or a different checkout service
CHECKOUT_INIT = f"{TPCI_API}/checkout"
CHECKOUT_SHIPPING = f"{TPCI_API}/checkout/shipping"
CHECKOUT_PAYMENT = f"{TPCI_API}/checkout/payment"
CHECKOUT_SUBMIT = f"{TPCI_API}/checkout/submit"
ORDER_CONFIRM = f"{TPCI_API}/orders/{{order_id}}"


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

def cart_add_payload(quantity: int = 1, clobber: bool = False) -> dict:
    """
    Build add-to-cart payload (discovered via DevTools).

    The product ID goes in the URL path, not the body.
    POST /tpci-ecommweb-api/cart/add-product/{encoded_product_id}

    Args:
        quantity: Number of items to add
        clobber: If True, replace existing item in cart
    """
    return {
        "clobber": clobber,
        "quantity": quantity,
        "configuration": {},
        "dynamicAdd": False,
    }


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


def cart_add_url(encoded_product_id: str) -> str:
    """
    Build cart-add URL with product ID in path.

    The encoded_product_id is a base64-like string (e.g., 'qgqvhkjxgazs2ojwgm4dc=')
    that identifies the product variant.
    """
    return f"{BASE_URL}{CART_ADD}/{encoded_product_id}"


def product_referer(product_id: str, slug: str = "") -> str:
    """Build product page referer URL."""
    if slug:
        return f"{BASE_URL}/en-ca/product/{product_id}/{slug}"
    return f"{BASE_URL}/en-ca/product/{product_id}"
