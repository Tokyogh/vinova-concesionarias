# ES: Ejecuta el flujo operativo «CREAR ADMIN STAGING» con fallos controlados y sin ocultar errores.
# EN: Runs the «CREAR ADMIN STAGING» operational flow with controlled failures and visible errors.
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$ProjectRoot = "",
    [string]$EnvFile = ".env.staging"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if (-not (Test-Path (Join-Path $ProjectRoot "manage.py") -PathType Leaf)) {
    throw "Indique la raiz de Vinova Pro: CREAR-ADMIN-STAGING.bat C:\ruta\vinova-cns+"
}
$EnvPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) { $EnvFile } else { Join-Path $ProjectRoot $EnvFile }
if (-not (Test-Path $EnvPath -PathType Leaf)) { throw "No existe $EnvPath" }

$Username = (Read-Host "Nombre de usuario para iniciar sesion").Trim()
$Email = (Read-Host "Correo del administrador").Trim()
$PasswordSecure = Read-Host "Contrasena segura" -AsSecureString
$PasswordConfirmSecure = Read-Host "Repita la contrasena" -AsSecureString

function Convert-SecureToPlain([System.Security.SecureString]$SecureValue) {
    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer) }
}

$Password = Convert-SecureToPlain $PasswordSecure
$PasswordConfirm = Convert-SecureToPlain $PasswordConfirmSecure
if (-not $Username -or -not $Email -or -not $Password) { throw "Todos los datos son obligatorios." }
if ($Password -ne $PasswordConfirm) { throw "Las contrasenas no coinciden." }

$ComposeArgs = @(
    "--env-file", $EnvFile,
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.staging.yml"
)

Push-Location $ProjectRoot
try {
    $Password | & docker compose @ComposeArgs exec -T `
        -e VINOVA_ENVIRONMENT=staging `
        web python manage.py bootstrap_staging_admin `
        --username $Username `
        --email $Email `
        --password-stdin `
        --clear-login-cache
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear o reparar el administrador." }
    Write-Host "Ya puede iniciar sesion en https://localhost con el usuario o correo indicado." -ForegroundColor Green
}
finally {
    $Password = $null
    $PasswordConfirm = $null
    Pop-Location
}
