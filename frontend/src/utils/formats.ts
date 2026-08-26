import type { DownloadDraft, MediaFormat, VideoInfo } from "../types";

export const DEFAULT_VIDEO = "bestvideo";
export const DEFAULT_AUDIO = "bestaudio";

export function videoOptions(video: VideoInfo): MediaFormat[] {
  return video.formats.length ? video.formats : [{ formatId: DEFAULT_VIDEO, label: "最佳可用画质（推荐）" }];
}

export function audioOptions(video: VideoInfo): MediaFormat[] {
  return video.audioFormats.length ? video.audioFormats : [{ formatId: DEFAULT_AUDIO, label: "最佳可用音质（推荐）" }];
}

export function createDraft(video: VideoInfo, useCookie: boolean): DownloadDraft {
  return {
    id: crypto.randomUUID(),
    video,
    videoFormatId: videoOptions(video)[0].formatId,
    audioFormatId: audioOptions(video)[0].formatId,
    useCookie,
  };
}

export function combinedFormat(draft: DownloadDraft): string {
  return `${draft.videoFormatId}+${draft.audioFormatId}/best`;
}

export function durationText(seconds?: number): string {
  if (!seconds) return "";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}

