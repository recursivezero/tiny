# 📘 Cache – Complete Guide (Concepts, How It Works, How to Use It)

`1. What is Cache?`

Cache is a temporary storage layer used to store frequently accessed data so that future requests can be served faster.

Instead of fetching data repeatedly from a slow source (like a database, API, or disk), the application first checks the cache.
If the data exists in cache, it is returned immediately.

If not, the application fetches it from the original source and stores it in the cache for next time.

Simple definition:

Cache is a fast memory layer that stores frequently used data to reduce latency and load on the main data source.

# 2. Why Cache is Needed

Without cache:

- Every request hits the database or external service

- Response time is slow

- Database load increases

- Application does not scale well

With cache:

- Most requests are served from fast memory

- Database load is reduced

- Response time improves significantly

- Application handles more traffic with the same resources

Key benefits:

- Performance improvement

- Reduced load on database

- Better user experience

- Lower infrastructure cost

- Improved scalability

  # 3. How Cache Works (High-Level Flow)

Basic flow:

```
User Request
      ↓
Application checks Cache
      ↓
Cache Hit? ── Yes ──> Return data from Cache
      │
      No
      ↓
Fetch from Database / Source
      ↓
Store result in Cache
      ↓
Return data to User

```

Cache Hit vs Cache Miss

- Cache Hit:  
  Data is found in cache → fast response

- Cache Miss:  
  Data is not in cache → fetch from main source → save to cache → return response

# 5. Cache Lifetime (TTL – Time To Live)

Cached data should not live forever.
A TTL (Time To Live) defines how long data remains in cache before it expires.

`Why TTL is important:`

- Prevents stale data

- Frees memory

- Keeps cache fresh

- Avoids serving outdated values

`Examples:`

- Short TTL → fast-changing data

- Long TTL → stable data

`Once TTL expires:`

- Data is removed from cache automatically

- Next request becomes a cache miss

# 6. Cache Invalidation (Keeping Cache Correct)

Cache invalidation means removing or updating cached data when the original data changes.

`When to invalidate cache:`

- Data is updated

- Data is deleted

- Data becomes invalid

- TTL expires

`Why invalidation is important:`

- Prevents serving outdated or incorrect data

- Keeps cache consistent with main data source  
  Cache invalidation is one of the hardest problems in system design because it requires keeping cache and source data in sync.

# 7. Common Cache Strategies (Conceptual)

`1️⃣ Read-Through Cache`

- Application reads from cache first

- On miss, fetches from source and stores in cache

`2️⃣ Write-Through Cache`

- Data is written to cache and main storage together

`3️⃣ Write-Behind Cache`

- Data is written to cache first

- Main storage is updated later asynchronously

`Each strategy has trade-offs between:`

- Speed

- Consistency

- Reliability

# 1. Cache Consistency vs Performance

Cache improves performance but can introduce stale data.

There is always a trade-off between:

- Strong consistency → always fresh data

- High performance → faster responses

`Design choice depends on:`

- How critical correctness is

- How often data changes

- How much stale data is acceptable

# 9. Cache Failure Handling

Cache should never be a single point of failure.

`Good design principles:`

- Application should still work if cache is unavailable

- Cache is an optimization, not the source of truth

- Main data source remains authoritative

`If cache fails:`

- Application should fallback to main data source

- Cache can be repopulated later

# 10. Cache in Application Architecture

`Cache usually sits between application and main storage:`

```Client
  ↓
Application
  ↓
Cache Layer
  ↓
Database / External Service
```
