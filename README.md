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

2. **配置**
```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml：
# - 邮件配置（必填）
# - data_sources.tushare.token（可选，作为第三顺位场内行情备用源）
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

### 数据源优先级

场内行情（ETF/LOF 价格）按以下顺序尝试，直到成功：

1. **akshare**：默认第一顺位，免费，但东方财富接口可能限流或拦截
2. **finshare**：第二顺位，可选依赖，安装后自动启用，无需额外配置
3. **Tushare**：第三顺位，需在 [tushare.pro](https://tushare.pro) 注册并配置 Token
4. **Baostock**：最后兜底，免费（使用最近交易日收盘价）

当前版本会优先尝试 akshare；若失败或返回非实时行情结构，则自动回退到 finshare、Tushare、Baostock。

**akshare 东方财富(em) 请求**：若 akshare 调用东方财富接口被限流/拦截，需配置 `nid18` 与 `nid18_create_time`（见 akshare 相关 issue）。在 `config.yaml` 的 `data_sources.akshare_em` 中填写，或设置环境变量 `AKSHARE_EM_NID18`、`AKSHARE_EM_NID18_CREATE_TIME`。本仓库已使用 akshare >= 1.18.21。

**finshare**：安装 `finshare` 后自动参与回退链，不需要新增配置项。

**生产环境建议**：至少配置以下两种方案中的一种，以提高线上实时行情稳定性：

1. `TUSHARE_TOKEN`
2. `AKSHARE_EM_NID18` + `AKSHARE_EM_NID18_CREATE_TIME`

## 📝 计算公式

**溢价率** = (场内价格 - 场外价格) / 场外价格 × 100%

- 🔺 溢价率为正表示溢价
- 🔻 溢价率为负表示折价

## ⚙️ 配置说明

配置文件 `config.yaml` 包含以下配置项：

- `data_sources.tushare.token`: Tushare Token；第三顺位场内行情备用源，也可通过环境变量 `TUSHARE_TOKEN` 配置
- `data_sources.akshare_em.nid18` / `nid18_create_time`: 东方财富请求 cookie；用于提升第一顺位 akshare 的可用性，也可通过环境变量 `AKSHARE_EM_NID18`、`AKSHARE_EM_NID18_CREATE_TIME` 配置
- `email`: 邮件发送配置（SMTP服务器、账号、收件人等）
- `report`: 报告配置（排行榜数量、是否只发送溢价等）

**注意：** 定时任务配置在 `.github/workflows/etf_premium_rate_schedule.yml` 文件中设置，不在 `config.yaml` 中配置。

详细配置说明请参考 `config.example.yaml`。Tushare Token 获取方式：登录 [tushare.pro](https://tushare.pro) → 个人中心 → 接口 Token。`finshare` 不需要单独配置，安装依赖后会自动参与场内行情回退链。

## ⚠️ 免责声明

本工具提供的数据仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。

## 📄 License

MIT License

---

<div align="center">

**⭐ 如果这个工具对你有帮助，请给个 Star ⭐**

</div>
