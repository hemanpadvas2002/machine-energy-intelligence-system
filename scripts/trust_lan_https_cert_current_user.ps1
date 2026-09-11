$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$rootCaPath = Join-Path $repoRoot "certs\root-ca.crt"
$fallbackCertPath = Join-Path $repoRoot "certs\server.crt"

if (Test-Path $rootCaPath) {
    $certToTrust = $rootCaPath
} elseif (Test-Path $fallbackCertPath) {
    $certToTrust = $fallbackCertPath
} else {
    throw "No certificate found. Run scripts\create_streamlit_https_cert.ps1 first."
}

$result = Import-Certificate `
    -FilePath $certToTrust `
    -CertStoreLocation Cert:\CurrentUser\Root

Write-Host "Trusted certificate for the current Windows user:"
Write-Host "  $certToTrust"
Write-Host "Thumbprint:"
Write-Host "  $($result.Thumbprint)"
