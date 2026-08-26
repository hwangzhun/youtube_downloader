import { useEffect, useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import type { ToolProgress, ToolUpdate } from "../types";

type UpdatingTarget = ToolUpdate["tool"] | "app";

export function VersionsPage() {
  const runtime = useAppStore((state) => state.runtime);
  const refreshRuntime = useAppStore((state) => state.refreshRuntime);
  const [updates, setUpdates] = useState<ToolUpdate[]>([]);
  const [checking, setChecking] = useState(false);
  const [appUpdateAvailable, setAppUpdateAvailable] = useState(false);
  const [updating, setUpdating] = useState<UpdatingTarget | null>(null);
  const [error, setError] = useState("");
  const [toolProgress, setToolProgress] = useState<ToolProgress>();
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

  const updateTool = async (tool: ToolUpdate["tool"], installed: boolean) => {
    const action = installed ? "更新" : "安装";
    setUpdating(tool);
    setToolProgress({ tool, percentage: 0, phase: "准备下载" });
    setError("");
    try {
      await api.updateTool(tool, setToolProgress);
      await refreshRuntime();
      setUpdates((current) => current.map((update) =>
        update.tool === tool ? { ...update, available: false, currentVersion: undefined } : update
      ));
    } catch (reason) {
      setError(`${tool === "ytDlp" ? "yt-dlp" : "ffmpeg"} ${action}失败：${normalizeError(reason)}`);
    } finally {
      setUpdating(null);
      setToolProgress(undefined);
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
        description="检查应用和下载组件；组件安装或更新会显示实时进度，并在校验后原子切换。"
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
          const installed = available;
          const actionLabel = installed ? "更新" : "安装";
          const progress = isUpdating && toolProgress?.tool === tool ? toolProgress : undefined;
          return <div key={name} className={isUpdating ? "is-updating" : undefined}>
          <span><i className={available ? "ok" : "bad"} />{name}</span>
          <code>{installed && update?.available && update.latestVersion ? `${displayVersion} → ${update.latestVersion}` : displayVersion}</code>
          {tool && (!installed || update?.available)
            ? <button className="ghost loading-button" disabled={updating !== null} onClick={() => void updateTool(tool, installed)}>
                {isUpdating && <span className="spinner" aria-hidden="true" />}
                {isUpdating ? `${actionLabel}中 ${progress?.percentage ?? 0}%` : actionLabel}
              </button>
            : <small>{available ? "已就绪" : name === "ffprobe" ? "随 FFmpeg 安装" : "需要安装"}</small>}
          {progress && <div className="component-update-progress">
            <div><span>{progress.phase}</span><b>{progress.percentage}%</b></div>
            <div className="component-progress-track"><i style={{ width: `${progress.percentage}%` }} /></div>
          </div>}
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
