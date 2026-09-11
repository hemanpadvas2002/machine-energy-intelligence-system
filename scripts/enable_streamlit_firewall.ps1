$ErrorActionPreference = "Stop"

$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [System.Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator) {
    throw "Run this script from PowerShell opened as Administrator."
}

@(
    @{ Name = "AMTDC Streamlit HTTPS 8501"; Port = 8501 },
    @{ Name = "AMTDC Telemetry HTTPS 8765"; Port = 8765 }
) | ForEach-Object {
    $ruleName = $_.Name
    $port = $_.Port
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

    if ($existingRule) {
        Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Profile Private
        Write-Host "Firewall rule is already present and enabled: $ruleName"
    } else {
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $port `
            -Profile Private `
            -RemoteAddress LocalSubnet | Out-Null

        Write-Host "Created LAN-only firewall rule: $ruleName"
    }
}
