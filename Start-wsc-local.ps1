[CmdletBinding()]
param(
    [string]$Distribution = '',
    [switch]$Check,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
try {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw 'WSL2 fehlt. In einer administrativen PowerShell: wsl --install. Danach Windows neu starten.'
    }
    $linuxRoot = ''
    if ($PSScriptRoot -match '^\\\\wsl(?:\.localhost|\$)\\([^\\]+)(\\.*)?$') {
        if ($Distribution -and $Distribution -ne $Matches[1]) {
            throw 'Das Repository liegt in einer anderen WSL-Distribution. Ohne -Distribution erneut starten.'
        }
        $Distribution = $Matches[1]
        $linuxRoot = $Matches[2].Replace('\', '/')
    }
    $wslTarget = @()
    if ($Distribution) { $wslTarget = @('--distribution', $Distribution) }
    $kernelOutput = & wsl.exe @wslTarget --exec uname -r 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'WSL konnte nicht starten. Mit wsl --list --verbose die Distributionen pruefen.' }
    $kernel = ($kernelOutput -join "`n").Replace([string][char]0, '').Trim()
    if ($kernel -notmatch '(?i)microsoft-standard|wsl2') {
        throw 'WSL2 wird benoetigt. Mit wsl --list --verbose den Distributionsnamen ermitteln, dann wsl --set-version NAME 2 ausfuehren.'
    }
    if (-not $linuxRoot) {
        $pathOutput = & wsl.exe @wslTarget --exec wslpath -u $PSScriptRoot 2>$null
        if ($LASTEXITCODE -ne 0) { throw 'Der Repository-Pfad konnte nicht nach WSL uebersetzt werden.' }
        $linuxRoot = ($pathOutput -join "`n").Replace([string][char]0, '').Trim()
    }
    Write-Host 'wsc-local startet in Windows/WSL2.'
    Write-Host 'Docker Desktop muss laufen; die WSL-Integration muss fuer diese Distribution aktiviert sein.'
    if ($Check) {
        & wsl.exe @wslTarget --exec python3 ($linuxRoot + '/wsc') check
    } else {
        $launchArguments = @('--exec', 'bash', ($linuxRoot + '/setup.sh'))
        if ($NoOpen) { $launchArguments += '--no-open' }
        & wsl.exe @wslTarget @launchArguments
    }
    exit $LASTEXITCODE
} catch {
    Write-Host ('Start nicht moeglich: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Anleitung: docs/platforms.md'
    exit 1
}
