!macro NSIS_HOOK_PREINSTALL
  ; 关闭旧 PyQt/PyInstaller 进程。失败时继续，因为旧程序可能没有运行。
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /IM YouTube_Downloader.exe /T /F'

  ; Inno Setup 使用 AppId 后缀 _is1 写入卸载项。优先检查机器级安装，再检查用户级安装。
  StrCpy $0 ""
  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}_is1" "UninstallString"
  ${If} $0 == ""
    ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}_is1" "UninstallString"
  ${EndIf}

  ${If} $0 != ""
    DetailPrint "检测到 YouTube Downloader 1.x，正在卸载旧版…"
    ExecWait '$0 /VERYSILENT /SUPPRESSMSGBOXES /NORESTART' $1
    ${If} $1 != 0
      MessageBox MB_ICONSTOP|MB_OK "旧版卸载未完成（错误码 $1）。Tauri 2 安装已停止，旧用户数据不会被删除。"
      Abort
    ${EndIf}
  ${EndIf}
!macroend
