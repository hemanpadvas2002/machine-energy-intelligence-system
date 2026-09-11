param(
    [string]$IpAddress = "",
    [string]$DnsName = $env:COMPUTERNAME,
    [int]$ValidYears = 3
)

$ErrorActionPreference = "Stop"

function Get-DefaultLanIp {
    $config = Get-NetIPConfiguration |
        Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.IPv4Address -ne $null } |
        Select-Object -First 1

    if (-not $config) {
        throw "Could not find a LAN IPv4 address. Pass one manually with -IpAddress 192.168.x.x"
    }

    return $config.IPv4Address.IPAddress
}

if ([string]::IsNullOrWhiteSpace($IpAddress)) {
    $IpAddress = Get-DefaultLanIp
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $repoRoot "certs"
$rootCaCertPath = Join-Path $certDir "root-ca.crt"
$rootCaKeyPath = Join-Path $certDir "root-ca.key"
$certPath = Join-Path $certDir "server.crt"
$keyPath = Join-Path $certDir "server.key"

New-Item -ItemType Directory -Force -Path $certDir | Out-Null

function New-OpenSslCert {
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    $opensslPath = $null
    if ($openssl) {
        $opensslPath = $openssl.Source
    } elseif (Test-Path "C:\Program Files\Git\usr\bin\openssl.exe") {
        $opensslPath = "C:\Program Files\Git\usr\bin\openssl.exe"
    }

    if (-not $opensslPath) {
        return $false
    }

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    $rootConfig = Join-Path $env:TEMP "amtdc-root-ca.cnf"
    try {
    @"
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no

[req_distinguished_name]
CN = AMTDC LAN Root CA

[v3_ca]
basicConstraints = critical, CA:true
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
"@ | Set-Content -Path $rootConfig -Encoding ascii

    & $opensslPath req `
        -x509 `
        -newkey rsa:4096 `
        -keyout $rootCaKeyPath `
        -out $rootCaCertPath `
        -days ($ValidYears * 365) `
        -nodes `
        -sha256 `
        -config $rootConfig `
        -extensions v3_ca > $null 2> $null

    if ($LASTEXITCODE -ne 0) {
        return $false
    }

    $serverConfig = Join-Path $env:TEMP "amtdc-server-san.cnf"
    @"
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = $IpAddress

[v3_req]
basicConstraints = critical, CA:false
subjectAltName = @alt_names
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectKeyIdentifier = hash

[alt_names]
DNS.1 = localhost
DNS.2 = $DnsName
IP.1 = 127.0.0.1
IP.2 = $IpAddress
"@ | Set-Content -Path $serverConfig -Encoding ascii

    $csrPath = Join-Path $env:TEMP "amtdc-server.csr"

    & $opensslPath req `
        -new `
        -newkey rsa:4096 `
        -keyout $keyPath `
        -out $csrPath `
        -nodes `
        -sha256 `
        -config $serverConfig `
        -extensions v3_req > $null 2> $null

    if ($LASTEXITCODE -ne 0) {
        return $false
    }

    & $opensslPath x509 `
        -req `
        -in $csrPath `
        -CA $rootCaCertPath `
        -CAkey $rootCaKeyPath `
        -CAcreateserial `
        -out $certPath `
        -days ($ValidYears * 365) `
        -sha256 `
        -extfile $serverConfig `
        -extensions v3_req > $null 2> $null

    return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

if (New-OpenSslCert) {
    Write-Host "Created HTTPS certificate with OpenSSL:"
    Write-Host "  Root CA:     $rootCaCertPath"
    Write-Host "  Certificate: $certPath"
    Write-Host "  Private key: $keyPath"
    Write-Host ""
    Write-Host "Use these LAN URLs from another computer on the same Wi-Fi:"
    Write-Host "  Portal:        https://${IpAddress}:8501/Live_Data"
    Write-Host "  Telemetry API: https://${IpAddress}:8765/api/telemetry/dashboard"
    Write-Host ""
    Write-Host "To avoid the browser warning on this or another computer, import this Root CA as a Trusted Root certificate:"
    Write-Host "  $rootCaCertPath"
    exit 0
}

$rsa = [System.Security.Cryptography.RSA]::Create(4096)
$subject = "CN=$DnsName"
$request = [System.Security.Cryptography.X509Certificates.CertificateRequest]::new(
    $subject,
    $rsa,
    [System.Security.Cryptography.HashAlgorithmName]::SHA256,
    [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
)

$basicConstraints = [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($false, $false, 0, $true)
$request.CertificateExtensions.Add($basicConstraints)

$keyUsageFlags = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor
    [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment
$keyUsage = [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new($keyUsageFlags, $true)
$request.CertificateExtensions.Add($keyUsage)

$enhancedKeyUsages = [System.Security.Cryptography.OidCollection]::new()
$enhancedKeyUsages.Add([System.Security.Cryptography.Oid]::new("1.3.6.1.5.5.7.3.1")) | Out-Null
$serverAuth = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($enhancedKeyUsages, $true)
$request.CertificateExtensions.Add($serverAuth)

$san = [System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
$san.AddDnsName("localhost")
$san.AddDnsName($DnsName)
$san.AddIpAddress([System.Net.IPAddress]::Parse("127.0.0.1"))
$san.AddIpAddress([System.Net.IPAddress]::Parse($IpAddress))
$request.CertificateExtensions.Add($san.Build())

$notBefore = [System.DateTimeOffset]::Now.AddMinutes(-5)
$notAfter = $notBefore.AddYears($ValidYears)
$certificate = $request.CreateSelfSigned($notBefore, $notAfter)

function Convert-ToPem {
    param(
        [byte[]]$Bytes,
        [string]$Label
    )

    $base64 = [System.Convert]::ToBase64String(
        $Bytes,
        [System.Base64FormattingOptions]::InsertLineBreaks
    )

    return "-----BEGIN $Label-----`n$base64`n-----END $Label-----"
}

function Join-ByteArrays {
    param([object[]]$Arrays)

    $stream = [System.IO.MemoryStream]::new()
    foreach ($array in $Arrays) {
        $bytes = [byte[]]$array
        $stream.Write($bytes, 0, $bytes.Length)
    }

    return $stream.ToArray()
}

function New-DerLength {
    param([int]$Length)

    if ($Length -lt 128) {
        return [byte[]]@($Length)
    }

    $bytes = New-Object System.Collections.Generic.List[byte]
    $value = $Length
    while ($value -gt 0) {
        $bytes.Insert(0, [byte]($value -band 0xff))
        $value = $value -shr 8
    }

    $prefix = [byte](0x80 -bor $bytes.Count)
    return [byte[]](@($prefix) + $bytes.ToArray())
}

function New-DerInteger {
    param([byte[]]$Bytes)

    $start = 0
    while ($start -lt ($Bytes.Length - 1) -and $Bytes[$start] -eq 0) {
        $start++
    }

    $value = [byte[]]$Bytes[$start..($Bytes.Length - 1)]
    if (($value[0] -band 0x80) -ne 0) {
        $value = [byte[]](@(0) + $value)
    }

    return Join-ByteArrays @([byte[]]@(0x02), (New-DerLength $value.Length), $value)
}

function New-DerSequence {
    param([byte[]]$Body)

    return Join-ByteArrays @([byte[]]@(0x30), (New-DerLength $Body.Length), $Body)
}

function New-RsaPrivateKeyDer {
    param([System.Security.Cryptography.RSAParameters]$Parameters)

    $body = Join-ByteArrays @(
        (New-DerInteger ([byte[]]@(0))),
        (New-DerInteger $Parameters.Modulus),
        (New-DerInteger $Parameters.Exponent),
        (New-DerInteger $Parameters.D),
        (New-DerInteger $Parameters.P),
        (New-DerInteger $Parameters.Q),
        (New-DerInteger $Parameters.DP),
        (New-DerInteger $Parameters.DQ),
        (New-DerInteger $Parameters.InverseQ)
    )

    return New-DerSequence $body
}

$certBytes = $certificate.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
$keyBytes = New-RsaPrivateKeyDer ($rsa.ExportParameters($true))

Set-Content -Path $certPath -Value (Convert-ToPem -Bytes $certBytes -Label "CERTIFICATE") -Encoding ascii
Set-Content -Path $keyPath -Value (Convert-ToPem -Bytes $keyBytes -Label "RSA PRIVATE KEY") -Encoding ascii

Write-Host "Created HTTPS certificate with PowerShell fallback:"
Write-Host "  Certificate: $certPath"
Write-Host "  Private key: $keyPath"
Write-Host ""
Write-Host "Use these LAN URLs from another computer on the same Wi-Fi:"
Write-Host "  Portal:        https://${IpAddress}:8501/Live_Data"
Write-Host "  Telemetry API: https://${IpAddress}:8765/api/telemetry/dashboard"
Write-Host ""
Write-Host "To avoid the browser warning on the other computer, import this certificate there as a Trusted Root certificate:"
Write-Host "  $certPath"
