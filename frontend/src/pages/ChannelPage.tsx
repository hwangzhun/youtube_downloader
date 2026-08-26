import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { ParsingStatus } from "../components/ParsingStatus";
import { useSessionState } from "../hooks/useSessionState";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import type { VideoInfo } from "../types";
import { createDraft } from "../utils/formats";

export function ChannelPage() {
  const navigate = useNavigate();
  const [url, setUrl] = useSessionState("page.channel.url", "");
  const [videos, setVideos] = useSessionState<VideoInfo[]>("page.channel.videos", []);
  const [selectedUrls, setSelectedUrls] = useSessionState<string[]>("page.channel.selected", []);
  const [useCookie, setUseCookie] = useSessionState("page.channel.cookie", false);
  const selected = new Set(selectedUrls);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { settings, addDrafts } = useAppStore();

  const parse = async () => {
    setLoading(true); setError(""); setVideos([]);
    try {
      const result = await api.fetchChannel({ url: url.trim(), useCookie, proxyUrl: settings.proxyEnabled && settings.proxyUrl ? settings.proxyUrl : undefined });
      setVideos(result); setSelectedUrls(result.map((item) => item.url));
    } catch (reason) { setError(normalizeError(reason)); }
    finally { setLoading(false); }
  };

  const add = () => {
    addDrafts(videos.filter((video) => selected.has(video.url)).map((video) => createDraft(video, useCookie)));
    navigate("/downloads");
  };

  const toggle = (videoUrl: string, checked: boolean) => {
    const next = new Set(selected);
    checked ? next.add(videoUrl) : next.delete(videoUrl);
    setSelectedUrls([...next]);
  };

  return (
    <>
      <PageHeader eyebrow="CHANNEL" title="频道下载" description="先读取频道视频，选择需要的内容，再统一加入下载列表。" />
      <section className="card hero-card">
        <label className="field grow"><span>频道链接</span>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/@channel/videos" />
        </label>
        <button className="primary" disabled={!url.trim() || loading} onClick={parse}><Icon name="manage_search" />{loading ? "解析频道中…" : "解析频道"}</button>
        <label className="check"><input type="checkbox" checked={useCookie} onChange={(e) => setUseCookie(e.target.checked)} />使用已保存 Cookie</label>
        {error && <p className="inline-error">{error}</p>}
      </section>
      {loading && <ParsingStatus detail="正在读取频道视频列表…" />}
      {!!videos.length && <section className="card result-card">
        <div className="toolbar no-margin"><strong>解析完成 · 已选择 {selected.size} / {videos.length}</strong>
          <button className="ghost push-right" onClick={() => setSelectedUrls(selected.size === videos.length ? [] : videos.map((v) => v.url))}>
            <Icon name={selected.size === videos.length ? "deselect" : "select_all"} />{selected.size === videos.length ? "取消全选" : "全选"}
          </button>
          <button className="primary" disabled={!selected.size} onClick={add}><Icon name="playlist_add" />加入下载列表</button>
        </div>
        <div className="selection-list">
          {videos.map((video) => <label key={video.url}>
            <input type="checkbox" checked={selected.has(video.url)} onChange={(e) => toggle(video.url, e.target.checked)} />
            <span>{video.title}</span><small>{video.channel || "YouTube"}</small>
          </label>)}
        </div>
      </section>}
    </>
  );
}



