# Run the studio: backend API on :8700, frontend on :3000.
#
#   .\dev.ps1 [project-directory]
#
# Defaults to ..\studio_test_project. Ctrl-C stops both.
param(
    [Parameter(Position = 0)]
    [string] $Project
)

$ErrorActionPreference = 'Stop'

$here = $PSScriptRoot
$repo = Split-Path -Parent $here
if (-not $Project) {
    $Project = Join-Path $repo 'studio_test_project'
}

# Resolve against the caller's cwd so --project is valid after we change
# the child process working directories (bash leaves a relative path as-is,
# which would then be interpreted from backend/).
if (-not [System.IO.Path]::IsPathRooted($Project)) {
    $Project = Join-Path (Get-Location).Path $Project
}
$Project = [System.IO.Path]::GetFullPath($Project)

if (-not (Test-Path -LiteralPath $Project -PathType Container)) {
    [Console]::Error.WriteLine("project directory does not exist: $Project")
    exit 1
}

$backendDir = Join-Path $here 'backend'
$frontendDir = Join-Path $here 'frontend'
$onWindows = $env:OS -eq 'Windows_NT'

$venvDir = Join-Path $backendDir '.venv'
if (-not (Test-Path -LiteralPath $venvDir -PathType Container)) {
    Write-Host 'installing the backend environment…'
    Push-Location $backendDir
    try {
        & uv sync --python 3.12
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

$nodeModules = Join-Path $frontendDir 'node_modules'
if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
    Write-Host 'installing the frontend environment…'
    Push-Location $frontendDir
    try {
        & npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

$python = Join-Path $venvDir 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $venvDir 'bin\python'
}
if (-not (Test-Path -LiteralPath $python)) {
    [Console]::Error.WriteLine("backend python not found under $venvDir")
    exit 1
}

function Start-StudioProcess {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string] $Arguments,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory
    )
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $FilePath
    $info.Arguments = $Arguments
    $info.WorkingDirectory = $WorkingDirectory
    $info.UseShellExecute = $false
    return [System.Diagnostics.Process]::Start($info)
}

function Stop-StudioProcessTree {
    param([System.Diagnostics.Process] $Process)
    if ($null -eq $Process) { return }
    try {
        if ($Process.HasExited) { return }
    } catch {
        return
    }
    if ($onWindows) {
        & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
    } else {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

$backend = $null
$frontend = $null
try {
    Write-Host "backend  → http://127.0.0.1:8700  (project: $Project)"
    $quotedProject = '"' + ($Project -replace '"', '\"') + '"'
    $backend = Start-StudioProcess `
        -FilePath $python `
        -Arguments "-m studio_backend.cli serve --project $quotedProject" `
        -WorkingDirectory $backendDir

    Write-Host 'frontend → http://127.0.0.1:3000'
    if ($onWindows) {
        $frontend = Start-StudioProcess `
            -FilePath "$env:ComSpec" `
            -Arguments '/d /c npm run dev' `
            -WorkingDirectory $frontendDir
    } else {
        $frontend = Start-StudioProcess `
            -FilePath 'npm' `
            -Arguments 'run dev' `
            -WorkingDirectory $frontendDir
    }

    # Sleep-wait so Ctrl-C can run the finally block (Wait-Process often
    # swallows it on Windows). Stays until both children have exited.
    while ($true) {
        $alive = $false
        foreach ($proc in @($backend, $frontend)) {
            if ($proc -and -not $proc.HasExited) { $alive = $true }
        }
        if (-not $alive) { break }
        Start-Sleep -Milliseconds 400
    }
} finally {
    Stop-StudioProcessTree $backend
    Stop-StudioProcessTree $frontend
}
