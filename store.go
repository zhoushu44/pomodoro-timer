package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Data 番茄钟的全部持久化数据。
// 磁盘上只保存在 %APPDATA%\PomodoroTimer\ 目录下，软件目录不产生任何文件。
type Data struct {
	Projects       []string                               // 项目列表
	ProjectTargets map[string]int                         // 项目目标
	TaskTargets    map[string]int                         // 任务目标
	Days           map[string]map[string]int              // 日期 -> 项目 -> 番茄数
	Tasks          map[string]map[string]map[string]int   // 日期 -> 项目 -> 任务 -> 番茄数
}

// Store 负责数据的读写与云端同步，所有访问都加锁保证线程安全。
type Store struct {
	mu   sync.Mutex
	dir  string
	path string
}

// NewStore 创建存储对象，数据目录固定在 %APPDATA%\PomodoroTimer。
func NewStore() (*Store, error) {
	base := os.Getenv("APPDATA")
	if base == "" {
		var err error
		base, err = os.UserConfigDir()
		if err != nil {
			return nil, err
		}
	}
	dir := filepath.Join(base, "PomodoroTimer")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	return &Store{dir: dir, path: filepath.Join(dir, "data.json")}, nil
}

// Dir 返回数据目录，供云端配置文件使用。
func (s *Store) Dir() string { return s.dir }

func newData() *Data {
	return &Data{
		Projects:       []string{"默认项目"},
		ProjectTargets: map[string]int{},
		TaskTargets:    map[string]int{},
		Days:           map[string]map[string]int{},
		Tasks:          map[string]map[string]map[string]int{},
	}
}

// Load 读取全部数据；文件不存在时返回空数据。
func (s *Store) Load() (*Data, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.loadLocked()
}

func (s *Store) loadLocked() (*Data, error) {
	raw, err := os.ReadFile(s.path)
	if err != nil {
		if os.IsNotExist(err) {
			return newData(), nil
		}
		return nil, err
	}
	if len(raw) == 0 {
		return newData(), nil
	}

	// 两趟解析：先取顶层键，再按类型分派，便于兼容旧格式。
	var top map[string]json.RawMessage
	if err := json.Unmarshal(raw, &top); err != nil {
		return nil, err
	}

	d := newData()
	d.Projects = nil
	if v, ok := top["projects"]; ok {
		_ = json.Unmarshal(v, &d.Projects)
	}
	if v, ok := top["project_targets"]; ok {
		_ = json.Unmarshal(v, &d.ProjectTargets)
	}
	if v, ok := top["task_targets"]; ok {
		_ = json.Unmarshal(v, &d.TaskTargets)
	}
	if v, ok := top["tasks"]; ok {
		parseTasks(v, d)
	}

	// 其余键均为日期 -> 项目 -> 数量
	for key, v := range top {
		if isReservedKey(key) {
			continue
		}
		var day map[string]int
		if err := json.Unmarshal(v, &day); err == nil {
			d.Days[key] = day
		}
	}

	if d.Projects == nil {
		d.Projects = []string{"默认项目"}
	}
	hasDefault := false
	for _, p := range d.Projects {
		if p == "默认项目" {
			hasDefault = true
			break
		}
	}
	if !hasDefault {
		d.Projects = append([]string{"默认项目"}, d.Projects...)
	}
	return d, nil
}

func isReservedKey(key string) bool {
	switch key {
	case "projects", "project_targets", "task_targets", "tasks":
		return true
	}
	return false
}

// parseTasks 解析任务数据，同时兼容旧的扁平格式（任务 -> 数量）。
func parseTasks(raw json.RawMessage, d *Data) {
	var byDate map[string]json.RawMessage
	if err := json.Unmarshal(raw, &byDate); err != nil {
		return
	}
	for date, dayRaw := range byDate {
		var entries map[string]json.RawMessage
		if err := json.Unmarshal(dayRaw, &entries); err != nil {
			continue
		}
		day := map[string]map[string]int{}
		for key, valRaw := range entries {
			// 新格式：项目 -> {任务: 数量}
			var sub map[string]int
			if err := json.Unmarshal(valRaw, &sub); err == nil {
				day[key] = sub
				continue
			}
			// 旧格式：任务 -> 数量，归入当天唯一项目或"未分类"
			var count int
			if err := json.Unmarshal(valRaw, &count); err == nil {
				proj := "未分类"
				if projects := d.Days[date]; len(projects) == 1 {
					for p := range projects {
						proj = p
					}
				}
				if day[proj] == nil {
					day[proj] = map[string]int{}
				}
				day[proj][key] = count
			}
		}
		if len(day) > 0 {
			d.Tasks[date] = day
		}
	}
}

// Save 把数据整体写回磁盘（先写临时文件再改名，避免中断损坏）。
func (s *Store) Save(d *Data) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.saveLocked(d)
}

func (s *Store) saveLocked(d *Data) error {
	obj := map[string]interface{}{
		"projects":        d.Projects,
		"project_targets": d.ProjectTargets,
		"task_targets":    d.TaskTargets,
	}
	for date, projects := range d.Days {
		if _, clash := obj[date]; !clash {
			obj[date] = projects
		}
	}
	if len(d.Tasks) > 0 {
		obj["tasks"] = d.Tasks
	}

	body, err := json.MarshalIndent(obj, "", "  ")
	if err != nil {
		return err
	}
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, body, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, s.path)
}

// Marshal 返回用于上传云端的 JSON 字节。
func (s *Store) Marshal(d *Data) ([]byte, error) {
	obj := map[string]interface{}{
		"projects":        d.Projects,
		"project_targets": d.ProjectTargets,
		"task_targets":    d.TaskTargets,
	}
	for date, projects := range d.Days {
		if _, clash := obj[date]; !clash {
			obj[date] = projects
		}
	}
	if len(d.Tasks) > 0 {
		obj["tasks"] = d.Tasks
	}
	return json.MarshalIndent(obj, "", "  ")
}

// Unmarshal 解析来自云端的 JSON 字节。
func (s *Store) Unmarshal(body []byte) (*Data, error) {
	var top map[string]json.RawMessage
	if err := json.Unmarshal(body, &top); err != nil {
		return nil, err
	}
	d := newData()
	d.Projects = nil
	if v, ok := top["projects"]; ok {
		_ = json.Unmarshal(v, &d.Projects)
	}
	if v, ok := top["project_targets"]; ok {
		_ = json.Unmarshal(v, &d.ProjectTargets)
	}
	if v, ok := top["task_targets"]; ok {
		_ = json.Unmarshal(v, &d.TaskTargets)
	}
	if v, ok := top["tasks"]; ok {
		parseTasks(v, d)
	}
	for key, v := range top {
		if isReservedKey(key) {
			continue
		}
		var day map[string]int
		if err := json.Unmarshal(v, &day); err == nil {
			d.Days[key] = day
		}
	}
	if d.Projects == nil {
		d.Projects = []string{"默认项目"}
	}
	return d, nil
}

// ---- 业务辅助方法 ----

// Today 返回本地日期字符串。
func Today() string { return time.Now().Format("2006-01-02") }

// DayProjectCount 返回某天的项目番茄数映射。
func (d *Data) DayProjectCount(date string) map[string]int {
	if d.Days[date] == nil {
		return map[string]int{}
	}
	return d.Days[date]
}

// TodayTotal 返回今日番茄总数。
func (d *Data) TodayTotal() int {
	total := 0
	for _, c := range d.Days[Today()] {
		total += c
	}
	return total
}

// DayTaskCounts 返回某天的任务明细 [(项目, 任务, 数量), ...]。
func (d *Data) DayTaskCounts(date string) [][3]interface{} {
	result := [][3]interface{}{}
	day := d.Tasks[date]
	for project, tasks := range day {
		for task, count := range tasks {
			result = append(result, [3]interface{}{project, task, count})
		}
	}
	return result
}

// AddPomodoro 记录一次番茄，返回是否成功。
func (d *Data) AddPomodoro(project, task string) {
	today := Today()
	if d.Days[today] == nil {
		d.Days[today] = map[string]int{}
	}
	d.Days[today][project]++

	if d.Tasks[today] == nil {
		d.Tasks[today] = map[string]map[string]int{}
	}
	if d.Tasks[today][project] == nil {
		d.Tasks[today][project] = map[string]int{}
	}
	d.Tasks[today][project][task]++
}

// ClearToday 清空今日的项目与任务记录。
func (d *Data) ClearToday() {
	today := Today()
	delete(d.Days, today)
	delete(d.Tasks, today)
}

// WeekDates 返回本周（周一起）7 天的日期字符串。
func WeekDates() []string {
	now := time.Now()
	offset := (int(now.Weekday()) + 6) % 7 // 周一为 0
	start := now.AddDate(0, 0, -offset)
	dates := make([]string, 0, 7)
	for i := 0; i < 7; i++ {
		dates = append(dates, start.AddDate(0, 0, i).Format("2006-01-02"))
	}
	return dates
}

// WeekdayName 返回中文星期名。
func WeekdayName(dateStr string) string {
	t, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return ""
	}
	names := []string{"周日", "周一", "周二", "周三", "周四", "周五", "周六"}
	return names[int(t.Weekday())]
}

// Progress 根据数量与目标生成进度文案。
func Progress(count, target int) string {
	if target <= 0 {
		return "未设置目标"
	}
	if count >= target {
		return fmt.Sprintf("已完成 (%d/%d)", count, target)
	}
	return fmt.Sprintf("%.1f%% (%d/%d)", float64(count)/float64(target)*100, count, target)
}
