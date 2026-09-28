param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

# 自动加 v 前缀（不重复加）
if ($Version -notmatch '^v') {
    $tag = "v$Version"
} else {
    $tag = $Version
}

Write-Host "=== 创建 Release ===" -ForegroundColor Cyan
Write-Host "版本号: $tag" -ForegroundColor Yellow

# 检查 tag 是否已存在
$existing = git tag -l $tag
if ($existing) {
    Write-Host "Tag $tag 已存在，请先删除: git tag -d $tag" -ForegroundColor Red
    exit 1
}

# 确认工作区干净
$status = git status --porcelain
if ($status) {
    Write-Host "工作区有未提交的更改，请先 commit 或 stash" -ForegroundColor Red
    exit 1
}

git tag $tag
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "推送 tag $tag ..." -ForegroundColor Cyan
git push origin $tag
if ($LASTEXITCODE -ne 0) {
    Write-Host "推送失败，正在回滚 tag" -ForegroundColor Red
    git tag -d $tag
    exit 1
}

Write-Host "=== 完成 ===" -ForegroundColor Green
Write-Host "GitHub Actions 将自动构建并发布 Release" -ForegroundColor Green
Write-Host "查看: https://github.com/$($env:GITHUB_REPOSITORY ?? 'zhoushu44/pomodoro-timer')/actions" -ForegroundColor Green
