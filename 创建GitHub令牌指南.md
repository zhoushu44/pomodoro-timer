# 创建GitHub个人访问令牌指南

## 为什么需要GitHub令牌？
由于GitHub不再支持密码认证，您需要创建一个个人访问令牌(PAT)来通过命令行推送代码。

## 创建步骤：

### 步骤1：登录GitHub
1. 打开浏览器，访问：https://github.com
2. 使用您的账号 `zhoushu44` 登录

### 步骤2：进入令牌设置页面
1. 点击右上角头像 → "Settings"
2. 在左侧菜单中，点击"Developer settings"
3. 点击"Personal access tokens"
4. 点击"Tokens (classic)"
5. 点击"Generate new token"
6. 选择"Generate new token (classic)"

### 步骤3：配置令牌
1. **Note**: `番茄钟项目发布`
2. **Expiration**: 选择"90 days"（推荐）
3. **Select scopes**（勾选以下权限）：
   - [x] `repo` (全部)
     - [x] repo:status
     - [x] repo_deployment
     - [x] public_repo
     - [x] repo:invite
     - [x] security_events
   - [x] `workflow`
   - [x] `write:packages`
   - [x] `delete:packages`

### 步骤4：生成令牌
1. 滚动到页面底部
2. 点击"Generate token"
3. **重要**：立即复制生成的令牌（只显示一次！）
4. 将令牌保存到安全的地方

## 使用令牌推送代码

### 方法1：使用令牌作为密码
```bash
# 当Git要求输入密码时，使用令牌代替
用户名: zhoushu44
密码: [粘贴您的令牌]
```

### 方法2：将令牌保存到Git配置
```bash
# 将令牌添加到Git配置
git config --global credential.helper store
# 下次推送时会要求输入用户名和密码，输入令牌即可
```

### 方法3：在URL中包含令牌
```bash
# 修改远程仓库URL
git remote set-url origin https://zhoushu44:[您的令牌]@github.com/zhoushu44/pomodoro-timer.git
```

## 安全注意事项
1. **不要分享**：令牌就像密码，不要分享给他人
2. **定期更新**：设置合适的过期时间
3. **撤销令牌**：如果怀疑泄露，立即在GitHub上撤销
4. **不要提交**：不要将令牌提交到代码仓库

## 故障排除

### 问题1：令牌无效
- 检查令牌是否已过期
- 确认权限是否正确
- 重新生成新令牌

### 问题2：认证失败
```bash
# 清除旧的Git凭证
git credential-manager reject https://github.com
# 或
git config --global --unset credential.helper
```

### 问题3：网络问题
```bash
# 检查网络连接
ping github.com
# 如果使用代理，配置Git代理
git config --global http.proxy http://proxy.example.com:8080
```

## 创建仓库的替代方法

如果您不想创建令牌，可以通过网页直接创建仓库：

### 网页创建仓库步骤：
1. 访问：https://github.com/new
2. 填写：
   - Repository name: `pomodoro-timer`
   - Description: "番茄钟应用程序"
   - Public
   - 不要初始化任何文件
3. 点击"Create repository"
4. 创建后，按照页面上的命令推送代码

## 获取帮助
- GitHub官方文档：https://docs.github.com/authentication
- 令牌管理：https://github.com/settings/tokens
- 问题反馈：https://github.com/contact

---

**创建令牌后，返回命令行继续发布项目！**