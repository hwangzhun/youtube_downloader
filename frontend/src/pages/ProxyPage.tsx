import { useState } from "react";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { useSessionState } from "../hooks/useSessionState";
import { api } from "../services/api";
import { normalizeError, useAppStore } from "../stores/appStore";

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error("代理测试超时，请检查代理地址和代理程序是否正在运行")), timeoutMs);
    promise.then(
      (value) => { window.clearTimeout(timer); resolve(value); },
      (error) => { window.clearTimeout(timer); reject(error); },
    );
  });
}

export function ProxyPage() {
  const { settings, saveSettings } = useAppStore();
  const [proxyUrl, setProxyUrl] = useSessionState("page.proxy.url", settings.proxyUrl);
  const [saved, setSaved] = useSessionState("page.proxy.saved", false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState("");
  const [testError, setTestError] = useState("");
  const valid = !proxyUrl || /^(https?|socks5):\/\//i.test(proxyUrl);
  const canEnable = Boolean(settings.proxyUrl);

  const toggleProxy = async () => {
    if (!canEnable && !settings.proxyEnabled) return;
    await saveSettings({ ...settings, proxyEnabled: !settings.proxyEnabled });
  };

  const testProxy = async () => {
    const nextUrl = proxyUrl.trim();
    if (!nextUrl || !valid) return;
    setTesting(true);
    setTestResult("");
    setTestError("");
    try {
      setTestResult(await withTimeout(api.testProxy(nextUrl), 20_000));
    } catch (error) {
      setTestError(normalizeError(error));
    } finally {
      setTesting(false);
    }
  };

  return (
    <>
      <PageHeader eyebrow="NETWORK" title="代理设置" description="代理关闭时会保留地址，但解析、Cookie 验证、下载和组件更新都将使用直连。" />
      <section className="card narrow-card">
        <div className="setting-row">
          <div><strong>启用代理</strong><small>{settings.proxyEnabled ? "当前所有新请求都会使用代理" : "当前使用直接连接"}</small></div>
          <button className={`switch-control ${settings.proxyEnabled ? "on" : ""}`} role="switch"
            aria-checked={settings.proxyEnabled} disabled={!canEnable && !settings.proxyEnabled}
            title={canEnable ? "切换代理状态" : "请先保存代理地址"} onClick={toggleProxy}>
            <span />
          </button>
        </div>
        <label className="field"><span>代理 URL</span>
          <input value={proxyUrl} onChange={(e) => { setProxyUrl(e.target.value); setSaved(false); setTestResult(""); setTestError(""); }}
            placeholder="http://127.0.0.1:7890 或 socks5://127.0.0.1:1080" /></label>
        {!valid && <p className="inline-error">仅支持 HTTP、HTTPS 或 SOCKS5 代理 URL</p>}
        <label className="field"><span>最大并发任务</span>
          <select value={settings.maxConcurrent}
            onChange={(e) => saveSettings({ ...settings, maxConcurrent: Number(e.target.value) })}>
            {[1, 2, 3, 4].map((value) => <option key={value} value={value}>{value}</option>)}
          </select></label>
        <div className="proxy-actions">
          <button className="ghost loading-button" disabled={!proxyUrl.trim() || !valid || testing} onClick={() => void testProxy()}>
            {testing ? <span className="spinner" aria-hidden="true" /> : <Icon name="network_check" />}
            {testing ? "正在测试…" : "测试代理"}
          </button>
          <button className="primary" disabled={!valid} onClick={async () => {
            const nextUrl = proxyUrl.trim();
            await saveSettings({ ...settings, proxyUrl: nextUrl, proxyEnabled: nextUrl ? settings.proxyEnabled : false });
            setSaved(true);
          }}><Icon name="save" />保存设置</button>
        </div>
        {testResult && <p className="success-text proxy-test-result">{testResult}</p>}
        {testError && <p className="inline-error proxy-test-result">{testError}</p>}
        {saved && <p className="success-text">设置已保存。{settings.proxyEnabled ? "代理已启用。" : "可通过上方开关启用代理。"}</p>}
      </section>
    </>
  );
}

