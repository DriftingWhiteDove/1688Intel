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
# Auto-detect Chrome path
$chromePaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)
$chromeExe = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chromeExe) { throw "Chrome not found, please set chromeExe path manually" }
Start-Process -FilePath $chromeExe -ArgumentList $args

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
