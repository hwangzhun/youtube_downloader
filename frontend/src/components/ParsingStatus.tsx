import { useEffect, useState } from "react";
import { Icon } from "./Icon";

const phases = [
  "正在连接 YouTube…",
  "正在读取视频信息…",
  "正在整理画质与音质选项…",
  "仍在处理中，请稍候…",
];

export function ParsingStatus({ detail }: { detail?: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const startedAt = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const phase = detail || phases[Math.min(Math.floor(elapsed / 4), phases.length - 1)];

  return (
    <div className="parsing-status" role="status" aria-live="polite">
      <div className="parsing-icon"><Icon name="sync" /></div>
      <div className="parsing-copy">
        <div><strong>{phase}</strong><span>已等待 {elapsed} 秒</span></div>
        <div className="parsing-progress"><i /></div>
        <small>部分视频、播放列表或使用 Cookie 时可能需要更长时间，请不要关闭页面。</small>
      </div>
    </div>
  );
}

