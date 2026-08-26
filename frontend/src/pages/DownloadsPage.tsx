import { useState } from "react";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { QualitySelectors } from "../components/QualitySelectors";
import { TaskTable } from "../components/TaskTable";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import { combinedFormat, durationText } from "../utils/formats";

export function DownloadsPage() {
  const {
    drafts, updateDraft, removeDraft, clearDrafts, settings, saveSettings,
    applyTaskEvent, queuePaused, setQueuePaused,
  } = useAppStore();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const chooseDir = async () => {
    const outputDir = await api.selectOutputDirectory();
    if (outputDir) await saveSettings({ ...settings, outputDir });
  };

  const startAll = async () => {
    if (!settings.outputDir || !drafts.length) return;
    setStarting(true); setError("");
    try {
      for (const draft of drafts) {
        await api.enqueueDownloads({
          urls: [draft.video.url],
          outputDir: settings.outputDir,
          formatId: combinedFormat(draft),
          useCookie: draft.useCookie,
          proxyUrl: settings.proxyEnabled && settings.proxyUrl ? settings.proxyUrl : undefined,
        }, applyTaskEvent);
      }
      clearDrafts();
    } catch (reason) {
      setError(normalizeError(reason));
    } finally { setStarting(false); }
  };

  return (
    <>
      <PageHeader eyebrow="DOWNLOADS" title="下载列表"
        description="在这里统一设置保存位置、调整每项画质与音质，然后开始全部下载。"
        action={<button className="ghost" onClick={() => setQueuePaused(!queuePaused)}><Icon name={queuePaused ? "play_arrow" : "pause"} />{queuePaused ? "继续下载" : "暂停下载"}</button>} />
      <section className="card download-settings">
        <label className="field grow"><span>全局保存位置</span>
          <button className="path-button" onClick={chooseDir}><Icon name="folder_open" />{settings.outputDir || "选择下载文件夹"}</button>
        </label>
        <div><small className="muted">此位置会保存为全局设置，之后的所有任务默认使用它。</small></div>
      </section>

      <section className="section-block">
        <div className="section-heading"><h2>待下载 · {drafts.length}</h2>
          {!!drafts.length && <button className="text-button danger" onClick={clearDrafts}><Icon name="delete_sweep" />清空列表</button>}
        </div>
        {!drafts.length ? <div className="empty">解析完成的视频会先出现在这里</div> :
          <div className="draft-list">
            {drafts.map((draft) => (
              <article className="draft-card" key={draft.id}>
                {draft.video.thumbnail ? <img src={draft.video.thumbnail} alt="" /> : <div className="draft-thumb"><Icon name="play_arrow" /></div>}
                <div className="draft-main">
                  <h3>{draft.video.title}</h3>
                  <p>{[draft.video.channel, durationText(draft.video.duration)].filter(Boolean).join(" · ")}</p>
                  <QualitySelectors video={draft.video} videoFormatId={draft.videoFormatId} audioFormatId={draft.audioFormatId}
                    onVideoChange={(videoFormatId) => updateDraft(draft.id, { videoFormatId })}
                    onAudioChange={(audioFormatId) => updateDraft(draft.id, { audioFormatId })} />
                </div>
                <button className="icon-button danger" title="移除" onClick={() => removeDraft(draft.id)}><Icon name="close" /></button>
              </article>
            ))}
          </div>}
        {error && <p className="inline-error spaced">{error}</p>}
        {!!drafts.length && <div className="download-bar">
          <span>{settings.outputDir ? `准备下载 ${drafts.length} 个视频` : "请先选择保存位置"}</span>
          <button className="primary loading-button" disabled={!settings.outputDir || starting} onClick={startAll}>
            {starting ? <span className="spinner" aria-hidden="true" /> : <Icon name="download" />}
            {starting ? "正在加入任务…" : "开始全部下载"}
          </button>
        </div>}
      </section>

      <section className="section-block"><div className="section-heading"><h2>下载任务</h2></div><TaskTable /></section>
    </>
  );
}



