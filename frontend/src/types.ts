export type TaskStatus =
  | "pending" | "resolving" | "queued" | "downloading"
  | "postprocessing" | "completed" | "failed" | "cancelled";

export interface AppError {
  code: string;
  message: string;
  recoverable: boolean;
  details?: unknown;
}

export interface MediaFormat {
  formatId: string;
  label: string;
  extension?: string;
  width?: number;
  height?: number;
  fps?: number;
  fileSize?: number;
  videoCodec?: string;
  audioCodec?: string;
}

export interface VideoInfo {
  id: string;
  url: string;
  title: string;
  channel?: string;
  duration?: number;
  thumbnail?: string;
  formats: MediaFormat[];
  audioFormats: MediaFormat[];
}

export interface ParseRequest {
  url: string;
  useCookie: boolean;
  proxyUrl?: string;
}

export interface DownloadRequest {
  urls: string[];
  outputDir: string;
  formatId: string;
  useCookie: boolean;
  proxyUrl?: string;
}

export interface DownloadTask {
  id: string;
  url: string;
  title?: string;
  outputDir: string;
  formatId: string;
  status: TaskStatus;
  progress: number;
  speed?: string;
  eta?: string;
  error?: string;
  createdAt: string;
}

export type TaskEvent =
  | { event: "snapshot"; data: DownloadTask }
  | { event: "queuePaused"; data: { paused: boolean } };

export interface RuntimeTool {
  available: boolean;
  version?: string;
  path?: string;
}

export interface RuntimeStatus {
  appVersion: string;
  webview2: RuntimeTool;
  ytDlp: RuntimeTool;
  ffmpeg: RuntimeTool;
  ffprobe: RuntimeTool;
  javascriptRuntime: RuntimeTool;
}

export interface CookieStatus {
  state: "missing" | "valid" | "invalid" | "unverified";
  source?: "import" | "webview";
  message: string;
  cookieCount: number;
}

export interface Settings {
  outputDir: string;
  proxyUrl: string;
  proxyEnabled: boolean;
  maxConcurrent: number;
  firstRunNoticePending: boolean;
}

export interface DownloadDraft {
  id: string;
  video: VideoInfo;
  videoFormatId: string;
  audioFormatId: string;
  useCookie: boolean;
}

export interface ToolProgress {
  tool: "ytDlp" | "ffmpeg";
  percentage: number;
  phase: string;
}

export interface ToolUpdate {
  tool: "ytDlp" | "ffmpeg";
  currentVersion?: string;
  latestVersion?: string;
  available: boolean;
}



