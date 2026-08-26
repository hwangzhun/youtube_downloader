use crate::{
    error::{AppError, AppResult},
    models::{Settings, TaskEvent, TaskRecord},
};
use std::{
    collections::HashMap,
    fs,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};
use tauri::ipc::Channel;
use tokio::sync::{Mutex, RwLock, Semaphore};
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    inner: Arc<Inner>,
}

struct Inner {
    pub app_data_dir: PathBuf,
    pub resource_dir: PathBuf,
    pub settings: RwLock<Settings>,
    pub tasks: Mutex<HashMap<Uuid, TaskRecord>>,
    pub task_channels: Mutex<HashMap<Uuid, Channel<TaskEvent>>>,
    pub child_pids: Mutex<HashMap<Uuid, u32>>,
    pub queue_paused: AtomicBool,
    pub semaphore: RwLock<Arc<Semaphore>>,
}

impl AppState {
    pub fn load(app_data_dir: PathBuf, resource_dir: PathBuf) -> AppResult<Self> {
        fs::create_dir_all(&app_data_dir)?;
        fs::create_dir_all(app_data_dir.join("config"))?;
        fs::create_dir_all(app_data_dir.join("cookies"))?;
        fs::create_dir_all(app_data_dir.join("temp"))?;
        fs::create_dir_all(app_data_dir.join("tools"))?;
        let settings =
            load_json::<Settings>(&app_data_dir.join("config/settings.json")).unwrap_or_default();
        let max = settings.max_concurrent.clamp(1, 4);
        Ok(Self {
            inner: Arc::new(Inner {
                app_data_dir,
                resource_dir,
                settings: RwLock::new(settings),
                tasks: Mutex::new(HashMap::new()),
                task_channels: Mutex::new(HashMap::new()),
                child_pids: Mutex::new(HashMap::new()),
                queue_paused: AtomicBool::new(false),
                semaphore: RwLock::new(Arc::new(Semaphore::new(max))),
            }),
        })
    }

    pub fn app_data_dir(&self) -> &Path {
        &self.inner.app_data_dir
    }
    pub fn resource_dir(&self) -> &Path {
        &self.inner.resource_dir
    }
    pub fn is_paused(&self) -> bool {
        self.inner.queue_paused.load(Ordering::SeqCst)
    }
    pub fn set_paused(&self, value: bool) {
        self.inner.queue_paused.store(value, Ordering::SeqCst);
    }
    pub async fn settings(&self) -> Settings {
        self.inner.settings.read().await.clone()
    }
    pub async fn save_settings(&self, mut settings: Settings) -> AppResult<Settings> {
        settings.max_concurrent = settings.max_concurrent.clamp(1, 4);
        atomic_json(
            &self.inner.app_data_dir.join("config/settings.json"),
            &settings,
        )?;
        *self.inner.settings.write().await = settings.clone();
        *self.inner.semaphore.write().await = Arc::new(Semaphore::new(settings.max_concurrent));
        Ok(settings)
    }
    pub async fn semaphore(&self) -> Arc<Semaphore> {
        self.inner.semaphore.read().await.clone()
    }
    pub async fn insert_task(&self, record: TaskRecord, channel: Channel<TaskEvent>) {
        self.inner
            .task_channels
            .lock()
            .await
            .insert(record.public.id, channel);
        self.inner
            .tasks
            .lock()
            .await
            .insert(record.public.id, record);
    }
    pub async fn broadcast(&self, event: TaskEvent) {
        for channel in self.inner.task_channels.lock().await.values() {
            let _ = channel.send(event.clone());
        }
    }
    pub async fn record(&self, id: Uuid) -> Option<TaskRecord> {
        self.inner.tasks.lock().await.get(&id).cloned()
    }
    pub async fn update_record(&self, record: TaskRecord) {
        self.inner
            .tasks
            .lock()
            .await
            .insert(record.public.id, record.clone());
        if let Some(channel) = self.inner.task_channels.lock().await.get(&record.public.id) {
            let _ = channel.send(TaskEvent::Snapshot(record.public));
        }
    }
    pub async fn list_tasks(&self) -> Vec<crate::models::DownloadTask> {
        self.inner
            .tasks
            .lock()
            .await
            .values()
            .map(|record| record.public.clone())
            .collect()
    }
    pub async fn set_pid(&self, id: Uuid, pid: u32) {
        self.inner.child_pids.lock().await.insert(id, pid);
    }
    pub async fn remove_pid(&self, id: Uuid) {
        self.inner.child_pids.lock().await.remove(&id);
    }
    pub async fn pid(&self, id: Uuid) -> Option<u32> {
        self.inner.child_pids.lock().await.get(&id).copied()
    }
}

fn load_json<T: serde::de::DeserializeOwned>(path: &Path) -> Option<T> {
    fs::read(path)
        .ok()
        .and_then(|bytes| serde_json::from_slice(&bytes).ok())
}

pub fn atomic_json<T: serde::Serialize>(path: &Path, value: &T) -> AppResult<()> {
    let parent = path
        .parent()
        .ok_or_else(|| AppError::fatal("invalid_path", "配置路径无父目录"))?;
    fs::create_dir_all(parent)?;
    let temp = path.with_extension("tmp");
    fs::write(&temp, serde_json::to_vec_pretty(value)?)?;
    if path.exists() {
        fs::remove_file(path)?;
    }
    fs::rename(temp, path)?;
    Ok(())
}
