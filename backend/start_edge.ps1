# Kill existing Edge and Chrome
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# Generate temp profile path
$tmpdir = Join-Path $env:TEMP "edge-debug-$([System.IO.Path]::GetRandomFileName())"

# Start Edge with remote debugging
$args = @(
    "--remote-debugging-port=9222",
    "--no-first-run",
    "--no-default-browser-check",
    "--user-data-dir=$tmpdir",
    "--new-window",
    "about:blank"
)
Start-Process -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList $args

Start-Sleep -Seconds 5

# Verify
$p = Get-Process msedge -ErrorAction SilentlyContinue | Measure-Object
Write-Output "Edge processes: $($p.Count)"

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
