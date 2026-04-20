# 日程猎人 (Schedule Hunter) 后端开发指南

## 概述

日程猎人是 Uni-app Android 套壳应用，前端基于 Vue 3 + Pinia + Tailwind CSS 构建。后端需对接 RTX 5060，为前端提供日程解析与日历同步服务。

## 基础配置

- **API 地址**: `http://127.0.0.1:8000`
- **前端端口**: `http://localhost:3001`
- **环境变量**: `VITE_API_URL` / `VITE_API_HOST`

## 接口规范

### 1. 日程文本解析

```
POST /api/v1/task/parse
Content-Type: application/json

Request:
{
  "text": "明天上午10点在望京SOHO开会"
}

Response:
{
  "parsed": {
    "id": "task_xxx",
    "title": "开会",
    "start_time": "2026-04-21T02:00:00.000Z",
    "end_time": "2026-04-21T03:00:00.000Z",
    "location": "望京SOHO",
    "confidence": 0.92,
    "has_warning": false,
    "ai_suggestion": "建议提前10分钟到达"
  },
  "is_conflict": false,
  "conflict": null
}
```

### 2. 日历同步

```
GET /api/v1/calendar/sync?month=2026-04

Response:
{
  "month": "2026-04",
  "tasks": [...],
  "summary": {
    "total": 15,
    "conflicts": 2,
    "warnings": 3
  }
}
```

### 3. 任务 CRUD

```
GET    /api/v1/tasks
POST   /api/v1/tasks
PUT    /api/v1/tasks/{task_id}
DELETE /api/v1/tasks/{task_id}

Request (POST/PUT):
{
  "title": "产品评审",
  "start_time": "2026-04-21T06:00:00.000Z",
  "end_time": "2026-04-21T07:30:00.000Z",
  "location": "望京SOHO T3",
  "difficulty": "medium",
  "is_conflict": false,
  "has_warning": false
}

Response:
{
  "id": "task_xxx",
  "title": "产品评审",
  "start_time": "2026-04-21T06:00:00.000Z",
  "end_time": "2026-04-21T07:30:00.000Z",
  "location": "望京SOHO T3",
  "is_conflict": false,
  "has_warning": false,
  "difficulty": "medium"
}
```

### 4. 冲突检测

```
POST /api/v1/tasks/conflict-check

Request:
{
  "start_time": "2026-04-21T06:00:00.000Z",
  "end_time": "2026-04-21T07:30:00.000Z"
}

Response:
{
  "conflict": {
    "detail": "与现有日程'技术评审'存在时间重叠",
    "suggestions": [
      "建议将开始时间调整为 08:00",
      "考虑将任务拆分到其他时段"
    ]
  }
}
```

### 5. WebSocket 推送 (可选)

```
WS ws://127.0.0.1:8000/ws/push

Push Message:
{
  "type": "schedule_sniff",
  "text": "今天下午3点去机场"
}
```

## 数据模型

### Task

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 任务唯一标识 |
| title | string | 任务标题 |
| start_time | ISO8601 | 开始时间 |
| end_time | ISO8601 | 结束时间 |
| location | string | 地点 |
| is_conflict | boolean | 是否冲突 |
| has_warning | boolean | 是否有警告 |
| difficulty | string | 难度: easy/medium/hard |
| is_overnight | boolean | 是否跨天 |
| conflict_with | string | 冲突任务ID |
| conflict_detail | string | 冲突详情 |
| confidence | float | AI解析置信度 |
| ai_suggestion | string | AI建议 |

## 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 开发建议

1. 使用 FastAPI 或类似框架快速搭建
2. 实现自然语言时间解析 (可用正则 + 规则引擎)
3. 支持多种时间表达：中文数字、英文、"今天/明天/后天"等
4. 冲突检测基于时间区间重叠判断
5. 提供 WebSocket 实时推送接口供安卓原生调用

## 测试命令

```bash
curl -X POST http://127.0.0.1:8000/api/v1/task/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "明天上午10点在望京SOHO开会"}'
