# 🚀 GitHub Actions 部署指南

本指南将帮助你将 ETF 溢价率报告脚本部署到 GitHub Actions，实现自动定时发送邮件。

## 📋 快速开始（5分钟部署）

### 步骤 1: 创建 GitHub 仓库

1. 登录 [GitHub](https://github.com)
2. 点击右上角 `+` → `New repository`
3. 填写仓库名称（如：`etf-premium-rate`）
4. 选择 `Private`（推荐，因为包含敏感信息）
5. 点击 `Create repository`

### 步骤 2: 推送代码

```bash
# 在项目根目录下执行
cd /Users/zane/Documents/Bigo/etf-premium-rate

git init
git add .
git commit -m "Initial commit: ETF premium rate report"

# 添加你的仓库地址（替换为实际地址）
git remote add origin https://github.com/你的用户名/etf-premium-rate.git

# 推送代码
git branch -M main
git push -u origin main
```

### 步骤 3: 配置 GitHub Secrets

1. 进入仓库页面，点击 `Settings`
2. 左侧菜单选择 `Secrets and variables` → `Actions`
3. 点击 `New repository secret`，依次添加以下 Secrets：

#### 必需配置：

| Secret 名称 | 说明 | 示例值 |
|------------|------|--------|
| `EMAIL_SMTP_HOST` | SMTP服务器 | `smtp.qq.com` |
| `EMAIL_SMTP_PORT` | SMTP端口 | `587` |
| `EMAIL_SMTP_USE_TLS` | 是否使用TLS | `true` |
| `EMAIL_USERNAME` | 发送邮箱 | `your_email@qq.com` |
| `EMAIL_PASSWORD` | 邮箱授权码 | `你的16位授权码` |
| `EMAIL_RECIPIENTS` | 收件人（多个用逗号分隔） | `email1@example.com,email2@example.com` |

#### 可选配置：

| Secret 名称 | 说明 | 默认值 |
|------------|------|--------|
| `EMAIL_SUBJECT` | 邮件主题 | `📊 ETF/LOF溢价率排行榜 - {date}` |
| `REPORT_TOP_N` | 排行榜数量 | `100` |
| `REPORT_ONLY_PREMIUM` | 是否只发送溢价 | `false` |

### 步骤 4: 测试运行

1. 进入仓库的 `Actions` 标签页
2. 在左侧选择 `ETF Premium Rate Report`
3. 点击右侧 `Run workflow` → `Run workflow`
4. 等待运行完成（约1-2分钟）
5. 检查邮箱是否收到报告

### 步骤 5: 验证定时任务

- 定时任务会在每天 UTC 2:00（北京时间 10:00）自动运行
- 可以在 `Actions` 页面查看运行历史

## 📧 获取邮箱授权码

### QQ邮箱

1. 登录 [QQ邮箱](https://mail.qq.com)
2. 点击 `设置` → `账户`
3. 找到 `POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务`
4. 开启 `POP3/SMTP服务` 或 `IMAP/SMTP服务`
5. 点击 `生成授权码`，会得到一个16位的授权码
6. **重要**：这个授权码就是 `EMAIL_PASSWORD` 的值（不是QQ密码）

### Gmail

1. 登录 Google 账户
2. 进入 [账户安全设置](https://myaccount.google.com/security)
3. 启用 `两步验证`
4. 在 `应用专用密码` 中生成新密码
5. 使用生成的16位密码作为 `EMAIL_PASSWORD`

### 163/126邮箱

1. 登录邮箱网页版
2. 设置 → `POP3/SMTP/IMAP`
3. 开启 `SMTP服务`
4. 设置授权码（6位数字或字母）
5. 使用授权码作为 `EMAIL_PASSWORD`

## ⚙️ 常用邮箱SMTP配置

### QQ邮箱
```yaml
EMAIL_SMTP_HOST: smtp.qq.com
EMAIL_SMTP_PORT: 587
EMAIL_SMTP_USE_TLS: true
```

### Gmail
```yaml
EMAIL_SMTP_HOST: smtp.gmail.com
EMAIL_SMTP_PORT: 587
EMAIL_SMTP_USE_TLS: true
```

### 163邮箱
```yaml
EMAIL_SMTP_HOST: smtp.163.com
EMAIL_SMTP_PORT: 25  # 或 465
EMAIL_SMTP_USE_TLS: true
```

### Outlook
```yaml
EMAIL_SMTP_HOST: smtp-mail.outlook.com
EMAIL_SMTP_PORT: 587
EMAIL_SMTP_USE_TLS: true
```

## ⏰ 修改发送时间

编辑 `.github/workflows/etf_premium_rate.yml` 文件中的 cron 表达式：

```yaml
schedule:
  - cron: '0 2 * * *'  # UTC 2:00 = 北京时间 10:00
```

**常用时间对照表：**

| 北京时间 | UTC时间 | Cron表达式 |
|---------|---------|-----------|
| 08:00 | 00:00 | `0 0 * * *` |
| 10:00 | 02:00 | `0 2 * * *` |
| 14:00 | 06:00 | `0 6 * * *` |
| 18:00 | 10:00 | `0 10 * * *` |
| 22:00 | 14:00 | `0 14 * * *` |

**Cron 表达式格式：**
```
分钟 小时 日 月 星期
0-59  0-23 1-31 1-12 0-7
```

## 🔍 故障排查

### 问题1: 邮件发送失败

**可能原因：**
- SMTP配置错误
- 授权码错误（注意：不是登录密码）
- 未开启SMTP服务
- 网络问题

**解决方法：**
1. 查看 GitHub Actions 运行日志
2. 检查错误信息
3. 在本地测试邮件发送功能

### 问题2: Workflow 没有运行

**可能原因：**
- 未启用 Actions
- cron 表达式错误
- 仓库是 Private 但未设置 Actions 权限

**解决方法：**
1. 检查 `Settings` → `Actions` → `General`
2. 确保 `Allow all actions and reusable workflows` 已启用
3. 手动触发一次测试

### 问题3: 收不到邮件

**可能原因：**
- 收件人邮箱错误
- 邮件在垃圾邮件文件夹
- 发送频率过高被限制

**解决方法：**
1. 检查 `EMAIL_RECIPIENTS` 配置
2. 查看垃圾邮件文件夹
3. 尝试发送到不同邮箱测试

### 问题4: Secrets 未生效

**可能原因：**
- Secret 名称拼写错误
- 未正确设置 Secret

**解决方法：**
1. 检查 Secret 名称是否完全匹配（区分大小写）
2. 重新设置 Secret
3. 查看 workflow 日志中的配置信息

## 📝 部署检查清单

完成以下检查项，确保部署成功：

- [ ] GitHub 仓库已创建
- [ ] 代码已推送到 GitHub
- [ ] 所有必需的 GitHub Secrets 已配置
- [ ] 邮箱授权码已获取并配置
- [ ] Workflow 文件已提交
- [ ] 手动触发测试成功
- [ ] 收到测试邮件
- [ ] 定时任务时间已设置正确

## 🔐 安全建议

1. **使用 Private 仓库**：如果包含敏感信息，建议使用 Private 仓库
2. **定期更新授权码**：建议每3-6个月更新一次邮箱授权码
3. **限制收件人**：只添加必要的收件人邮箱
4. **监控运行日志**：定期检查 Actions 运行日志，确保正常

## 📚 相关资源

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Cron 表达式生成器](https://crontab.guru/)
- [SMTP 服务器配置指南](https://www.serversmtp.com/)

## 💡 进阶配置

### 多收件人配置

在 `EMAIL_RECIPIENTS` Secret 中，多个邮箱用逗号分隔：
```
email1@example.com,email2@example.com,email3@example.com
```

### 自定义邮件主题

设置 `EMAIL_SUBJECT` Secret：
```
📊 ETF溢价率日报 - {date}
```

### 只发送溢价率最高的

设置 `REPORT_ONLY_PREMIUM` Secret 为 `true`

### 调整排行榜数量

设置 `REPORT_TOP_N` Secret（如：`50` 表示只显示前50名）

---

**🎉 完成部署后，你将每天自动收到精美的 ETF 溢价率报告邮件！**

如有问题，请查看 GitHub Actions 的运行日志或提交 Issue。
