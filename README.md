# ZS-monitor

这是一个用于监控招商银行和宁波银行配对交易的 Streamlit 应用。

## 功能

*   实时监控两只股票的价格和涨跌幅。
*   计算价差 (A-B)。
*   当价差超过阈值时发出报警。
*   支持侧边栏调整报警阈值。


## 运行

### 方式一：Streamlit Cloud (网页版)
1. 连接 GitHub 仓库。
2. 在 Settings -> Secrets 中添加 `BARK_KEY` 和 `PUSHPLUS_TOKEN`。
3. 网页保持打开即可接收实时推送。

### 方式二：GitHub Actions (后台自动巡检)
本项目已配置 GitHub Actions 自动巡检：
- **频率**：周一至周五，北京时间 9:30 - 15:30，每30分钟运行一次。
- **配置**：需在 GitHub 仓库 Settings -> Secrets and variables -> Actions 中添加 `BARK_KEY` 和 `PUSHPLUS_TOKEN`。
- **效果**：即使不打开网页，触发信号时也会自动推送。

