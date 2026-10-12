# YouTube Downloader website

独立的中英双语静态官网。无生产依赖，无服务端，无 Tauri 调用。

## 本地构建与预览

需要 Node.js 22 或更新版本：

```bash
cd website
npm run build
npm test
npm run preview
```

预览地址：`http://127.0.0.1:4173/`。中文 `/zh/`、英文 `/en/`，根路径跳转中文。页面 HTML 完整生成，可直接访问或刷新语言路径，不需要 SPA 回退规则。

## EdgeOne Pages

连接当前 GitHub 仓库，并在构建配置中设置：

| 设置 | 值 |
| --- | --- |
| 框架 | Other / 自定义静态网站 |
| 根目录 | `website` |
| 构建命令 | `npm run build` |
| 输出目录 | `dist` |
| Node.js | 22 或更新版本 |

页面构建无需安装依赖。不使用当前仓库根目录的桌面应用构建命令，也不使用 `dist-web` 输出。

在 EdgeOne 环境变量中配置下表，然后重新部署。正式环境和预览环境可使用不同设置；预览环境留空 Umami 两项可避免测试流量污染正式统计。

| 环境变量 | 用途 | 示例 |
| --- | --- | --- |
| `SITE_URL` | 当前网站完整域名，用于 canonical、分享图片绝对地址、hreflang 和站点地图 | `https://your-domain.example` |
| `UMAMI_SCRIPT_URL` | 从 Umami 网站跟踪代码取得的脚本地址 | `https://your-umami.example/script.js` |
| `UMAMI_WEBSITE_ID` | 跟踪代码的 `data-website-id` | 复制实际 Website ID |

`SITE_URL` 只填写协议和域名，不带子路径、参数或片段。支持域名根路径部署。未配置时可以本地预览，但正式分享前必须填写并重建。不要把 Umami 管理后台密码、API Token 或任何密钥放进上述变量。

Umami 两项都留空时不加载跟踪脚本；只填写一项会导致构建报错，以防部署成错误的统计配置。脚本在每个语言页面加载一次，使用 Umami 的自动页面访问统计及声明式点击事件，不另外调用 `umami.track()`：

| 事件 | 触发 | 属性 |
| --- | --- | --- |
| `download_click` | 前往 GitHub 最新发布页 | `language`, `position` |
| `github_click` | 查看源码或 MIT 许可证 | `language`, `position` |
| `language_switch` | 切换语言 | `language`（切换前）, `position` |

`position` 用于区分首屏、快速上手、开源区域和页脚等入口。下载入口点击表示下载意向，无法确认用户是否下载或安装。该接入仅发生在官网，属性不包含视频链接、Cookie、本地目录或下载记录。

上线后访问两种语言页面，点击下载、源码和语言切换，再确认 Umami 后台收到页面访问和上述事件；如果没有数据，检查脚本请求、实例可访问性、Website ID、域名限制和浏览器屏蔽设置。脚本不可用时页面与所有链接仍能工作。

## 文案、Logo 与图片

- `content.mjs` 维护双语文案，`build.mjs` 共用页面模板。
- 构建从仓库 `resources/icons/` 复制原始方形与横版 Logo，保持原始比例。
- `public/assets/app-preview.png` 来自现有 React 应用界面，以本地虚拟数据展示，不是实际下载记录。英语页面明确注明界面为中文。
- `public/assets/share-zh.png` 与 `share-en.png` 是 1200×630 分享缩略图，包含原始项目 Logo 和对应语言的免费开源文案。
- 所有图片随站点部署，不依赖第三方图片 CDN。正式域名配置后，页面为 Open Graph 和 Twitter Card 提供绝对图片地址。

图片已提交，日常构建不用浏览器。需要更新时，可使用可选维护工具（Playwright 及 Chrome 仅用于生成图片）：

1. 在仓库根目录安装开发依赖，并运行 `npm run dev`。
2. 在临时工具目录安装 Playwright：`npm install --prefix /tmp/ytd-website-tools playwright`。
3. 在仓库根目录运行：

```bash
PLAYWRIGHT_MODULE=/tmp/ytd-website-tools/node_modules/playwright/index.mjs \
CHROME_PATH=/path/to/google-chrome \
node website/tools/generate-images.mjs
```

可通过 `APP_PREVIEW_URL` 指定应用开发服务器地址。工具只在自己的浏览器上下文内模拟 Tauri 数据，不修改桌面应用；截图中的内容标注为示例。重新生成后应检查图片布局并再次运行网站构建与测试。

## 发布前检查

确认移动与桌面布局、键盘焦点、FAQ 展开、语言切换、GitHub 链接、Logo 比例和分享图片。用正式域名配置构建后检查 `/sitemap.xml`、`/robots.txt` 及分享元数据。真实 EdgeOne 发布和 Umami 上报验证需要对应项目权限与配置。
