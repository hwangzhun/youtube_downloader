param(
    [string]$YtDlpBaseUrl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download",
    [string]$FfmpegBaseUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$toolTarget = Join-Path $repoRoot "src-tauri\resources\tools"
$taskTemp = Join-Path ([IO.Path]::GetTempPath()) ("youtube-downloader-tools-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $taskTemp -Force | Out-Null
New-Item -ItemType Directory -Path $toolTarget -Force | Out-Null

function Assert-Checksum {
    param([string]$File, [string]$Manifest, [string]$AssetName)
    $line = Get-Content -LiteralPath $Manifest |
        Where-Object { $_ -match ("\s\*?" + [regex]::Escape($AssetName) + "$") } |
        Select-Object -First 1
    if (-not $line) { throw "发布校验清单中没有 $AssetName" }
    $expected = ($line -split "\s+")[0].ToLowerInvariant()
    $sha256 = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($File)
    try {
        $actual = ([BitConverter]::ToString($sha256.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
    if ($actual -ne $expected) { throw "$AssetName SHA-256 校验失败" }
}

try {
    $ytExe = Join-Path $taskTemp "yt-dlp.exe"
    $ytSums = Join-Path $taskTemp "yt-dlp-sha256.txt"
    Invoke-WebRequest "$YtDlpBaseUrl/yt-dlp.exe" -OutFile $ytExe
    Invoke-WebRequest "$YtDlpBaseUrl/SHA2-256SUMS" -OutFile $ytSums
    Assert-Checksum -File $ytExe -Manifest $ytSums -AssetName "yt-dlp.exe"

    $ffmpegName = "ffmpeg-master-latest-win64-gpl-shared.zip"
    $ffmpegZip = Join-Path $taskTemp $ffmpegName
    $ffmpegSums = Join-Path $taskTemp "ffmpeg-sha256.txt"
    Invoke-WebRequest "$FfmpegBaseUrl/$ffmpegName" -OutFile $ffmpegZip
    Invoke-WebRequest "$FfmpegBaseUrl/checksums.sha256" -OutFile $ffmpegSums
    Assert-Checksum -File $ffmpegZip -Manifest $ffmpegSums -AssetName $ffmpegName

    $extractDir = Join-Path $taskTemp "ffmpeg"
    Expand-Archive -LiteralPath $ffmpegZip -DestinationPath $extractDir
    $runtimeFiles = Get-ChildItem -LiteralPath $extractDir -Recurse -File |
        Where-Object {
            $_.Name -in @("ffmpeg.exe", "ffprobe.exe") -or $_.Extension -eq ".dll"
        }
    if (-not ($runtimeFiles.Name -contains "ffmpeg.exe") -or
        -not ($runtimeFiles.Name -contains "ffprobe.exe")) {
        throw "FFmpeg 压缩包缺少 ffmpeg.exe 或 ffprobe.exe"
    }

    Copy-Item -LiteralPath $ytExe -Destination (Join-Path $toolTarget "yt-dlp.exe") -Force
    foreach ($runtimeFile in $runtimeFiles) {
        Copy-Item -LiteralPath $runtimeFile.FullName -Destination (Join-Path $toolTarget $runtimeFile.Name) -Force
    }
    Write-Host "下载组件已验证并写入 $toolTarget"
}
finally {
    $resolvedTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $resolvedTaskTemp = [IO.Path]::GetFullPath($taskTemp)
    if ($resolvedTaskTemp.StartsWith($resolvedTempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedTaskTemp)) {
        Remove-Item -LiteralPath $resolvedTaskTemp -Recurse -Force
    }
}

