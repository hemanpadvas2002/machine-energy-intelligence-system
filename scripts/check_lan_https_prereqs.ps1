$ErrorActionPreference = "Continue"

$checks = @(
    @{ Name = "Node.js"; Command = "node"; Args = @("-v") },
    @{ Name = "npm"; Command = "npm"; Args = @("-v") },
    @{ Name = "PM2"; Command = "pm2"; Args = @("-v") },
    @{ Name = "OpenSSL"; Command = "openssl"; Args = @("version") },
    @{ Name = "Git"; Command = "git"; Args = @("--version") },
    @{ Name = "Python"; Command = "python"; Args = @("--version") }
)

foreach ($check in $checks) {
    $command = Get-Command $check.Command -ErrorAction SilentlyContinue
    if (-not $command -and $check.Command -eq "openssl" -and (Test-Path "C:\Program Files\Git\usr\bin\openssl.exe")) {
        $command = @{ Source = "C:\Program Files\Git\usr\bin\openssl.exe" }
    }

    if (-not $command) {
        Write-Host "[MISSING] $($check.Name): install or add to PATH"
        continue
    }

    $version = & $command.Source @($check.Args) 2>&1
    Write-Host "[OK] $($check.Name): $version"
}

Write-Host ""
Write-Host "LAN IPv4 addresses:"
ipconfig | Select-String "IPv4"
