# 📊 ETF/LOF溢价率排行榜 - 邮件推送版

自动获取A股ETF和LOF基金的溢价率数据，并通过邮件发送精美的HTML报告。

## ✨ 功能特点

- 📧 **邮件推送**：自动发送精美的HTML格式报告到指定邮箱
- 📊 **数据全面**：包含ETF和LOF基金的实时溢价率数据
- ⚙️ **灵活配置**：支持配置多个收件人、排行榜数量、发送时间等
- 🎨 **精美展示**：针对邮箱优化的HTML格式，表格清晰易读
- ⏰ **定时发送**：支持GitHub Actions定时任务

## 📁 项目结构

```
etf-premium-rate/
├── src/                          # 源代码目录
│   └── etf_premium_rate.py      # 主程序
├── docs/                         # 文档目录
│   ├── DEPLOY.md                # 部署指南
│   └── UPLOAD.md                # 上传指南
├── .github/                      # GitHub配置
│   └── workflows/               # GitHub Actions工作流
│       └── etf_premium_rate.yml
├── config.example.yaml           # 配置文件示例
├── requirements.txt              # Python依赖
├── .gitignore                   # Git忽略文件
└── README.md                    # 项目说明（本文件）
```

## 🚀 快速开始

### 本地运行

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置邮件**
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填写你的邮件配置
```

3. **运行脚本**
```bash
python src/etf_premium_rate.py
```

### GitHub Actions 部署

📖 **详细部署指南请查看：[docs/DEPLOY.md](docs/DEPLOY.md)**

快速步骤：
1. 推送代码到 GitHub
2. 配置 GitHub Secrets（见部署指南）
3. 手动触发测试运行
4. 验证邮件发送

## 📋 数据说明

- **场内价格**：ETF/LOF在交易所的实时交易价格
- **场外价格**：基金的单位净值（IOPV实时估值）
- **溢价率**：场内价格相对于场外价格的偏离程度
- **申购状态**：基金的申购限制情况（开放/限大额/暂停）
- **赎回状态**：基金的赎回状态
- **手续费**：基金申购/赎回的手续费率

## 📝 计算公式

**溢价率** = (场内价格 - 场外价格) / 场外价格 × 100%

- 🔺 溢价率为正表示溢价
- 🔻 溢价率为负表示折价

## ⚙️ 配置说明

配置文件 `config.yaml` 包含以下配置项：

- `email`: 邮件发送配置（SMTP服务器、账号、收件人等）
- `report`: 报告配置（排行榜数量、是否只发送溢价等）
- `schedule`: 定时任务配置（发送时间）

详细配置说明请参考 `config.example.yaml`

## ⚠️ 免责声明

本工具提供的数据仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

## 📄 License

MIT License

---

<div align="center">

**⭐ 如果这个工具对你有帮助，请给个 Star ⭐**

</div>

