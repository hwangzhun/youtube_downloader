use crate::{
    models::{RuntimeStatus, RuntimeTool},
    state::AppState,
};
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::{
    path::{Path, PathBuf},
    process::Command,
};

const CREATE_NO_WINDOW: u32 = 0x08000000;

pub fn runtime_status(state: &AppState) -> RuntimeStatus {
    let yt_dlp = locate(state, "YTDLP_PATH", "yt-dlp.exe");
    let ffmpeg = locate(state, "FFMPEG_PATH", "ffmpeg.exe");
    let ffprobe = locate(state, "FFPROBE_PATH", "ffprobe.exe");
    let js = system_tool(&["node", "deno"]);
    RuntimeStatus {
        app_version: env!("CARGO_PKG_VERSION").into(),
        webview2: RuntimeTool {
            available: true,
            version: None,
            path: None,
        },
        yt_dlp: describe(yt_dlp, &["--version"]),
        ffmpeg: describe(ffmpeg, &["-version"]),
        ffprobe: describe(ffprobe, &["-version"]),
        javascript_runtime: js,
    }
}

pub fn yt_dlp_path(state: &AppState) -> Option<PathBuf> {
    locate(state, "YTDLP_PATH", "yt-dlp.exe")
}

pub fn ffmpeg_path(state: &AppState) -> Option<PathBuf> {
    locate(state, "FFMPEG_PATH", "ffmpeg.exe")
}

fn locate(state: &AppState, env_name: &str, name: &str) -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Some(value) = std::env::var_os(env_name) {
        candidates.push(PathBuf::from(value));
    }
    candidates.push(state.app_data_dir().join("tools/active").join(name));
    candidates.push(state.resource_dir().join("tools").join(name));
    candidates.into_iter().find(|path| path.is_file())
}

fn describe(path: Option<PathBuf>, args: &[&str]) -> RuntimeTool {
    let Some(path) = path else {
        return RuntimeTool {
            available: false,
            version: None,
            path: None,
        };
    };
    let version = run_version(&path, args);
    RuntimeTool {
        available: version.is_some(),
        version,
        path: Some(path.to_string_lossy().into_owned()),
    }
}

fn system_tool(names: &[&str]) -> RuntimeTool {
    for name in names {
        if let Some(version) = run_version(Path::new(name), &["--version"]) {
            return RuntimeTool {
                available: true,
                version: Some(format!("{name} {version}")),
                path: Some((*name).into()),
            };
        }
    }
    RuntimeTool {
        available: false,
        version: None,
        path: None,
    }
}

fn run_version(path: &Path, args: &[&str]) -> Option<String> {
    let mut command = Command::new(path);
    command.args(args);
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
    let output = command.output().ok()?;
    if !output.status.success() {
        return None;
    }
    let text = if output.stdout.is_empty() {
        &output.stderr
    } else {
        &output.stdout
    };
    String::from_utf8_lossy(text)
        .lines()
        .next()
        .map(|line| line.trim().to_owned())
}
