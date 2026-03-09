import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import time
import json
import os
from datetime import datetime, timedelta
import pymysql
import threading

class PomodoroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("番茄钟")
        self.root.geometry("500x365")  # 改为500x365，裁剪底部空白
        self.root.resizable(False, False)
        
        # 设置窗口图标（同时设置任务栏和标题栏图标）
        if os.path.exists("icon.ico"):
            try:
                self.root.iconbitmap("icon.ico")  # 任务栏图标
            except:
                pass
        if os.path.exists("番茄.png"):
            try:
                from PIL import Image, ImageTk
                icon = Image.open("番茄.png")
                icon = ImageTk.PhotoImage(icon)
                self.root.iconphoto(False, icon)  # 标题栏图标
            except:
                pass
        
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
        
        # 云端同步设置（在load_data之前定义）
        self.cloud_enabled = True
        self.mysql_config = {
            'host': '8.163.52.51',
            'port': 13306,
            'user': 'root',
            'password': 'LFajEj6Lw7tKfZ8z',
            'database': 'pomodoro'
        }
        self.db_connection = None
        self.last_sync_time = None
        
        self.load_data()
        
        self.is_float_mode = False
        
        self.create_widgets()
        self.update_clock()
        self.start_cloud_sync()
    
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
        self.main_container =   tk.Frame(self.root, bg=self.colors["bg"])
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
        
        # 云端按钮（右上角）
        self.cloud_btn = tk.Button(
            self.main_container, 
            text="云端", 
            command=self.show_cloud_settings, 
            font=("微软雅黑", 11),
            relief=tk.FLAT,
            padx=15,
            pady=6,
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"],
            activebackground="#F8F8F8",
            activeforeground=self.colors["text_primary"],
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        self.cloud_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        
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
            self.add_project_btn, self.delete_project_btn, self.cloud_btn
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
        self.is_running = False
        self.pomodoro_count += 1
        try:
            self.save_pomodoro()
        except Exception as e:
            print(f"保存番茄钟失败: {str(e)}")
        try:
            self.today_count = self.get_today_pomodoro_count()
            self.today_label.config(text=f"今日番茄数: {'🍅' * self.today_count if self.today_count > 0 else '暂无'}")
        except Exception as e:
            print(f"获取今日番茄数失败: {str(e)}")
        # 重置计时为25:00
        self.current_time = self.work_time
        self.time_label.config(text=self.format_time(self.current_time))
        # 如果是悬浮模式，更新悬浮窗的显示
        if self.is_float_mode:
            if hasattr(self, 'float_time_label'):
                self.float_time_label.config(text=self.format_time(self.current_time))
            if hasattr(self, 'progress_bar'):
                self.progress_bar.config(width=0)
        # 显示自动消失的完成提示
        self.show_auto_close_message("番茄钟完成！")
    
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
            # 云端同步项目
            if self.cloud_enabled:
                try:
                    self.sync_project_to_cloud()
                except Exception as e:
                    print(f"同步项目到云端失败: {str(e)}")
            # 更新下拉框显示
            self.project_combobox.config(values=self.projects)
    
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
                # 云端同步项目
                if self.cloud_enabled:
                    try:
                        # 从projects表中删除项目
                        connection = self.get_db_connection()
                        cursor = connection.cursor()
                        delete_sql = "DELETE FROM projects WHERE name = %s"
                        cursor.execute(delete_sql, (selected_project,))
                        connection.commit()
                        cursor.close()
                        print(f"项目 '{selected_project}' 已从云端删除")
                    except Exception as e:
                        print(f"从云端删除项目失败: {str(e)}")
                # 更新下拉框显示
                self.project_combobox.config(values=self.projects)
            messagebox.showinfo("提示", f"项目 '{selected_project}' 已删除！")
    
    def save_pomodoro(self):
        if self.cloud_enabled:
            today = datetime.now().strftime("%Y-%m-%d")
            project = self.project_var.get()
            self.save_pomodoro_cloud(today, project)
        else:
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
        if self.cloud_enabled:
            return self.get_today_pomodoro_count_cloud()
        else:
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
        
        # 星期几名称
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        # 创建表格
        tree = ttk.Treeview(stats_window, columns=["date", "count"], show="headings")
        tree.heading("date", text="日期")
        tree.heading("count", text="番茄数")
        tree.pack(fill=tk.BOTH, expand=True, pady=20)
        
        if self.cloud_enabled:
            # 从云端获取数据
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            for i in range(7):
                date_obj = week_start + timedelta(days=i)
                date_str = date_obj.strftime("%Y-%m-%d")
                weekday_name = weekdays[i]
                display_date = f"{date_str} ({weekday_name})"
                sql = "SELECT SUM(count) FROM pomodoro_data WHERE date = %s"
                cursor.execute(sql, (date_str,))
                result = cursor.fetchone()
                count = result[0] if result[0] else 0
                tree.insert("", tk.END, values=[display_date, count])
            
            cursor.close()
        else:
            # 从本地JSON获取数据
            data = self.load_json()
            
            for i in range(7):
                date_obj = week_start + timedelta(days=i)
                date_str = date_obj.strftime("%Y-%m-%d")
                weekday_name = weekdays[i]
                display_date = f"{date_str} ({weekday_name})"
                count = sum(data.get(date_str, {}).values()) if date_str in data else 0
                tree.insert("", tk.END, values=[display_date, count])
    
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
        
        project_counts = {}
        
        if self.cloud_enabled:
            # 从云端获取数据
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            for i in range(7):
                date = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
                sql = "SELECT project, SUM(count) FROM pomodoro_data WHERE date = %s GROUP BY project"
                cursor.execute(sql, (date,))
                results = cursor.fetchall()
                
                for project, count in results:
                    if project not in project_counts:
                        project_counts[project] = 0
                    project_counts[project] += count
            
            cursor.close()
        else:
            # 从本地JSON获取数据
            data = self.load_json()
            
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
        
        if self.cloud_enabled:
            # 从云端清零
            try:
                connection = self.get_db_connection()
                cursor = connection.cursor()
                
                # 确认清零
                if messagebox.askyesno("确认", "确定要清零今日的番茄数吗？\n此操作不可撤销。"):
                    # 删除今日数据
                    delete_sql = "DELETE FROM pomodoro_data WHERE date = %s"
                    cursor.execute(delete_sql, (today,))
                    connection.commit()
                    cursor.close()
                    
                    # 更新主窗口显示
                    self.today_count = 0
                    self.today_label.config(text="今日番茄数: 暂无")
                    
                    # 显示自动消失的提示
                    self.show_auto_close_message("今日数据已清零")
                    
                    # 如果统计窗口打开，需要刷新
                    self.refresh_open_stats_windows()
            except Exception as e:
                messagebox.showerror("错误", f"清零今日数据失败：\n{str(e)}")
        else:
            # 从本地JSON清零
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
    
    def sync_projects_from_cloud(self):
        # 从云端同步项目列表到本地
        if not self.cloud_enabled:
            return
        
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            # 从 projects 表查询项目列表
            sql = "SELECT name FROM projects ORDER BY name"
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # 提取项目列表
            cloud_projects = [row[0] for row in results]
            
            # 确保包含"默认项目"
            if "默认项目" not in cloud_projects:
                cloud_projects.insert(0, "默认项目")
            
            # 检查项目列表是否有变化
            if cloud_projects != self.projects:
                self.projects = cloud_projects
                # 更新下拉框（如果已创建）
                if hasattr(self, 'project_combobox'):
                    self.project_combobox.config(values=self.projects)
                    # 确保当前项目仍在列表中
                    if hasattr(self, 'project_var') and self.current_project not in self.projects:
                        self.current_project = "默认项目"
                        self.project_var.set("默认项目")
            
            cursor.close()
            print(f"已从云端同步项目列表: {self.projects}")
        except Exception as e:
            print(f"从云端同步项目列表失败: {str(e)}")
    
    def load_data(self):
        if self.cloud_enabled:
            # 从云端读取项目列表
            self.sync_projects_from_cloud()
        else:
            # 从本地JSON读取项目列表
            data = self.load_json()
            if "projects" in data:
                self.projects = data["projects"]
    
    def save_projects(self):
        if self.cloud_enabled:
            # 保存项目列表到云端（不直接保存，通过数据同步实现）
            # 云端的项目列表通过pomodoro_data表中的数据自动维护
            # 立即同步新项目到云端
            self.sync_project_to_cloud()
        else:
            # 保存项目列表到本地JSON
            data = self.load_json()
            data["projects"] = self.projects
            self.save_json(data)
    
    def sync_project_to_cloud(self):
        # 同步项目列表到云端（使用projects表）
        if not self.cloud_enabled:
            return
        
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            # 为每个项目在projects表中创建记录（如果不存在）
            for project in self.projects:
                # 检查项目是否存在
                check_sql = "SELECT COUNT(*) FROM projects WHERE name = %s"
                cursor.execute(check_sql, (project,))
                result = cursor.fetchone()
                
                # 如果项目不存在，创建记录
                if result[0] == 0:
                    insert_sql = "INSERT INTO projects (name) VALUES (%s)"
                    cursor.execute(insert_sql, (project,))
            
            connection.commit()
            cursor.close()
            print(f"项目列表已同步到云端: {self.projects}")
        except Exception as e:
            print(f"同步项目列表到云端失败: {str(e)}")
    
    def show_cloud_settings(self):
        cloud_window = tk.Toplevel(self.root)
        cloud_window.title("云端设置")
        cloud_window.geometry("500x400")
        cloud_window.resizable(False, False)
        cloud_window.configure(bg=self.colors["bg"])
        
        # 主容器
        container = tk.Frame(cloud_window, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            container, 
            text="MySQL 数据库设置", 
            font=("微软雅黑", 14, "bold"), 
            bg=self.colors["bg"], 
            fg=self.colors["text_primary"]
        )
        title_label.pack(pady=(0, 20))
        
        # MySQL 配置输入
        config_frame = tk.Frame(container, bg=self.colors["bg"])
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 主机地址
        tk.Label(config_frame, text="主机地址:", font=("微软雅黑", 10), bg=self.colors["bg"], fg=self.colors["text_secondary"]).grid(row=0, column=0, sticky="w", pady=5)
        host_entry = tk.Entry(config_frame, font=("微软雅黑", 10), width=30)
        host_entry.insert(0, self.mysql_config['host'])
        host_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # 端口
        tk.Label(config_frame, text="端口:", font=("微软雅黑", 10), bg=self.colors["bg"], fg=self.colors["text_secondary"]).grid(row=1, column=0, sticky="w", pady=5)
        port_entry = tk.Entry(config_frame, font=("微软雅黑", 10), width=30)
        port_entry.insert(0, str(self.mysql_config['port']))
        port_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # 用户名
        tk.Label(config_frame, text="用户名:", font=("微软雅黑", 10), bg=self.colors["bg"], fg=self.colors["text_secondary"]).grid(row=2, column=0, sticky="w", pady=5)
        user_entry = tk.Entry(config_frame, font=("微软雅黑", 10), width=30)
        user_entry.insert(0, self.mysql_config['user'])
        user_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # 密码
        tk.Label(config_frame, text="密码:", font=("微软雅黑", 10), bg=self.colors["bg"], fg=self.colors["text_secondary"]).grid(row=3, column=0, sticky="w", pady=5)
        password_entry = tk.Entry(config_frame, font=("微软雅黑", 10), width=30, show="*")
        password_entry.insert(0, self.mysql_config['password'])
        password_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
        
        # 数据库名
        tk.Label(config_frame, text="数据库名:", font=("微软雅黑", 10), bg=self.colors["bg"], fg=self.colors["text_secondary"]).grid(row=4, column=0, sticky="w", pady=5)
        db_entry = tk.Entry(config_frame, font=("微软雅黑", 10), width=30)
        db_entry.insert(0, self.mysql_config['database'])
        db_entry.grid(row=4, column=1, pady=5, padx=(10, 0))
        
        # 按钮框架
        button_frame = tk.Frame(container, bg=self.colors["bg"])
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 测试连接按钮
        test_btn = tk.Button(
            button_frame,
            text="测试连接",
            command=lambda: self.test_mysql_connection(
                host_entry.get(),
                port_entry.get(),
                user_entry.get(),
                password_entry.get(),
                db_entry.get()
            ),
            font=("微软雅黑", 11),
            bg="#333333",
            fg="#FFFFFF",
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        test_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 保存配置按钮
        save_btn = tk.Button(
            button_frame,
            text="保存配置",
            command=lambda: self.save_mysql_config(
                host_entry.get(),
                port_entry.get(),
                user_entry.get(),
                password_entry.get(),
                db_entry.get(),
                cloud_window
            ),
            font=("微软雅黑", 11),
            bg=self.colors["primary"],
            fg="#FFFFFF",
            padx=20,
            pady=8,
            relief=tk.FLAT,
            cursor="hand2"
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 云端同步开关
        sync_frame = tk.Frame(container, bg=self.colors["bg"])
        sync_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.cloud_var = tk.BooleanVar(value=self.cloud_enabled)
        cloud_check = tk.Checkbutton(
            sync_frame,
            text="启用云端同步",
            variable=self.cloud_var,
            font=("微软雅黑", 11),
            bg=self.colors["bg"],
            fg=self.colors["text_primary"],
            selectcolor=self.colors["bg"],
            activebackground=self.colors["bg"],
            activeforeground=self.colors["text_primary"],
            cursor="hand2",
            command=self.toggle_cloud_sync
        )
        cloud_check.pack(side=tk.LEFT)
        
        # 同步状态标签
        self.sync_status_label = tk.Label(
            sync_frame,
            text=f"状态: {'已启用' if self.cloud_enabled else '未启用'}",
            font=("微软雅黑", 10),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"]
        )
        self.sync_status_label.pack(side=tk.LEFT, padx=(20, 0))
    
    def test_mysql_connection(self, host, port, user, password, database):
        try:
            # 测试连接（不指定数据库）
            temp_config = {
                'host': host,
                'port': int(port),
                'user': user,
                'password': password
            }
            connection = pymysql.connect(**temp_config)
            connection.close()
            messagebox.showinfo("成功", "MySQL 连接测试成功！")
        except Exception as e:
            messagebox.showerror("错误", f"MySQL 连接测试失败：\n{str(e)}")
    
    def save_mysql_config(self, host, port, user, password, database, window):
        try:
            self.mysql_config = {
                'host': host,
                'port': int(port),
                'user': user,
                'password': password,
                'database': database
            }
            
            # 测试连接（不指定数据库）
            temp_config = {
                'host': host,
                'port': int(port),
                'user': user,
                'password': password
            }
            connection = pymysql.connect(**temp_config)
            connection.close()
            
            # 初始化数据库
            self.init_database()
            
            messagebox.showinfo("成功", "MySQL 配置保存成功！")
            window.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：\n{str(e)}")
    
    def toggle_cloud_sync(self):
        self.cloud_enabled = self.cloud_var.get()
        if hasattr(self, 'sync_status_label'):
            self.sync_status_label.config(text=f"状态: {'已启用' if self.cloud_enabled else '未启用'}")
        
        if self.cloud_enabled:
            # 启用云端同步，初始化数据库
            try:
                self.init_database()
                # 同步本地数据到云端
                self.sync_local_to_cloud()
                messagebox.showinfo("成功", "云端同步已启用！")
            except Exception as e:
                messagebox.showerror("错误", f"启用云端同步失败：\n{str(e)}")
                self.cloud_var.set(False)
                self.cloud_enabled = False
                if hasattr(self, 'sync_status_label'):
                    self.sync_status_label.config(text="状态: 未启用")
        else:
            # 禁用云端同步
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
            messagebox.showinfo("提示", "云端同步已禁用！")
    
    def init_database(self):
        # 先连接到MySQL服务器（不指定数据库）
        temp_config = {
            'host': self.mysql_config['host'],
            'port': self.mysql_config['port'],
            'user': self.mysql_config['user'],
            'password': self.mysql_config['password']
        }
        
        connection = pymysql.connect(**temp_config)
        cursor = connection.cursor()
        
        # 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS pomodoro")
        cursor.execute("USE pomodoro")
        
        # 创建 projects 表
        create_projects_table_sql = """
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor.execute(create_projects_table_sql)
        
        # 创建 pomodoro_data 表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS pomodoro_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            project VARCHAR(100) NOT NULL,
            count INT NOT NULL DEFAULT 0,
            UNIQUE KEY unique_date_project (date, project)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor.execute(create_table_sql)
        
        # 确保默认项目存在
        try:
            cursor.execute("INSERT IGNORE INTO projects (name) VALUES ('默认项目')")
        except Exception as e:
            print(f"添加默认项目失败: {str(e)}")
        
        connection.commit()
        cursor.close()
        connection.close()
    
    def get_db_connection(self):
        if not self.db_connection or not self.db_connection.open:
            # 添加时区设置，确保日期处理正确
            config = self.mysql_config.copy()
            config['init_command'] = "SET time_zone = '+00:00'"
            self.db_connection = pymysql.connect(**config)
        return self.db_connection
    
    def save_pomodoro_cloud(self, date, project):
        if not self.cloud_enabled:
            return
        
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            # 检查记录是否存在
            check_sql = "SELECT count FROM pomodoro_data WHERE date = %s AND project = %s"
            cursor.execute(check_sql, (date, project))
            result = cursor.fetchone()
            
            if result:
                # 更新记录
                update_sql = "UPDATE pomodoro_data SET count = count + 1 WHERE date = %s AND project = %s"
                cursor.execute(update_sql, (date, project))
            else:
                # 插入新记录
                insert_sql = "INSERT INTO pomodoro_data (date, project, count) VALUES (%s, %s, 1)"
                cursor.execute(insert_sql, (date, project))
            
            connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"保存到云端失败: {str(e)}")
    
    def get_today_pomodoro_count_cloud(self):
        if not self.cloud_enabled:
            return 0
        
        try:
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            today = datetime.now().strftime("%Y-%m-%d")
            sql = "SELECT SUM(count) FROM pomodoro_data WHERE date = %s"
            cursor.execute(sql, (today,))
            result = cursor.fetchone()
            
            cursor.close()
            
            return int(result[0]) if result[0] else 0
            
        except Exception as e:
            print(f"从云端获取今日番茄数失败: {str(e)}")
            return 0
    
    def sync_local_to_cloud(self):
        if not self.cloud_enabled:
            return
        
        try:
            data = self.load_json()
            connection = self.get_db_connection()
            cursor = connection.cursor()
            
            # 同步本地项目到云端
            if "projects" in data:
                for project in data["projects"]:
                    # 检查项目是否存在
                    check_sql = "SELECT COUNT(*) FROM projects WHERE name = %s"
                    cursor.execute(check_sql, (project,))
                    result = cursor.fetchone()
                    
                    # 如果项目不存在，创建记录
                    if result[0] == 0:
                        insert_sql = "INSERT INTO projects (name) VALUES (%s)"
                        cursor.execute(insert_sql, (project,))
            
            # 同步番茄钟数据
            for date, projects in data.items():
                if date == "projects" or date == "project_targets":
                    continue
                
                for project, count in projects.items():
                    if isinstance(count, int) and count > 0:
                        # 确保项目存在于projects表
                        check_project_sql = "SELECT COUNT(*) FROM projects WHERE name = %s"
                        cursor.execute(check_project_sql, (project,))
                        project_result = cursor.fetchone()
                        
                        if project_result[0] == 0:
                            insert_project_sql = "INSERT INTO projects (name) VALUES (%s)"
                            cursor.execute(insert_project_sql, (project,))
                        
                        # 检查记录是否存在
                        check_sql = "SELECT count FROM pomodoro_data WHERE date = %s AND project = %s"
                        cursor.execute(check_sql, (date, project))
                        result = cursor.fetchone()
                        
                        if result:
                            # 更新记录
                            update_sql = "UPDATE pomodoro_data SET count = %s WHERE date = %s AND project = %s"
                            cursor.execute(update_sql, (count, date, project))
                        else:
                            # 插入新记录
                            insert_sql = "INSERT INTO pomodoro_data (date, project, count) VALUES (%s, %s, %s)"
                            cursor.execute(insert_sql, (date, project, count))
            
            connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"同步本地数据到云端失败: {str(e)}")
    
    def start_cloud_sync(self):
        def sync_task():
            while True:
                if self.cloud_enabled:
                    self.sync_local_to_cloud()
                    # 同步项目列表
                    self.sync_projects_from_cloud()
                    # 更新今日番茄数显示
                    try:
                        today_count = self.get_today_pomodoro_count_cloud()
                        if today_count > 0:
                            self.today_count = today_count
                            self.today_label.config(text=f"今日番茄数: {'🍅' * today_count}")
                        else:
                            self.today_count = 0
                            self.today_label.config(text="今日番茄数: 暂无")
                    except Exception as e:
                        print(f"获取今日番茄数失败: {str(e)}")
                time.sleep(60)  # 每分钟同步一次
        
        sync_thread = threading.Thread(target=sync_task, daemon=True)
        sync_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()