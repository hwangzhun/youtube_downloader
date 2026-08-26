use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use uuid::Uuid;

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ParseRequest {
    pub url: String,
    #[serde(default)]
    pub use_cookie: bool,
    pub proxy_url: Option<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DownloadRequest {
    pub urls: Vec<String>,
    pub output_dir: String,
    pub format_id: String,
    #[serde(default)]
    pub use_cookie: bool,
    pub proxy_url: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MediaFormat {
    pub format_id: String,
    pub label: String,
    pub extension: Option<String>,
    pub width: Option<u64>,
    pub height: Option<u64>,
    pub fps: Option<f64>,
    pub file_size: Option<u64>,
    pub video_codec: Option<String>,
    pub audio_codec: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VideoInfo {
    pub id: String,
    pub url: String,
    pub title: String,
    pub channel: Option<String>,
    pub duration: Option<f64>,
    pub thumbnail: Option<String>,
    pub formats: Vec<MediaFormat>,
    pub audio_formats: Vec<MediaFormat>,
}

impl VideoInfo {
    pub fn from_ytdlp(value: &Value, fallback_url: &str) -> Self {
        let mut formats: Vec<MediaFormat> = value
            .get("formats")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter(|format| {
                format.get("height").and_then(Value::as_u64).is_some()
                    && format
                        .get("vcodec")
                        .and_then(Value::as_str)
                        .unwrap_or("none")
                        != "none"
                    && format
                        .get("acodec")
                        .and_then(Value::as_str)
                        .unwrap_or("none")
                        == "none"
            })
            .map(|format| {
                let height = format.get("height").and_then(Value::as_u64);
                let extension = format.get("ext").and_then(Value::as_str).map(str::to_owned);
                let note = format
                    .get("format_note")
                    .and_then(Value::as_str)
                    .unwrap_or("");
                MediaFormat {
                    format_id: format
                        .get("format_id")
                        .and_then(Value::as_str)
                        .unwrap_or("best")
                        .to_owned(),
                    label: format!(
                        "{}p {} {}",
                        height.unwrap_or_default(),
                        note,
                        extension.as_deref().unwrap_or("")
                    )
                    .split_whitespace()
                    .collect::<Vec<_>>()
                    .join(" "),
                    extension,
                    width: format.get("width").and_then(Value::as_u64),
                    height,
                    fps: format.get("fps").and_then(Value::as_f64),
                    file_size: format
                        .get("filesize")
                        .or_else(|| format.get("filesize_approx"))
                        .and_then(Value::as_u64),
                    video_codec: format
                        .get("vcodec")
                        .and_then(Value::as_str)
                        .map(str::to_owned),
                    audio_codec: format
                        .get("acodec")
                        .and_then(Value::as_str)
                        .map(str::to_owned),
                }
            })
            .collect();
        formats.sort_by_key(|format| std::cmp::Reverse(format.height.unwrap_or_default()));
        formats.dedup_by(|left, right| {
            left.height == right.height && left.extension == right.extension
        });
        formats.insert(
            0,
            MediaFormat {
                format_id: "bestvideo".into(),
                label: "最佳可用画质（推荐）".into(),
                extension: None,
                width: None,
                height: None,
                fps: None,
                file_size: None,
                video_codec: None,
                audio_codec: None,
            },
        );
        let mut audio_formats: Vec<MediaFormat> = value
            .get("formats")
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .filter(|format| {
                format
                    .get("vcodec")
                    .and_then(Value::as_str)
                    .unwrap_or("none")
                    == "none"
                    && format
                        .get("acodec")
                        .and_then(Value::as_str)
                        .unwrap_or("none")
                        != "none"
            })
            .map(|format| {
                let extension = format.get("ext").and_then(Value::as_str).map(str::to_owned);
                let bitrate = format
                    .get("abr")
                    .or_else(|| format.get("tbr"))
                    .and_then(Value::as_f64);
                let codec = format
                    .get("acodec")
                    .and_then(Value::as_str)
                    .unwrap_or("audio");
                MediaFormat {
                    format_id: format
                        .get("format_id")
                        .and_then(Value::as_str)
                        .unwrap_or("bestaudio")
                        .to_owned(),
                    label: format!(
                        "{} · {} · {}",
                        bitrate
                            .map(|value| format!("{value:.0} kbps"))
                            .unwrap_or_else(|| "自动码率".into()),
                        extension.as_deref().unwrap_or("audio").to_ascii_uppercase(),
                        codec
                    ),
                    extension,
                    width: None,
                    height: None,
                    fps: None,
                    file_size: format
                        .get("filesize")
                        .or_else(|| format.get("filesize_approx"))
                        .and_then(Value::as_u64),
                    video_codec: None,
                    audio_codec: Some(codec.to_owned()),
                }
            })
            .collect();
        audio_formats.sort_by(|left, right| {
            right
                .file_size
                .unwrap_or_default()
                .cmp(&left.file_size.unwrap_or_default())
        });
        audio_formats.dedup_by(|left, right| {
            left.extension == right.extension && left.audio_codec == right.audio_codec
        });
        audio_formats.insert(
            0,
            MediaFormat {
                format_id: "bestaudio".into(),
                label: "最佳可用音质（推荐）".into(),
                extension: None,
                width: None,
                height: None,
                fps: None,
                file_size: None,
                video_codec: None,
                audio_codec: None,
            },
        );
        Self {
            id: value
                .get("id")
                .and_then(Value::as_str)
                .unwrap_or_default()
                .to_owned(),
            url: {
                let candidate = value
                    .get("webpage_url")
                    .or_else(|| value.get("url"))
                    .and_then(Value::as_str)
                    .unwrap_or(fallback_url);
                if candidate.starts_with("http://") || candidate.starts_with("https://") {
                    candidate.to_owned()
                } else {
                    let id = value.get("id").and_then(Value::as_str).unwrap_or(candidate);
                    if id.is_empty() {
                        fallback_url.to_owned()
                    } else {
                        format!("https://www.youtube.com/watch?v={id}")
                    }
                }
            },
            title: value
                .get("title")
                .and_then(Value::as_str)
                .unwrap_or("未知视频")
                .to_owned(),
            channel: value
                .get("channel")
                .or_else(|| value.get("uploader"))
                .and_then(Value::as_str)
                .map(str::to_owned),
            duration: value.get("duration").and_then(Value::as_f64),
            thumbnail: value
                .get("thumbnail")
                .and_then(Value::as_str)
                .map(str::to_owned),
            formats,
            audio_formats,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum TaskStatus {
    Pending,
    Resolving,
    Queued,
    Downloading,
    Postprocessing,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DownloadTask {
    pub id: Uuid,
    pub url: String,
    pub title: Option<String>,
    pub output_dir: String,
    pub format_id: String,
    pub status: TaskStatus,
    pub progress: f64,
    pub speed: Option<String>,
    pub eta: Option<String>,
    pub error: Option<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Clone, Debug)]
pub struct TaskRecord {
    pub public: DownloadTask,
    pub use_cookie: bool,
    pub proxy_url: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(tag = "event", content = "data", rename_all = "camelCase")]
pub enum TaskEvent {
    Snapshot(DownloadTask),
    QueuePaused { paused: bool },
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Settings {
    pub output_dir: String,
    pub proxy_url: String,
    pub proxy_enabled: bool,
    pub max_concurrent: usize,
    pub first_run_notice_pending: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            output_dir: String::new(),
            proxy_url: String::new(),
            proxy_enabled: false,
            max_concurrent: 2,
            first_run_notice_pending: true,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeTool {
    pub available: bool,
    pub version: Option<String>,
    pub path: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeStatus {
    pub app_version: String,
    pub webview2: RuntimeTool,
    pub yt_dlp: RuntimeTool,
    pub ffmpeg: RuntimeTool,
    pub ffprobe: RuntimeTool,
    pub javascript_runtime: RuntimeTool,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CookieStatus {
    pub state: String,
    pub source: Option<String>,
    pub message: String,
    pub cookie_count: usize,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolUpdate {
    pub tool: String,
    pub current_version: Option<String>,
    pub latest_version: Option<String>,
    pub available: bool,
}
