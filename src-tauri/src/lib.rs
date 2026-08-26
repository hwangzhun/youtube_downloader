mod commands;
mod cookie;
mod downloader;
mod error;
mod models;
mod runtime;
mod state;
mod tools;

use state::AppState;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_log::Builder::new()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            let _ = app.remove_menu()?;
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.remove_menu()?;
            }
            let app_data_dir = app.path().app_data_dir()?;
            let resource_dir = app.path().resource_dir()?;
            let state = AppState::load(app_data_dir, resource_dir).map_err(|error| {
                let source: Box<dyn std::error::Error> = Box::new(error);
                tauri::Error::Setup(source.into())
            })?;
            if let Err(error) = tools::install_bundled_tools(&state) {
                log::warn!("无法安装内置下载组件：{error}");
            }
            let show = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            TrayIconBuilder::new()
                .icon(
                    app.default_window_icon()
                        .ok_or_else(|| tauri::Error::AssetNotFound("default icon".into()))?
                        .clone(),
                )
                .tooltip("YouTube Downloader")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        if let Some(window) = tray.app_handle().get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_runtime_status,
            commands::parse_video,
            commands::expand_playlist,
            commands::fetch_channel,
            commands::enqueue_downloads,
            commands::list_tasks,
            commands::cancel_task,
            commands::retry_task,
            commands::open_task_directory,
            commands::set_queue_paused,
            commands::get_settings,
            commands::save_settings,
            commands::select_output_directory,
            commands::open_login_window,
            commands::capture_login_cookies,
            commands::clear_login_profile,
            commands::import_cookie_file,
            commands::get_cookie_status,
            commands::validate_cookie,
            commands::clear_cookie,
            commands::check_tool_updates,
            commands::update_tool,
            commands::check_app_update,
            commands::install_app_update,
        ])
        .run(tauri::generate_context!())
        .expect("failed to run YouTube Downloader");
}
