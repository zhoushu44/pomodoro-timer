import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
import json
import os
from datetime import datetime, timedelta

class PomodoroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("番茄钟")
        self.root.geometry("500x365")  # 改为500x365，裁剪底部空白
        self.root.resizable(False, False)
        
        self.work_time = 25 * 60  # 25分钟
        self.short_break = 5 * 60  # 5分钟
        self.long_break = 15 * 60  # 15分钟
        
        self.current_time = self.work_time
        self.is_running = False
        self.is_break = False
        self.pomodoro_count = 0
        
        self.current_project = "默认项目"
        self.projects = ["默认项目"]
        
        self.data_file = "pomodoro_data.json"
        self.load_data()
        
        self.is_float_mode = False
        self.create_widgets()
        self.update_clock()
    
    def create_widgets(self):
        # 设计规范颜色定义
        self.colors = {
            "primary": "#FF5A36",      # 番茄红（主色）
            "progress_active": "#FF8A65",  # 进度环激活色
            "progress_bg": "#EFEFEF",   # 进度环底色
            "bg": "#FFFFFF",            # 背景色
            "text_primary": "#333333",  # 文字主色
            "text_secondary": "#666666", # 文字辅助色
            "btn_disabled": "#F5F5F5",  # 按钮禁用色
            "leaf_green": "#4CAF50",    # 绿叶色
            "border": "#E0E0E0"         # 边框色
        }
        
        # 设置窗口背景色
        self.root.configure(bg=self.colors["bg"])
        
        # 主容器 - 使用网格布局更紧凑
        self.main_container = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)  # 减少上下内边距
        
        # 第1行：时间显示（移除圆环）
        self.timer_frame = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.timer_frame.grid(row=0, column=0, columnspan=2, pady=(5, 10))  # 减少上下间距
        
        # 时间显示（居中显示）
        self.time_label = tk.Label(
            self.timer_frame, 
            text=self.format_time(self.current_time), 
            font=("微软雅黑", 48, "bold"),  # 放大字体，更突出
            bg=self.colors["bg"], 
            fg=self.colors["text_primary"]
        )
        self.time_label.pack()
        
        # 第2行：项目选择
        self.project_frame = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.project_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        
        self.project_label = tk.Label(
            self.project_frame, 
            text="项目:", 
            font=("微软雅黑", 11),  # 缩小字体
            bg=self.colors["bg"], 
            fg=self.colors["text_secondary"]
        )
        self.project_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.project_var = tk.StringVar(value=self.current_project)
        
        # 配置Combobox样式
        style = ttk.Style()
        style.configure("TCombobox", font=("微软雅黑", 10))
        
        self.project_combobox = ttk.Combobox(
            self.project_frame, 
            textvariable=self.project_var, 
            values=self.projects, 
            width=12,
            font=("微软雅黑", 10)
        )
        self.project_combobox.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        self.project_var.trace_add("write", self.on_project_change)
        
        # 次要按钮样式（添加/删除项目）- 圆角按钮
        secondary_btn_style = {
            "font": ("微软雅黑", 9),
            "relief": tk.FLAT,
            "bd": 0,
            "padx": 10,
            "pady": 4,
            "bg": self.colors["bg"],
            "fg": self.colors["text_secondary"],
            "activebackground": "#F8F8F8",
            "activeforeground": self.colors["text_primary"],
            "cursor": "hand2",
            "borderwidth": 0,
            "highlightthickness": 0
        }
        
        self.add_project_btn = tk.Button(
            self.project_frame, 
            text="添加", 
            command=self.add_project, 
            **secondary_btn_style
        )
        self.add_project_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_project_btn = tk.Button(
            self.project_frame, 
            text="删除", 
            command=self.delete_project, 
            **secondary_btn_style
        )
        self.delete_project_btn.pack(side=tk.LEFT)
        
        # 第3行：控制按钮（一行排列）
        self.control_frame = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        
        # 控制按钮样式 - 背景 #333333 / 文字 #FFFFFF / 圆角 24px / 高度 35px，宽度80px
        control_btn_style = {
            "font": ("微软雅黑", 11, "bold"),  # 稍微缩小字体以适应35px高度
            "relief": tk.FLAT,
            "bd": 0,
            "width": 8,  # 宽度80px（每个字符约10px）
            "height": 1,  # 高度35px（1行，通过pady调整）
            "bg": "#333333",
            "fg": "#FFFFFF",
            "activebackground": "#555555",
            "activeforeground": "#FFFFFF",
            "cursor": "hand2",
            "borderwidth": 0,
            "highlightthickness": 0,
            "pady": 8  # 增加垂直内边距以达到35px高度
        }
        
        # 开始按钮
        self.start_btn = tk.Button(
            self.control_frame, 
            text="开始", 
            command=self.start_pomodoro, 
            **control_btn_style
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        
        # 暂停按钮
        self.pause_btn = tk.Button(
            self.control_frame, 
            text="暂停", 
            command=self.pause_pomodoro, 
            **control_btn_style
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        
        # 重置按钮
        self.reset_btn = tk.Button(
            self.control_frame, 
            text="重置", 
            command=self.reset_pomodoro, 
            **control_btn_style
        )
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 8), expand=True, fill=tk.X)
        
        # 完成按钮
        self.complete_btn = tk.Button(
            self.control_frame, 
            text="完成", 
            command=self.complete_pomodoro, 
            **control_btn_style
        )
        self.complete_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 第4行：悬浮模式切换按钮
        self.float_frame = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.float_frame.grid(row=3, column=0, columnspan=2, pady=(5, 10), sticky="ew")
        
        self.float_mode_btn = tk.Button(
            self.float_frame, 
            text="切换到悬浮模式", 
            command=self.toggle_float_mode, 
            font=("微软雅黑", 11),
            relief=tk.FLAT,
            padx=20,
            pady=6,
            bg=self.colors["primary"],
            fg="#FFFFFF",
            activebackground=self.colors["progress_active"],
            activeforeground="#FFFFFF",
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        self.float_mode_btn.pack(fill=tk.X)
        
        # 第5行：今日番茄数
        self.today_count = self.get_today_pomodoro_count()
        self.today_label = tk.Label(
            self.main_container, 
            text=f"今日番茄数: {'🍅' * self.today_count if self.today_count > 0 else '暂无'}", 
            font=("微软雅黑", 11), 
            bg=self.colors["bg"], 
            fg=self.colors["text_secondary"]
        )
        self.today_label.grid(row=4, column=0, columnspan=2, pady=(0, 10))
        
        # 第6行：统计按钮
        self.stats_frame = tk.Frame(self.main_container, bg=self.colors["bg"])
        self.stats_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        
        stats_btn_style = {
            "font": ("微软雅黑", 10),
            "relief": tk.FLAT,
            "bd": 0,
            "padx": 12,
            "pady": 6,
            "bg": self.colors["bg"],
            "fg": self.colors["text_secondary"],
            "activebackground": "#F8F8F8",
            "activeforeground": self.colors["text_primary"],
            "cursor": "hand2",
            "borderwidth": 0,
            "highlightthickness": 0
        }
        
        self.weekly_day_btn = tk.Button(
            self.stats_frame, 
            text="按周查看每天番茄数", 
            command=self.show_weekly_day_stats, 
            **stats_btn_style
        )
        self.weekly_day_btn.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        self.weekly_project_btn = tk.Button(
            self.stats_frame, 
            text="按周查看项目番茄数", 
            command=self.show_weekly_project_stats, 
            **stats_btn_style
        )
        self.weekly_project_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 配置网格权重
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)
        
        # 为所有按钮添加圆角效果（通过创建圆角矩形背景）
        self.add_rounded_corners()
    
    def add_rounded_corners(self):
        # 为所有按钮添加圆角效果
        buttons = [
            self.start_btn, self.pause_btn, self.reset_btn, self.complete_btn,
            self.float_mode_btn, self.weekly_day_btn, self.weekly_project_btn,
            self.add_project_btn, self.delete_project_btn
        ]
        
        for btn in buttons:
            btn.config(borderwidth=0, highlightthickness=0)
            # 创建圆角效果
            btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover(e, b))
            btn.bind("<Leave>", lambda e, b=btn: self.on_button_leave(e, b))
    
    def on_button_hover(self, event, button):
        # 鼠标悬停效果
        if button in [self.start_btn, self.pause_btn, self.reset_btn, self.complete_btn]:
            # 控制按钮悬停效果：背景加深
            button.config(bg="#555555")
        elif button == self.float_mode_btn:
            # 悬浮模式按钮悬停效果
            button.config(bg=self.colors["progress_active"])
        else:
            # 其他按钮悬停效果
            button.config(bg="#F8F8F8")
    
    def on_button_leave(self, event, button):
        # 鼠标离开效果
        if button in [self.start_btn, self.pause_btn, self.reset_btn, self.complete_btn]:
            # 控制按钮恢复原样
            button.config(bg="#333333")
        elif button == self.float_mode_btn:
            # 悬浮模式按钮恢复原样
            button.config(bg=self.colors["primary"])
        else:
            # 其他按钮恢复原样
            button.config(bg=self.colors["bg"])
    
    def toggle_float_mode(self):
        # 切换悬浮模式
        if not self.is_float_mode:
            # 切换到悬浮模式
            self.is_float_mode = True
            self.root.withdraw()  # 隐藏主窗口
            
            # 创建悬浮窗口
            self.float_window = tk.Toplevel()
            self.float_window.overrideredirect(True)  # 隐藏标题栏
            
            # 计算悬浮窗口位置：离桌面底部10%和离右边10%的距离
            screen_width = self.float_window.winfo_screenwidth()
            screen_height = self.float_window.winfo_screenheight()
            window_width = 200
            window_height = 75
            x_position = int(screen_width * 0.9 - window_width)  # 离右边10%
            y_position = int(screen_height * 0.9 - window_height)  # 离底部10%
            
            self.float_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
            self.float_window.resizable(False, False)
            self.float_window.attributes("-topmost", True)  # 始终置顶
            self.float_window.attributes("-alpha", 0.9)  # 半透明
            self.float_window.configure(bg="#333333")
            
            # 添加窗口拖动功能
            self.float_window.bind("<Button-1>", self.start_drag)
            self.float_window.bind("<B1-Motion>", self.drag_window)
            
            # 添加右键菜单
            self.right_click_menu = tk.Menu(self.float_window, tearoff=0, bg="#333333", fg="#FFFFFF")
            self.right_click_menu.add_command(label="开始", command=self.start_from_menu)
            self.right_click_menu.add_command(label="暂停", command=self.pause_from_menu)
            self.right_click_menu.add_command(label="重置", command=self.reset_pomodoro)
            self.right_click_menu.add_command(label="完成", command=self.complete_pomodoro)
            self.right_click_menu.add_command(label="今日清零", command=self.clear_today_data)
            self.right_click_menu.add_command(label="主菜单窗口", command=self.show_main_window)
            self.right_click_menu.add_separator()
            self.right_click_menu.add_command(label="关闭", command=self.float_window.destroy)
            
            # 绑定右键菜单
            self.float_window.bind("<Button-3>", self.show_right_click_menu)
            
            # 时间显示区
            self.float_time_frame = tk.Frame(self.float_window, bg="#333333")
            self.float_time_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
            
            # 进度条背景
            self.progress_frame = tk.Frame(self.float_time_frame, bg="#333333")
            self.progress_frame.place(x=0, y=0, relwidth=1, relheight=1)
            self.progress_bar = tk.Frame(self.progress_frame, bg="#0088FF")
            self.progress_bar.place(x=0, y=0, width=0, relheight=1)
            
            # 数字钟风格的时间显示
            self.float_time_label = tk.Label(self.float_time_frame, text=self.format_time(self.current_time), font=("Consolas", 36, "bold"), bg="#333333", fg="#FFFFFF")
            self.float_time_label.pack(fill=tk.BOTH, expand=True)
            
            # 初始状态
            self.update_float_state()
    
    def show_right_click_menu(self, event):
        # 显示右键菜单
        self.right_click_menu.post(event.x_root, event.y_root)
    
    def start_from_menu(self):
        # 从菜单开始计时
        if not self.is_running:
            self.start_pomodoro()
    
    def pause_from_menu(self):
        # 从菜单暂停计时
        if self.is_running:
            self.pause_pomodoro()
    
    def start_drag(self, event):
        # 开始拖动窗口
        self.float_window.x = event.x
        self.float_window.y = event.y
    
    def drag_window(self, event):
        # 拖动窗口
        x = self.float_window.winfo_x() - self.float_window.x + event.x
        y = self.float_window.winfo_y() - self.float_window.y + event.y
        self.float_window.geometry(f"200x75+{x}+{y}")
    
    def update_float_state(self):
        # 更新悬浮窗状态
        if self.is_running:
            # 状态1：计时中
            self.update_progress()
        else:
            # 状态2：计时就绪/已暂停
            if hasattr(self, 'progress_bar'):
                self.progress_bar.config(width=0)
    
    def update_progress(self):
        # 更新进度条
        if self.is_running and hasattr(self, 'progress_bar') and hasattr(self, 'float_time_frame'):
            progress = (self.work_time - self.current_time) / self.work_time
            width = int(self.float_time_frame.winfo_width() * progress)
            self.progress_bar.config(width=width)
    
    def show_main_window(self):
        # 切换回主窗口
        self.is_float_mode = False
        self.float_window.destroy()  # 销毁悬浮窗口
        # 确保主窗口的项目选择与当前项目一致
        self.project_var.set(self.current_project)
        self.project_combobox.config(values=self.projects)
        self.root.deiconify()  # 显示主窗口
    
    def format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"
    
    def start_pomodoro(self):
        if not self.is_running:
            self.is_running = True
            self.start_time = time.time() - (self.work_time - self.current_time)
            self.update_clock()
    
    def pause_pomodoro(self):
        if self.is_running:
            self.is_running = False
    
    def reset_pomodoro(self):
        self.is_running = False
        self.is_break = False
        self.current_time = self.work_time
        self.time_label.config(text=self.format_time(self.current_time))
        
        # 如果是悬浮模式，更新悬浮窗的显示
        if self.is_float_mode:
            if hasattr(self, 'float_time_label'):
                self.float_time_label.config(text=self.format_time(self.current_time))
            if hasattr(self, 'progress_bar'):
                self.progress_bar.config(width=0)
    
    def complete_pomodoro(self):
        # 手动完成番茄钟
        if self.is_running:
            self.is_running = False
            self.pomodoro_count += 1
            self.save_pomodoro()
            self.today_count = self.get_today_pomodoro_count()
            self.today_label.config(text=f"今日番茄数: {'🍅' * self.today_count}")
            # 显示自动消失的完成提示
            self.show_auto_close_message("番茄钟完成！")
            self.reset_pomodoro()
    
    def update_clock(self):
        if self.is_running:
            elapsed = time.time() - self.start_time
            self.current_time = max(0, self.work_time - int(elapsed))
            self.time_label.config(text=self.format_time(self.current_time))
            
            # 如果是悬浮模式，更新悬浮窗的显示
            if self.is_float_mode:
                if hasattr(self, 'float_time_label'):
                    self.float_time_label.config(text=self.format_time(self.current_time))
                if hasattr(self, 'update_progress'):
                    self.update_progress()
            
            if self.current_time == 0:
                self.is_running = False
                self.pomodoro_count += 1
                self.save_pomodoro()
                self.today_count = self.get_today_pomodoro_count()
                self.today_label.config(text=f"今日番茄数: {'🍅' * self.today_count}")
                # 显示自动消失的完成提示
                self.show_auto_close_message("番茄钟完成！")
                self.reset_pomodoro()
        
        self.root.after(1000, self.update_clock)
    
    def show_auto_close_message(self, message):
        # 创建自动消失的提示窗口
        popup = tk.Toplevel(self.root)
        popup.title("提示")
        popup.geometry("300x100")
        popup.resizable(False, False)
        popup.configure(bg="#333333")
        
        # 使窗口居中
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")
        
        # 提示内容
        label = tk.Label(
            popup, 
            text=message, 
            font=("微软雅黑", 14, "bold"), 
            bg="#333333", 
            fg="#FFFFFF",
            wraplength=280
        )
        label.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        # 1秒后自动关闭窗口
        popup.after(1000, popup.destroy)
    
    def on_project_change(self, *args):
        # 当项目选择变化时，更新current_project变量
        self.current_project = self.project_var.get()
    
    def add_project(self):
        project_name = tk.simpledialog.askstring("添加项目", "请输入项目名称:")
        if project_name and project_name not in self.projects:
            self.projects.append(project_name)
            self.project_combobox.config(values=self.projects)
            self.save_projects()
    
    def delete_project(self):
        # 删除当前选中的项目
        selected_project = self.project_var.get()
        if selected_project == "默认项目":
            messagebox.showinfo("提示", "默认项目不能删除！")
            return
        
        if selected_project in self.projects:
            # 确认删除
            if messagebox.askyesno("确认", f"确定要删除项目 '{selected_project}' 吗？"):
                self.projects.remove(selected_project)
                self.project_combobox.config(values=self.projects)
                # 如果删除的是当前项目，切换到默认项目
                if selected_project == self.current_project:
                    self.current_project = "默认项目"
                    self.project_var.set("默认项目")
                self.save_projects()
                messagebox.showinfo("提示", f"项目 '{selected_project}' 已删除！")
    
    def save_pomodoro(self):
        data = self.load_json()
        today = datetime.now().strftime("%Y-%m-%d")
        project = self.project_var.get()
        
        if today not in data:
            data[today] = {}
        
        if project not in data[today]:
            data[today][project] = 0
        
        data[today][project] += 1
        
        self.save_json(data)
    
    def get_today_pomodoro_count(self):
        data = self.load_json()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today in data:
            return sum(data[today].values())
        return 0
    
    def show_weekly_day_stats(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("每周每天番茄数统计")
        stats_window.geometry("600x400")
        
        # 获取本周日期
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        # 创建表格
        tree = ttk.Treeview(stats_window, columns=["date", "count"], show="headings")
        tree.heading("date", text="日期")
        tree.heading("count", text="番茄数")
        tree.pack(fill=tk.BOTH, expand=True, pady=20)
        
        data = self.load_json()
        
        for i in range(7):
            date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            count = sum(data.get(date, {}).values()) if date in data else 0
            tree.insert("", tk.END, values=[date, count])
    
    def show_weekly_project_stats(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("每周项目番茄数统计")
        stats_window.geometry("700x500")  # 增加窗口尺寸以容纳目标列
        
        # 获取本周日期
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        
        # 创建表格 - 添加目标列
        tree = ttk.Treeview(stats_window, columns=["project", "count", "target", "progress"], show="headings")
        tree.heading("project", text="项目")
        tree.heading("count", text="番茄数")
        tree.heading("target", text="目标")
        tree.heading("progress", text="进度")
        
        # 设置列宽
        tree.column("project", width=150)
        tree.column("count", width=100)
        tree.column("target", width=100)
        tree.column("progress", width=150)
        
        tree.pack(fill=tk.BOTH, expand=True, pady=20, padx=20)
        
        # 添加目标输入功能
        target_data = self.load_target_data()
        
        data = self.load_json()
        project_counts = {}
        
        for i in range(7):
            date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            if date in data:
                for project, count in data[date].items():
                    if project not in project_counts:
                        project_counts[project] = 0
                    project_counts[project] += count
        
        # 插入数据到表格
        for project, count in project_counts.items():
            target = target_data.get(project, 0)
            progress = self.calculate_progress(count, target)
            tree.insert("", tk.END, values=[project, count, target, progress])
        
        # 添加目标设置按钮
        button_frame = tk.Frame(stats_window)
        button_frame.pack(pady=10)
        
        set_target_btn = tk.Button(
            button_frame,
            text="设置目标",
            command=lambda: self.set_project_target(tree, target_data),
            font=("微软雅黑", 11),
            bg="#333333",
            fg="#FFFFFF",
            padx=20,
            pady=5
        )
        set_target_btn.pack(side=tk.LEFT, padx=10)
        
        refresh_btn = tk.Button(
            button_frame,
            text="刷新",
            command=lambda: self.refresh_project_stats(tree, stats_window),
            font=("微软雅黑", 11),
            bg="#333333",
            fg="#FFFFFF",
            padx=20,
            pady=5
        )
        refresh_btn.pack(side=tk.LEFT, padx=10)
    
    def load_target_data(self):
        # 加载项目目标数据
        data = self.load_json()
        if "project_targets" in data:
            return data["project_targets"]
        return {}
    
    def save_target_data(self, target_data):
        # 保存项目目标数据
        data = self.load_json()
        data["project_targets"] = target_data
        self.save_json(data)
    
    def calculate_progress(self, count, target):
        # 计算进度
        if target == 0:
            return "未设置目标"
        elif count >= target:
            return f"已完成 ({count}/{target})"
        else:
            percentage = (count / target) * 100
            return f"{percentage:.1f}% ({count}/{target})"
    
    def set_project_target(self, tree, target_data):
        # 设置项目目标
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showinfo("提示", "请先选择一个项目")
            return
        
        item = selected_item[0]
        values = tree.item(item, "values")
        project = values[0]
        
        # 弹出输入对话框
        target_str = tk.simpledialog.askstring("设置目标", f"为项目 '{project}' 设置目标番茄数:", initialvalue=str(target_data.get(project, 0)))
        
        if target_str is not None:
            try:
                target = int(target_str)
                if target < 0:
                    messagebox.showwarning("警告", "目标值不能为负数")
                    return
                
                # 更新目标数据
                target_data[project] = target
                self.save_target_data(target_data)
                
                # 更新表格显示
                count = int(values[1])
                progress = self.calculate_progress(count, target)
                tree.item(item, values=(project, count, target, progress))
                
                # 取消成功弹窗，静默更新
            except ValueError:
                messagebox.showwarning("警告", "请输入有效的数字")
    
    def clear_today_data(self):
        # 今日数据清零
        today = datetime.now().strftime("%Y-%m-%d")
        data = self.load_json()
        
        if today in data:
            # 确认清零
            if messagebox.askyesno("确认", "确定要清零今日的番茄数吗？\n此操作不可撤销。"):
                # 删除今日数据
                del data[today]
                self.save_json(data)
                
                # 更新主窗口显示
                self.today_count = 0
                self.today_label.config(text="今日番茄数: 暂无")
                
                # 显示自动消失的提示
                self.show_auto_close_message("今日数据已清零")
                
                # 如果统计窗口打开，需要刷新
                self.refresh_open_stats_windows()
    
    def refresh_open_stats_windows(self):
        # 刷新已打开的统计窗口
        # 这里可以添加刷新逻辑，但通常用户会手动刷新
        pass
    
    def refresh_project_stats(self, tree, window):
        # 刷新项目统计
        window.destroy()
        self.show_weekly_project_stats()
    
    def load_json(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def save_json(self, data):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_data(self):
        data = self.load_json()
        if "projects" in data:
            self.projects = data["projects"]
    
    def save_projects(self):
        data = self.load_json()
        data["projects"] = self.projects
        self.save_json(data)

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()