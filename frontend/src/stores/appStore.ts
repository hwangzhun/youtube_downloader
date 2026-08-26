import { create } from "zustand";
import { api } from "../services/api";
import type { DownloadDraft, DownloadTask, RuntimeStatus, Settings, TaskEvent } from "../types";

const defaultSettings: Settings = {
  outputDir: "",
  proxyUrl: "",
  proxyEnabled: false,
  maxConcurrent: 2,
  firstRunNoticePending: true,
};

interface AppState {
  runtime?: RuntimeStatus;
  settings: Settings;
  tasks: Record<string, DownloadTask>;
  queuePaused: boolean;
  busy: boolean;
  error?: string;
  drafts: DownloadDraft[];
  theme: "light" | "dark";
  bootstrap: () => Promise<void>;
  refreshRuntime: () => Promise<void>;
  applyTaskEvent: (event: TaskEvent) => void;
  saveSettings: (settings: Settings) => Promise<void>;
  setQueuePaused: (paused: boolean) => Promise<void>;
  clearError: () => void;
  addDrafts: (drafts: DownloadDraft[]) => void;
  updateDraft: (id: string, patch: Partial<DownloadDraft>) => void;
  removeDraft: (id: string) => void;
  clearDrafts: () => void;
  toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  settings: defaultSettings,
  tasks: {},
  queuePaused: false,
  busy: false,
  error: undefined,
  drafts: [],
  theme: localStorage.getItem("theme") === "light" ? "light" : "dark",
  bootstrap: async () => {
    set({ busy: true, error: undefined });
    try {
      const [runtime, settings, tasks] = await Promise.all([
        api.runtimeStatus(), api.getSettings(), api.listTasks(),
      ]);
      set({ runtime, settings, tasks: Object.fromEntries(tasks.map((task) => [task.id, task])) });
    } catch (error) {
      set({ error: normalizeError(error) });
    } finally {
      set({ busy: false });
    }
  },
  refreshRuntime: async () => {
    const runtime = await api.runtimeStatus();
    set({ runtime });
  },
  applyTaskEvent: (event) => {
    if (event.event === "snapshot") {
      set({ tasks: { ...get().tasks, [event.data.id]: event.data } });
    } else {
      set({ queuePaused: event.data.paused });
    }
  },
  saveSettings: async (settings) => {
    const saved = await api.saveSettings(settings);
    set({ settings: saved });
  },
  setQueuePaused: async (paused) => {
    await api.setQueuePaused(paused);
    set({ queuePaused: paused });
  },
  clearError: () => set({ error: undefined }),
  addDrafts: (drafts) => set({
    drafts: [...get().drafts.filter((item) => !drafts.some((next) => next.video.url === item.video.url)), ...drafts],
  }),
  updateDraft: (id, patch) => set({
    drafts: get().drafts.map((item) => item.id === id ? { ...item, ...patch } : item),
  }),
  removeDraft: (id) => set({ drafts: get().drafts.filter((item) => item.id !== id) }),
  clearDrafts: () => set({ drafts: [] }),
  toggleTheme: () => {
    const theme = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", theme);
    set({ theme });
  },
}));

export function normalizeError(error: unknown): string {
  if (error && typeof error === "object") {
    const record = error as Record<string, unknown>;
    if (typeof record.message === "string") return record.message;
    const user = record.user;
    if (user && typeof user === "object" && "message" in user) {
      return String((user as Record<string, unknown>).message);
    }
    if (typeof record.internal === "string") return `内部错误：${record.internal}`;
  }
  if (error instanceof Error) return error.message;
  if (typeof error === "string") {
    try {
      const parsed = JSON.parse(error) as Record<string, unknown>;
      if (typeof parsed.message === "string") return parsed.message;
    } catch {
      return error || "发生未知错误";
    }
    return error;
  }
  return "发生未知错误";
}



