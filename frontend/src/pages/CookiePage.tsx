import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useState } from "react";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { api } from "../services/api";
import { normalizeError } from "../stores/appStore";
import type { CookieStatus } from "../types";

export function CookiePage() {
  const [status, setStatus] = useState<CookieStatus>({ state: "missing", message: "尚未配置 Cookie", cookieCount: 0 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.cookieStatus().then(setStatus).catch(() => undefined); }, []);
  const run = async (action: () => Promise<CookieStatus>) => {
    setBusy(true); setError("");
    try { setStatus(await action()); } catch (reason) { setError(normalizeError(reason)); }
    finally { setBusy(false); }
  };
  const importFile = async () => {
    const path = await open({ multiple: false, filters: [{ name: "Netscape Cookie", extensions: ["txt", "cookies"] }] });
    if (typeof path === "string") await run(() => api.importCookieFile(path));
  };

  return (
    <>
      <PageHeader eyebrow="AUTH" title="Cookie 与网页登录" description="通过网页登录或手动导入保存 Cookie，再在状态卡中联网验证登录状态。" />
      <section className="status-card cookie-status-card">
        <span className={`status-dot ${status.state}`} />
        <div className="status-copy">
          <strong>{status.message}</strong>
          <small>
            {status.cookieCount ? `已保存 ${status.cookieCount} 条 Cookie` : "可通过网页登录或 Netscape 文件导入"}
            {status.source ? ` · 来源：${status.source === "webview" ? "网页登录" : "手动导入"}` : ""}
          </small>
        </div>
        <button className="primary status-action" disabled={busy || status.state === "missing"} onClick={() => run(api.validateCookie)}>
          <Icon name="verified_user" />{busy ? "验证中…" : "验证 Cookie"}
        </button>
      </section>
      {error && <div className="alert error">{error}</div>}
      <div className="two-columns">
        <section className="card">
          <span className="eyebrow">WEBVIEW2</span><h2>网页登录</h2>
          <p>打开隔离的 YouTube 登录窗口。完成登录后回到这里获取 Cookie。</p>
          <div className="stack">
            <button className="primary" disabled={busy} onClick={() => api.openLoginWindow()}><Icon name="login" />打开登录窗口</button>
            <button className="ghost" disabled={busy} onClick={() => run(api.captureLoginCookies)}><Icon name="cookie" />完成登录并获取 Cookie</button>
            <button className="text-button" onClick={() => api.clearLoginProfile()}><Icon name="delete_sweep" />清除网页登录数据</button>
          </div>
        </section>
        <section className="card">
          <span className="eyebrow">NETSCAPE</span><h2>手动导入</h2>
          <p>选择由浏览器扩展导出的 Netscape Cookie 文件，内容会由 Windows DPAPI 保护。</p>
          <div className="stack">
            <button className="primary" disabled={busy} onClick={importFile}><Icon name="upload_file" />选择 Cookie 文件</button>
            <button className="text-button danger" onClick={async () => {
              await api.clearCookie();
              setStatus({ state: "missing", message: "Cookie 已清除", cookieCount: 0 });
            }}><Icon name="delete" />清除 Cookie</button>
          </div>
        </section>
      </div>
    </>
  );
}

