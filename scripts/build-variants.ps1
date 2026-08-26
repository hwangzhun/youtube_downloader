param(
    [ValidateSet("Lite", "Core", "All")]
    [string]$Variant = "All",
    [switch]$RefreshTools
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$tauriRoot = Join-Path $repoRoot "src-tauri"
$tauriCli = Join-Path $repoRoot "node_modules\.bin\tauri.cmd"
$outputRoot = Join-Path $repoRoot "dist-installers"
$toolRoot = Join-Path $tauriRoot "resources\tools"
$version = (Get-Content -Raw -LiteralPath (Join-Path $tauriRoot "tauri.conf.json") | ConvertFrom-Json).version

if (-not (Test-Path -LiteralPath $tauriCli -PathType Leaf)) {
    throw "未找到 Tauri CLI。请先在项目根目录运行 npm install。"
}
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

function Test-CoreTools {
    $required = @("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe")
    foreach ($name in $required) {
        if (-not (Test-Path -LiteralPath (Join-Path $toolRoot $name) -PathType Leaf)) {
            return $false
        }
    }
    return @(Get-ChildItem -LiteralPath $toolRoot -Filter "*.dll" -File -ErrorAction SilentlyContinue).Count -gt 0
}

function Build-Variant {
    param(
        [string]$Name,
        [string]$Config,
        [string]$OutputLabel
    )

    Write-Host ""
    Write-Host "=== 构建 $Name 版本 ===" -ForegroundColor Cyan
    $startedAt = Get-Date
    Push-Location $repoRoot
    try {
        & $tauriCli build --config $Config
        if ($LASTEXITCODE -ne 0) { throw "$Name 版本构建失败，退出代码 $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }

    $bundleDir = Join-Path $tauriRoot "target\release\bundle\nsis"
    $installer = Get-ChildItem -LiteralPath $bundleDir -Filter "*.exe" -File |
        Where-Object { $_.LastWriteTime -ge $startedAt.AddSeconds(-2) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $installer) {
        throw "没有找到 $Name 版本的 NSIS 安装包"
    }

    $destination = Join-Path $outputRoot ("YouTube_Downloader_{0}_{1}_x64-setup.exe" -f $version, $OutputLabel)
    Copy-Item -LiteralPath $installer.FullName -Destination $destination -Force
    $sizeMb = [math]::Round((Get-Item -LiteralPath $destination).Length / 1MB, 2)
    Write-Host "完成：$destination ($sizeMb MB)" -ForegroundColor Green
}

if ($Variant -in @("Lite", "All")) {
    Build-Variant -Name "精简版（不带核心）" -Config "src-tauri/tauri.lite.conf.json" -OutputLabel "Lite"
}

if ($Variant -in @("Core", "All")) {
    if ($RefreshTools -or -not (Test-CoreTools)) {
        Write-Host "正在下载并校验 yt-dlp 与 FFmpeg 核心组件…" -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot "fetch-tools.ps1")
        if (-not $?) { throw "核心组件准备失败" }
    }
    if (-not (Test-CoreTools)) {
        throw "核心组件不完整，无法构建核心版"
    }
    Build-Variant -Name "核心版（内置核心）" -Config "src-tauri/tauri.core.conf.json" -OutputLabel "Core"
}

Write-Host ""
Write-Host "安装包输出目录：$outputRoot" -ForegroundColor Cyan



