# 日程猎人 (Schedule Hunter)

> AIGC 驱动的全域日程管理基建 —— 利用系统级无障碍嗅探与蓝心大模型，实现日程零感录入。

[![AIGC 创新赛参赛项目](https://img.shields.io/badge/AIGC-创新赛-6C63FF?style=flat-square)](https://)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4-4FC08D?style=flat-square&logo=vue.js)](https://vuejs.org/)
[![Capacitor](https://img.shields.io/badge/Capacitor-8.3-5364FA?style=flat-square)](https://capacitorjs.com/)
[![BlueLM API](https://img.shields.io/badge/BlueLM-vivo-00A8E8?style=flat-square)](https://developer.vivo.com.cn/)

---

## 目录

- [项目简介](#项目简介-about-the-project)
- [技术架构](#技术架构-tech-stack)
- [环境依赖](#环境依赖-prerequisites)
- [环境变量与配置](#环境变量与配置-configuration)
- [本地部署与运行](#本地部署与运行-installation--running)
- [移动端打包](#移动端打包-mobile-build)
- [核心目录结构](#核心目录结构-project-structure)
- [API 接口文档](#api-接口文档-api-reference)
- [灵动岛状态说明](#灵动岛状态说明-island-states)
- [常见问题](#常见问题-faq)
- [作者与团队](#作者与团队-team)

---

## 项目简介 (About The Project)

**日程猎人** 是一款面向未来的智能日程管理应用，核心特点：

- **零感录入**：用户只需输入自然语言（如"明天下午3点开会"），AI 自动解析时间、地点、参与者
- **AIGC 驱动**：集成 vivo 蓝心大模型（BlueLM），实现意图识别与时间提取
- **全域管理**：支持 Web、移动端（Android）多端同步
- **冲突预警**：智能检测日程冲突并提供解决方案
- **灵动岛集成**：Android 端支持灵动岛实时状态展示与快捷操作

### 核心功能

| 功能 | 描述 |
|------|------|
| 自然语言解析 | AI 理解"明天下午三点"、"本周五晚"等模糊时间 |
| 智能冲突检测 | 自动检测时间、地点冲突并提示 |
| 实时提醒 | 任务开始前多时段提醒（30min/10min/5min） |
| 跨端同步 | Web + Android 数据实时同步 |
| 灵动岛状态 | 动态展示任务倒计时、状态提醒 |

---

## 技术架构 (Tech Stack)

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.4.0 | 渐进式前端框架（Composition API） |
| Vite | ^5.0.0 | 下一代前端构建工具 |
| Tailwind CSS | ^3.4.0 | 原子化 CSS 框架 |
| Pinia | ^2.1.0 | Vue 状态管理 |
| Capacitor | ^8.3.1 | 跨平台原生桥接 |
| @capacitor/android | ^8.3.1 | Android 原生平台支持 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 后端开发语言 |
| FastAPI | ^0.109.0 | 高性能 Web 框架 |
| Uvicorn | ^0.27.0 | ASGI 服务器 |
| SQLite | - | 轻量级关系数据库 |
| httpx | ^0.27.0 | 异步 HTTP 客户端 |
| APScheduler | ^3.10.4 | 定时任务调度 |
| Pydantic | ^2.5.3 | 数据验证 |

### AI 服务

| 服务 | 用途 |
|------|------|
| vivo BlueLM (Doubao-Seed-2.0-lite) | 自然语言时间解析 |
| BlueLM API | <https://api-ai.vivo.com.cn/v1/chat/completions> |

---

## 环境依赖 (Prerequisites)

在开始之前，请确保已安装以下软件：

### 必须安装

| 软件 | 版本要求 | 下载地址 |
|------|----------|----------|
| **Node.js** | 18.x 或更高 | <https://nodejs.org> |
| **Python** | 3.10 或更高 | <https://www.python.org> |
| **pip** | 最新版本 | Python 自带 |

### 可选安装（移动端开发）

| 软件 | 用途 | 下载地址 |
|------|------|----------|
| **Android Studio** | Android 真机/模拟器开发 | <https://developer.android.com/studio> |
| **ADB** | Android 调试桥 | Android Studio 自带 |
| **JDK** | Java 开发环境 | <https://adoptium.net> |

### 验证安装

```bash
# 检查 Node.js 版本
node --version   # 应显示 v18.x.x 或更高

# 检查 Python 版本
python --version  # 应显示 Python 3.10.x 或更高

# 检查 pip 版本
pip --version     # 应显示最新版本
```

---

## 环境变量与配置 (Configuration)

### 1. 创建 `.env` 配置文件

在后端目录创建 `.env` 文件（**注意：此文件不会被 Git 跟踪**）：

```bash
cd backend
touch .env
```

### 2. 填写配置内容

```bash
# ========== 必填：API Key 配置 ==========
# 蓝心大模型 API Key（必填）
# 请访问 https://developer.vivo.com.cn/ 获取您的 API Key
BLUELM_API_KEY=your_bluelm_api_key_here

# 通用 LLM API Key（可选，若与 BLUELM_API_KEY 相同可省略）
LLM_API_KEY=your_llm_api_key_here

# ========== 可选：服务配置 ==========
# 服务地址和端口
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库路径（可选，默认使用 SQLite）
DATABASE_URL=sqlite:///./data/schedule.db

# CORS 配置（可选，默认允许所有）
CORS_ORIGINS=*
```

### 3. 获取 BlueLM API Key

1. 访问 [vivo 开发者平台](https://developer.vivo.com.cn/)
2. 注册/登录开发者账号
3. 进入「蓝心大模型 API 服务」
4. 创建应用并获取 API Key
5. 将 API Key 填入 `.env` 文件的 `BLUELM_API_KEY`

### 4. 前端局域网配置（重点排坑）

**问题**：真机或模拟器无法访问本地 `localhost` 地址

**解决方案**：修改前端配置为局域网 IP

#### 4.1 修改 `vite.config.js`

```javascript
// frontend/vite.config.js
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    host: true,  // 监听所有网络接口，允许局域网访问
    proxy: {
      '/api': {
        // 修改为你的局域网 IP 地址
        target: 'http://192.168.x.x:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://192.168.x.x:8000',
        ws: true
      }
    }
  }
})
```

#### 4.2 修改 `capacitor.config.json`

```json
{
  "appId": "com.example.schedulehunter",
  "appName": "ScheduleHunter",
  "webDir": "dist",
  "server": {
    "cleartext": true,  // 允许 HTTP 明文传输，防止黑屏
    "url": "http://192.168.x.x:5173"  // 修改为你的局域网 IP
  }
}
```

#### 4.3 获取本机局域网 IP

```bash
# Windows
ipconfig | findstr "IPv4"

# macOS / Linux
ifconfig | grep "inet " | grep -v 127.0.0.1
```

#### 4.4 配置 Android cleartext 权限

`capacitor.config.json` 中的 `"cleartext": true` 已自动配置，若手动修改：

```xml
<!-- android/app/src/main/res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">192.168.x.x</domain>
    </domain-config>
</network-security-config>
```

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<application
    android:usesCleartextTraffic="true"
    ... >
```

---

## 本地部署与运行 (Installation & Running)

### 步骤 1：克隆项目

```bash
git clone <repository_url>
cd schedulemanneger
```

### 步骤 2：启动后端服务

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 启动后端服务（自动创建数据库和日志目录）
python main.py
```

后端成功启动后，显示：

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 步骤 3：启动前端开发服务器

**新开一个终端窗口**：

```bash
# 进入前端目录
cd frontend

# 安装 Node.js 依赖
npm install

# 启动开发服务器（允许局域网访问）
npm run dev -- --host
```

前端成功启动后，显示：

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/  ← 真机访问此地址
```

### 步骤 4：验证服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 Web | <http://localhost:5173> | 本地浏览器访问 |
| 后端 API | <http://localhost:8000> | API 根路径 |
| API 文档 | <http://localhost:8000/docs> | Swagger UI |
| 健康检查 | <http://localhost:8000/> | 返回服务状态 |

---

## 移动端打包 (Mobile Build)

### 准备工作

```bash
cd frontend

# 安装 Capacitor 依赖（如果尚未安装）
npm install @capacitor/core @capacitor/cli @capacitor/android
```

### 步骤 1：构建 Web 应用

```bash
cd frontend

# 构建生产版本
npm run build
```

### 步骤 2：初始化 Capacitor

```bash
# 仅首次需要执行
npx cap init ScheduleHunter com.example.schedulehunter --web-dir=dist
```

### 步骤 3：添加 Android 平台

```bash
# 仅首次需要执行
npx cap add android
```

### 步骤 4：同步 Web 到 Android

```bash
# 每次修改前端代码后都需要执行
npx cap sync android
```

### 步骤 5：在 Android Studio 中打开项目

```bash
# Capacitor 会创建 android 目录
cd android

# 启动 Android Studio
# macOS
open -a "Android Studio" .

# Windows
start Android Studio
```

### 步骤 6：运行到设备

#### 方式 A：通过 Android Studio

1. 在 Android Studio 中打开项目
2. 连接 Android 设备（开启 USB 调试）
3. 点击 `Run` → `Run 'app'`

#### 方式 B：通过 ADB 安装

```bash
# 确保设备已连接并开启 USB 调试
adb devices

# 安装 APK 到设备
adb install app-debug.apk

# 或安装并启动
adb install -r app-debug.apk && adb shell am start -n com.example.schedulehunter/.MainActivity
```

### 步骤 7：查看日志

```bash
# 实时查看设备日志
adb logcat -s Capacitor

# 查看特定应用日志
adb logcat | grep -i "schedulehunter"
```

---

## 核心目录结构 (Project Structure)

```
schedulemanneger/
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── components/               # Vue 组件
│   │   │   ├── Index.vue            # 主页入口
│   │   │   ├── AddTaskModal.vue     # 添加任务弹窗
│   │   │   ├── BountyList.vue       # 任务列表组件
│   │   │   ├── CalendarGrid.vue     # 日历网格组件
│   │   │   └── Island/              # 灵动岛相关
│   │   │       └── ScheduleIsland.vue  # 灵动岛状态组件
│   │   ├── stores/                  # Pinia 状态管理
│   │   │   └── useTaskStore.js      # 任务状态管理
│   │   ├── services/               # 服务层
│   │   │   ├── apiService.js        # API 封装（parse_task, create_task 等）
│   │   │   └── mockProvider.js      # Mock 数据（已弃用）
│   │   ├── styles/
│   │   │   └── main.css             # Tailwind 全局样式
│   │   ├── App.vue                  # 根组件
│   │   └── main.js                  # 入口文件
│   ├── android/                     # Capacitor Android 项目
│   ├── dist/                        # 构建输出目录
│   ├── index.html
│   ├── vite.config.js               # Vite 配置（含代理）
│   ├── capacitor.config.json         # Capacitor 配置
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── backend/                          # 后端服务
│   ├── main.py                       # FastAPI 入口 + 路由注册
│   ├── requirements.txt              # Python 依赖
│   ├── .env.example                  # 环境变量模板
│   ├── data/                         # SQLite 数据库目录
│   ├── logs/                         # 日志文件目录
│   └── src/
│       ├── api/v1/                  # API 路由层
│       │   ├── task.py             # 任务 CRUD + 解析接口
│       │   └── websocket.py        # WebSocket 实时推送
│       ├── core/                    # 核心配置
│       │   ├── config.py           # Settings 配置类
│       │   └── logger.py           # 日志 + TraceID 中间件
│       ├── db/                      # 数据访问层
│       │   ├── base.py             # SQLite 连接 + 建表
│       │   └── task_repo.py        # 任务 Repository
│       ├── models/                  # Pydantic 模型
│       │   ├── request.py          # 请求模型
│       │   └── response.py         # 响应模型
│       └── services/               # 业务逻辑层
│           ├── parse_service.py    # 解析服务（LLM + Fallback）
│           ├── llm_service.py      # BlueLM 调用封装
│           ├── task_service.py     # 任务业务逻辑
│           ├── conflict_service.py # 冲突检测引擎
│           └── reminder_service.py  # 提醒调度器
│
├── docs/                             # 项目文档
├── .gitignore                        # Git 忽略配置
└── README.md                         # 本文件
```

---

## API 接口文档 (API Reference)

### 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | <http://localhost:8000> |
| API 文档 | <http://localhost:8000/docs> |
| 认证方式 | 无（开放 API） |

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 健康检查 |
| `POST` | `/api/v1/task/parse` | 解析自然语言文本 |
| `POST` | `/api/v1/tasks` | 创建任务 |
| `GET` | `/api/v1/tasks` | 查询任务列表 |
| `GET` | `/api/v1/tasks/{id}` | 获取单个任务 |
| `PUT` | `/api/v1/tasks/{id}` | 更新任务 |
| `DELETE` | `/api/v1/tasks/{id}` | 删除任务 |
| `PATCH` | `/api/v1/tasks/{id}/status` | 更新任务状态 |
| `POST` | `/api/v1/tasks/conflict-check` | 冲突检测 |
| `WebSocket` | `/ws/tasks` | 实时任务推送 |

### 核心接口示例

#### 解析自然语言

```bash
curl -X POST http://localhost:8000/api/v1/task/parse \
  -H "Content-Type: application/json" \
  -d '{
    "source_text": "明天下午3点去望京SOHO开会",
    "context": {
      "recent_tasks": [],
      "user_preferences": {
        "default_duration_minutes": 60,
        "timezone": "Asia/Shanghai"
      }
    }
  }'
```

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "title": "开会",
    "start_time": "2026-05-07T15:00:00+08:00",
    "end_time": "2026-05-07T16:00:00+08:00",
    "location": "望京SOHO",
    "confidence": 0.95,
    "needs_confirmation": false
  }
}
```

#### 创建任务

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "source_text": "明天下午3点去望京SOHO开会",
    "parsed": {
      "title": "开会",
      "start_time": "2026-05-07T15:00:00+08:00",
      "end_time": "2026-05-07T16:00:00+08:00",
      "location": "望京SOHO"
    }
  }'
```

---

## 灵动岛状态说明 (Island States)

| 状态 | 触发条件 | 视觉效果 | 可用操作 |
|------|----------|----------|----------|
| `idle` | 无活跃/即将开始的任务 | 胶囊静默态 | - |
| `tracking` | 任务即将开始（30分钟内） | 倒计时展示 | 查看详情 |
| `active` | 任务正在进行中 | 进度指示 | 标记完成 |
| `reminder` | 任务到达开始时间 | 闪烁提醒 | 稍后提醒/已完成 |
| `warning` | 检测到日程冲突 | 红色警告标识 | 查看冲突/解决 |

### 状态流转图

```text
idle ──[任务在30min内]──→ tracking ──[时间到达]──→ active
  ↑                              │                    │
  │                              │                    ↓
  └──[无活跃任务]←──[用户操作]── reminder ──[已提醒]── warning
```

---

## 常见问题 (FAQ)

### Q1: 真机调试时页面显示黑屏

**原因**：Android 默认禁止 HTTP 明文传输

**解决**：确保 `capacitor.config.json` 中已设置 `"cleartext": true`，并执行：

```bash
npx cap sync android
```

### Q2: 模拟器无法访问本机服务

**解决**：

1. 使用 `adb reverse` 端口映射：

```bash
adb reverse tcp:8000 tcp:8000
adb reverse tcp:5173 tcp:5173
```

1. 或直接使用 Android Studio 的模拟器内置地址 `10.0.2.2` 访问本机

### Q3: BlueLM API 调用失败

**排查步骤**：

1. 检查 `.env` 文件中的 `BLUELM_API_KEY` 是否正确
2. 确认 API Key 已激活且有可用配额
3. 检查网络是否能访问 `api-ai.vivo.com.cn`

### Q4: 数据库初始化失败

**原因**：缺少 `data` 目录权限

**解决**：

```bash
cd backend
mkdir -p data logs
```

### Q5: CORS 跨域错误

**原因**：前端 API 请求被浏览器拦截

**解决**：后端已配置 `allow_origins=["*"]`，确保后端服务正常启动

### Q6: WebSocket 连接失败

**排查**：

1. 检查后端 WebSocket 路由是否正确注册
2. 确认前端 `apiService.js` 中的 WebSocket URL 与后端一致
3. 检查是否有代理配置阻止了 WebSocket 连接

---

## 作者与团队 (Team)

| 成员 | 职责 |
|------|------|
| **康国智** | 项目负责人 / 后端架构 |
| **王梓杰** | 前端开发 / 移动端集成 |
| **由灏洋** | AI 集成 / 蓝心大模型对接 |

### 参赛信息

- **赛事**：AIGC 创新赛
- **项目**：日程猎人 (Schedule Hunter)
- **技术栈**：Vue 3 + FastAPI + SQLite + BlueLM + Capacitor

---

## 许可证 (License)

本项目仅供参赛和学习使用。

---

## 致谢 (Acknowledgments)

- [vivo 开发者平台](https://developer.vivo.com.cn/) - 蓝心大模型 API
- [Vue.js](https://vuejs.org/) - 前端框架
- [FastAPI](https://fastapi.tiangolo.com/) - Python Web 框架
- [Capacitor](https://capacitorjs.com/) - 跨平台解决方案
