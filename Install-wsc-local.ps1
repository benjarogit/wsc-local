[CmdletBinding()]
param([string]$Distribution = '', [switch]$WindowsPackagesOnly, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
if ($DryRun) {
    Write-Host 'Windows: WSL2/Ubuntu if missing; Docker.DockerDesktop and FiloSottile.mkcert via winget. Linux packages via scripts/install-host.sh. OS/license prompts remain interactive.'
    exit 0
}
try {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'Microsoft App Installer (winget) fehlt. Aus dem Microsoft Store installieren und erneut starten.'
    }
    function Install-MissingPackage([string]$Id) {
        & winget.exe list --exact --id $Id --source winget --accept-source-agreements | Out-Host
        if ($LASTEXITCODE -ne 0) {
            & winget.exe install --exact --id $Id --source winget --interactive
            if ($LASTEXITCODE -ne 0) { throw "Installation von $Id nicht abgeschlossen." }
        }
    }
    Install-MissingPackage 'Docker.DockerDesktop'
    Install-MissingPackage 'FiloSottile.mkcert'
    # winget may add portable executables to PATH during this process.
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
    $dockerDesktop = @("$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe", "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($dockerDesktop) { Start-Process $dockerDesktop }
    Write-Host 'Docker Desktop: erste Freigabe und WSL-Integration fuer deine Distribution bestaetigen.'
    if ($WindowsPackagesOnly) { exit 0 }
    $distros = & wsl.exe --list --quiet 2>$null
    if ($LASTEXITCODE -ne 0 -or -not (($distros -join '').Replace([string][char]0,'').Trim())) {
        Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile','-Command','wsl --install -d Ubuntu --no-launch'
        Write-Host 'Falls erforderlich Windows neu starten. Ubuntu einmal oeffnen, Linux-Benutzer anlegen und dieses Skript erneut starten.'
        exit 0
    }
    $target = @()
    if ($Distribution) { $target = @('--distribution',$Distribution) }
    if ($PSScriptRoot -match '^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(\\.*)?$') {
        if ($Distribution -and $Distribution -ne $Matches[1]) { throw 'Das Repository liegt in einer anderen WSL-Distribution.' }
        $Distribution = $Matches[1]
        $target = @('--distribution',$Distribution)
        $linuxRoot = $Matches[2].Replace('\','/')
    } else {
        $linuxRoot = (& wsl.exe @target --exec wslpath -u $PSScriptRoot) -join "`n"
        if ($LASTEXITCODE -ne 0) { throw 'Repository-Pfad in WSL nicht erreichbar. Repository in deiner WSL2-Distribution ablegen.' }
    }
    & wsl.exe @target --exec bash ($linuxRoot.Trim() + '/scripts/install-host.sh')
    if ($LASTEXITCODE -ne 0) { throw 'Linux-Einrichtung nicht abgeschlossen. Hinweise im Terminal beachten.' }
    Write-Host 'Jetzt Start-wsc-local.cmd oeffnen.'
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
