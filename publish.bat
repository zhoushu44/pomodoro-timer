@echo off
echo ========================================
echo       番茄钟项目发布脚本
echo ========================================
echo.

echo [1/4] 检查Git配置...
git --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Git未安装！
    echo 请先安装Git: https://git-scm.com/
    pause
    exit /b 1
)

echo Git已安装: 
git --version

echo.
echo [2/4] 检查当前目录...
cd /d "%~dp0"
echo 当前目录: %cd%

echo.
echo [3/4] 检查远程仓库配置...
git remote -v
if errorlevel 1 (
    echo 错误: 不是Git仓库或Git配置有问题
    pause
    exit /b 1
)

echo.
echo [4/4] 准备推送代码到GitHub...
echo.
echo ========================================
echo 重要提示：
echo 1. 请确保已在GitHub上创建仓库：
echo    https://github.com/zhoushu44/pomodoro-timer
echo.
echo 2. 如果还没创建仓库，请：
echo    a) 访问 https://github.com
echo    b) 登录账号 zhoushu44
echo    c) 点击"+" -> "New repository"
echo    d) 仓库名: pomodoro-timer
echo    e) 不要勾选初始化选项
echo    f) 点击"Create repository"
echo.
echo 3. 创建仓库后，按任意键继续推送代码...
echo ========================================
pause

echo.
echo 设置远程仓库...
git remote remove origin 2>nul
git remote add origin https://github.com/zhoushu44/pomodoro-timer.git

echo.
echo 推送代码到GitHub...
echo 注意：可能会打开浏览器要求登录GitHub
git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================
    echo 推送失败！可能的原因：
    echo 1. GitHub仓库不存在（请先创建）
    echo 2. 网络连接问题
    echo 3. 认证失败
    echo.
    echo 请参考"发布指南.md"文件中的故障排除部分
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo 恭喜！代码已成功推送到GitHub！
echo.
echo 下一步：
echo 1. 访问 https://github.com/zhoushu44/pomodoro-timer
echo 2. 点击"Releases" -> "Create a new release"
echo 3. 创建v1.0版本，上传 dist/番茄钟_v1.exe
echo 4. 填写版本描述（参考发布指南.md）
echo ========================================
echo.
echo 按任意键打开GitHub仓库页面...
pause
start https://github.com/zhoushu44/pomodoro-timer