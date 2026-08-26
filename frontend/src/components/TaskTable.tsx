import { useState } from "react";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";
import { Icon } from "./Icon";

const statusText: Record<string, string> = {
  pending: "等待处理",
  resolving: "解析中",
  queued: "排队中",
  downloading: "下载中",
  postprocessing: "合并处理中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const activeStatuses = ["pending", "resolving", "queued", "downloading", "postprocessing"];

export function TaskTable() {
  const tasks = Object.values(useAppStore((state) => state.tasks))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const apply = useAppStore((state) => state.applyTaskEvent);
  const queuePaused = useAppStore((state) => state.queuePaused);
  const activeTasks = tasks.filter((task) => activeStatuses.includes(task.status));
  const [actionError, setActionError] = useState("");

  if (!tasks.length) {
    return <div className="empty">下载任务会显示在这里</div>;
  }

  return (
    <div className="task-list">
      {actionError && <div className="alert error task-action-error" role="alert">
        <span>{actionError}</span><button onClick={() => setActionError("")}>关闭</button>
      </div>}
      {!!activeTasks.length && (
        <div className={`download-waiting${queuePaused ? " paused" : ""}`} role="status" aria-live="polite">
          <div className="download-waiting-icon"><Icon name={queuePaused ? "pause" : "downloading"} /></div>
          <div className="download-waiting-copy">
            <div>
              <strong>{queuePaused ? "下载队列已暂停" : `正在处理 ${activeTasks.length} 个下载任务`}</strong>
              <span>{queuePaused ? "点击继续下载以恢复任务" : "请保持应用运行"}</span>
            </div>
            <div className="download-waiting-progress"><i /></div>
          </div>
        </div>
      )}
      {tasks.map((task) => (
        <article className={`task-row task-${task.status}`} key={task.id}>
          <div className="task-main">
            <strong>{task.title || task.url}</strong>
            <small className="task-status">
              {activeStatuses.includes(task.status) && <span className="mini-spinner" aria-hidden="true" />}
              {statusText[task.status] || task.status}
            </small>
            <div className="progress-track">
              <span style={{ width: `${Math.max(0, Math.min(100, task.progress))}%` }} />
            </div>
          </div>
          <div className="task-meta">
            <b>{task.progress.toFixed(1)}%</b>
            <small>{task.speed || task.eta || ""}</small>
          </div>
          <div className="task-actions">
            {activeStatuses.includes(task.status) && (
              <button className="ghost" onClick={() => api.cancelTask(task.id)}>取消</button>
            )}
            {["failed", "cancelled"].includes(task.status) && (
              <button className="ghost" onClick={async () => {
                await api.retryTask(task.id);
                const updated = (await api.listTasks()).find((item) => item.id === task.id);
                if (updated) apply({ event: "snapshot", data: updated });
              }}>重试</button>
            )}
            {task.status === "completed" && (
              <button className="ghost" onClick={async () => {
                setActionError("");
                try {
                  await api.openTaskDirectory(task.id);
                } catch (reason) {
                  setActionError(`打开下载目录失败：${normalizeError(reason)}`);
                }
              }}><Icon name="folder_open" />打开目录</button>
            )}
          </div>
          {task.error && <p className="task-error">{task.error}</p>}
        </article>
      ))}
    </div>
  );
}
