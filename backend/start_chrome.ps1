# Kill existing Chrome
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# Generate temp profile path
$tmpdir = Join-Path $env:TEMP "chrome-debug-$([System.IO.Path]::GetRandomFileName())"

# Start Chrome with remote debugging
$args = @(
    "--remote-debugging-port=9222",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=$tmpdir",
    "--new-window",
    "about:blank"
)
Start-Process -FilePath "C:\Users\34678\AppData\Local\Google\Chrome\Application\chrome.exe" -ArgumentList $args

Start-Sleep -Seconds 5

# Verify
$p = Get-Process chrome -ErrorAction SilentlyContinue | Measure-Object
Write-Output "Chrome processes: $($p.Count)"

$port = netstat -ano | Select-String ":9222"
if ($port) {
    Write-Output "Port 9222: LISTENING"
} else {
    Write-Output "Port 9222: NOT LISTENING"
}

# Test CDP endpoint
try {
    $ver = Invoke-RestMethod -Uri "http://localhost:9222/json/version" -ErrorAction Stop
    Write-Output "CDP OK: $($ver.Browser)"
} catch {
    Write-Output "CDP FAILED: $_"
}
