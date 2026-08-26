import { Channel, invoke } from "@tauri-apps/api/core";
import type {
  CookieStatus,
  DownloadRequest,
  DownloadTask,
  ParseRequest,
  RuntimeStatus,
  Settings,
  TaskEvent,
  ToolProgress,
  ToolUpdate,
  VideoInfo,
} from "../types";

export const api = {
  runtimeStatus: () => invoke<RuntimeStatus>("get_runtime_status"),
  parseVideo: (request: ParseRequest) =>
    invoke<VideoInfo>("parse_video", { request }),
  expandPlaylist: (request: ParseRequest) =>
    invoke<VideoInfo[]>("expand_playlist", { request }),
  fetchChannel: (request: ParseRequest) =>
    invoke<VideoInfo[]>("fetch_channel", { request }),
  listTasks: () => invoke<DownloadTask[]>("list_tasks"),
  enqueueDownloads: async (
    request: DownloadRequest,
    onEvent: (event: TaskEvent) => void,
  ) => {
    const channel = new Channel<TaskEvent>();
    channel.onmessage = onEvent;
    return invoke<string[]>("enqueue_downloads", { request, onEvent: channel });
  },
  cancelTask: (id: string) => invoke<void>("cancel_task", { id }),
  retryTask: (id: string) => invoke<void>("retry_task", { id }),
  openTaskDirectory: (id: string) => invoke<void>("open_task_directory", { id }),
  setQueuePaused: (paused: boolean) =>
    invoke<void>("set_queue_paused", { paused }),
  getSettings: () => invoke<Settings>("get_settings"),
  saveSettings: (settings: Settings) =>
    invoke<Settings>("save_settings", { settings }),
  testProxy: (proxyUrl: string) => invoke<string>("test_proxy", { proxyUrl }),
  selectOutputDirectory: () =>
    invoke<string | null>("select_output_directory"),
  openLoginWindow: () => invoke<void>("open_login_window"),
  captureLoginCookies: () =>
    invoke<CookieStatus>("capture_login_cookies"),
  clearLoginProfile: () => invoke<void>("clear_login_profile"),
  importCookieFile: (path: string) =>
    invoke<CookieStatus>("import_cookie_file", { path }),
  validateCookie: () => invoke<CookieStatus>("validate_cookie"),
  clearCookie: () => invoke<void>("clear_cookie"),
  cookieStatus: () => invoke<CookieStatus>("get_cookie_status"),
  checkToolUpdates: () => invoke<ToolUpdate[]>("check_tool_updates"),
  updateTool: async (tool: ToolUpdate["tool"], onProgress: (progress: ToolProgress) => void) => {
    const channel = new Channel<ToolProgress>();
    channel.onmessage = onProgress;
    return invoke<void>("update_tool", { tool, onProgress: channel });
  },
  checkAppUpdate: () => invoke<boolean>("check_app_update"),
  installAppUpdate: () => invoke<void>("install_app_update"),
};
