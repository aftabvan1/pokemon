# Endpoint Mapping Guide

Before the bot can work, you must manually map the real API endpoints for your target site.

## Why This Is Critical

The bot currently has **placeholder endpoints**. These won't work. You need to intercept the actual API calls the site makes and update `src/endpoints.py`.

---

## Step-by-Step Process

### 1. Open Chrome DevTools

1. Go to [pokemoncenter.com](https://www.pokemoncenter.com)
2. Press `F12` (or right-click → Inspect)
3. Click the **Network** tab
4. Check **Preserve log** (important!)
5. Filter by **Fetch/XHR** (hides images, CSS, etc.)

### 2. Capture Stock Check Endpoint

1. Search for a product
2. Click on a product page
3. Watch the Network tab for requests
4. Look for requests containing:
   - `availability`
   - `inventory`
   - `stock`
   - Product ID in URL

**Record:**
```
Method: GET
URL: https://www.pokemoncenter.com/api/...
Response: { "status": "IN_STOCK" } or similar
```

### 3. Capture Add to Cart Endpoint

1. Click "Add to Cart" on a product
2. Watch for POST requests
3. Look for requests containing:
   - `cart`
   - `add`
   - `basket`

**Record:**
```
Method: POST
URL: https://www.pokemoncenter.com/api/cart/...
Headers:
  - Cookie: (your session cookies)
  - X-CSRF-Token: (if present)
Request Body: { "productId": "...", "quantity": 1, ... }
Response: { "success": true, ... }
```

### 4. Capture Checkout Endpoints

Go through the checkout flow (you don't need to complete the purchase):

1. **Shipping Address**
   - Look for POST to `/checkout/shipping` or similar
   - Record the payload structure

2. **Payment Method**
   - Look for POST to `/checkout/payment` or similar
   - Note: Card details may be tokenized

3. **Order Submit**
   - Look for final POST to `/checkout/submit` or `/order`
   - This is the most critical endpoint

---

## How to Record a Request

For each request, copy these details:

### URL
Right-click the request → Copy → Copy URL

### Headers
Click the request → Headers tab → scroll to Request Headers
Important headers:
- `Cookie`
- `X-CSRF-Token`
- `Authorization`
- `Content-Type`

### Request Body
Click the request → Payload tab (or Request tab)
Copy the JSON payload

### Response
Click the request → Response tab
Note the structure for parsing

---

## Update endpoints.py

After mapping, update `src/endpoints.py`:

```python
# Example - replace with real values
BASE_URL = "https://www.pokemoncenter.com"

# Stock checking
STOCK_CHECK = "/api/v1/products/{product_id}/inventory"

# Cart
CART_ADD = "/api/v1/cart/items"
CART_VIEW = "/api/v1/cart"

# Checkout
CHECKOUT_INIT = "/api/v1/checkout"
CHECKOUT_SHIPPING = "/api/v1/checkout/shipping"
CHECKOUT_PAYMENT = "/api/v1/checkout/payment"
CHECKOUT_SUBMIT = "/api/v1/checkout/submit"

# Payload structures (examples)
CART_ADD_PAYLOAD = {
    "productId": "{product_id}",
    "quantity": 1,
    "selectedOptions": {}
}

SHIPPING_PAYLOAD = {
    "address": {
        "firstName": "{first_name}",
        "lastName": "{last_name}",
        "line1": "{address1}",
        "line2": "{address2}",
        "city": "{city}",
        "state": "{state}",
        "postalCode": "{zip}",
        "country": "{country}",
        "phone": "{phone}"
    }
}
```

---

## Tips

1. **Use Incognito** - Fresh session, no cached data
2. **Log in first** - Some endpoints require authentication
3. **Check for CSRF tokens** - Often in response headers or hidden inputs
4. **Watch for redirects** - The real endpoint may be different
5. **Test with curl** - Verify endpoints work outside browser

### Testing with curl

```bash
# Test stock check (replace with real URL)
curl -s "https://www.pokemoncenter.com/api/products/ABC123/inventory" \
  -H "Cookie: your_session_cookie" | jq

# Test add to cart
curl -X POST "https://www.pokemoncenter.com/api/cart/add" \
  -H "Content-Type: application/json" \
  -H "Cookie: your_session_cookie" \
  -H "X-CSRF-Token: your_token" \
  -d '{"productId": "ABC123", "quantity": 1}' | jq
```

---

## Common Patterns

### Shopify-based sites
```
/cart/add.js
/cart.js
/checkout.json
```

### Salesforce Commerce Cloud
```
/on/demandware.store/Sites-{site}-Site/default/Cart-AddProduct
/on/demandware.store/Sites-{site}-Site/default/CheckoutServices-*
```

### Custom platforms (likely Pokemon Center)
```
/api/v1/* or /api/*
Look for versioned API paths
```

---

## After Mapping

1. Update `src/endpoints.py` with real URLs
2. Update payload structures in `src/cart.py` and `src/checkout.py`
3. Run `python3 -m src.main run --dry-run` to verify no errors
4. Test with a low-value item first
