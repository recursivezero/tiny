# 📄 URL Mapping for Cache Memory in TinyURL Project

## What is URL Mapping?

URL mapping means connecting a short code to the original long URL.

**Example:**

- `abc123` → `https://www.google.com`
- `xYz789` → `https://github.com`

So when a user opens:

- `http://tinyurl.com/abc123`

Your system finds:

- `abc123` → `https://www.google.com`

and redirects the user to the original URL.

## Why Do We Use Cache for URL Mapping?

Without cache:

- Every redirect request hits the database
- Slower response time
- More load on the DB

With cache:

- Frequently accessed URLs are stored in memory
- Faster redirect
- Fewer database calls
- Better performance

**Flow:**
User → Cache → (if miss) → Database → Cache → Redirect

## How URL Mapping Works with Cache (Flow)

### Redirect Flow

1. User opens short URL: `/abc123`
2. App checks cache:
   - If found → redirect immediately
   - If not found → fetch from DB → store in cache → redirect

### Create Short URL Flow

1. User submits long URL
2. App generates short code
3. Store mapping in database
4. Optionally add to cache

## Cache Structure in Python (In-Memory)

We use a Python dictionary as cache:

```python
cache = {
    "abc123": {
        "url": "https://google.com",
        "expires_at": 1700000000
    }
}
```

- Key = short code
- Value = original URL + expiry time (TTL)

## TTL (Time To Live) for Cache

TTL means how long a URL mapping should stay in cache.

**Example:**

- TTL = 10 minutes
- After 10 minutes → cache entry is removed
- Next request goes to the database again

**Why TTL is important:**

- Prevents memory overflow
- Keeps cache fresh
- Removes unused URLs automatically

## Cache Logic (Concept)

Check cache first:

```python
if shortcode in cache:
    return original_url
else:
    fetch from DB
    store in cache
    return original_url
```

## FastAPI + URL Mapping (Conceptual Flow)

Example endpoint: `GET /{shortcode}`

Flow:

1. FastAPI receives `/abc123`
2. Extract `abc123`
3. Check cache:
   - If exists → redirect
   - Else → fetch from DB → store in cache → redirect

FastAPI just handles routing. Mapping logic stays the same.

## What Happens When Cache Is Full?

In a simple Python cache:

- It grows until memory limit
- You manually control cleanup

With TTL:

- Old entries auto-expire
- Memory stays stable

## Limitations of In-Memory Cache

- Cache clears when the server restarts
- Not shared across multiple servers
- Not suitable for production scale

## Summary

- Cache mapping → fast redirect
- Reduces DB calls
- TTL expiry
- Persistent storage: no
- Multi-server support: no
