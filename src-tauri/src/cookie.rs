use crate::{
    error::{AppError, AppResult},
    models::CookieStatus,
    state::AppState,
};
use std::{
    fs,
    path::{Path, PathBuf},
};
use uuid::Uuid;

const COOKIE_FILE: &str = "cookies/youtube.dpapi";

pub struct TempCookie {
    path: PathBuf,
}

impl TempCookie {
    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempCookie {
    fn drop(&mut self) {
        if let Ok(metadata) = fs::metadata(&self.path) {
            let _ = fs::write(&self.path, vec![0u8; metadata.len() as usize]);
        }
        let _ = fs::remove_file(&self.path);
    }
}

pub fn save(state: &AppState, netscape: &str, source: &str) -> AppResult<CookieStatus> {
    let count = validate_netscape(netscape)?;
    let protected = protect_current_user(netscape.as_bytes())?;
    let path = state.app_data_dir().join(COOKIE_FILE);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, protected)?;
    Ok(CookieStatus {
        state: "unverified".into(),
        source: Some(source.into()),
        message: "Cookie 已安全保存，尚未联网验证".into(),
        cookie_count: count,
    })
}

pub fn import_file(state: &AppState, path: &Path) -> AppResult<CookieStatus> {
    let metadata = fs::metadata(path)
        .map_err(|_| AppError::user("cookie_file_missing", "Cookie 文件不存在"))?;
    if metadata.len() > 4 * 1024 * 1024 {
        return Err(AppError::user(
            "cookie_file_too_large",
            "Cookie 文件异常大，已拒绝导入",
        ));
    }
    let content = fs::read_to_string(path).map_err(|_| {
        AppError::user(
            "cookie_read_failed",
            "无法读取 Cookie 文件，请确认它是 UTF-8 文本",
        )
    })?;
    save(state, &content, "import")
}

pub fn materialize(state: &AppState) -> AppResult<TempCookie> {
    let protected = fs::read(state.app_data_dir().join(COOKIE_FILE))
        .map_err(|_| AppError::user("cookie_missing", "尚未保存 Cookie"))?;
    let plaintext = unprotect_current_user(&protected)?;
    let text = String::from_utf8(plaintext)
        .map_err(|_| AppError::fatal("cookie_corrupt", "Cookie 存储已损坏"))?;
    validate_netscape(&text)?;
    let path = state
        .app_data_dir()
        .join("temp")
        .join(format!("cookies-{}.txt", Uuid::new_v4()));
    fs::write(&path, text.as_bytes())?;
    Ok(TempCookie { path })
}

pub fn status(state: &AppState) -> CookieStatus {
    match materialize(state) {
        Ok(file) => {
            let count = fs::read_to_string(file.path())
                .ok()
                .and_then(|value| validate_netscape(&value).ok())
                .unwrap_or_default();
            CookieStatus {
                state: "unverified".into(),
                source: None,
                message: "Cookie 已保存".into(),
                cookie_count: count,
            }
        }
        Err(_) => CookieStatus {
            state: "missing".into(),
            source: None,
            message: "尚未配置 Cookie".into(),
            cookie_count: 0,
        },
    }
}

pub fn clear(state: &AppState) -> AppResult<()> {
    let path = state.app_data_dir().join(COOKIE_FILE);
    if path.exists() {
        if let Ok(metadata) = fs::metadata(&path) {
            let _ = fs::write(&path, vec![0u8; metadata.len() as usize]);
        }
        fs::remove_file(path)?;
    }
    Ok(())
}

pub fn validate_netscape(content: &str) -> AppResult<usize> {
    if !content
        .lines()
        .next()
        .unwrap_or_default()
        .contains("Netscape HTTP Cookie File")
    {
        return Err(AppError::user(
            "cookie_format",
            "Cookie 文件不是 Netscape 格式",
        ));
    }
    let mut count = 0;
    let mut youtube = false;
    for line in content.lines() {
        let data = line.strip_prefix("#HttpOnly_").unwrap_or(line);
        if data.starts_with('#') || data.trim().is_empty() {
            continue;
        }
        let columns: Vec<_> = data.split('\t').collect();
        if columns.len() != 7 {
            continue;
        }
        count += 1;
        let domain = columns[0].to_ascii_lowercase();
        youtube |= domain.contains("youtube.com") || domain.contains("google.com");
    }
    if count == 0 || !youtube {
        return Err(AppError::user(
            "cookie_content",
            "没有找到 YouTube 登录 Cookie",
        ));
    }
    Ok(count)
}

#[cfg(windows)]
fn protect_current_user(input: &[u8]) -> AppResult<Vec<u8>> {
    use std::{ffi::c_void, ptr::null_mut};
    use windows_sys::Win32::{
        Foundation::LocalFree,
        Security::Cryptography::{CryptProtectData, CRYPTPROTECT_UI_FORBIDDEN, CRYPT_INTEGER_BLOB},
    };
    let mut input_blob = CRYPT_INTEGER_BLOB {
        cbData: u32::try_from(input.len())
            .map_err(|_| AppError::fatal("cookie_too_large", "Cookie 内容过大"))?,
        pbData: input.as_ptr().cast_mut(),
    };
    let mut output = CRYPT_INTEGER_BLOB {
        cbData: 0,
        pbData: null_mut(),
    };
    let ok = unsafe {
        CryptProtectData(
            &mut input_blob,
            std::ptr::null(),
            std::ptr::null(),
            null_mut(),
            std::ptr::null(),
            CRYPTPROTECT_UI_FORBIDDEN,
            &mut output,
        )
    };
    if ok == 0 {
        return Err(AppError::fatal("dpapi_encrypt", "Windows 无法保护 Cookie"));
    }
    let result =
        unsafe { std::slice::from_raw_parts(output.pbData, output.cbData as usize).to_vec() };
    unsafe {
        LocalFree(output.pbData.cast::<c_void>());
    }
    Ok(result)
}

#[cfg(windows)]
fn unprotect_current_user(input: &[u8]) -> AppResult<Vec<u8>> {
    use std::{ffi::c_void, ptr::null_mut};
    use windows_sys::Win32::{
        Foundation::LocalFree,
        Security::Cryptography::{
            CryptUnprotectData, CRYPTPROTECT_UI_FORBIDDEN, CRYPT_INTEGER_BLOB,
        },
    };
    let mut input_blob = CRYPT_INTEGER_BLOB {
        cbData: u32::try_from(input.len())
            .map_err(|_| AppError::fatal("cookie_too_large", "Cookie 内容过大"))?,
        pbData: input.as_ptr().cast_mut(),
    };
    let mut output = CRYPT_INTEGER_BLOB {
        cbData: 0,
        pbData: null_mut(),
    };
    let ok = unsafe {
        CryptUnprotectData(
            &mut input_blob,
            null_mut(),
            std::ptr::null(),
            null_mut(),
            std::ptr::null(),
            CRYPTPROTECT_UI_FORBIDDEN,
            &mut output,
        )
    };
    if ok == 0 {
        return Err(AppError::fatal(
            "dpapi_decrypt",
            "Cookie 无法解密，可能来自其他 Windows 用户",
        ));
    }
    let mut result =
        unsafe { std::slice::from_raw_parts(output.pbData, output.cbData as usize).to_vec() };
    unsafe {
        std::ptr::write_bytes(output.pbData, 0, output.cbData as usize);
        LocalFree(output.pbData.cast::<c_void>());
    }
    if result.is_empty() {
        result.clear();
    }
    Ok(result)
}

#[cfg(not(windows))]
fn protect_current_user(_: &[u8]) -> AppResult<Vec<u8>> {
    Err(AppError::fatal(
        "unsupported_platform",
        "此版本仅支持 Windows",
    ))
}

#[cfg(not(windows))]
fn unprotect_current_user(_: &[u8]) -> AppResult<Vec<u8>> {
    Err(AppError::fatal(
        "unsupported_platform",
        "此版本仅支持 Windows",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_netscape_cookie() {
        let content = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsecret\n";
        assert_eq!(validate_netscape(content).unwrap(), 1);
    }

    #[test]
    fn rejects_unrelated_cookie() {
        let content = "# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tTRUE\t0\tSID\tsecret\n";
        assert!(validate_netscape(content).is_err());
    }
}
