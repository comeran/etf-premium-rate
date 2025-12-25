# 📤 上传到 GitHub 指南

## 📁 项目位置

所有文件已组织好，位于项目根目录：
```
<项目目录>/
```

## 📋 项目结构

```
etf-premium-rate/
├── src/                          # 源代码
│   └── etf_premium_rate.py      # 主程序
├── docs/                         # 文档
│   ├── DEPLOY.md                # 部署指南
│   └── UPLOAD.md                # 本文件
├── .github/                      # GitHub配置
│   └── workflows/
│       └── etf_premium_rate.yml # GitHub Actions
├── config.example.yaml           # 配置示例
├── requirements.txt              # 依赖列表
├── .gitignore                   # Git忽略文件
└── README.md                    # 项目说明
```

## 🚀 上传步骤

### 方法一：使用 Git 命令行（推荐）

```bash
# 1. 进入项目目录
cd <项目目录>

# 2. 初始化 Git 仓库
git init

# 3. 添加所有文件
git add .

# 4. 提交
git commit -m "Initial commit: ETF premium rate report"

# 5. 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/仓库名.git

# 6. 推送到 GitHub
git branch -M main
git push -u origin main
```

### 方法二：使用 GitHub Desktop

1. 打开 GitHub Desktop
2. 点击 `File` → `Add Local Repository`
3. 选择项目根目录文件夹
4. 点击 `Publish repository` 上传

### 方法三：使用 GitHub 网页

1. 在 GitHub 创建新仓库
2. 不要初始化 README
3. 按照页面提示上传文件

## ⚠️ 重要提示

1. **不要上传 `config.yaml`** - 此文件包含敏感信息，已在 `.gitignore` 中排除
2. **上传后配置 Secrets** - 按照 `docs/DEPLOY.md` 中的说明配置 GitHub Secrets
3. **测试运行** - 上传后手动触发一次 workflow 测试

## 📝 下一步

上传完成后，请按照 `docs/DEPLOY.md` 中的说明：
1. 配置 GitHub Secrets
2. 测试运行
3. 验证邮件发送

---

**🎉 准备好上传了！**

