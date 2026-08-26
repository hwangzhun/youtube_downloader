# 双版本构建

项目提供两个 Windows NSIS 安装包：

- **Lite**：不附带 yt-dlp、FFmpeg。安装后在“版本与组件”页面下载。
- **Core**：附带 yt-dlp、ffmpeg、ffprobe 和 FFmpeg shared build 所需 DLL，可在离线环境直接使用下载核心。

## 命令

```powershell
npm run build:lite
npm run build:core
npm run build:variants
```

强制重新下载最新核心：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-variants.ps1 -Variant Core -RefreshTools
```

安装包统一输出到 `dist-installers`。核心工具是安装包中的独立资源文件，并非链接进主程序 EXE。

