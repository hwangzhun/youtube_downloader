use serde::{ser::SerializeStruct, Serialize, Serializer};
use serde_json::Value;
use std::borrow::Cow;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("{message}")]
    User {
        code: String,
        message: String,
        recoverable: bool,
        details: Option<Value>,
    },
    #[error("内部错误：{0}")]
    Internal(String),
}
impl Serialize for AppError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        let (code, message, recoverable, details): (&str, Cow<'_, str>, bool, Option<&Value>) =
            match self {
                Self::User {
                    code,
                    message,
                    recoverable,
                    details,
                } => (
                    code.as_str(),
                    Cow::Borrowed(message.as_str()),
                    *recoverable,
                    details.as_ref(),
                ),
                Self::Internal(message) => (
                    "internal_error",
                    Cow::Owned(format!("内部错误：{message}")),
                    false,
                    None,
                ),
            };
        let mut value = serializer.serialize_struct("AppError", 4)?;
        value.serialize_field("code", code)?;
        value.serialize_field("message", &message)?;
        value.serialize_field("recoverable", &recoverable)?;
        value.serialize_field("details", &details)?;
        value.end()
    }
}

impl AppError {
    pub fn user(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self::User {
            code: code.into(),
            message: message.into(),
            recoverable: true,
            details: None,
        }
    }

    pub fn fatal(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self::User {
            code: code.into(),
            message: message.into(),
            recoverable: false,
            details: None,
        }
    }
}

impl From<std::io::Error> for AppError {
    fn from(value: std::io::Error) -> Self {
        Self::Internal(value.to_string())
    }
}

impl From<serde_json::Error> for AppError {
    fn from(value: serde_json::Error) -> Self {
        Self::Internal(value.to_string())
    }
}

impl From<tauri::Error> for AppError {
    fn from(value: tauri::Error) -> Self {
        Self::Internal(value.to_string())
    }
}

pub type AppResult<T> = Result<T, AppError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serializes_as_flat_ipc_error() {
        let value = serde_json::to_value(AppError::user("parse_failed", "解析失败")).unwrap();
        assert_eq!(value["code"], "parse_failed");
        assert_eq!(value["message"], "解析失败");
        assert_eq!(value["recoverable"], true);
        assert!(value.get("user").is_none());
    }
}
