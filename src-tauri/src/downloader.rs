use crate::{
    cookie,
    error::{AppError, AppResult},
    models::{
        CookieStatus, DownloadRequest, DownloadTask, ParseRequest, TaskEvent, TaskRecord,
        TaskStatus, VideoInfo,
    },
    runtime,
    state::AppState,
};
use chrono::Utc;
use regex::Regex;
use serde_json::Value;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::{path::Path, process::Stdio, time::Duration};
use tauri::ipc::Channel;
use tokio::{
    io::{AsyncBufReadExt, BufReader},
    process::Command,
};
use uuid::Uuid;

const CREATE_NO_WINDOW: u32 = 0x08000000;

pub async fn parse_video(state: &AppState, request: ParseRequest) -> AppResult<VideoInfo> {
    validate_url(&request.url)?;
    let value = run_json(state, &request, &["--no-playlist"]).await?;
    Ok(VideoInfo::from_ytdlp(&value, &request.url))
}

pub async fn expand_collection(
    state: &AppState,
    request: ParseRequest,
) -> AppResult<Vec<VideoInfo>> {
    validate_url(&request.url)?;
    let value = run_json(state, &request, &["--flat-playlist"]).await?;
    let entries = value
        .get("entries")
        .and_then(Value::as_array)
        .ok_or_else(|| AppError::user("collection_empty", "没有找到可下载的视频"))?;
    Ok(entries
        .iter()
        .map(|entry| {
            VideoInfo::from_ytdlp(
                entry,
                entry.get("url").and_then(Value::as_str).unwrap_or(""),
            )
        })
        .collect())
}

async fn run_json(state: &AppState, request: &ParseRequest, extra: &[&str]) -> AppResult<Value> {
    let binary = runtime::yt_dlp_path(state)
        .ok_or_else(|| AppError::fatal("yt_dlp_missing", "未找到 yt-dlp，请先安装下载组件"))?;
    let cookie = if request.use_cookie {
        Some(cookie::materialize(state)?)
    } else {
        None
    };
    let mut command = Command::new(binary);
    command.args(["--dump-single-json", "--no-warnings"]);
    command.args(extra);
    append_common_args(
        &mut command,
        state,
        request.proxy_url.as_deref(),
        cookie.as_ref().map(|file| file.path()),
    )?;
    command.arg(&request.url);
    configure(&mut command);
    let output = command.output().await?;
    if !output.status.success() {
        return Err(AppError::user(
            "parse_failed",
            sanitize_stderr(&output.stderr),
        ));
    }
    serde_json::from_slice(&output.stdout)
        .map_err(|_| AppError::user("invalid_engine_output", "yt-dlp 返回了无法解析的数据"))
}

pub async fn validate_cookie_online(state: &AppState) -> AppResult<CookieStatus> {
    let binary = runtime::yt_dlp_path(state)
        .ok_or_else(|| AppError::fatal("yt_dlp_missing", "未找到 yt-dlp，请先安装下载组件"))?;
    let cookie = cookie::materialize(state)?;
    let content = std::fs::read_to_string(cookie.path())?;
    let count = cookie::validate_netscape(&content)?;
    let settings = state.settings().await;
    let mut command = Command::new(binary);
    command.args([
        "--dump-single-json",
        "--flat-playlist",
        "--playlist-end",
        "1",
        "--no-warnings",
        "--cookies",
    ]);
    command.arg(cookie.path());
    if settings.proxy_enabled && !settings.proxy_url.is_empty() {
        validate_proxy(&settings.proxy_url)?;
        command.args(["--proxy", &settings.proxy_url]);
    }
    command.arg("https://www.youtube.com/feed/history");
    configure(&mut command);
    let output = command.output().await?;
    if output.status.success() {
        Ok(CookieStatus {
            state: "valid".into(),
            source: None,
            message: "Cookie 联网验证成功，YouTube 登录状态有效".into(),
            cookie_count: count,
        })
    } else {
        Ok(CookieStatus {
            state: "invalid".into(),
            source: None,
            message: "Cookie 已失效或 YouTube 未识别登录状态，请重新登录或导入".into(),
            cookie_count: count,
        })
    }
}

pub async fn enqueue(
    state: AppState,
    request: DownloadRequest,
    on_event: Channel<TaskEvent>,
) -> AppResult<Vec<Uuid>> {
    if request.urls.is_empty() {
        return Err(AppError::user("empty_urls", "请至少输入一个视频链接"));
    }
    let output = Path::new(&request.output_dir);
    if !output.is_dir() {
        return Err(AppError::user("invalid_output_dir", "下载目录不存在"));
    }
    for url in &request.urls {
        validate_url(url)?;
    }

    let mut ids = Vec::with_capacity(request.urls.len());
    for url in request.urls {
        let id = Uuid::new_v4();
        let record = TaskRecord {
            public: DownloadTask {
                id,
                url,
                title: None,
                output_dir: request.output_dir.clone(),
                format_id: request.format_id.clone(),
                status: TaskStatus::Queued,
                progress: 0.0,
                speed: None,
                eta: None,
                error: None,
                created_at: Utc::now(),
            },
            use_cookie: request.use_cookie,
            proxy_url: request.proxy_url.clone(),
        };
        state.insert_task(record.clone(), on_event.clone()).await;
        let _ = on_event.send(TaskEvent::Snapshot(record.public.clone()));
        let task_state = state.clone();
        tokio::spawn(async move {
            run_task(task_state, id).await;
        });
        ids.push(id);
    }
    Ok(ids)
}

pub async fn retry(state: AppState, id: Uuid) -> AppResult<()> {
    let mut record = state
        .record(id)
        .await
        .ok_or_else(|| AppError::user("task_not_found", "任务不存在"))?;
    if !matches!(
        record.public.status,
        TaskStatus::Failed | TaskStatus::Cancelled
    ) {
        return Err(AppError::user(
            "task_not_retryable",
            "只有失败或已取消的任务可以重试",
        ));
    }
    record.public.status = TaskStatus::Queued;
    record.public.progress = 0.0;
    record.public.error = None;
    state.update_record(record).await;
    tokio::spawn(async move {
        run_task(state, id).await;
    });
    Ok(())
}

pub async fn cancel(state: &AppState, id: Uuid) -> AppResult<()> {
    let mut record = state
        .record(id)
        .await
        .ok_or_else(|| AppError::user("task_not_found", "任务不存在"))?;
    record.public.status = TaskStatus::Cancelled;
    record.public.error = None;
    state.update_record(record).await;
    if let Some(pid) = state.pid(id).await {
        kill_process_tree(pid).await;
    }
    Ok(())
}

async fn run_task(state: AppState, id: Uuid) {
    while state.is_paused() {
        if is_cancelled(&state, id).await {
            return;
        }
        tokio::time::sleep(Duration::from_millis(250)).await;
    }
    let permit_source = state.semaphore().await;
    let Ok(_permit) = permit_source.acquire_owned().await else {
        return;
    };
    if is_cancelled(&state, id).await {
        return;
    }

    let Some(mut record) = state.record(id).await else {
        return;
    };
    record.public.status = TaskStatus::Resolving;
    state.update_record(record.clone()).await;

    let result = execute_download(&state, &mut record).await;
    state.remove_pid(id).await;
    match result {
        Ok(()) if !is_cancelled(&state, id).await => {
            record.public.status = TaskStatus::Completed;
            record.public.progress = 100.0;
            record.public.speed = None;
            record.public.eta = None;
            state.update_record(record).await;
        }
        Ok(()) => {}
        Err(error) if !is_cancelled(&state, id).await => {
            record.public.status = TaskStatus::Failed;
            record.public.error = Some(error.to_string());
            state.update_record(record).await;
        }
        Err(_) => {}
    }
}

async fn execute_download(state: &AppState, record: &mut TaskRecord) -> AppResult<()> {
    let binary = runtime::yt_dlp_path(state)
        .ok_or_else(|| AppError::fatal("yt_dlp_missing", "未找到 yt-dlp，请先安装下载组件"))?;
    let cookie = if record.use_cookie {
        Some(cookie::materialize(state)?)
    } else {
        None
    };
    let mut command = Command::new(binary);
    command.args([
        "--newline",
        "--no-playlist",
        "--continue",
        "--no-warnings",
        "--progress-template",
        "download:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--output",
        "%(title)s [%(id)s].%(ext)s",
        "--merge-output-format",
        "mp4",
        "--format",
        &record.public.format_id,
        "--paths",
        &record.public.output_dir,
    ]);
    append_common_args(
        &mut command,
        state,
        record.proxy_url.as_deref(),
        cookie.as_ref().map(|file| file.path()),
    )?;
    command.arg(&record.public.url);
    command
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);
    configure(&mut command);

    record.public.status = TaskStatus::Downloading;
    state.update_record(record.clone()).await;
    let mut child = command.spawn()?;
    if let Some(pid) = child.id() {
        state.set_pid(record.public.id, pid).await;
    }
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| AppError::fatal("process_pipe", "无法读取下载进度"))?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| AppError::fatal("process_pipe", "无法读取下载错误"))?;
    let stderr_task = tokio::spawn(async move {
        let mut reader = BufReader::new(stderr);
        let mut line_bytes = Vec::new();
        let mut buffer = Vec::new();
        loop {
            line_bytes.clear();
            let Ok(read) = reader.read_until(b'\n', &mut line_bytes).await else {
                break;
            };
            if read == 0 {
                break;
            }
            let line = String::from_utf8_lossy(&line_bytes);
            if line.contains("ERROR:") {
                buffer.push(line.trim_end().to_owned());
            }
        }
        buffer.join("\n")
    });

    let progress = Regex::new(r"download:\s*([0-9.]+)%\|([^|]*)\|([^|]*)").expect("progress regex");
    let mut reader = BufReader::new(stdout);
    let mut line_bytes = Vec::new();
    loop {
        line_bytes.clear();
        if reader.read_until(b'\n', &mut line_bytes).await? == 0 {
            break;
        }
        let line = String::from_utf8_lossy(&line_bytes);
        let line = line.trim_end();
        if is_cancelled(state, record.public.id).await {
            let _ = child.kill().await;
            return Ok(());
        }
        if let Some(captures) = progress.captures(&line) {
            record.public.progress = captures[1].parse().unwrap_or(record.public.progress);
            record.public.speed = clean_field(captures.get(2).map(|value| value.as_str()));
            record.public.eta = clean_field(captures.get(3).map(|value| value.as_str()));
            state.update_record(record.clone()).await;
        } else if line.contains("[Merger]") || line.contains("[VideoConvertor]") {
            record.public.status = TaskStatus::Postprocessing;
            state.update_record(record.clone()).await;
        } else if let Some(name) = line.strip_prefix("[download] Destination: ") {
            record.public.title = Path::new(name)
                .file_name()
                .map(|name| name.to_string_lossy().into_owned());
        }
    }
    let status = child.wait().await?;
    let stderr = stderr_task.await.unwrap_or_default();
    if !status.success() {
        return Err(AppError::user(
            "download_failed",
            if stderr.is_empty() {
                "下载进程异常退出".into()
            } else {
                sanitize_text(&stderr)
            },
        ));
    }
    Ok(())
}

fn append_common_args(
    command: &mut Command,
    state: &AppState,
    proxy: Option<&str>,
    cookie: Option<&Path>,
) -> AppResult<()> {
    if let Some(proxy) = proxy.filter(|value| !value.is_empty()) {
        validate_proxy(proxy)?;
        command.args(["--proxy", proxy]);
    }
    if let Some(cookie) = cookie {
        command.arg("--cookies").arg(cookie);
    }
    if let Some(ffmpeg) =
        runtime::ffmpeg_path(state).and_then(|path| path.parent().map(Path::to_owned))
    {
        command.arg("--ffmpeg-location").arg(ffmpeg);
    }
    if command_available("node") {
        command.args(["--js-runtimes", "node"]);
    } else if command_available("deno") {
        command.args(["--js-runtimes", "deno"]);
    }
    Ok(())
}

pub fn validate_url(value: &str) -> AppResult<()> {
    let url = url::Url::parse(value.trim())
        .map_err(|_| AppError::user("invalid_url", "请输入有效的 YouTube 链接"))?;
    if url.scheme() != "https" && url.scheme() != "http" {
        return Err(AppError::user("invalid_url", "链接必须使用 HTTP 或 HTTPS"));
    }
    let host = url.host_str().unwrap_or_default().to_ascii_lowercase();
    if !(host == "youtu.be" || host == "youtube.com" || host.ends_with(".youtube.com")) {
        return Err(AppError::user(
            "unsupported_host",
            "目前仅支持 YouTube 链接",
        ));
    }
    Ok(())
}

fn validate_proxy(value: &str) -> AppResult<()> {
    let url = url::Url::parse(value)
        .map_err(|_| AppError::user("invalid_proxy", "代理 URL 格式不正确"))?;
    if !matches!(url.scheme(), "http" | "https" | "socks5") {
        return Err(AppError::user(
            "invalid_proxy",
            "代理仅支持 HTTP、HTTPS 或 SOCKS5",
        ));
    }
    Ok(())
}

fn configure(command: &mut Command) {
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
}

fn command_available(name: &str) -> bool {
    let mut command = std::process::Command::new(name);
    command.arg("--version");
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
    command
        .output()
        .map(|result| result.status.success())
        .unwrap_or(false)
}

async fn is_cancelled(state: &AppState, id: Uuid) -> bool {
    state
        .record(id)
        .await
        .map(|record| record.public.status == TaskStatus::Cancelled)
        .unwrap_or(true)
}

async fn kill_process_tree(pid: u32) {
    #[cfg(windows)]
    {
        let mut command = Command::new("taskkill");
        command.args(["/PID", &pid.to_string(), "/T", "/F"]);
        configure(&mut command);
        let _ = command.output().await;
    }
    #[cfg(not(windows))]
    let _ = pid;
}

fn clean_field(value: Option<&str>) -> Option<String> {
    value
        .map(str::trim)
        .filter(|value| !value.is_empty() && *value != "NA")
        .map(str::to_owned)
}

fn sanitize_stderr(stderr: &[u8]) -> String {
    let text = String::from_utf8_lossy(stderr);
    let normalized = text.to_ascii_lowercase();
    if normalized.contains("not a bot") || normalized.contains("sign in to confirm") {
        return "YouTube 要求验证身份。请前往 Cookie 页面完成网页登录并获取 Cookie，然后返回此页面勾选“使用已保存 Cookie”后重试。"
            .into();
    }
    if text.trim().is_empty() {
        "视频解析失败".into()
    } else {
        sanitize_text(&text)
    }
}

fn sanitize_text(value: &str) -> String {
    value
        .lines()
        .filter(|line| line.contains("ERROR") || line.contains("error"))
        .take(4)
        .collect::<Vec<_>>()
        .join("\n")
        .trim()
        .trim_start_matches("ERROR:")
        .trim()
        .to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_youtube_hosts() {
        assert!(validate_url("https://www.youtube.com/watch?v=abc").is_ok());
        assert!(validate_url("https://youtu.be/abc").is_ok());
    }

    #[test]
    fn rejects_other_hosts() {
        assert!(validate_url("https://example.com/watch?v=abc").is_err());
        assert!(validate_url("file:///tmp/video").is_err());
    }

    #[test]
    fn removes_sensitive_noise_from_errors() {
        assert_eq!(
            sanitize_text("debug\nERROR: unavailable\ntrace"),
            "unavailable"
        );
    }

    #[test]
    fn explains_youtube_authentication_requirement() {
        assert!(sanitize_stderr(
            b"ERROR: Sign in to confirm you're not a bot. Use --cookies for authentication."
        )
        .contains("Cookie"));
    }
}
