package main

import (
	"fmt"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
	"unsafe"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
	"github.com/lxn/win"
)

// ---- 全局样式 ----

var (
	colorDark         = walk.RGB(0x33, 0x33, 0x33)
	colorProgressBlue = walk.RGB(0x00, 0x88, 0xFF)
	colorWhite        = walk.RGB(0xFF, 0xFF, 0xFF)
	colorLightGray    = walk.RGB(0xF5, 0xF5, 0xF5)
	colorTextDark     = walk.RGB(0x33, 0x33, 0x33)
	colorTextSec      = walk.RGB(0x66, 0x66, 0x66)
	colorAccent       = walk.RGB(0x00, 0x7A, 0xCC)
	colorPrimary      = walk.RGB(0xFF, 0x5A, 0x36)  // 番茄红
	colorBtnDisabled  = walk.RGB(0xF5, 0xF5, 0xF5)
	colorBorder       = walk.RGB(0xE0, 0xE0, 0xE0)
)

const (
	workTime    = 25 * 60
	floatWidth  = 200
	floatHeight = 75
)

// 白色简约背景画刷
func bgWhite() Brush { return SolidColorBrush{Color: colorWhite} }
func bgLight() Brush { return SolidColorBrush{Color: colorLightGray} }

// ---- app 主结构 ----

type app struct {
	mw    *walk.MainWindow
	store *Store
	cloud CloudConfig

	// UI 控件
	timeLabel    *walk.Label
	projectCombo *walk.ComboBox
	taskEdit     *walk.LineEdit
	todayLabel   *walk.Label

	// 状态
	mu             sync.Mutex
	currentTime    int
	isRunning      bool
	startTime      time.Time
	pomodoroCount  int
	currentProject string
	projects       []string

	// 悬浮窗
	floatMW        *walk.MainWindow
	floatTimeLabel *walk.Label
	floatProgress  *walk.CustomWidget
	floatDragX     int
	floatDragY     int
	isFloatMode    bool

	// 计时
	ticker *time.Ticker
}

// ---- 入口 ----

func main() {
	st, err := NewStore()
	if err != nil {
		walk.MsgBox(nil, "错误", "初始化存储失败: "+err.Error(), walk.MsgBoxIconError)
		return
	}
	a := &app{store: st, currentTime: workTime, currentProject: "默认项目", projects: []string{"默认项目"}}

	a.cloud = LoadCloudConfig(st.Dir())
	if a.cloud.Enabled {
		a.pullFromCloud()
	}

	data, _ := st.Load()
	if len(data.Projects) > 0 {
		a.projects = data.Projects
	}
	a.ensureDefaultProject()

	if err := a.createMainWindow(); err != nil {
		walk.MsgBox(nil, "错误", "创建窗口失败: "+err.Error(), walk.MsgBoxIconError)
		return
	}

	a.ticker = time.NewTicker(1 * time.Second)
	go a.tickLoop()
	go a.cloudSyncLoop()
	a.updateTodayLabel()

	a.mw.Run()
}

// ---- 辅助 ----

func (a *app) ensureDefaultProject() {
	has := false
	for _, p := range a.projects {
		if p == "默认项目" {
			has = true
			break
		}
	}
	if !has {
		a.projects = append([]string{"默认项目"}, a.projects...)
	}
}

func formatTime(seconds int) string {
	m, s := seconds/60, seconds%60
	return fmt.Sprintf("%02d:%02d", m, s)
}

func (a *app) currentTask() string {
	t := strings.TrimSpace(a.taskEdit.Text())
	if t == "" {
		return "默认任务"
	}
	return t
}

func makeFixedSize(hwnd win.HWND) {
	style := win.GetWindowLongPtr(hwnd, win.GWL_STYLE)
	style &^= win.WS_THICKFRAME | win.WS_MAXIMIZEBOX
	win.SetWindowLongPtr(hwnd, win.GWL_STYLE, style)
	win.SetWindowPos(hwnd, 0, 0, 0, 0, 0, win.SWP_NOMOVE|win.SWP_NOSIZE|win.SWP_NOZORDER|win.SWP_FRAMECHANGED)
}

// resizeDialog 强制设置窗口客户区大小并锁定尺寸
func resizeDialog(hwnd win.HWND, clientW, clientH int32) {
	// 先锁定不可缩放
	style := win.GetWindowLongPtr(hwnd, win.GWL_STYLE)
	style &^= win.WS_THICKFRAME | win.WS_MAXIMIZEBOX
	win.SetWindowLongPtr(hwnd, win.GWL_STYLE, style)

	// 计算窗口实际大小（加标题栏+边框）
	var rc win.RECT
	rc.Right = clientW
	rc.Bottom = clientH
	win.AdjustWindowRect(&rc, uint32(win.GetWindowLongPtr(hwnd, win.GWL_STYLE)), false)
	winW := rc.Right - rc.Left
	winH := rc.Bottom - rc.Top

	win.SetWindowPos(hwnd, 0, 0, 0, winW, winH, win.SWP_NOMOVE|win.SWP_NOZORDER|win.SWP_FRAMECHANGED)
}

// 设置TableView网格线（declarative不直接支持，需Create后手动设置）
func setupTableView(tv *walk.TableView) {
	if tv != nil {
		tv.SetGridlines(true)
		tv.SetLastColumnStretched(false)
	}
}

// ---- 主窗口创建 ----

func (a *app) createMainWindow() error {
	font := Font{Family: "微软雅黑", PointSize: 10}

	mw := MainWindow{
		AssignTo:    &a.mw,
		Title:       "番茄钟",
		Size:        Size{Width: 500, Height: 365},
		MinSize:     Size{Width: 500, Height: 365},
		MaxSize:     Size{Width: 500, Height: 365},
		Font:        font,
		Background:  bgWhite(),
		Layout:      VBox{Margins: Margins{20, 5, 20, 5}, Spacing: 8},
		MenuItems: []MenuItem{
			Menu{
				Text: "菜单",
				Items: []MenuItem{
					Action{
						Text:        "云端设置",
						OnTriggered: a.showCloudSettings,
					},
					Separator{},
					Action{
						Text:        "今日清零",
						OnTriggered: a.clearTodayData,
					},
				},
			},
		},
		Children: []Widget{
			// 时间显示
			Label{
				AssignTo:   &a.timeLabel,
				Text:       formatTime(a.currentTime),
				Font:       Font{Family: "微软雅黑", PointSize: 48, Bold: true},
				Background: bgWhite(),
				TextColor:  colorTextDark,
				Alignment:  AlignHCenterVCenter,
				MinSize:    Size{Width: 0, Height: 70},
			},
			// 项目行
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 8},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "项目:", Background: bgWhite(), TextColor: colorTextSec, Font: Font{Family: "微软雅黑", PointSize: 11}},
					ComboBox{
						AssignTo:              &a.projectCombo,
						Model:                 a.projects,
						Value:                 a.currentProject,
						Editable:              true,
						OnCurrentIndexChanged: a.onProjectChange,
					},
					PushButton{Text: "添加", OnClicked: a.addProject},
					PushButton{Text: "删除", OnClicked: a.deleteProject},
				},
			},
			// 任务行
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 8},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "任务:", Background: bgWhite(), TextColor: colorTextSec, Font: Font{Family: "微软雅黑", PointSize: 11}},
					LineEdit{
						AssignTo: &a.taskEdit,
						Text:     "默认任务",
					},
				},
			},
			// 控制按钮行
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 8},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "开始", Font: Font{Family: "微软雅黑", PointSize: 11, Bold: true}, OnClicked: a.startPomodoro},
					PushButton{Text: "暂停", Font: Font{Family: "微软雅黑", PointSize: 11, Bold: true}, OnClicked: a.pausePomodoro},
					PushButton{Text: "重置", Font: Font{Family: "微软雅黑", PointSize: 11, Bold: true}, OnClicked: a.resetPomodoro},
					PushButton{Text: "完成", Font: Font{Family: "微软雅黑", PointSize: 11, Bold: true}, OnClicked: a.completePomodoro},
				},
			},
			// 悬浮模式
			PushButton{Text: "切换到悬浮模式", Font: Font{Family: "微软雅黑", PointSize: 11}, OnClicked: a.toggleFloatMode},
			// 今日番茄数
			Label{
				AssignTo:   &a.todayLabel,
				Alignment:  AlignHCenterVCenter,
				Background: bgWhite(),
				TextColor:  colorTextSec,
				Font:       Font{Family: "微软雅黑", PointSize: 11},
			},
			// 统计按钮行
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 5},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "按周查看每天番茄数", OnClicked: a.showWeeklyDayStats},
					PushButton{Text: "按周查看项目番茄数", OnClicked: a.showWeeklyProjectStats},
					PushButton{Text: "按周查看任务番茄数", OnClicked: a.showWeeklyTaskStats},
				},
			},
			VSpacer{},
		},
	}

	if err := mw.Create(); err != nil {
		return err
	}

	// 等布局稳定后强制锁定尺寸
	a.mw.Synchronize(func() {
		hwnd := a.mw.Handle()
		// 去掉可缩放边框
		style := win.GetWindowLongPtr(hwnd, win.GWL_STYLE)
		style &^= win.WS_THICKFRAME | win.WS_MAXIMIZEBOX
		win.SetWindowLongPtr(hwnd, win.GWL_STYLE, style)
		// 计算含标题栏+边框的实际窗口大小
		var rc win.RECT
		rc.Right = 500
		rc.Bottom = 365
		win.AdjustWindowRect(&rc, uint32(style), false)
		winW := rc.Right - rc.Left
		winH := rc.Bottom - rc.Top
		// 强制设置窗口大小
		win.SetWindowPos(hwnd, 0, 0, 0, winW, winH, win.SWP_NOMOVE|win.SWP_NOZORDER|win.SWP_FRAMECHANGED)
	})

	// 设置图标
	if icon, err := walk.NewIconFromFile("icon.ico"); err == nil {
		a.mw.SetIcon(icon)
	}

	return nil
}

// ---- 计时 ----

func (a *app) tickLoop() {
	for range a.ticker.C {
		if a.isRunning {
			elapsed := time.Since(a.startTime)
			remaining := workTime - int(elapsed.Seconds())
			if remaining < 0 {
				remaining = 0
			}
			a.currentTime = remaining

			a.mw.Synchronize(func() {
				a.timeLabel.SetText(formatTime(a.currentTime))
				if a.isFloatMode {
					a.updateFloatDisplay()
				}
				if a.currentTime == 0 {
					a.isRunning = false
					a.pomodoroCount++
					a.savePomodoro()
					a.updateTodayLabel()
					a.showAutoCloseMessage("番茄钟完成！")
					a.resetPomodoro()
				}
			})
		}
	}
}

func (a *app) startPomodoro() {
	if !a.isRunning {
		a.isRunning = true
		a.startTime = time.Now().Add(-time.Duration(workTime-a.currentTime) * time.Second)
	}
}

func (a *app) pausePomodoro() {
	a.isRunning = false
}

func (a *app) resetPomodoro() {
	a.isRunning = false
	a.currentTime = workTime
	a.timeLabel.SetText(formatTime(a.currentTime))
	if a.isFloatMode {
		a.updateFloatDisplay()
	}
}

func (a *app) completePomodoro() {
	a.isRunning = false
	a.pomodoroCount++
	a.savePomodoro()
	a.updateTodayLabel()
	a.currentTime = workTime
	a.timeLabel.SetText(formatTime(a.currentTime))
	if a.isFloatMode {
		a.updateFloatDisplay()
	}
	a.showAutoCloseMessage("番茄钟完成！")
}

// ---- 数据操作 ----

func (a *app) savePomodoro() {
	data, _ := a.store.Load()
	data.AddPomodoro(a.currentProject, a.currentTask())
	a.store.Save(data)
	if a.cloud.Enabled {
		go a.uploadToCloud()
	}
}

func (a *app) updateTodayLabel() {
	data, _ := a.store.Load()
	count := data.TodayTotal()
	if count > 0 {
		a.todayLabel.SetText(fmt.Sprintf("今日番茄数: %s", strings.Repeat("🍅", count)))
	} else {
		a.todayLabel.SetText("今日番茄数: 暂无")
	}
}

func (a *app) onProjectChange() {
	if a.projectCombo != nil {
		a.currentProject = a.projectCombo.Text()
	}
}

func (a *app) addProject() {
	name := a.inputDialog("添加项目", "请输入项目名称:", "")
	if name == "" {
		return
	}
	for _, p := range a.projects {
		if p == name {
			return
		}
	}
	a.projects = append(a.projects, name)
	a.projectCombo.SetModel(a.projects)
	a.projectCombo.SetText(name)
	a.currentProject = name
	a.saveProjects()
}

func (a *app) deleteProject() {
	selected := a.projectCombo.Text()
	if selected == "默认项目" {
		walk.MsgBox(a.mw, "提示", "默认项目不能删除！", walk.MsgBoxIconInformation)
		return
	}
	for i, p := range a.projects {
		if p == selected {
			result := walk.MsgBox(a.mw, "确认", fmt.Sprintf("确定要删除项目 '%s' 吗？", selected), walk.MsgBoxYesNo|walk.MsgBoxIconQuestion)
			if result == win.IDYES {
				a.projects = append(a.projects[:i], a.projects[i+1:]...)
				a.projectCombo.SetModel(a.projects)
				if selected == a.currentProject {
					a.currentProject = "默认项目"
					a.projectCombo.SetText("默认项目")
				}
				a.saveProjects()
			}
			return
		}
	}
}

func (a *app) saveProjects() {
	data, _ := a.store.Load()
	data.Projects = a.projects
	a.store.Save(data)
	if a.cloud.Enabled {
		go a.uploadToCloud()
	}
}

// ---- 悬浮窗 ----

var (
	floatHwnd           win.HWND
	floatOrigWndProcPtr uintptr
	floatAppPtr         *app
	floatWndProcPtr     uintptr
	floatClassRegistered bool
)

// 注册自定义窗口类
func registerFloatWindowClass() {
	if floatClassRegistered {
		return
	}
	className := syscall.StringToUTF16Ptr("PomodoroFloatWindow")

	var wc win.WNDCLASSEX
	wc.CbSize = uint32(unsafe.Sizeof(wc))
	wc.LpfnWndProc = floatWndProcPtr
	wc.LpszClassName = className
	wc.HbrBackground = win.COLOR_3DDKSHADOW + 1 // 深色背景
	wc.Style = win.CS_HREDRAW | win.CS_VREDRAW

	win.RegisterClassEx(&wc)
	floatClassRegistered = true
}

// 添加悬浮窗右键菜单项
func floatAddMenuItem(hmenu win.HMENU, text string, id uint32, enabled bool) {
	var mii win.MENUITEMINFO
	mii.CbSize = uint32(unsafe.Sizeof(mii))
	mii.FMask = win.MIIM_STRING | win.MIIM_ID | win.MIIM_STATE
	mii.FType = win.MFT_STRING
	if !enabled {
		mii.FState = win.MFS_DISABLED
	} else {
		mii.FState = win.MFS_ENABLED
	}
	mii.WID = id
	mii.DwTypeData = syscall.StringToUTF16Ptr(text)
	mii.Cch = uint32(len([]rune(text)))
	win.InsertMenuItem(hmenu, ^uint32(0), true, &mii)
}

func floatAddMenuSeparator(hmenu win.HMENU) {
	var mii win.MENUITEMINFO
	mii.CbSize = uint32(unsafe.Sizeof(mii))
	mii.FMask = win.MIIM_TYPE
	mii.FType = win.MFT_SEPARATOR
	win.InsertMenuItem(hmenu, ^uint32(0), true, &mii)
}

// 悬浮窗WndProc：直接处理所有消息
func floatWndProc(hwnd win.HWND, msg uint32, wParam, lParam uintptr) uintptr {
	switch msg {
	case win.WM_NCHITTEST:
		return win.HTCAPTION // 整个窗口可拖动
	case win.WM_PAINT:
		var ps win.PAINTSTRUCT
		hdc := win.BeginPaint(hwnd, &ps)
		if hdc != 0 {
			if floatAppPtr != nil {
				floatAppPtr.paintFloatWindow(hdc)
			}
			win.EndPaint(hwnd, &ps)
		}
		return 0
	case win.WM_NCRBUTTONUP, win.WM_RBUTTONUP, win.WM_CONTEXTMENU:
		// 右键菜单 - 直接用Win32 API
		hmenu := win.CreatePopupMenu()
		if hmenu != 0 {
			a := floatAppPtr
			// 添加菜单项
			floatAddMenuItem(hmenu, "开始", 1001, !a.isRunning)
			floatAddMenuItem(hmenu, "暂停", 1002, a.isRunning)
			floatAddMenuItem(hmenu, "重置", 1003, true)
			floatAddMenuItem(hmenu, "完成", 1004, true)
			floatAddMenuItem(hmenu, "今日清零", 1005, true)
			floatAddMenuItem(hmenu, "主菜单窗口", 1006, true)
			floatAddMenuSeparator(hmenu)
			floatAddMenuItem(hmenu, "关闭", 1007, true)

			var point win.POINT
			win.GetCursorPos(&point)
			// 用TPM_RETURNCMD获取菜单选择ID，直接处理
			cmd := win.TrackPopupMenu(hmenu, win.TPM_RIGHTBUTTON|win.TPM_RETURNCMD, point.X, point.Y, 0, hwnd, nil)
			win.DestroyMenu(hmenu)

			// 直接处理菜单命令
			switch cmd {
			case 1001:
				if !a.isRunning {
					a.startPomodoro()
				}
			case 1002:
				if a.isRunning {
					a.pausePomodoro()
				}
			case 1003:
				a.resetPomodoro()
			case 1004:
				a.completePomodoro()
			case 1005:
				a.clearTodayData()
			case 1006, 1007:
				a.showMainWindow()
			}
		}
		return 0
	case win.WM_LBUTTONDBLCLK:
		// 双击切换回主窗口
		if floatAppPtr != nil {
			floatAppPtr.showMainWindow()
		}
		return 0
	case win.WM_DESTROY:
		// 清理
		floatHwnd = 0
	}
	return win.DefWindowProc(hwnd, msg, wParam, lParam)
}

func (a *app) toggleFloatMode() {
	if !a.isFloatMode {
		a.isFloatMode = true
		floatAppPtr = a
		a.mw.SetVisible(false)

		// 注册自定义窗口类（使用自定义WndProc，不用子类化）
		floatWndProcPtr = syscall.NewCallback(floatWndProc)
		registerFloatWindowClass()

		// 用自定义类创建无边框窗口
		floatHwnd = win.CreateWindowEx(
			win.WS_EX_TOPMOST|win.WS_EX_TOOLWINDOW|win.WS_EX_LAYERED,
			syscall.StringToUTF16Ptr("PomodoroFloatWindow"),
			syscall.StringToUTF16Ptr(""),
			win.WS_POPUP|win.WS_VISIBLE,
			0, 0, int32(floatWidth), int32(floatHeight),
			0, 0, 0, nil,
		)
		if floatHwnd == 0 {
			return
		}

		// 设置半透明
		setLayeredAttrs(floatHwnd, 230)

		// 设置窗口位置（右下角）
		sw := win.GetSystemMetrics(win.SM_CXSCREEN)
		sh := win.GetSystemMetrics(win.SM_CYSCREEN)
		x := int32(float64(sw)*0.9) - floatWidth
		y := int32(float64(sh)*0.9) - floatHeight
		win.SetWindowPos(floatHwnd, win.HWND_TOPMOST, x, y, int32(floatWidth), int32(floatHeight), win.SWP_SHOWWINDOW)

		a.updateFloatDisplay()
	}
}

// 绘制悬浮窗内容
func (a *app) updateFloatDisplay() {
	if floatHwnd == 0 {
		return
	}
	// 强制重绘
	win.InvalidateRect(floatHwnd, nil, true)
}

// 实际绘制函数，在WM_PAINT中调用
func (a *app) paintFloatWindow(hdc win.HDC) {
	// 用 syscall 调用 GDI 函数
	gdi32 := syscall.NewLazyDLL("gdi32.dll")
	user32 := syscall.NewLazyDLL("user32.dll")

	createSolidBrush := gdi32.NewProc("CreateSolidBrush")
	fillRect := user32.NewProc("FillRect")
	createFontW := gdi32.NewProc("CreateFontW")
	drawTextW := user32.NewProc("DrawTextW")

	// 背景填充
	rect := win.RECT{Left: 0, Top: 0, Right: int32(floatWidth), Bottom: int32(floatHeight)}
	bgColor := win.RGB(0x33, 0x33, 0x33)
	brush, _, _ := createSolidBrush.Call(uintptr(bgColor))
	fillRect.Call(uintptr(hdc), uintptr(unsafe.Pointer(&rect)), uintptr(brush))

	// 进度条
	if a.isRunning {
		progress := float64(workTime-a.currentTime) / float64(workTime)
		barWidth := int32(float64(floatWidth-30) * progress)
		if barWidth > 0 {
			barRect := win.RECT{Left: 15, Top: 5, Right: 15 + barWidth, Bottom: 10}
			barColor := win.RGB(0x00, 0x88, 0xFF)
			barBrush, _, _ := createSolidBrush.Call(uintptr(barColor))
			fillRect.Call(uintptr(hdc), uintptr(unsafe.Pointer(&barRect)), uintptr(barBrush))
		}
	}

	// 时间文字 - 字体放大一倍(72pt)但窗口尺寸不变
	fontName := syscall.StringToUTF16Ptr("Consolas")
	font, _, _ := createFontW.Call(
		uintptr(72),           // nHeight 放大一倍
		uintptr(0),             // nWidth
		uintptr(0),             // nEscapement
		uintptr(0),             // nOrientation
		uintptr(700),           // fnWeight (FW_BOLD)
		uintptr(0),             // fdwItalic
		uintptr(0),             // fdwUnderline
		uintptr(0),             // fdwStrikeOut
		uintptr(0),             // fdwCharSet
		uintptr(0),             // fdwOutputPrecision
		uintptr(0),             // fdwClipPrecision
		uintptr(0),             // fdwQuality
		uintptr(0),             // fdwPitchAndFamily
		uintptr(unsafe.Pointer(fontName)), // lpszFace
	)
	oldFont, _, _ := gdi32.NewProc("SelectObject").Call(uintptr(hdc), uintptr(font))
	win.SetTextColor(hdc, win.RGB(0xFF, 0xFF, 0xFF))
	win.SetBkMode(hdc, win.TRANSPARENT)
	text := syscall.StringToUTF16Ptr(formatTime(a.currentTime))
	textRect := win.RECT{Left: 0, Top: 10, Right: int32(floatWidth), Bottom: int32(floatHeight)}
	drawTextW.Call(
		uintptr(hdc),
		uintptr(unsafe.Pointer(text)),
		uintptr(0xFFFFFFFF), // -1 as uint32
		uintptr(unsafe.Pointer(&textRect)),
		uintptr(win.DT_CENTER|win.DT_VCENTER|win.DT_SINGLELINE),
	)
	gdi32.NewProc("SelectObject").Call(uintptr(hdc), oldFont)
}

func (a *app) paintProgress(canvas *walk.Canvas, bounds walk.Rectangle) error {
	// 不再使用walk的自绘进度条
	return nil
}

func (a *app) showMainWindow() {
	a.isFloatMode = false
	if floatHwnd != 0 {
		win.DestroyWindow(floatHwnd)
		floatHwnd = 0
	}
	a.projectCombo.SetModel(a.projects)
	a.projectCombo.SetText(a.currentProject)
	a.mw.SetVisible(true)
}

// ---- 统计窗口 ----

func (a *app) showWeeklyDayStats() {
	model := &dayStatsModel{}
	a.populateDayStats(model)

	var dlg *walk.Dialog
	var tv *walk.TableView

	Dialog{
		AssignTo:   &dlg,
		Title:      "每周每天番茄数统计",
		Size:       Size{Width: 700, Height: 500},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{10, 10, 10, 10}, Spacing: 10},
		Children: []Widget{
			TableView{
				AssignTo: &tv,
				Columns: []TableViewColumn{
					{Title: "日期", Width: 300},
					{Title: "番茄数", Width: 100},
				},
				Model:    model,
				MinSize:  Size{Width: 0, Height: 400},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "复制", OnClicked: func() { a.copyDayStats(model) }},
					PushButton{Text: "关闭", OnClicked: func() { dlg.Dispose() }},
					HSpacer{},
				},
			},
		},
	}.Create(a.mw)

	setupTableView(tv)
	dlg.Show()
	resizeDialog(dlg.Handle(), 700, 500)
}

type dayStatsModel struct {
	walk.TableModelBase
	rows [][2]string
}

func (m *dayStatsModel) RowCount() int { return len(m.rows) }
func (m *dayStatsModel) Value(row, col int) interface{} {
	if row < 0 || row >= len(m.rows) {
		return nil
	}
	switch col {
	case 0:
		return m.rows[row][0]
	case 1:
		return m.rows[row][1]
	}
	return nil
}

func (a *app) populateDayStats(m *dayStatsModel) {
	data, _ := a.store.Load()
	dates := WeekDates()
	m.rows = [][2]string{}
	for _, d := range dates {
		count := 0
		for _, c := range data.DayProjectCount(d) {
			count += c
		}
		wd := WeekdayName(d)
		m.rows = append(m.rows, [2]string{fmt.Sprintf("%s (%s)", d, wd), strconv.Itoa(count)})
	}
	m.PublishRowsReset()
}

func (a *app) showWeeklyProjectStats() {
	model := &projectStatsModel{}
	a.populateProjectStats(model)

	var dlg *walk.Dialog
	var tv *walk.TableView

	Dialog{
		AssignTo:   &dlg,
		Title:      "每周项目番茄数统计",
		Size:       Size{Width: 700, Height: 600},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{10, 10, 10, 10}, Spacing: 10},
		Children: []Widget{
			TableView{
				AssignTo: &tv,
				Columns: []TableViewColumn{
					{Title: "项目", Width: 150},
					{Title: "番茄数", Width: 100},
					{Title: "目标", Width: 100},
					{Title: "进度", Width: 150},
				},
				Model:    model,
				MinSize:  Size{Width: 0, Height: 500},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "设置目标", OnClicked: func() { a.setProjectTarget(tv, model) }},
					PushButton{Text: "刷新", OnClicked: func() { dlg.Dispose(); a.showWeeklyProjectStats() }},
					PushButton{Text: "复制", OnClicked: func() { a.copyProjectStats(model) }},
					PushButton{Text: "关闭", OnClicked: func() { dlg.Dispose() }},
					HSpacer{},
				},
			},
		},
	}.Create(a.mw)

	setupTableView(tv)
	dlg.Show()
	resizeDialog(dlg.Handle(), 700, 600)
}

type projectStatsModel struct {
	walk.TableModelBase
	rows [][]string
}

func (m *projectStatsModel) RowCount() int { return len(m.rows) }
func (m *projectStatsModel) Value(row, col int) interface{} {
	if row < 0 || row >= len(m.rows) {
		return nil
	}
	if col < 0 || col >= len(m.rows[row]) {
		return nil
	}
	return m.rows[row][col]
}

func (a *app) populateProjectStats(m *projectStatsModel) {
	data, _ := a.store.Load()
	dates := WeekDates()
	counts := map[string]int{}
	for _, d := range dates {
		for proj, c := range data.DayProjectCount(d) {
			counts[proj] += c
		}
	}
	m.rows = [][]string{}
	for proj, c := range counts {
		target := data.ProjectTargets[proj]
		m.rows = append(m.rows, []string{proj, strconv.Itoa(c), strconv.Itoa(target), Progress(c, target)})
	}
	m.PublishRowsReset()
}

func (a *app) setProjectTarget(tv *walk.TableView, model *projectStatsModel) {
	idx := tv.CurrentIndex()
	if idx < 0 {
		walk.MsgBox(a.mw, "提示", "请先选择一个项目", walk.MsgBoxIconInformation)
		return
	}
	name := model.rows[idx][0]
	oldTarget := "0"
	data, _ := a.store.Load()
	if t, ok := data.ProjectTargets[name]; ok {
		oldTarget = strconv.Itoa(t)
	}
	input := a.inputDialog("设置目标", fmt.Sprintf("为项目 '%s' 设置目标番茄数:", name), oldTarget)
	if input == "" {
		return
	}
	target, err := strconv.Atoi(input)
	if err != nil {
		walk.MsgBox(a.mw, "警告", "请输入有效的数字", walk.MsgBoxIconWarning)
		return
	}
	if target < 0 {
		walk.MsgBox(a.mw, "警告", "目标值不能为负数", walk.MsgBoxIconWarning)
		return
	}
	data.ProjectTargets[name] = target
	a.store.Save(data)
	if a.cloud.Enabled {
		go a.uploadToCloud()
	}
	count, _ := strconv.Atoi(model.rows[idx][1])
	model.rows[idx][2] = strconv.Itoa(target)
	model.rows[idx][3] = Progress(count, target)
	model.PublishRowChanged(idx)
}

func (a *app) showWeeklyTaskStats() {
	model := &taskStatsModel{}
	a.populateTaskStats(model)

	var dlg *walk.Dialog
	var tv *walk.TableView

	Dialog{
		AssignTo:   &dlg,
		Title:      "每周任务番茄数统计",
		Size:       Size{Width: 700, Height: 600},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{10, 10, 10, 10}, Spacing: 10},
		Children: []Widget{
			TableView{
				AssignTo: &tv,
				Columns: []TableViewColumn{
					{Title: "项目", Width: 130},
					{Title: "任务", Width: 160},
					{Title: "番茄数", Width: 80},
					{Title: "目标", Width: 80},
					{Title: "进度", Width: 130},
				},
				Model:    model,
				MinSize:  Size{Width: 0, Height: 500},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "设置目标", OnClicked: func() { a.setTaskTarget(tv, model) }},
					PushButton{Text: "刷新", OnClicked: func() { dlg.Dispose(); a.showWeeklyTaskStats() }},
					PushButton{Text: "复制", OnClicked: func() { a.copyTaskStats(model) }},
					PushButton{Text: "关闭", OnClicked: func() { dlg.Dispose() }},
					HSpacer{},
				},
			},
		},
	}.Create(a.mw)

	setupTableView(tv)
	dlg.Show()
	resizeDialog(dlg.Handle(), 700, 600)
}

type taskStatsModel struct {
	walk.TableModelBase
	rows [][]string
}

func (m *taskStatsModel) RowCount() int { return len(m.rows) }
func (m *taskStatsModel) Value(row, col int) interface{} {
	if row < 0 || row >= len(m.rows) {
		return nil
	}
	if col < 0 || col >= len(m.rows[row]) {
		return nil
	}
	return m.rows[row][col]
}

func (a *app) populateTaskStats(m *taskStatsModel) {
	data, _ := a.store.Load()
	dates := WeekDates()
	type key struct{ proj, task string }
	counts := map[key]int{}
	for _, d := range dates {
		for _, entry := range data.DayTaskCounts(d) {
			proj := entry[0].(string)
			task := entry[1].(string)
			count := entry[2].(int)
			counts[key{proj, task}] += count
		}
	}
	m.rows = [][]string{}
	for k, c := range counts {
		target := data.TaskTargets[k.task]
		m.rows = append(m.rows, []string{k.proj, k.task, strconv.Itoa(c), strconv.Itoa(target), Progress(c, target)})
	}
	m.PublishRowsReset()
}

func (a *app) setTaskTarget(tv *walk.TableView, model *taskStatsModel) {
	idx := tv.CurrentIndex()
	if idx < 0 {
		walk.MsgBox(a.mw, "提示", "请先选择一个任务", walk.MsgBoxIconInformation)
		return
	}
	name := model.rows[idx][1]
	oldTarget := "0"
	data, _ := a.store.Load()
	if t, ok := data.TaskTargets[name]; ok {
		oldTarget = strconv.Itoa(t)
	}
	input := a.inputDialog("设置目标", fmt.Sprintf("为任务 '%s' 设置目标番茄数:", name), oldTarget)
	if input == "" {
		return
	}
	target, err := strconv.Atoi(input)
	if err != nil {
		walk.MsgBox(a.mw, "警告", "请输入有效的数字", walk.MsgBoxIconWarning)
		return
	}
	if target < 0 {
		walk.MsgBox(a.mw, "警告", "目标值不能为负数", walk.MsgBoxIconWarning)
		return
	}
	data.TaskTargets[name] = target
	a.store.Save(data)
	if a.cloud.Enabled {
		go a.uploadToCloud()
	}
	count, _ := strconv.Atoi(model.rows[idx][2])
	model.rows[idx][3] = strconv.Itoa(target)
	model.rows[idx][4] = Progress(count, target)
	model.PublishRowChanged(idx)
}

// ---- 复制到剪贴板 ----

func (a *app) copyDayStats(model *dayStatsModel) {
	lines := []string{"日期\t番茄数"}
	for _, row := range model.rows {
		lines = append(lines, row[0]+"\t"+row[1])
	}
	walk.Clipboard().SetText(strings.Join(lines, "\n"))
	a.showAutoCloseMessage("已复制")
}

func (a *app) copyProjectStats(model *projectStatsModel) {
	lines := []string{"项目\t番茄数\t目标\t进度"}
	for _, row := range model.rows {
		lines = append(lines, strings.Join(row, "\t"))
	}
	walk.Clipboard().SetText(strings.Join(lines, "\n"))
	a.showAutoCloseMessage("已复制")
}

func (a *app) copyTaskStats(model *taskStatsModel) {
	lines := []string{"项目\t任务\t番茄数\t目标\t进度"}
	for _, row := range model.rows {
		lines = append(lines, strings.Join(row, "\t"))
	}
	walk.Clipboard().SetText(strings.Join(lines, "\n"))
	a.showAutoCloseMessage("已复制")
}

// ---- 清零今日 ----

func (a *app) clearTodayData() {
	result := walk.MsgBox(a.mw, "确认", "确定要清零今日的番茄数吗？\n此操作不可撤销。", walk.MsgBoxYesNo|walk.MsgBoxIconQuestion)
	if result != win.IDYES {
		return
	}
	data, _ := a.store.Load()
	data.ClearToday()
	a.store.Save(data)
	if a.cloud.Enabled {
		go a.uploadToCloud()
	}
	a.updateTodayLabel()
	a.showAutoCloseMessage("今日数据已清零")
}

// ---- 云端设置 ----

func (a *app) showCloudSettings() {
	cfg := a.cloud
	var endpointEdit, regionEdit, bucketEdit, prefixEdit, accessKeyEdit, secretKeyEdit, objectKeyEdit *walk.LineEdit
	var cloudCheck *walk.CheckBox
	var dlg *walk.Dialog

	Dialog{
		AssignTo:   &dlg,
		Title:      "云端设置",
		Size:       Size{Width: 600, Height: 480},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{20, 20, 20, 20}, Spacing: 10},
		Children: []Widget{
			Label{Text: "S3 对象存储设置", Font: Font{Family: "微软雅黑", PointSize: 14, Bold: true}, Background: bgWhite(), TextColor: colorTextDark},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "Endpoint:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &endpointEdit, Text: cfg.Endpoint},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "Region:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &regionEdit, Text: cfg.Region},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "Bucket:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &bucketEdit, Text: cfg.Bucket},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "Key前缀:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &prefixEdit, Text: cfg.Prefix},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "AccessKey:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &accessKeyEdit, Text: cfg.AccessKey},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "SecretKey:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &secretKeyEdit, Text: cfg.SecretKey, PasswordMode: true},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					Label{Text: "对象名:", MinSize: Size{Width: 80, Height: 0}, Background: bgWhite(), TextColor: colorTextDark},
					LineEdit{AssignTo: &objectKeyEdit, Text: cfg.ObjectKey},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					PushButton{Text: "测试连接", OnClicked: func() {
						testCfg := CloudConfig{
							Endpoint:  endpointEdit.Text(),
							Region:    regionEdit.Text(),
							Bucket:    bucketEdit.Text(),
							AccessKey: accessKeyEdit.Text(),
							SecretKey: secretKeyEdit.Text(),
						}
						client, err := NewCloudClient(testCfg)
						if err != nil {
							walk.MsgBox(dlg, "错误", "S3 连接测试失败：\n"+err.Error(), walk.MsgBoxIconError)
							return
						}
						ctx, cancel := cloudTimeout()
						defer cancel()
						if err := client.Test(ctx); err != nil {
							walk.MsgBox(dlg, "错误", "S3 连接测试失败：\n"+err.Error(), walk.MsgBoxIconError)
							return
						}
						walk.MsgBox(dlg, "成功", "S3 连接测试成功！", walk.MsgBoxIconInformation)
					}},
					PushButton{Text: "保存配置", OnClicked: func() {
						newCfg := CloudConfig{
							Endpoint:  endpointEdit.Text(),
							Region:    regionEdit.Text(),
							Bucket:    bucketEdit.Text(),
							Prefix:    prefixEdit.Text(),
							AccessKey: accessKeyEdit.Text(),
							SecretKey: secretKeyEdit.Text(),
							ObjectKey: objectKeyEdit.Text(),
							Enabled:   cfg.Enabled,
						}
						if newCfg.ObjectKey == "" {
							newCfg.ObjectKey = "pomodoro_data.json"
						}
						client, err := NewCloudClient(newCfg)
						if err != nil {
							walk.MsgBox(dlg, "错误", "保存配置失败：\n"+err.Error(), walk.MsgBoxIconError)
							return
						}
						ctx, cancel := cloudTimeout()
						defer cancel()
						if err := client.Test(ctx); err != nil {
							walk.MsgBox(dlg, "错误", "保存配置失败：\n"+err.Error(), walk.MsgBoxIconError)
							return
						}
						a.cloud = newCfg
						if err := SaveCloudConfig(a.store.Dir(), newCfg); err != nil {
							walk.MsgBox(dlg, "错误", "保存配置失败：\n"+err.Error(), walk.MsgBoxIconError)
							return
						}
						walk.MsgBox(dlg, "成功", "S3 配置保存成功！", walk.MsgBoxIconInformation)
						dlg.Dispose()
					}},
					PushButton{Text: "关闭", OnClicked: func() { dlg.Dispose() }},
				},
			},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 20},
				Background: bgWhite(),
				Children: []Widget{
					CheckBox{
						AssignTo: &cloudCheck,
						Text:     "启用云端同步",
						Checked:  cfg.Enabled,
						OnClicked: func() {
							a.cloud.Enabled = cloudCheck.Checked()
							SaveCloudConfig(a.store.Dir(), a.cloud)
							if cloudCheck.Checked() {
								go a.uploadToCloud()
							}
						},
					},
				},
			},
		},
	}.Create(a.mw)

	resizeDialog(dlg.Handle(), 600, 480)
	dlg.Show()
}

func (a *app) uploadToCloud() {
	if !a.cloud.Enabled {
		return
	}
	client, err := NewCloudClient(a.cloud)
	if err != nil {
		return
	}
	data, _ := a.store.Load()
	body, err := a.store.Marshal(data)
	if err != nil {
		return
	}
	ctx, cancel := cloudTimeout()
	defer cancel()
	client.Upload(ctx, body)
}

func (a *app) pullFromCloud() {
	client, err := NewCloudClient(a.cloud)
	if err != nil {
		return
	}
	ctx, cancel := cloudTimeout()
	defer cancel()
	body, err := client.Download(ctx)
	if err != nil || body == nil {
		if a.cloud.Enabled {
			go a.uploadToCloud()
		}
		return
	}
	data, err := a.store.Unmarshal(body)
	if err == nil && data != nil {
		a.store.Save(data)
	}
}

func (a *app) cloudSyncLoop() {
	for {
		time.Sleep(60 * time.Second)
		if a.cloud.Enabled {
			a.uploadToCloud()
			a.mw.Synchronize(func() {
				a.updateTodayLabel()
			})
		}
	}
}

// ---- 自动消失提示 ----

func (a *app) showAutoCloseMessage(message string) {
	var dlg *walk.Dialog

	Dialog{
		AssignTo:   &dlg,
		Title:      "提示",
		Size:       Size{Width: 350, Height: 120},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{10, 10, 10, 10}},
		Children: []Widget{
			Label{
				Text:       message,
				Font:       Font{Family: "微软雅黑", PointSize: 14, Bold: true},
				Background: bgWhite(),
				TextColor:  colorTextDark,
				Alignment:  AlignHCenterVCenter,
			},
		},
	}.Create(a.mw)

	makeFixedSize(dlg.Handle())

	// 居中
	hwnd := dlg.Handle()
	sw := win.GetSystemMetrics(win.SM_CXSCREEN)
	sh := win.GetSystemMetrics(win.SM_CYSCREEN)
	resizeDialog(hwnd, 350, 120)
	win.SetWindowPos(hwnd, 0, int32(sw/2-175), int32(sh/2-60), 0, 0, win.SWP_NOSIZE|win.SWP_NOZORDER)

	dlg.Show()
	time.AfterFunc(1*time.Second, func() {
		dlg.Synchronize(func() {
			dlg.Accept()
		})
	})
}

// ---- 输入对话框 ----

func (a *app) inputDialog(title, prompt, initial string) string {
	var dlg *walk.Dialog
	var edit *walk.LineEdit
	var result string
	var ok bool

	Dialog{
		AssignTo:   &dlg,
		Title:      title,
		Size:       Size{Width: 450, Height: 160},
		Font:       Font{Family: "微软雅黑", PointSize: 10},
		Background: bgWhite(),
		Layout:     VBox{Margins: Margins{15, 15, 15, 15}, Spacing: 10},
		Children: []Widget{
			Label{Text: prompt, Background: bgWhite(), TextColor: colorTextDark},
			LineEdit{AssignTo: &edit, Text: initial},
			Composite{
				Layout:     HBox{MarginsZero: true, Spacing: 10},
				Background: bgWhite(),
				Children: []Widget{
					HSpacer{},
					PushButton{Text: "确定", OnClicked: func() {
						result = edit.Text()
						ok = true
						dlg.Accept()
					}},
					PushButton{Text: "取消", OnClicked: func() {
						dlg.Cancel()
					}},
				},
			},
		},
	}.Create(a.mw)

	resizeDialog(dlg.Handle(), 450, 160)
	if dlg.Run() == walk.DlgCmdOK || ok {
		return result
	}
	return ""
}

// ---- 菜单辅助 ----

func addMenuItem(menu *walk.Menu, text string, handler func()) {
	action := walk.NewAction()
	action.SetText(text)
	action.Triggered().Attach(handler)
	menu.Actions().Add(action)
}

func addMenuSeparator(menu *walk.Menu) {
	sep := walk.NewSeparatorAction()
	menu.Actions().Add(sep)
}

// ---- Win32 调用：SetLayeredWindowAttributes ----

var (
	user32         = syscall.NewLazyDLL("user32.dll")
	procSetLayered = user32.NewProc("SetLayeredWindowAttributes")
)

func setLayeredAttrs(hwnd win.HWND, alpha byte) {
	procSetLayered.Call(uintptr(hwnd), 0, uintptr(alpha), uintptr(2)) // LWA_ALPHA = 2
}
