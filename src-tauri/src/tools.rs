use crate::{
    error::{AppError, AppResult},
    models::ToolUpdate,
    runtime,
    state::AppState,
};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::{Cursor, Write},
    path::{Path, PathBuf},
};
use uuid::Uuid;

const YTDLP_EXE: &str = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe";
const YTDLP_SUMS: &str = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-256SUMS";
const YTDLP_API: &str = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest";
const FFMPEG_ZIP: &str = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip";
const FFMPEG_SUMS: &str =
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/checksums.sha256";

pub async fn check(state: &AppState) -> Vec<ToolUpdate> {
    let current = runtime::runtime_status(state);
    let latest_yt = latest_tag(YTDLP_API).await.ok();
    vec![
        ToolUpdate {
            tool: "ytDlp".into(),
            available: latest_yt.as_ref().is_some_and(|latest| {
                current
                    .yt_dlp
                    .version
                    .as_ref()
                    .is_none_or(|installed| !installed.contains(latest.trim_start_matches('v')))
            }),
            current_version: current.yt_dlp.version,
            latest_version: latest_yt,
        },
        ToolUpdate {
            tool: "ffmpeg".into(),
            available: !current.ffmpeg.available,
            current_version: current.ffmpeg.version,
            latest_version: Some("BtbN latest shared build".into()),
        },
    ]
}

pub async fn update(state: &AppState, tool: &str) -> AppResult<()> {
    match tool {
        "ytDlp" => update_ytdlp(state).await,
        "ffmpeg" => update_ffmpeg(state).await,
        _ => Err(AppError::user("unknown_tool", "未知的下载组件")),
    }
}

async fn update_ytdlp(state: &AppState) -> AppResult<()> {
    let (binary, sums) = tokio::try_join!(download(YTDLP_EXE), download(YTDLP_SUMS))?;
    verify_published_checksum(&binary, &String::from_utf8_lossy(&sums), "yt-dlp.exe")?;
    let staging = prepare_staging(state)?;
    fs::write(staging.join("yt-dlp.exe"), binary)?;
    verify_executable(&staging.join("yt-dlp.exe"))?;
    activate(state, staging)
}

async fn update_ffmpeg(state: &AppState) -> AppResult<()> {
    let (archive, sums) = tokio::try_join!(download(FFMPEG_ZIP), download(FFMPEG_SUMS))?;
    let archive_name = "ffmpeg-master-latest-win64-gpl-shared.zip";
    verify_published_checksum(&archive, &String::from_utf8_lossy(&sums), archive_name)?;
    let staging = prepare_staging(state)?;
    let target = staging.clone();
    tokio::task::spawn_blocking(move || extract_ffmpeg(&archive, &target))
        .await
        .map_err(|error| AppError::Internal(error.to_string()))??;
    verify_executable(&staging.join("ffmpeg.exe"))?;
    verify_executable(&staging.join("ffprobe.exe"))?;
    activate(state, staging)
}

async fn latest_tag(url: &str) -> AppResult<String> {
    let value: serde_json::Value = client()
        .get(url)
        .send()
        .await
        .map_err(network)?
        .error_for_status()
        .map_err(network)?
        .json()
        .await
        .map_err(network)?;
    value
        .get("tag_name")
        .and_then(serde_json::Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| AppError::user("release_metadata", "发布信息缺少版本号"))
}

async fn download(url: &str) -> AppResult<Vec<u8>> {
    let response = client()
        .get(url)
        .send()
        .await
        .map_err(network)?
        .error_for_status()
        .map_err(network)?;
    let length = response.content_length().unwrap_or_default();
    if length > 250 * 1024 * 1024 {
        return Err(AppError::fatal("tool_too_large", "组件下载大小异常"));
    }
    response
        .bytes()
        .await
        .map(|value| value.to_vec())
        .map_err(network)
}

fn client() -> reqwest::Client {
    reqwest::Client::builder()
        .user_agent("YouTube-Downloader/2.0")
        .timeout(std::time::Duration::from_secs(180))
        .build()
        .expect("http client")
}

fn network(error: reqwest::Error) -> AppError {
    AppError::user("tool_network", format!("组件下载失败：{error}"))
}

fn verify_published_checksum(bytes: &[u8], manifest: &str, file_name: &str) -> AppResult<()> {
    let expected = manifest
        .lines()
        .find_map(|line| {
            let mut parts = line.split_whitespace();
            let hash = parts.next()?;
            let name = parts.next()?.trim_start_matches('*');
            (name == file_name).then(|| hash.to_ascii_lowercase())
        })
        .ok_or_else(|| AppError::fatal("checksum_missing", "发布方校验清单中没有目标文件"))?;
    let actual = hex::encode(Sha256::digest(bytes));
    if actual != expected {
        return Err(AppError::fatal(
            "checksum_mismatch",
            "组件 SHA-256 校验失败，已拒绝安装",
        ));
    }
    Ok(())
}

fn prepare_staging(state: &AppState) -> AppResult<PathBuf> {
    let tools = state.app_data_dir().join("tools");
    fs::create_dir_all(&tools)?;
    let staging = tools.join(format!(".staging-{}", Uuid::new_v4()));
    fs::create_dir_all(&staging)?;
    let active = tools.join("active");
    if active.is_dir() {
        copy_dir(&active, &staging)?;
    }
    Ok(staging)
}

fn activate(state: &AppState, staging: PathBuf) -> AppResult<()> {
    let tools = state.app_data_dir().join("tools");
    let active = tools.join("active");
    let previous = tools.join("previous");
    if previous.exists() {
        fs::remove_dir_all(&previous)?;
    }
    if active.exists() {
        fs::rename(&active, &previous)?;
    }
    if let Err(error) = fs::rename(&staging, &active) {
        if previous.exists() && !active.exists() {
            let _ = fs::rename(&previous, &active);
        }
        return Err(error.into());
    }
    Ok(())
}

fn extract_ffmpeg(bytes: &[u8], target: &Path) -> AppResult<()> {
    let mut archive = zip::ZipArchive::new(Cursor::new(bytes))
        .map_err(|error| AppError::user("ffmpeg_archive", error.to_string()))?;
    let mut installed = 0;
    for index in 0..archive.len() {
        let mut entry = archive
            .by_index(index)
            .map_err(|error| AppError::user("ffmpeg_archive", error.to_string()))?;
        let Some(name) = entry
            .enclosed_name()
            .and_then(|path| path.file_name().map(|name| name.to_owned()))
        else {
            continue;
        };
        let lower = name.to_string_lossy().to_ascii_lowercase();
        if lower == "ffplay.exe"
            || !(lower == "ffmpeg.exe" || lower == "ffprobe.exe" || lower.ends_with(".dll"))
        {
            continue;
        }
        let mut output = fs::File::create(target.join(name))?;
        std::io::copy(&mut entry, &mut output)?;
        output.flush()?;
        installed += 1;
    }
    if installed < 3 {
        return Err(AppError::fatal(
            "ffmpeg_archive",
            "FFmpeg 压缩包缺少运行文件",
        ));
    }
    Ok(())
}

fn verify_executable(path: &Path) -> AppResult<()> {
    let metadata = fs::metadata(path).map_err(|_| {
        AppError::fatal("tool_missing", format!("组件文件缺失：{}", path.display()))
    })?;
    if metadata.len() < 64 * 1024 {
        return Err(AppError::fatal(
            "tool_invalid",
            format!("组件文件大小异常：{}", path.display()),
        ));
    }
    Ok(())
}

fn copy_dir(source: &Path, target: &Path) -> AppResult<()> {
    fs::create_dir_all(target)?;
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        let destination = target.join(entry.file_name());
        if path.is_dir() {
            copy_dir(&path, &destination)?;
        } else {
            fs::copy(path, destination)?;
        }
    }
    Ok(())
}

pub fn install_bundled_tools(state: &AppState) -> AppResult<()> {
    let active = state.app_data_dir().join("tools/active");
    if active.join("yt-dlp.exe").is_file() && active.join("ffmpeg.exe").is_file() {
        return Ok(());
    }
    let bundled = state.resource_dir().join("tools");
    if !bundled.join("yt-dlp.exe").is_file() {
        return Ok(());
    }
    let staging = prepare_staging(state)?;
    copy_dir(&bundled, &staging)?;
    activate(state, staging)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_checksum_manifest() {
        let bytes = b"hello";
        let hash = hex::encode(Sha256::digest(bytes));
        let manifest = format!("{hash}  yt-dlp.exe\n");
        assert!(verify_published_checksum(bytes, &manifest, "yt-dlp.exe").is_ok());
        assert!(verify_published_checksum(b"changed", &manifest, "yt-dlp.exe").is_err());
    }
}
