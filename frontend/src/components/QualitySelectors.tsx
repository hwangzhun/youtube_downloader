import type { VideoInfo } from "../types";
import { audioOptions, videoOptions } from "../utils/formats";

export function QualitySelectors(props: {
  video: VideoInfo;
  videoFormatId: string;
  audioFormatId: string;
  onVideoChange: (value: string) => void;
  onAudioChange: (value: string) => void;
}) {
  return (
    <div className="quality-grid">
      <label className="field">
        <span>视频画质</span>
        <select value={props.videoFormatId} onChange={(event) => props.onVideoChange(event.target.value)}>
          {videoOptions(props.video).map((format) => (
            <option key={format.formatId} value={format.formatId}>{format.label}</option>
          ))}
        </select>
        <small>选择画面清晰度与帧率</small>
      </label>
      <label className="field">
        <span>音频音质</span>
        <select value={props.audioFormatId} onChange={(event) => props.onAudioChange(event.target.value)}>
          {audioOptions(props.video).map((format) => (
            <option key={format.formatId} value={format.formatId}>{format.label}</option>
          ))}
        </select>
        <small>下载时自动与视频合并</small>
      </label>
    </div>
  );
}

