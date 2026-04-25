# 日程猎人 (Schedule Hunter)

基于 Vue 3 + FastAPI + BlueLM 的智能日程管理应用。

## 技术栈

### 前端
- Vue 3 (Composition API) + Vite
- Tailwind CSS
- Pinia 状态管理

### 后端
- Python 3.10+ / FastAPI
- SQLite
- httpx (LLM 调用)

## 项目结构

```
schedule-hunter/
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── Index.vue                    # 主页
│   │   │   ├── AddTaskModal.vue             # 手动添加任务弹窗
│   │   │   ├── BountyList.vue               # 任务列表
│   │   │   ├── CalendarGrid.vue             # 日历面板
│   │   │   └── Island/
│   │   │       └── ScheduleIsland.vue       # 灵动岛组件
│   │   ├── stores/useTaskStore.js           # 状态管理
│   │   ├── services/
│   │   │   ├── apiService.js                # API 封装
│   │   │   └── mockProvider.js              # Mock 数据（已弃用）
│   │   ├── styles/main.css                  # 全局样式
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
├── backend/                     # 后端服务
│   ├── main.py                              # FastAPI 入口
│   ├── requirements.txt
│   ├── data/                                # SQLite 数据库文件
│   ├── logs/                                # 日志文件
│   └── src/
│       ├── api/v1/
│       │   ├── task.py                      # 任务 API 路由
│       │   └── websocket.py                 # WebSocket 路由
│       ├── core/
│       │   ├── config.py                    # 配置管理
│       │   └── logger.py                    # 日志 + TraceID 中间件
│       ├── db/
│       │   ├── base.py                      # 数据库连接
│       │   └── task_repo.py                 # 任务 CRUD
│       ├── models/
│       │   ├── request.py                   # 请求模型 (Pydantic)
│       │   └── response.py                  # 响应模型 (Pydantic)
│       └── services/
│           ├── parse_service.py             # 解析服务（LLM + 正则 fallback）
│           ├── llm_service.py               # BlueLM 调用层
│           ├── task_service.py              # 任务业务逻辑
│           └── conflict_service.py          # 冲突检测引擎
├── docs/                          # 文档
│   ├── 日程猎人项目架构设计.md
│   ├── 架构设计与实际实现差异分析.md
│   ├── 架构实现最新差异分析_20260425.md
│   ├── 全栈功能闭环实现差异报告_20260426.md
│   └── 架构目标与现状差距分析报告_V2_20260426.md
└── README.md
```

## 前置要求

- Node.js 18+
- Python 3.10+
- pip

## 快速开始

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端默认运行在 `http://127.0.0.1:8000`

- API 文档: `http://127.0.0.1:8000/docs`
- 健康检查: `http://127.0.0.1:8000/`

### 2. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`

Vite 已配置 proxy，前端 `/api` 请求自动转发到后端 `127.0.0.1:8000`。

### 3. 使用

1. 打开浏览器访问 `http://localhost:5173`
2. 在顶部文本框输入自然语言日程描述，点击「智能解析」
3. 示例输入：
   - "明天下午3点去望京SOHO找张总谈合作"
   - "今晚8点在和平饭店吃饭"
   - "4月28号上午10点开会"
4. 灵动岛将弹出 AI 解析结果，确认后自动创建任务
5. 日历面板点击日期可切换查看任务列表

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/task/parse | 解析自然语言文本 |
| POST | /api/v1/tasks | 创建任务 |
| GET | /api/v1/tasks?date=YYYY-MM-DD | 按日期查询任务 |
| POST | /api/v1/tasks/conflict-check | 冲突检测 |
| WebSocket | /ws/tasks | 实时推送 |

## 灵动岛状态

| 状态 | 触发条件 | 说明 |
|------|----------|------|
| idle | 无活跃任务 | 胶囊静默态 |
| tracking | 任务即将开始（30分钟内） | 倒计时展示 |
| reminder | 任务到达开始时间 | 提醒操作面板 |
| warning | 检测到日程冲突 | 冲突预警 + 建议 |

## 环境配置

后端配置位于 `backend/src/core/config.py`，支持环境变量覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| APP_HOST | 0.0.0.0 | 监听地址 |
| APP_PORT | 8000 | 监听端口 |
| DEBUG | true | 调试模式 |
| DATABASE_URL | sqlite:///./data/tasks.db | 数据库路径 |
| DEFAULT_TIMEZONE | Asia/Shanghai | 默认时区 |
| DEFAULT_DURATION_MINUTES | 60 | 默认任务时长 |
