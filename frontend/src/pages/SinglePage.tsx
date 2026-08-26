import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { ParsingStatus } from "../components/ParsingStatus";
import { QualitySelectors } from "../components/QualitySelectors";
import { useSessionState } from "../hooks/useSessionState";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import type { VideoInfo } from "../types";
import { createDraft, durationText } from "../utils/formats";

export function SinglePage() {
  const navigate = useNavigate();
  const [url, setUrl] = useSessionState("page.single.url", "");
  const [video, setVideo] = useSessionState<VideoInfo | undefined>("page.single.video", undefined);
  const [videoFormatId, setVideoFormatId] = useSessionState("page.single.videoFormat", "bestvideo");
  const [audioFormatId, setAudioFormatId] = useSessionState("page.single.audioFormat", "bestaudio");
  const [useCookie, setUseCookie] = useSessionState("page.single.cookie", false);
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState("");
  const { settings, addDrafts } = useAppStore();

  const parse = async () => {
    setLoading(true); setLocalError(""); setVideo(undefined);
    try {
      const result = await api.parseVideo({ url: url.trim(), useCookie, proxyUrl: settings.proxyEnabled && settings.proxyUrl ? settings.proxyUrl : undefined });
      const draft = createDraft(result, useCookie);
      setVideo(result); setVideoFormatId(draft.videoFormatId); setAudioFormatId(draft.audioFormatId);
    } catch (error) {
      setLocalError(normalizeError(error));
    } finally { setLoading(false); }
  };

  const add = () => {
    if (!video) return;
    addDrafts([{ ...createDraft(video, useCookie), videoFormatId, audioFormatId }]);
    navigate("/downloads");
  };

  return (
    <>
      <PageHeader eyebrow="SINGLE VIDEO" title="单视频下载" description="先解析视频并确认画质与音质，再加入下载列表。" />
      <section className="card hero-card">
        <label className="field grow"><span>视频链接</span>
          <input value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void parse()}
            placeholder="https://www.youtube.com/watch?v=..." />
        </label>
        <button className="primary" disabled={!url.trim() || loading} onClick={parse}><Icon name="search" />{loading ? "解析中…" : "解析视频"}</button>
        <label className="check"><input type="checkbox" checked={useCookie} onChange={(e) => setUseCookie(e.target.checked)} />使用已保存 Cookie</label>
        {localError && <p className="inline-error">{localError}</p>}
      </section>
      {loading && <ParsingStatus />}
      {video && (
        <section className="card video-card">
          {video.thumbnail ? <img src={video.thumbnail} alt="" /> : <div className="thumbnail-placeholder"><Icon name="play_arrow" /></div>}
          <div className="video-copy">
            <span className="eyebrow">PARSED</span>
            <h2>{video.title}</h2>
            <p>{[video.channel, durationText(video.duration)].filter(Boolean).join(" · ")}</p>
            <QualitySelectors video={video} videoFormatId={videoFormatId} audioFormatId={audioFormatId}
              onVideoChange={setVideoFormatId} onAudioChange={setAudioFormatId} />
            <button className="primary wide" onClick={add}><Icon name="playlist_add" />加入下载列表</button>
          </div>
        </section>
      )}
    </>
  );
}



