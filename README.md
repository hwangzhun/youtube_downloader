# YouTube Downloader

![YouTube Downloader](https://cdn.jsdelivr.net/gh/hwangzhun/youtube_downloader@main/resources/icons/app_icon_horizontal.png "YouTube Downloader")

一款的开源 YouTube 下载工具。2.0 版本已从 Python/PyQt 重构为
Tauri 2 + Rust + React，界面更轻量，下载、Cookie 与组件更新由本机 Rust 后端管理。

## 主要功能

- 单视频解析，可分别选择视频画质与音频质量
- 多链接批量解析、选择和下载
- 获取频道视频并批量加入下载列表
- 下载队列、实时进度、暂停队列及完成后打开目录
- 网页登录或导入 Netscape 文件获取 Cookie
- 使用 Windows DPAPI 加密本地 Cookie，仅在任务执行或验证时临时解密
- 支持 HTTP、HTTPS 和 SOCKS5 代理
- 检查并更新 `yt-dlp`、`ffmpeg` 与应用版本
- 明亮/暗黑主题、系统托盘、单实例运行和窗口状态恢复

## 系统要求

### 使用安装包

- Windows 10/11 x64
- Microsoft Edge WebView2 Runtime
- 可访问 YouTube 及 GitHub Releases 的网络连接

项目提供两种 NSIS 安装包：

- **Lite**：不附带下载组件，安装后在“版本与组件”页面获取
- **Core**：内置 `yt-dlp`、`ffmpeg`、`ffprobe` 及必要 DLL，安装后即可使用

## 本地开发

需要预先安装：

- Node.js 22
- Rust stable
- Visual Studio Build Tools（Desktop development with C++）
- WebView2 Runtime

```powershell
npm install
npm run tauri dev
```

只检查前端：

```powershell
npm run build
npm test
```

检查 Rust 后端：

```powershell
cargo test --manifest-path src-tauri/Cargo.toml
```

开发时可以通过 `YTDLP_PATH`、`FFMPEG_PATH` 和 `FFPROBE_PATH` 指向本地组件。
未设置时，应用会读取自己的应用数据目录，不依赖全局 Python 环境。

## 构建安装包

构建 Lite、Core 或全部变体：

```powershell
npm run build:lite
npm run build:core
npm run build:variants
```

安装包输出到 `dist-installers/`。Core 构建会下载并校验官方发布的下载组件；完整说明见
[BUILD_VARIANTS.md](BUILD_VARIANTS.md)。

正式发布前必须配置 Tauri updater 公钥，并在 CI Secrets 中设置：

- `TAURI_SIGNING_PRIVATE_KEY`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`

迁移和发布注意事项见 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)。

## 项目结构

```text
frontend/       React + TypeScript 界面
src-tauri/      Tauri 2 / Rust 后端
scripts/        下载组件与安装包构建脚本
.github/        Windows CI 与发布流程
resources/      应用图标等静态资源
```

## 从旧版升级

Tauri 2 版本使用新的应用标识和数据目录，不会读取或删除旧版 Python/PyQt 的设置、
Cookie、缓存或下载组件。首次启动后请重新选择下载目录，并按需重新登录或导入 Cookie。

## 使用提示

1. 首次使用 Lite 版时，先在“版本与组件”页面安装 `yt-dlp` 与 FFmpeg。
2. 下载受限内容时，在“Cookie”页面登录或导入 Netscape Cookie 文件，再在解析页面启用 Cookie。
3. 解析或下载失败时，先检查网络、代理、Cookie 状态和下载组件版本。
4. 请只下载你有权保存的内容，并遵守所在地法律及 YouTube 服务条款。

## 免责声明

本项目仅供个人学习与研究使用。使用者应自行确认下载行为获得授权，并承担使用本软件产生的责任。


<p align="center">
  <a href="https://developers.openai.com/codex/">
    <img src="https://img.shields.io/badge/AI%20辅助开发-OpenAI%20Codex-111111?style=for-the-badge&logo=openai&logoColor=white" alt="由 OpenAI Codex 辅助开发" />
  </a>
</p>

本项目在重构、测试和文档编写过程中使用了 [OpenAI Codex](https://developers.openai.com/codex/) 辅助开发。

> Codex 是 OpenAI 的产品。本项目为独立开源项目，与 OpenAI 不存在隶属或官方合作关系。
