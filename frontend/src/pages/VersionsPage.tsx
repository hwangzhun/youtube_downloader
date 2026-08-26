import { useEffect, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import type { ToolUpdate } from "../types";

type UpdatingTarget = ToolUpdate["tool"] | "app";

export function VersionsPage() {
  const runtime = useAppStore((state) => state.runtime);
  const [updates, setUpdates] = useState<ToolUpdate[]>([]);
  const [checking, setChecking] = useState(false);
  const [appUpdateAvailable, setAppUpdateAvailable] = useState(false);
  const [updating, setUpdating] = useState<UpdatingTarget | null>(null);
  const [error, setError] = useState("");
  const tools = runtime ? [
    ["应用", runtime.appVersion, true],
    ["yt-dlp", runtime.ytDlp.version || "未安装", runtime.ytDlp.available],
    ["ffmpeg", runtime.ffmpeg.version || "未安装", runtime.ffmpeg.available],
    ["ffprobe", runtime.ffprobe.version || "未安装", runtime.ffprobe.available],
    ["JavaScript Runtime", runtime.javascriptRuntime.version || "未检测到", runtime.javascriptRuntime.available],
  ] as const : [];

  const checkUpdates = async () => {
    setChecking(true);
    setError("");
    try {
      const [toolResult, appResult] = await Promise.allSettled([
        api.checkToolUpdates(),
        api.checkAppUpdate(),
      ]);
      const errors: string[] = [];
      if (toolResult.status === "fulfilled") setUpdates(toolResult.value);
      else errors.push(`组件检查失败：${normalizeError(toolResult.reason)}`);
      if (appResult.status === "fulfilled") setAppUpdateAvailable(appResult.value);
      else {
        setAppUpdateAvailable(false);
        errors.push(`应用检查失败：${normalizeError(appResult.reason)}`);
      }
      setError(errors.join("；"));
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => { void checkUpdates(); }, []);

  const updateTool = async (tool: ToolUpdate["tool"]) => {
    setUpdating(tool);
    setError("");
    try {
      await api.updateTool(tool);
      setUpdates((current) => current.map((update) =>
        update.tool === tool ? { ...update, available: false, currentVersion: update.latestVersion } : update
      ));
    } catch (reason) {
      setError(`${tool === "ytDlp" ? "yt-dlp" : "ffmpeg"} 更新失败：${normalizeError(reason)}`);
    } finally {
      setUpdating(null);
    }
  };

  const installAppUpdate = async () => {
    setUpdating("app");
    setError("");
    try {
      await api.installAppUpdate();
      setAppUpdateAvailable(false);
    } catch (reason) {
      setError(`应用更新失败：${normalizeError(reason)}`);
    } finally {
      setUpdating(null);
    }
  };

  return (
    <>
      <PageHeader eyebrow="RUNTIME" title="版本与组件"
        description="检查应用和下载组件；组件更新会校验后原子切换。" 
        action={<button className="ghost loading-button" disabled={checking || updating !== null} onClick={() => void checkUpdates()}>
          {checking && <span className="spinner" aria-hidden="true" />}
          {checking ? "检查中…" : "检查更新"}
        </button>} />
      {error && <div className="alert error update-error" role="alert">
        <span>{error}</span><button onClick={() => setError("")}>关闭</button>
      </div>}
      <section className="card version-list">
        {tools.map(([name, version, available]) => {
          const tool = name === "yt-dlp" ? "ytDlp" : name === "ffmpeg" ? "ffmpeg" : null;
          const update = tool ? updates.find((item) => item.tool === tool) : undefined;
          const isUpdating = tool !== null && updating === tool;
          const displayVersion = update?.currentVersion || version;
          return <div key={name} className={isUpdating ? "is-updating" : undefined}>
          <span><i className={available ? "ok" : "bad"} />{name}</span>
          <code>{update?.available && update.latestVersion ? `${displayVersion} → ${update.latestVersion}` : displayVersion}</code>
          {update?.available && tool
            ? <button className="ghost loading-button" disabled={updating !== null} onClick={() => void updateTool(tool)}>
                {isUpdating && <span className="spinner" aria-hidden="true" />}
                {isUpdating ? "更新中…" : "更新"}
              </button>
            : <small>{available ? "已就绪" : "需要安装"}</small>}
          </div>;
        })}
      </section>
      {appUpdateAvailable && <section className={`card notice app-update-notice${updating === "app" ? " is-updating" : ""}`}>
        <strong>应用更新</strong>
        <p>GitHub 上有新的应用版本可用。更新完成后请重新启动应用。</p>
        <button className="primary loading-button" disabled={updating !== null} onClick={() => void installAppUpdate()}>
          {updating === "app" && <span className="spinner" aria-hidden="true" />}
          {updating === "app" ? "更新中…" : "立即更新"}
        </button>
      </section>}
    </>
  );
}
