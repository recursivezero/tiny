param (
    [string]$file
)


if (-not $file) {
    $file = Read-Host "Enter path to JSON file"
}


if (-not (Test-Path $file)) {
    Write-Host "❌ File not found: $file" -ForegroundColor Red
    exit 1
}

# Read and parse JSON file
try {
    $data = Get-Content $file -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "❌ Invalid JSON file" -ForegroundColor Red
    exit 1
}

# API endpoint
$apiUrl = "http://127.0.0.1:8001/api/shorten"

Write-Host "🚀 Processing URLs..." -ForegroundColor Cyan

foreach ($item in $data) {

    if (-not $item.url) {
        Write-Host "⚠️ Skipping entry without url field" -ForegroundColor Yellow
        continue
    }

    $body = @{ url = $item.url } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod `
            -Uri $apiUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body $body

        Write-Host "✅ $($item.url) → short_code: $($response.short_code)" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed for $($item.url)" -ForegroundColor Red
    }
}

Write-Host "🎉 Done!" -ForegroundColor Cyan
