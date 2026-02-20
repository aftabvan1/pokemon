Pokémon Center Bot — Site Intelligence & Endpoint Research
This file contains everything discovered about pokemoncenter.com's API structure through manual network interception. Use this alongside CLAUDE.md to build the bot.

Platform Identification
Pokémon Center runs on Salesforce Commerce Cloud (SFCC) — also known as Demandware. This is confirmed by:

The rtss response header (Salesforce-specific)
The URL structure: /site/en-ca/resourceapi/
The allowsitespect header (SFCC-specific middleware)
CloudFront CDN in front (x-amz-cf-id, via headers confirm this)
Imperva/Incapsula for bot protection (x-cdn: Imperva, x-iinfo headers)

This is critical because SFCC has well-known API patterns. All endpoints follow the same base structure.

Base URL Structure
https://www.pokemoncenter.com/site/en-ca/resourceapi/
The locale segment en-ca will be in every API call for Canadian users.

Confirmed Endpoints
Cart Read (Confirmed via interception)
GET https://www.pokemoncenter.com/site/en-ca/resourceapi/cart

Returns full cart contents as JSON
Used to verify add-to-cart succeeded
Response is ~11.3 kB when cart has items
Cached via CloudFront (check cf-cache-status header)

Add to Cart (Inferred from SFCC pattern — needs payload verification)
POST https://www.pokemoncenter.com/site/en-ca/resourceapi/cart
Expected payload structure (standard SFCC):
json{
  "productId": "70-11179-101",
  "quantity": 1
}
Product Availability (Needs interception — search for this)
GET https://www.pokemoncenter.com/site/en-ca/resourceapi/products/{productId}/availability
OR possibly:
GET https://www.pokemoncenter.com/site/en-ca/resourceapi/products/{productId}
Look for a field like "inventoryStatus": "IN_STOCK" or "availability": true in the response.
Checkout Endpoints (Inferred from SFCC pattern — needs verification)
POST https://www.pokemoncenter.com/site/en-ca/resourceapi/checkout/shipping
POST https://www.pokemoncenter.com/site/en-ca/resourceapi/checkout/payment
POST https://www.pokemoncenter.com/site/en-ca/resourceapi/checkout/submit

Authentication System
Auth Token Location
The auth token is stored in a cookie called auth as a JSON object:
json{
  "access_token": "<token>",
  "token_type": "bearer",
  "expires_in": 604799,
  "scope": "pokemon-ca",
  "role": "REGISTERED",
  "roles": ["REGISTERED"],
  "id": <user_id>,
  "familyName": "<last>",
  "givenName": "<first>"
}
How to Use It
Extract the access_token value and send it as a Bearer token:
Authorization: Bearer <access_token>
Token expires in 604799 seconds (~7 days). Implement auto re-login when expired.

Bot Protection Layers
Pokémon Center has multiple protection layers. The bot needs to handle all of them:
1. Imperva/Incapsula

Detected via x-cdn: Imperva response header
Sets cookies: visid_incap_*, nlbi_*, incap_ses_*
These cookies must be present in every request
Obtained automatically when you first visit the site with a real browser

2. Reese84 (Bot detection token)

Cookie name: reese84
Long encrypted token that proves browser legitimacy
Must be captured from a real browser session and reused
Expires and needs periodic refresh

3. DataDome

Cookie name: datadome
Real-time bot detection service
One of the harder ones to deal with — detects headless browsers
Must use Playwright with stealth settings to avoid triggering it

4. CloudFront + Cloudflare

Both CDNs are present (cf-ray header confirms Cloudflare on some routes)
Rate limiting happens at CDN level
Use residential proxies to avoid IP bans

5. QuantumMetric

Behavioral analytics — tracks mouse movements, click patterns, timing
Not a hard blocker but feeds into bot scoring
Playwright helps here since it simulates real browser behavior


Required Cookies (Must be present in every request)
These cookies must all be captured from a real logged-in browser session:
CookiePurposeauthAuthentication token (JSON)reese84Bot protection tokendatadomeBot detectionvisid_incap_2682446Imperva visitor IDnlbi_2682446Imperva load balancerincap_ses_*Imperva sessionSSIDSalesforce session IDSSSCSalesforce session cookieSSODSalesforce session datacorrelationIdRequest correlation ID

Required Request Headers
Every request must include these headers exactly as a real Chrome on Mac would send them:
pythonheaders = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-CA,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Referer": "https://www.pokemoncenter.com/en-ca/product/{product_id}/{product_slug}",
    "Origin": "https://www.pokemoncenter.com",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-ch-device-memory": "8",
    "sec-ch-ua-arch": '"arm"',
    "sec-ch-ua-model": '""',
}

Product ID Format
Pokémon Center product IDs follow this format:
70-11179-101
Seen in the URL: /en-ca/product/70-11179-101/pokemon-30th-celebration-pin
The product ID is the numeric part before the slug. Use this for API calls.

Session Strategy
Because of the multiple bot protection layers, the recommended approach is:
Step 1 — Browser Login (Playwright with stealth)
Use Playwright to log in with a real Chromium browser. This will:

Trigger all the bot protection cookie generation naturally
Get a valid reese84 and datadome token
Get the auth JWT cookie

Step 2 — Extract and Save All Cookies
After login, dump all cookies to a JSON file:
pythoncookies = await context.cookies()
# Save to cookies.json
Step 3 — Use httpx for Speed-Critical Requests
Load saved cookies into httpx for monitoring and checkout:
pythoncookie_jar = {c["name"]: c["value"] for c in saved_cookies}
async with httpx.AsyncClient(cookies=cookie_jar, headers=headers) as client:
    response = await client.get(STOCK_ENDPOINT)
Step 4 — Refresh Session When Needed

Monitor for 401/403 responses
If detected, re-run Playwright login flow automatically
Save new cookies and continue


Stock Monitoring Strategy

Poll the product availability endpoint every 200-500ms
The API endpoint updates before the visible page does
Parse the response for stock status field
The moment status changes to in-stock, immediately fire add-to-cart

pythonasync def monitor(product_id: str):
    while True:
        r = await client.get(f"{BASE}/products/{product_id}/availability")
        data = r.json()
        # Field name TBD — needs verification via DevTools
        # Likely: data["inventoryStatus"] == "IN_STOCK"
        # Or: data["availability"]["orderable"] == True
        if is_in_stock(data):
            await add_to_cart(product_id)
            break
        await asyncio.sleep(0.3)

What Still Needs Manual Interception
These endpoints were not captured and need to be verified by watching DevTools during the actual actions:

Add to cart POST payload — need to see the exact JSON body when clicking Add to Cart
Stock check endpoint — need to find the exact URL and response field for availability
Checkout shipping payload — exact JSON structure when submitting shipping address
Checkout payment payload — exact JSON when selecting payment method
Order submit payload — final POST that places the order

How to capture what's missing:

Open DevTools → Network → Fetch/XHR
Filter by pokemoncenter in the search bar
Perform each action and look for POST requests to pokemoncenter.com (not third parties)
The add-to-cart POST fires the moment you click the button — watch closely
Click the request → Payload tab → copy the JSON body


Third Party Services to Ignore
These domains appear in network traffic but are analytics/tracking only — not part of the purchase flow:

ingest.quantummetric.com — behavioral analytics
api.amplitude.com — event tracking
eu01.records.in.treasuredata.com — data warehouse
we.turnto.com — reviews platform
www.googletagmanager.com — tag manager
Any collect?v=2 requests — Google Analytics


Known Challenges

DataDome is aggressive — it will block headless Playwright without stealth plugins. Use playwright-stealth or rebrowser-patches.
reese84 token is dynamic — it changes per session and possibly per request. May need to refresh it periodically.
CloudFront caching — the cart endpoint showed age: 3333 meaning cached responses. Add cache-busting query params when monitoring stock.
Rate limiting — too many requests from one IP triggers Imperva. Use residential proxy rotation for the monitoring loop.
CSRF tokens — SFCC sometimes requires a CSRF token in POST requests. Check response headers for x-csrf-token and include it in subsequent POST requests.