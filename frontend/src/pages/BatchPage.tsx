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

export function BatchPage() {
  const navigate = useNavigate();
  const [text, setText] = useSessionState("page.batch.text", "");
  const [useCookie, setUseCookie] = useSessionState("page.batch.cookie", false);
  const [videos, setVideos] = useSessionState<VideoInfo[]>("page.batch.videos", []);
  const [selectedUrls, setSelectedUrls] = useSessionState<string[]>("page.batch.selected", []);
  const selected = new Set(selectedUrls);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const { settings, addDrafts } = useAppStore();
  const urls = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  const parse = async () => {
    setLoading(true); setError(""); setVideos([]);
    try {
      const results: VideoInfo[] = [];
      for (let index = 0; index < urls.length; index += 1) {
        setProgress(`正在解析 ${index + 1} / ${urls.length}`);
        const request = { url: urls[index], useCookie, proxyUrl: settings.proxyEnabled && settings.proxyUrl ? settings.proxyUrl : undefined };
        const value = /[?&]list=|\/playlist/i.test(urls[index])
          ? await api.expandPlaylist(request) : [await api.parseVideo(request)];
        results.push(...value);
      }
      const unique = [...new Map(results.map((video) => [video.url, video])).values()];
      setVideos(unique); setSelectedUrls(unique.map((video) => video.url));
    } catch (reason) { setError(normalizeError(reason)); }
    finally { setLoading(false); setProgress(""); }
  };

  const add = () => {
    addDrafts(videos.filter((video) => selected.has(video.url)).map((video) => createDraft(video, useCookie)));
    navigate("/downloads");
  };

  const toggle = (url: string, checked: boolean) => {
    const next = new Set(selected);
    checked ? next.add(url) : next.delete(url);
    setSelectedUrls([...next]);
  };

  return (
    <>
      <PageHeader eyebrow="MULTIPLE VIDEOS" title="多视频下载" description="输入链接后先解析内容，确认选择，再加入下载列表。" />
      <section className="card">
        <label className="field"><span>链接列表 · {urls.length} 条</span>
          <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={"每行一个视频或播放列表链接\nhttps://youtu.be/..."} />
        </label>
        <div className="toolbar">
          <label className="check"><input type="checkbox" checked={useCookie} onChange={(e) => setUseCookie(e.target.checked)} />使用 Cookie</label>
          <button className="primary push-right" disabled={!urls.length || loading} onClick={parse}><Icon name="manage_search" />{loading ? progress : "解析全部"}</button>
        </div>
        {error && <p className="inline-error spaced">{error}</p>}
      </section>
      {loading && <ParsingStatus detail={progress} />}
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



