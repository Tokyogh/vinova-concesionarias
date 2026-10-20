# ES: Ejecuta el flujo operativo «qa e2e» con fallos controlados y sin ocultar errores.
# EN: Runs the «qa e2e» operational flow with controlled failures and visible errors.
param()

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProjectName = if ($env:VINOVA_QA_PROJECT_NAME) { $env:VINOVA_QA_PROJECT_NAME } else { "vinova-qa-cli" }
$ComposeFile = Join-Path $ProjectRoot "docker-compose.qa-cli.yml"
$ReportsDirectory = Join-Path $ProjectRoot "private\qa_reports"
$RunName = "e2e-targeted-$(Get-Date -Format 'yyyyMMdd-HHmmss-fff')"
$HostOutput = Join-Path $ReportsDirectory $RunName
$HostSummary = Join-Path $HostOutput "summary.json"
$ContainerOutput = "/app/private/qa_reports/$RunName"
$Compose = @("compose", "--project-name", $ProjectName, "-f", $ComposeFile)
$CurrentPhase = "bootstrap"
$ExitCode = 0
$LocationPushed = $false
$ComposeReady = $false
$RequestedScenarios = [System.Collections.Generic.List[string]]::new()
$Browser = "chromium"
$Rebuild = $false
$FailFastOverride = $null

$AllowedScenarios = @(
    "public", "auth", "vehicles", "customers", "inventory",
    "sales", "documents", "security", "roles", "accessibility", "portal", "maps", "all"
)
$LegacyAliases = @{
    "test_01" = "public"; "test_02" = "auth"; "test_03" = "vehicles";
    "test_04" = "customers"; "test_05" = "inventory"; "test_06" = "sales";
    "test_07" = "documents"; "test_08" = "security"; "test_09" = "roles";
    "test_10" = "accessibility"; "test_11" = "portal"; "test_12" = "maps"
}

# ES: La sección siguiente define precondiciones, límites y propagación explícita de fallos.
# EN: The following section defines preconditions, limits, and explicit failure propagation.
function Write-BootstrapFailureSummary {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$Phase = "bootstrap",
        [int]$Code = 1
    )

    New-Item -ItemType Directory -Force -Path $HostOutput | Out-Null
    $Payload = [ordered]@{
        schema_version = 1
        status = "failed"
        phase = $Phase
        environment = "windows-host-wrapper"
        requested_scenarios = @($RequestedScenarios)
        browser = $Browser
        exit_code = $Code
        message = $Message
        created_at = [DateTimeOffset]::Now.ToString("o")
        hint = "El fallo ocurrio antes de que Playwright generara su summary.json."
    }
    $Json = $Payload | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($HostSummary, $Json, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Resumen de error: $HostSummary"
}

try {
    New-Item -ItemType Directory -Force -Path $ReportsDirectory | Out-Null

    $CurrentPhase = "argument-validation"
    $RawArguments = if ($env:VINOVA_E2E_RAW_ARGS) { $env:VINOVA_E2E_RAW_ARGS } else { "" }
    $Tokens = [System.Collections.Generic.List[string]]::new()
    foreach ($Match in [regex]::Matches($RawArguments, '"([^"]*)"|([^\s]+)')) {
        $Token = if ($Match.Groups[1].Success) { $Match.Groups[1].Value } else { $Match.Groups[2].Value }
        if (-not [string]::IsNullOrWhiteSpace($Token)) { $Tokens.Add($Token.Trim()) }
    }

    for ($Index = 0; $Index -lt $Tokens.Count; $Index++) {
        $Token = $Tokens[$Index]
        $Lower = $Token.ToLowerInvariant()
        if ($Lower -eq "--browser") {
            $Index++
            if ($Index -ge $Tokens.Count) { throw "Falta el navegador despues de --browser." }
            $Browser = $Tokens[$Index].ToLowerInvariant()
            continue
        }
        if ($Lower -eq "--rebuild") {
            $Rebuild = $true
            continue
        }
        if ($Lower -eq "--fail-fast") {
            $FailFastOverride = $true
            continue
        }
        if ($Lower -eq "--no-fail-fast") {
            $FailFastOverride = $false
            continue
        }
        if (@("chromium", "firefox", "webkit") -contains $Lower) {
            $Browser = $Lower
            continue
        }

        if ($LegacyAliases.ContainsKey($Lower)) { $Lower = $LegacyAliases[$Lower] }
        if ($Token.Contains(",")) {
            throw "No uses listas con comas. Escribe: scripts\qa-e2e.cmd inventory accessibility"
        }
        if ($AllowedScenarios -notcontains $Lower) {
            throw "Escenario E2E no permitido: $Token. Usa public, auth, vehicles, customers, inventory, sales, documents, security, roles, accessibility, portal, maps o all."
        }
        if (-not $RequestedScenarios.Contains($Lower)) { $RequestedScenarios.Add($Lower) }
    }

    if ($RequestedScenarios.Count -eq 0) { $RequestedScenarios.Add("all") }
    if ($RequestedScenarios.Count -gt 1 -and $RequestedScenarios.Contains("all")) {
        throw "Usa 'all' solo o varios escenarios concretos."
    }
    if (@("chromium", "firefox", "webkit") -notcontains $Browser) {
        throw "Navegador no permitido: $Browser."
    }

    $FailFast = if ($null -ne $FailFastOverride) { [bool]$FailFastOverride } else { -not $RequestedScenarios.Contains("all") }

    if (-not (Test-Path $ComposeFile)) { throw "No se encontro docker-compose.qa-cli.yml en $ProjectRoot." }

    Push-Location $ProjectRoot
    $LocationPushed = $true

    $CurrentPhase = "docker-info"
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop no esta iniciado o el motor Docker no responde." }

    $CurrentPhase = "compose-validation"
    & docker @Compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw "La configuracion de Docker Compose QA no es valida." }
    $ComposeReady = $true

    $CurrentPhase = "image-preparation"
    $RunnerImageName = "$ProjectName-qa_runner"
    & docker image inspect $RunnerImageName *> $null
    $RunnerImageExists = ($LASTEXITCODE -eq 0)
    if ($Rebuild -or -not $RunnerImageExists) {
        if ($Rebuild) { Write-Host "Reconstruyendo la imagen QA por solicitud..." }
        else { Write-Host "La imagen QA no existe; construyendo una sola vez..." }
        & docker @Compose build qa_runner
        if ($LASTEXITCODE -ne 0) { throw "No se pudo construir la imagen QA." }
    }
    else {
        Write-Host "Reutilizando la imagen QA existente; el codigo actual se monta en modo solo lectura."
    }

    $CurrentPhase = "infrastructure-start"
    Write-Host "Iniciando PostgreSQL y Redis temporales..."
    & docker @Compose up -d --wait qa_db qa_redis
    if ($LASTEXITCODE -ne 0) {
        & docker @Compose ps --all
        & docker @Compose logs --tail=120 qa_db qa_redis
        throw "No se pudo iniciar la infraestructura QA."
    }

    $CurrentPhase = "e2e-execution"
    $Arguments = @("run", "--rm", "qa_runner", "python", "scripts/run_e2e.py")
    foreach ($Scenario in $RequestedScenarios) { $Arguments += $Scenario }
    $Arguments += @("--browsers", $Browser, "--output", $ContainerOutput)
    if ($FailFast) { $Arguments += "--fail-fast" }

    Write-Host "Ejecutando E2E: $($RequestedScenarios -join ' ') en $Browser"
    & docker @Compose @Arguments
    $ExitCode = $LASTEXITCODE

    if (Test-Path $HostSummary) { Write-Host "Resumen: $HostSummary" }
    else {
        Write-BootstrapFailureSummary -Message "El contenedor termino sin generar summary.json (codigo $ExitCode)." -Phase $CurrentPhase -Code $(if ($ExitCode -eq 0) { 1 } else { $ExitCode })
        if ($ExitCode -eq 0) { $ExitCode = 1 }
    }

    if ($ExitCode -ne 0) { throw "Los E2E terminaron con errores. Revisa el resumen indicado." }
}
catch {
    if ($ExitCode -eq 0) { $ExitCode = 1 }
    if (-not (Test-Path $HostSummary)) {
        Write-BootstrapFailureSummary -Message $_.Exception.Message -Phase $CurrentPhase -Code $ExitCode
    }
    [Console]::Error.WriteLine($_.Exception.Message)
}
finally {
    if ($ComposeReady) {
        try { & docker @Compose down --remove-orphans *> $null } catch {}
    }
    if ($LocationPushed) { Pop-Location }
}

exit $ExitCode
