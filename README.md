# 番茄钟 Pomodoro Timer v1

一个功能完整的番茄钟应用程序，具有现代化的界面设计和丰富的功能特性。

![番茄钟界面](screenshot.png)

## ✨ 功能特性

### 🕒 核心功能
- **25分钟番茄钟**：标准番茄工作法计时
- **悬浮模式**：可切换为悬浮小窗口，始终置顶
- **项目管理**：支持多项目分类统计
- **数据统计**：按周查看每天/项目番茄数

### 🎨 界面设计
- **现代化设计**：符合设计规范的UI界面
- **紧凑布局**：500x365窗口尺寸，无多余空白
- **圆角按钮**：所有按钮采用圆角设计
- **响应式交互**：按钮悬停效果

### 📊 高级功能
- **目标设置**：为项目设置番茄数目标，跟踪完成进度
- **今日清零**：一键清除今日所有番茄数记录
- **自动提示**：完成提示自动消失1秒
- **数据持久化**：JSON文件保存所有数据

## 🚀 快速开始

### 方法一：使用exe文件（推荐）
1. 下载 `番茄钟_v1.exe`
2. 双击运行即可
3. 无需安装Python环境

### 方法二：运行Python源码
```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main_v2.py
```

## 📁 文件结构

```
番茄钟/
├── main_v2.py              # 主程序源码
├── 番茄钟_v1.exe           # 打包好的可执行文件
├── pomodoro_data.json     # 数据文件（运行时自动创建）
├── README.md              # 说明文档
├── requirements.txt       # Python依赖
└── .gitignore            # Git忽略文件
```

## 🎯 使用指南

### 主界面操作
1. **选择项目**：从下拉列表中选择或添加新项目
2. **开始计时**：点击"开始"按钮开始25分钟番茄钟
3. **控制计时**：使用"暂停"、"重置"、"完成"按钮控制
4. **切换模式**：点击"切换到悬浮模式"进入悬浮窗口

### 悬浮模式
- **右键菜单**：包含开始、暂停、重置、完成、今日清零等功能
- **拖动窗口**：可拖动悬浮窗口到任意位置
- **自动定位**：默认位于屏幕右下角（离底部10%，离右边10%）

### 数据统计
- **按周查看每天番茄数**：查看本周每天的番茄数统计
- **按周查看项目番茄数**：查看各项目本周番茄数，可设置目标

### 目标管理
1. 打开"按周查看项目番茄数"
2. 选择项目
3. 点击"设置目标"按钮
4. 输入目标番茄数
5. 查看进度列显示完成情况

### 今日清零
1. 切换到悬浮模式
2. 右键点击悬浮窗口
3. 选择"今日清零"
4. 确认操作
5. 今日所有番茄数记录将被清除

## ⚙️ 技术细节

### 开发环境
- **Python版本**：3.10.11
- **GUI框架**：Tkinter
- **打包工具**：PyInstaller 6.16.0
- **操作系统**：Windows 10/11

### 设计规范
- **主色调**：番茄红 #FF5A36
- **背景色**：纯白 #FFFFFF
- **文字色**：深灰 #333333
- **按钮样式**：圆角24px，高度35px，宽度80px
- **字体**：微软雅黑（跨设备一致性）

### 数据存储
- **格式**：JSON
- **文件**：pomodoro_data.json
- **结构**：
  ```json
  {
    "2025-01-01": {
      "项目A": 5,
      "项目B": 3
    },
    "project_targets": {
      "项目A": 10,
      "项目B": 5
    },
    "projects": ["默认项目", "项目A", "项目B"]
  }
  ```

## 🔧 开发指南

### 环境搭建
```bash
# 克隆仓库
git clone https://github.com/yourusername/pomodoro-timer.git

# 进入目录
cd pomodoro-timer

# 安装依赖
pip install -r requirements.txt
```

### 打包exe
```bash
# 安装PyInstaller
pip install pyinstaller

# 打包程序
pyinstaller --onefile --windowed --name "番茄钟_v1" main_v2.py
```

### 代码结构
- `PomodoroApp` 类：主应用程序类
- `create_widgets()`：创建界面组件
- `update_clock()`：计时器更新逻辑
- `show_weekly_project_stats()`：项目统计功能
- `clear_today_data()`：今日清零功能

## 📝 版本历史

### v1.0 (2026-02-02)
- ✅ 基础番茄钟功能
- ✅ 悬浮窗口模式
- ✅ 项目管理功能
- ✅ 数据统计功能
- ✅ 目标设置功能
- ✅ 今日清零功能
- ✅ exe文件打包

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- 感谢番茄工作法的发明者 Francesco Cirillo
- 感谢所有开源项目的贡献者
- 感谢用户反馈和建议

## 📧 联系信息

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [提交问题](https://github.com/yourusername/pomodoro-timer/issues)
- Email: your.email@example.com

---

**让每一分钟都有价值，用番茄钟提升工作效率！** 🍅