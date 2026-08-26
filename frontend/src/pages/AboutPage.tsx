import { openUrl } from "@tauri-apps/plugin-opener";
import { appIcon } from "../assets";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { useAppStore } from "../stores/appStore";

const REPOSITORY_URL = "https://github.com/hwangzhun/youtube_downloader";

export function AboutPage() {
  const runtime = useAppStore((state) => state.runtime);
  return (
    <>
      <PageHeader eyebrow="ABOUT" title="关于" description="简洁、安全的 Windows YouTube 下载工具。" />
      <section className="card about-hero">
        <img className="about-logo-image" src={appIcon} alt="YouTube Downloader" />
        <div className="about-title"><h2>YouTube Downloader</h2><p>版本 {runtime?.appVersion || "2.0.0"}</p></div>
        <button className="ghost about-github" onClick={() => openUrl(REPOSITORY_URL)}>
          <Icon name="code" />访问 GitHub 仓库<Icon name="open_in_new" />
        </button>
      </section>
      <div className="two-columns about-grid">
        <section className="card"><span className="eyebrow">AUTHOR</span><h2>作者信息</h2>
          <div className="author-row"><div className="author-avatar"><Icon name="person" /></div>
            <div><strong>hwangzhun</strong><p>项目作者与维护者</p></div></div>
        </section>
        <section className="card"><span className="eyebrow">OPEN SOURCE</span><h2>开源项目</h2>
          <p>应用基于 Tauri、React、yt-dlp 与 FFmpeg 构建。欢迎在 GitHub 提交问题和改进建议。</p>
          <button className="text-link" onClick={() => openUrl(REPOSITORY_URL)}>
            github.com/hwangzhun/youtube_downloader <Icon name="arrow_outward" />
          </button>
        </section>
      </div>
      <section className="card about-details">
        <div><span>应用版本</span><strong>{runtime?.appVersion || "—"}</strong></div>
        <div><span>yt-dlp 版本</span><strong>{runtime?.ytDlp.version || "未检测到"}</strong></div>
        <div><span>FFmpeg 版本</span><strong>{runtime?.ffmpeg.version || "未检测到"}</strong></div>
        <div><span>许可证</span><strong>MIT License</strong></div>
      </section>
      <section className="card privacy-note"><Icon name="shield_lock" /><div><strong>本地优先与隐私保护</strong>
        <p>解析与下载由本机 yt-dlp 执行。Cookie 使用 Windows DPAPI 加密，并只在任务执行或验证时临时解密。</p></div></section>
    </>
  );
}


