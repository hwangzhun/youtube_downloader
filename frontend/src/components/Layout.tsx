import { getCurrentWindow } from "@tauri-apps/api/window";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { appIcon } from "../assets";
import { useAppStore } from "../stores/appStore";
import { Icon } from "./Icon";

const nav = [
  ["/", "单视频", "smart_display"],
  ["/batch", "多视频", "playlist_play"],
  ["/channel", "频道下载", "video_library"],
  ["/downloads", "下载列表", "download"],
  ["/cookies", "Cookie", "cookie"],
  ["/proxy", "代理", "swap_horiz"],
  ["/versions", "版本与组件", "system_update_alt"],
  ["/about", "关于", "info"],
] as const;

export function Layout() {
  const { runtime, error, clearError, settings, saveSettings, drafts, theme, toggleTheme } = useAppStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const appWindow = getCurrentWindow();
  const location = useLocation();
  const versionLabel = `v${runtime?.appVersion ?? "2.0.0"}`;

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, []);

  return (
    <div className="window-shell" data-theme={theme}>
      <header className="titlebar" data-tauri-drag-region>
        <div className="app-menu-wrap" ref={menuRef}>
          <button className="app-menu-trigger" title="应用菜单" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
            <Icon name="menu" />
          </button>
          {menuOpen && (
            <div className="app-menu">
              <div className="app-menu-heading">导航</div>
              {nav.map(([to, label, icon]) => (
                <NavLink key={to} to={to} end={to === "/"} onClick={() => setMenuOpen(false)}>
                  <Icon name={icon} /><span>{label}</span>
                  {to === "/downloads" && drafts.length > 0 && <b>{drafts.length}</b>}
                  {to === "/proxy" && settings.proxyEnabled && settings.proxyUrl && <i className="proxy-enabled-dot" title="代理已启用" />}
                </NavLink>
              ))}
              <div className="app-menu-separator" />
              <button onClick={() => { toggleTheme(); setMenuOpen(false); }}>
                <Icon name={theme === "dark" ? "light_mode" : "dark_mode"} />
                <span>{theme === "dark" ? "明亮模式" : "暗黑模式"}</span>
              </button>
            </div>
          )}
        </div>
        <div className="titlebar-title" data-tauri-drag-region>
          <img className="titlebar-logo" src={appIcon} alt="" />
          <span>YouTube Downloader</span>
          <span className="titlebar-version">{versionLabel}</span>
        </div>
        <div className="titlebar-drag-space" data-tauri-drag-region />
        <div className="titlebar-actions">
          <button title={theme === "dark" ? "切换明亮模式" : "切换暗黑模式"} onClick={toggleTheme}>
            <Icon name={theme === "dark" ? "light_mode" : "dark_mode"} />
          </button>
          <button title="最小化" onClick={() => appWindow.minimize()}><Icon name="remove" /></button>
          <button title="最大化或还原" onClick={() => appWindow.toggleMaximize()}><Icon name="crop_square" /></button>
          <button className="window-close" title="关闭" onClick={() => appWindow.close()}><Icon name="close" /></button>
        </div>
      </header>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="brand">
            <img className="brand-logo" src={appIcon} alt="YouTube Downloader" />
            <div className="brand-copy">
              <div className="brand-name">
                <strong>YouTube</strong>
                <span className="brand-version">{versionLabel}</span>
              </div>
              <small>Downloader</small>
            </div>
          </div>
          <nav>
            {nav.map(([to, label, icon]) => (
              <NavLink key={to} to={to} end={to === "/"}>
                <Icon name={icon} />{label}
                {to === "/downloads" && drafts.length > 0 && <b className="nav-badge">{drafts.length}</b>}
                {to === "/proxy" && settings.proxyEnabled && settings.proxyUrl && <i className="proxy-enabled-dot" title="代理已启用" />}
              </NavLink>
            ))}
          </nav>
          <div className="runtime-pill">
            <i className={runtime?.ytDlp.available ? "ok" : "bad"} />
            {runtime?.ytDlp.available ? "下载引擎就绪" : "下载引擎缺失"}
          </div>
        </aside>
        <main className="content">
          {error && <div className="alert error"><span>{error}</span><button onClick={clearError}>关闭</button></div>}
          <div className="page-transition" key={location.pathname}>
            <Outlet />
          </div>
          {settings.firstRunNoticePending && (
            <div className="alert migration">
              <span className="migration-copy">
                <strong>欢迎使用新版 YouTube Downloader</strong>
                <span>本次升级不会迁移旧版设置、Cookie 或缓存，请重新选择下载目录并登录。</span>
              </span>
              <button onClick={() => saveSettings({ ...settings, firstRunNoticePending: false })}>我知道了</button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}


