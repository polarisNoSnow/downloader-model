# 🤗 HuggingFace Model Downloader

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15%2B-green?logo=qt&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**一个简洁、高效的 HuggingFace 模型下载工具**

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用说明](#-使用说明) • [截图预览](#-截图预览)

</div>

---

## 📖 简介

HuggingFace Model Downloader 是一个基于 PyQt5 开发的桌面应用程序，专为解决国内用户下载 HuggingFace 模型困难的问题而设计。支持多源切换、断点续传、实时进度显示等功能，让模型下载变得简单高效。

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🚀 **多源下载** | 支持 HF Mirror（国内推荐）、HuggingFace 官方双下载源 |
| ⏯️ **暂停/继续** | 随时暂停下载任务，支持断点续传，无需重新开始 |
| 📊 **实时进度** | 显示下载进度、速度、剩余时间，一目了然 |
| 💾 **配置记忆** | 自动保存下载源和保存目录设置，下次启动自动恢复 |
| 🎨 **现代界面** | 简洁美观的 UI 设计，操作直观友好 |
| 🔧 **轻量级** | 仅依赖 PyQt5 和 requests，无冗余依赖 |

## 📦 环境要求

- Python 3.8+
- Windows / Linux / macOS

## 🚀 快速开始

### 方式一：直接运行

```bash
# 克隆仓库
git clone https://github.com/your-username/huggingface-downloader.git
cd huggingface-downloader

# 安装依赖
pip install -r requirements.txt

# 运行程序
python app.py
```

### 方式二：打包为可执行文件

```bash
# 安装打包工具
pip install pyinstaller

# 打包
pyinstaller --onefile --windowed --name "HFDownloader" app.py

# 可执行文件位于 dist/ 目录
```

## 📝 使用说明

### 1. 获取模型 URL

在 HuggingFace 网站上找到需要下载的模型文件，复制文件链接。URL 格式示例：

```
https://huggingface.co/bert-base-uncased/blob/main/pytorch_model.bin
https://huggingface.co/datasets/squad/blob/main/train.json
```

### 2. 选择下载源

| 下载源 | 推荐场景 | 说明 |
|--------|----------|------|
| HF Mirror | 🇨🇳 国内用户 | 镜像站点，下载速度快 |
| HuggingFace 官方 | 🌍 海外用户 | 官方源，稳定可靠 |

### 3. 设置保存目录

选择模型文件的保存位置，默认为 `./models` 目录。

### 4. 开始下载

点击「开始下载」按钮，程序会自动解析 URL 并开始下载。

## 🎮 操作说明

| 按钮 | 功能 |
|------|------|
| ▶ 开始下载 | 解析 URL 并开始下载任务 |
| ⏸ 暂停 | 暂停当前下载，按钮变为「继续」 |
| ▶ 继续 | 恢复暂停的下载任务 |
| ⏹ 停止 | 取消下载，保留已下载的临时文件 |
| ✕ 退出 | 关闭程序（下载中会弹出确认） |

## 📁 项目结构

```
huggingface-downloader/
├── app.py              # 主程序
├── requirements.txt    # 依赖列表
├── .gitignore          # Git 忽略配置
└── README.md           # 说明文档
```

## 🔧 技术实现

- **GUI 框架**: PyQt5
- **HTTP 请求**: requests (支持流式下载、断点续传)
- **多线程**: QThread (避免阻塞 UI)
- **配置存储**: QSettings (跨平台配置持久化)

### 核心功能实现

```python
# 断点续传
if os.path.exists(temp_path):
    downloaded_bytes = os.path.getsize(temp_path)
    headers["Range"] = f"bytes={downloaded_bytes}-"

# 流式下载
response = requests.get(url, headers=headers, stream=True)
for chunk in response.iter_content(chunk_size=8192):
    # 实时写入文件并更新进度
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [HuggingFace](https://huggingface.co/) - 提供模型托管服务
- [HF Mirror](https://hf-mirror.com/) - 提供 HuggingFace 镜像服务

---

<div align="center">

如果这个项目对你有帮助，请给一个 ⭐️ Star 支持一下！

</div>
