use crate::{
    cookie, downloader,
    error::{AppError, AppResult},
    models::*,
    runtime,
    state::AppState,
    tools,
};
use std::{
    path::PathBuf,
    time::{Duration, Instant},
};
use tauri::{ipc::Channel, Manager, State, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_updater::UpdaterExt;
use uuid::Uuid;

#[tauri::command]
pub fn get_runtime_status(state: State<'_, AppState>) -> RuntimeStatus {
    runtime::runtime_status(state.inner())
}

#[tauri::command]
pub async fn parse_video(
    state: State<'_, AppState>,
    request: ParseRequest,
) -> AppResult<VideoInfo> {
    downloader::parse_video(state.inner(), request).await
}

#[tauri::command]
pub async fn expand_playlist(
    state: State<'_, AppState>,
    request: ParseRequest,
) -> AppResult<Vec<VideoInfo>> {
    downloader::expand_collection(state.inner(), request).await
}

#[tauri::command]
pub async fn fetch_channel(
    state: State<'_, AppState>,
    request: ParseRequest,
) -> AppResult<Vec<VideoInfo>> {
    downloader::expand_collection(state.inner(), request).await
}

#[tauri::command]
pub async fn enqueue_downloads(
    state: State<'_, AppState>,
    request: DownloadRequest,
    on_event: Channel<TaskEvent>,
) -> AppResult<Vec<Uuid>> {
    downloader::enqueue(state.inner().clone(), request, on_event).await
}

#[tauri::command]
pub async fn list_tasks(state: State<'_, AppState>) -> AppResult<Vec<DownloadTask>> {
    Ok(state.list_tasks().await)
}

#[tauri::command]
pub async fn cancel_task(state: State<'_, AppState>, id: Uuid) -> AppResult<()> {
    downloader::cancel(state.inner(), id).await
}

#[tauri::command]
pub async fn retry_task(state: State<'_, AppState>, id: Uuid) -> AppResult<()> {
    downloader::retry(state.inner().clone(), id).await
}

#[tauri::command]
pub async fn open_task_directory(state: State<'_, AppState>, id: Uuid) -> AppResult<()> {
    let record = state
        .record(id)
        .await
        .ok_or_else(|| AppError::user("task_not_found", "找不到对应的下载任务"))?;
    if record.public.status != TaskStatus::Completed {
        return Err(AppError::user(
            "task_not_completed",
            "只能打开已完成任务的下载目录",
        ));
    }
    let directory = PathBuf::from(&record.public.output_dir);
    if !directory.is_dir() {
        return Err(AppError::user(
            "download_directory_missing",
            "下载目录不存在或已被移动",
        ));
    }

    #[cfg(target_os = "windows")]
    let mut command = std::process::Command::new("explorer.exe");
    #[cfg(target_os = "macos")]
    let mut command = std::process::Command::new("open");
    #[cfg(all(unix, not(target_os = "macos")))]
    let mut command = std::process::Command::new("xdg-open");

    command.arg(directory).spawn().map_err(|error| {
        AppError::user(
            "open_directory_failed",
            format!("无法打开下载目录：{error}"),
        )
    })?;
    Ok(())
}

#[tauri::command]
pub async fn set_queue_paused(state: State<'_, AppState>, paused: bool) -> AppResult<()> {
    state.set_paused(paused);
    state.broadcast(TaskEvent::QueuePaused { paused }).await;
    Ok(())
}

#[tauri::command]
pub async fn get_settings(state: State<'_, AppState>) -> AppResult<Settings> {
    Ok(state.settings().await)
}

#[tauri::command]
pub async fn save_settings(state: State<'_, AppState>, settings: Settings) -> AppResult<Settings> {
    state.save_settings(settings).await
}

#[tauri::command]
pub async fn test_proxy(proxy_url: String) -> AppResult<String> {
    let proxy_url = proxy_url.trim();
    if proxy_url.is_empty() {
        return Err(AppError::user("proxy_required", "请先填写代理 URL"));
    }
    downloader::validate_proxy(proxy_url)?;
    let proxy = reqwest::Proxy::all(proxy_url)
        .map_err(|error| AppError::user("invalid_proxy", format!("代理 URL 无法使用：{error}")))?;
    let client = reqwest::Client::builder()
        .user_agent("YouTube-Downloader/2.0")
        .proxy(proxy)
        .connect_timeout(Duration::from_secs(8))
        .timeout(Duration::from_secs(15))
        .build()
        .map_err(|error| AppError::user("proxy_client", format!("无法创建代理连接：{error}")))?;
    let started = Instant::now();
    let response = client
        .get("https://www.youtube.com/generate_204")
        .send()
        .await
        .map_err(|error| {
            AppError::user(
                "proxy_test_failed",
                format!("代理连接 YouTube 失败：{error}"),
            )
        })?;
    let status = response.status();
    if status.is_server_error() {
        return Err(AppError::user(
            "proxy_test_failed",
            format!("代理服务器返回 HTTP {}", status.as_u16()),
        ));
    }
    Ok(format!(
        "代理可用 · YouTube 响应 {} · {} ms",
        status.as_u16(),
        started.elapsed().as_millis()
    ))
}

#[tauri::command]
pub fn select_output_directory(app: tauri::AppHandle) -> Option<String> {
    app.dialog()
        .file()
        .blocking_pick_folder()
        .and_then(|path| path.into_path().ok())
        .map(|path| path.to_string_lossy().into_owned())
}

#[tauri::command]
pub async fn open_login_window(app: tauri::AppHandle, state: State<'_, AppState>) -> AppResult<()> {
    if let Some(window) = app.get_webview_window("youtube-login") {
        window.show()?;
        window.set_focus()?;
        return Ok(());
    }
    let data_dir = state.app_data_dir().join("webview/youtube-login");
    std::fs::create_dir_all(&data_dir)?;
    let url = url::Url::parse("https://www.youtube.com/")
        .map_err(|error| AppError::Internal(error.to_string()))?;
    WebviewWindowBuilder::new(&app, "youtube-login", WebviewUrl::External(url))
        .title("登录 YouTube · YouTube Downloader")
        .inner_size(1080.0, 760.0)
        .min_inner_size(760.0, 560.0)
        .center()
        .data_directory(data_dir)
        .on_navigation(|url| {
            let host = url.host_str().unwrap_or_default().to_ascii_lowercase();
            host == "youtube.com"
                || host.ends_with(".youtube.com")
                || host == "google.com"
                || host.ends_with(".google.com")
                || host.ends_with(".gstatic.com")
        })
        .build()?;
    Ok(())
}

#[tauri::command]
pub async fn capture_login_cookies(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> AppResult<CookieStatus> {
    let webview = app
        .get_webview_window("youtube-login")
        .ok_or_else(|| AppError::user("login_window_missing", "请先打开 YouTube 登录窗口"))?;
    let cookies = tauri::async_runtime::spawn_blocking(move || webview.cookies())
        .await
        .map_err(|error| AppError::Internal(error.to_string()))??;
    let mut lines = vec![
        "# Netscape HTTP Cookie File".to_string(),
        "# Generated securely by YouTube Downloader 2".to_string(),
    ];
    let mut auth_cookie = false;
    for item in cookies {
        let domain = item.domain().unwrap_or_default().to_ascii_lowercase();
        if !(domain.contains("youtube.com")
            || domain.contains("google.com")
            || domain.contains("googlevideo.com"))
        {
            continue;
        }
        let name = item.name();
        auth_cookie |= matches!(
            name,
            "SID"
                | "HSID"
                | "SSID"
                | "APISID"
                | "SAPISID"
                | "__Secure-1PAPISID"
                | "__Secure-3PAPISID"
        );
        let domain_value = item.domain().unwrap_or(".youtube.com");
        let include_subdomains = if domain_value.starts_with('.') {
            "TRUE"
        } else {
            "FALSE"
        };
        let secure = if item.secure().unwrap_or(false) {
            "TRUE"
        } else {
            "FALSE"
        };
        let expires = item
            .expires()
            .and_then(|value| value.datetime())
            .map(|value| value.unix_timestamp())
            .unwrap_or(0);
        let prefix = if item.http_only().unwrap_or(false) {
            "#HttpOnly_"
        } else {
            ""
        };
        lines.push(format!(
            "{}{}\t{}\t{}\t{}\t{}\t{}\t{}",
            prefix,
            domain_value,
            include_subdomains,
            item.path().unwrap_or("/"),
            secure,
            expires,
            name,
            item.value()
        ));
    }
    if !auth_cookie {
        return Err(AppError::user(
            "login_incomplete",
            "尚未检测到 YouTube 登录 Cookie，请完成登录后重试",
        ));
    }
    cookie::save(state.inner(), &(lines.join("\n") + "\n"), "webview")
}

#[tauri::command]
pub async fn clear_login_profile(app: tauri::AppHandle) -> AppResult<()> {
    if let Some(window) = app.get_webview_window("youtube-login") {
        let clone = window.clone();
        tauri::async_runtime::spawn_blocking(move || clone.clear_all_browsing_data())
            .await
            .map_err(|error| AppError::Internal(error.to_string()))??;
        window.close()?;
    }
    Ok(())
}

#[tauri::command]
pub fn import_cookie_file(state: State<'_, AppState>, path: String) -> AppResult<CookieStatus> {
    cookie::import_file(state.inner(), &PathBuf::from(path))
}

#[tauri::command]
pub fn get_cookie_status(state: State<'_, AppState>) -> CookieStatus {
    cookie::status(state.inner())
}

#[tauri::command]
pub async fn validate_cookie(state: State<'_, AppState>) -> AppResult<CookieStatus> {
    downloader::validate_cookie_online(state.inner()).await
}

#[tauri::command]
pub fn clear_cookie(state: State<'_, AppState>) -> AppResult<()> {
    cookie::clear(state.inner())
}

#[tauri::command]
pub async fn check_tool_updates(state: State<'_, AppState>) -> AppResult<Vec<ToolUpdate>> {
    Ok(tools::check(state.inner()).await)
}

#[tauri::command]
pub async fn update_tool(
    state: State<'_, AppState>,
    tool: String,
    on_progress: Channel<ToolProgress>,
) -> AppResult<()> {
    tools::update(state.inner(), &tool, &on_progress).await
}

#[tauri::command]
pub async fn check_app_update(app: tauri::AppHandle) -> AppResult<bool> {
    let updater = app
        .updater()
        .map_err(|error| AppError::Internal(error.to_string()))?;
    updater
        .check()
        .await
        .map(|update| update.is_some())
        .map_err(|error| AppError::user("update_check_failed", error.to_string()))
}

#[tauri::command]
pub async fn install_app_update(app: tauri::AppHandle) -> AppResult<()> {
    let updater = app
        .updater()
        .map_err(|error| AppError::Internal(error.to_string()))?;
    if let Some(update) = updater
        .check()
        .await
        .map_err(|error| AppError::user("update_check_failed", error.to_string()))?
    {
        update
            .download_and_install(|_, _| {}, || {})
            .await
            .map_err(|error| AppError::user("update_install_failed", error.to_string()))?;
    }
    Ok(())
}
