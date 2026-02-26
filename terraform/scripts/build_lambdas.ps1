# Build Lambda deployment packages with dependencies (Windows)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TerraformDir = Split-Path -Parent $ScriptDir
$BuildDir = Join-Path $TerraformDir "build"
$LambdasDir = Join-Path $TerraformDir "lambdas"

if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Path $BuildDir | Out-Null

@("create_order", "generate_careplan", "get_order") | ForEach-Object {
    $name = $_
    Write-Host "Building $name..."
    $dir = Join-Path $LambdasDir $name
    $tmp = Join-Path $BuildDir "${name}_tmp"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Copy-Item (Join-Path $dir "index.py") $tmp
    pip install -q -r (Join-Path $dir "requirements.txt") -t $tmp
    Push-Location $tmp
    Compress-Archive -Path * -DestinationPath (Join-Path $BuildDir "${name}.zip") -Force
    Pop-Location
    Remove-Item -Recurse -Force $tmp
}

Write-Host "Done. Zips in $BuildDir"
