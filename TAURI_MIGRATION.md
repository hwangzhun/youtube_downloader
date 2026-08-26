# Tauri 2 开发与发布

桌面应用位于 `frontend/` 与 `src-tauri/`，版本为 2.0.0，仅支持 Windows 10/11 x64。旧 Python/PyQt 源码、依赖和构建流程已从本分支移除，发布产物仅由 Tauri 工具链生成。

## 开发

需要 Node.js 22、Rust stable、MSVC Build Tools 和 WebView2。

```powershell
npm install
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
npm run tauri dev
```

开发时可通过 `YTDLP_PATH`、`FFMPEG_PATH` 和 `FFPROBE_PATH` 指定本地工具。没有指定时，应用读取新应用数据目录中的 `tools/active`，不会读取旧版 `%APPDATA%\YouTubeDownloader`。

## 内置下载组件

发布构建前运行：

```powershell
.\scripts\fetch-tools.ps1
```

脚本从 yt-dlp 与 BtbN GitHub Releases 下载 Windows x64构建，使用发布方的 SHA-256清单验证，只保留 `yt-dlp.exe`、`ffmpeg.exe`、`ffprobe.exe` 和共享 DLL，不包含 `ffplay.exe`。运行时更新执行同样的校验，并通过 staging/active/previous目录原子切换。

## 更新签名

`src-tauri/tauri.conf.json` 中的 `REPLACE_WITH_TAURI_UPDATER_PUBLIC_KEY` 必须在正式构建前替换为真实公钥。私钥只能写入 CI Secrets：

- `TAURI_SIGNING_PRIVATE_KEY`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

没有真实公钥时可以开发和测试，但产物不得发布。正式 `v2.*` 标签由 Windows CI获取组件并生成 NSIS和签名更新包。

## 旧版替换

Tauri版使用新的应用标识和数据目录，不读取或删除旧版设置、Cookie、缓存及二进制。正式安装器接入旧 Inno卸载钩子前，应在隔离 Windows VM验证旧版运行中、需要 UAC和取消卸载三个场景。
