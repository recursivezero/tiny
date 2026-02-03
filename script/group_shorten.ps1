<#
=========================================================
 PowerShell Script: group_shorten.ps1
---------------------------------------------------------
 Description:
 Bulk URL shortener client for Tiny API.
 Reads a JSON file containing multiple URLs and sends
 them one-by-one to the /api/shorten endpoint.

---------------------------------------------------------
 HOW TO RUN (Windows PowerShell TERMINAL)
---------------------------------------------------------

 1. Open PowerShell as Administrator

 2. Allow script execution (one-time):
    Set-ExecutionPolicy RemoteSigned

 3. Navigate to project root:
    cd path\to\your\project

 4. Run with JSON file:
    .\group_shorten.ps1 -file ".\request\mixed_urls.json"

 5. Or run without argument (interactive):
    .\group_shorten.ps1


---------------------------------------------------------
 HOW TO RUN (Windows PowerShell ISE)
---------------------------------------------------------

 Method 1: Run with parameter
 --------------------------------
 1. Open Windows PowerShell ISE
 2. Open this script file (group_shorten.ps1)
 3. In the top menu, click:
      File → New PowerShell Tab
 4. In the console pane (bottom), run:
      .\group_shorten.ps1 -file ".\request\mixed_urls.json"

 Method 2: Run interactively
 --------------------------------
 1. Open Windows PowerShell ISE
 2. Open this script file
 3. Press the green ▶️ Run Script button
 4. When prompted, enter the JSON file path

---------------------------------------------------------
 Expected JSON input format:
 [
   { "url": "https://example.com" },
   { "url": "https://google.com" }
 ]
=========================================================
#>

param (
    [string]$file
)

# Ask for file path if not provided
if (-not $file) {
    $file = Read-Host "Enter path to JSON file"
}

if (-not (Test-Path $file)) {
    Write-Host "❌ File not found: $file" -ForegroundColor Red
    exit 1
}

# Read and parse JSON file
try {
    $data = Get-Content $file -Raw | ConvertFrom-Json
} catch {
    Write-Host "❌ Invalid JSON file" -ForegroundColor Red
    exit 1
}

$apiUrl = "http://127.0.0.1:8001/api/v1/shorten"

Write-Host "`n🚀 Processing URLs..." -ForegroundColor Cyan

foreach ($item in $data) {

    if (-not $item.url) {
        Write-Host "⚠️ Missing url field, skipping" -ForegroundColor Yellow
        continue
    }

    $body = @{ url = $item.url } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod `
            -Uri $apiUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body $body

        Write-Host "✅ SUCCESS:" $item.url "→" $response.short_code `
            -ForegroundColor Green
    }
    catch {
        $rawError = $_.ErrorDetails.Message

        try {
            $err = $rawError | ConvertFrom-Json
            Write-Host "❌ ERROR:" $item.url `
                "-" $err.error `
                "-" $err.message `
                -ForegroundColor Yellow
        }
        catch {
            Write-Host "❌ ERROR:" $item.url `
                "-" $rawError `
                -ForegroundColor Red
        }
    }
}

Write-Host "`n🎉 Done!" -ForegroundColor Cyan
