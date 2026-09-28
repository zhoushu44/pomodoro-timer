# 番茄钟 (Pomodoro Timer)

纯 Go 编写的 Windows 桌面番茄钟应用，单一 exe，无运行时依赖，数据存储在 `%APPDATA%\PomodoroTimer\`。

## 功能特性

### 核心功能
- **25分钟番茄钟** — 标准番茄工作法计时
- **悬浮模式** — 切换为悬浮小窗口，始终置顶，可拖动，右键菜单操作
- **项目管理** — 支持多项目分类，可添加/删除项目
- **任务管理** — 为每个番茄钟关联任务名称
- **数据统计** — 按周查看每天/项目/任务番茄数
- **云端同步** — 腾讯云 COS 数据同步，支持测试连接、自动同步

### 界面设计
- **白底简约风格** — 纯白背景，深灰文字，微软雅黑字体
- **固定窗口尺寸** — 主窗口 500x365，不可缩放
- **GDI 悬浮窗** — 纯 Win32 API 实现，深色背景 + 蓝色进度条

## 快速开始

1. 下载 `pomodoro-timer.exe`
2. 双击运行
3. 无需安装任何运行时环境

## 使用指南

### 主界面
1. **选择项目** — 从下拉列表选择或输入新项目名
2. **输入任务** — 在任务栏输入当前任务名称
3. **开始计时** — 点击"开始"按钮启动 25 分钟番茄钟
4. **控制按钮** — 暂停 / 重置 / 完成

### 悬浮模式
- 点击"切换到悬浮模式"进入悬浮窗
- **拖动** — 任意位置点击拖动
- **右键菜单** — 开始/暂停/重置/完成/今日清零/主菜单窗口/关闭
- **双击** — 切换回主窗口

### 数据统计
- **按周查看每天番茄数** — 每天完成番茄数表格
- **按周查看项目番茄数** — 各项目本周番茄数 + 目标进度
- **按周查看任务番茄数** — 各任务本周番茄数

### 云端同步
1. 菜单 → 云端设置
2. 填写腾讯云 COS 配置（Endpoint / Region / Bucket / AccessKey / SecretKey）
3. 点击"测试连接"验证配置
4. 勾选"启用云端同步"自动上传/下载数据

## 文件结构

```
pomodoro-timer/
├── main.go          # 主程序（GUI + 业务逻辑）
├── cloud.go         # 云端同步（腾讯云 COS HMAC-SHA1 签名）
├── store.go         # 数据存储层
├── go.mod           # Go 依赖
├── app.manifest     # 应用清单（Common Controls v6）
├── icon.ico         # 图标
├── rsrc.syso        # 嵌入资源（图标 + manifest）
└── pomodoro-timer.exe  # 最终可执行文件
```

## 技术栈

- **语言** — Go 1.26
- **GUI 框架** — [lxn/walk](https://github.com/lxn/walk) (declarative API)
- **Win32 API** — [lxn/win](https://github.com/lxn/win)
- **资源嵌入** — [akavel/rsrc](https://github.com/akavel/rsrc)
- **云端存储** — 腾讯云 COS（手动实现 HMAC-SHA1 签名，不依赖第三方 SDK）

## 数据存储

- **位置** — `%APPDATA%\PomodoroTimer\pomodoro_data.json`
- **云端** — 腾讯云 COS 对象存储
- **格式** — JSON
```json
{
  "2026-01-01": {
    "项目A|任务1": 5,
    "项目B|任务2": 3
  },
  "project_targets": {
    "项目A": 10
  },
  "projects": ["默认项目", "项目A"]
}
```

## 编译

```powershell
# 安装资源工具
go install github.com/akavel/rsrc@latest

# 生成嵌入资源（图标 + manifest）
rsrc -manifest app.manifest -ico icon.ico -o rsrc.syso

# 编译
$env:CGO_ENABLED=0
go build -ldflags "-H windowsgui -s -w" -o pomodoro-timer.exe
```

## 版本历史

### v2.0 (2026-09)
- Go 完全重写，单一 exe 无依赖
- 白底简约 UI
- 腾讯云 COS 云端同步
- 纯 Win32 悬浮窗（GDI 绘制 + 拖动 + 右键菜单）

### v1.0 (2026-02)
- Python + Tkinter 版本
