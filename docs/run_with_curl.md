# Run with Curl

## PowerShell Script: group_shorten.ps1

Description:
Bulk URL shortener client for Tiny API.
Reads a JSON file containing multiple URLs and sends
them one-by-one to the /api/shorten endpoint.

---

## HOW TO RUN (Windows PowerShell TERMINAL)

1. Open PowerShell as Administrator

2. Allow script execution (one-time):
   Set-ExecutionPolicy RemoteSigned

3. Navigate to project root:
   cd path\to\your\project

4. Run with JSON file:
   .\group_shorten.ps1 -file ".\request\mixed_urls.json"

5. Or run without argument (interactive):
   .\group_shorten.ps1

---

## HOW TO RUN (Windows PowerShell ISE)

# Run API using curl

▶️ Step 1: Start the FastAPI server

```#
poetry run tiny api
```

Server will start at:
`(http://127.0.0.1:8001)`

▶️ Step 2: Create request folder

in request folder Create a file named input.json in the project root:

```json
{
  "url": "https://recursivezero.com"
}
```

▶️ Step 3: Send request using curl (Windows PowerShell)

```#
$data = Get-Content .\request\urls.json -Raw | ConvertFrom-Json

Write-Host "🚀 Processing URLs..."

foreach ($item in $data) {
    if (-not $item.url) {
        Write-Host "❌ Skipping invalid entry (missing url field)"
        continue
    }

    $body = @{ url = $item.url } | ConvertTo-Json -Depth 3

    try {
        $response = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8001/shorten" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body

        Write-Host "✅ SUCCESS: $($item.url) -> $($response.short_code)"
    }
    catch {
        $status = $_.Exception.Response.StatusCode.value__ 2>$null
        if ($status -eq 400) {
            Write-Host "❌ ERROR: $($item.url) - Invalid URL"
        }
        elseif ($status -eq 404) {
            Write-Host "❌ ERROR: $($item.url) - API endpoint not found"
        }
        else {
            Write-Host "❌ ERROR: $($item.url) - Rejected by API"
        }
    }
}


```

▶️ Step 4: Expected Response

```json
{
  "short_url": "http://127.0.0.1:8001/abc123",
  "original_url": "https://example.com"
}
```
