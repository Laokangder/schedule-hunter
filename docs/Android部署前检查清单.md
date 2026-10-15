# 日程猎人 Android 部署前检查清单

> 审计日期：2026-10-15
> 适用范围：当前 Vue 3 + Capacitor 8 Android 容器与 FastAPI 后端
> 结论：前端生产构建、Android 容器同步、APK 后端配置、手机浏览器到后端的局域网连通、本地到点通知业务接线、冲突确认持久化和 Android 系统通知监听第一版已完成；App 内 API/WS、本地提醒与系统通知监听仍待真机矩阵验收。跨应用悬浮窗或厂商私有灵动岛尚未实现，不应作为已完成功能对外展示。

## 一、已验证通过

| 检查项 | 结果 | 说明 |
|---|---|---|
| 前端生产构建 | ✅ 通过 | Vite 成功构建 44 个模块 |
| Python 语法检查 | ✅ 通过 | `compileall` 未发现语法错误 |
| 后端依赖导入 | ✅ 通过 | 项目 `.venv` 可导入 FastAPI、Pydantic、httpx、APScheduler 和 regex |
| 后端集成测试 | ✅ 5/5 通过 | 覆盖 CRUD、冲突、降级解析、提醒策略和过期处理 |
| Android APK 构建 | ✅ 通过 | Gradle Daemon 固定使用 Android Studio JDK 21，Debug APK 已成功生成 |
| Capacitor 原生同步 | ✅ 通过 | Web 资源已复制，本地通知插件已进入 Android 工程 |
| APK 后端地址 | ✅ 已配置 | 生产构建已写入局域网后端地址，并支持用户在设置页覆盖 |
| 本地到点通知业务 | ✅ 已接线，待真机验收 | 已完成授权、注册、取消、改期重建、启动恢复与稳定 ID 去重 |
| Android 系统通知监听 | ✅ 第一版已接线，待真机验收 | 已完成 Service、Manifest、通知使用权入口、敏感过滤、时间线索预筛、去重队列和 Capacitor Bridge |
| Android 混合内容 | ✅ 已配置 | 局域网测试允许 WebView 从本地 HTTPS 页面访问 HTTP 后端；正式发布应改用 HTTPS 并关闭该能力 |
| 真实 DS LLM 调用 | ✅ 通过 | `deepseek-flash` 返回 HTTP 200，解析结果 `ai_fallback=false` |
| 冲突卡片确认创建 | ✅ 已完成 | 确认后调用创建接口，获得真实 `task_id` 后才关闭卡片；失败时保留卡片以便重试 |

## 二、已解决的部署环境问题

### 2.1 Android 构建环境不兼容（已解决）

当前使用 JDK 26，执行 `gradlew assembleDebug` 时出现：

```text
Unsupported class file major version 70
```

已完成：

- 复用 Android Studio 自带 OpenJDK 21.0.10。
- 在项目 `gradle.properties` 中设置 `org.gradle.java.home`，命令行不再依赖临时环境变量。
- 针对工作区中文路径启用 `android.overridePathCheck=true`。
- Gradle 8.14.3 已完成 124 项任务并成功生成 Debug APK。

### 2.2 Android 容器 Web 资源同步（已验证）

已执行 `npx cap sync android`，`dist` 已复制到 `frontend/android/app/src/main/assets/public`，本地通知插件也已写入 Capacitor Android 配置。

每次准备安装最新前端版本时仍需执行：

```bash
cd frontend
npm run build
npx cap sync android
```

不得把开发服务器 `server.url` 固化进正式包；正式包应加载本地 Web 资源，只把 API/WS 指向后端。

### 2.3 真实 DS LLM 链路（已验证）

已在联网环境中调用 `https://api.deepseek.com/chat/completions`，模型 `deepseek-flash` 返回 HTTP 200。中文样例“明天下午三点在会议室开项目评审会”成功解析出标题、时间和地点，结果为 `ai_fallback=false`、`needs_confirmation=false`。

该结果证明当前 DS 地址、模型名称、密钥和结构化返回链路可用。部署后仍需保留超时、限流、异常响应和正则降级回归测试，密钥不得写入日志或代码仓库。

### 2.4 APK 后端地址（已配置）

`frontend/.env.production` 提供构建期默认地址；App 设置页支持保存并测试当前后端地址，WebSocket 会根据 API 地址自动生成 `/ws/tasks` 连接。局域网真机浏览器已经可以访问开发电脑的 FastAPI `/docs`；`android.allowMixedContent=true` 已同步到 Android 工程，用于本地 HTTP 联调。

这项不再属于“地址缺失”阻断。重新安装最新构建后仍需在 App 内完成“保存并测试连接”，并单独验证 HTTP API 与 WebSocket。局域网 IP 由路由器动态分配，不应把某次测试地址视为正式部署地址。

### 2.5 冲突卡片“确认创建”持久化（已解决）

冲突卡片的“确认创建”现已调用统一的持久化动作：优先保存 `pending_task`，否则保存 `active_task`。只有创建接口返回 `code=0` 且包含真实 `task_id` 后，才清理冲突状态和关闭卡片；接口失败、业务错误或缺少任务 ID 时保留原卡片并允许重试。按钮在请求期间显示“创建中…”并禁止重复提交。前端生产构建已通过。

## 三、P0：部署前必须解决

### 3.1 Android 本地通知已接线，待真机验收

`@capacitor/local-notifications@8.3.1` 已加入依赖并同步到 Android 工程。当前代码已经完成：

- Android 13+ 通知显示授权和 Android 12+ 精确提醒设置引导；
- 创建任务后按 `30/10/5/0` 分钟注册通知；
- 删除、完成和过期时取消通知，恢复或改期时重建；
- 以 `task_id + offset_minutes` 生成稳定的 32 位通知 ID，并持久化映射；
- App 启动时以全部活动任务校准待触发通知，清理重复项；
- 依赖 Capacitor 原生恢复接收器处理手机重启后的已注册通知；
- Web 环境隔离，后端离线时不清空已恢复的系统通知。

尚未完成的是真机验收：前台、后台、息屏、断网、划掉进程、手机重启、权限拒绝和 vivo 省电策略都需要逐项验证。另因后端仍缺少任务编辑接口，用户可见的“改期保存”闭环尚未完成，当前只有通知重建能力可供未来编辑流程调用。

### 3.2 Android 系统通知监听第一版已实现，待真机验收

本地到点通知与系统通知监听是两项独立能力。当前工程已新增 `ScheduleNotificationListenerService`，在 Manifest 以 `BIND_NOTIFICATION_LISTENER_SERVICE` 注册，并通过 `SystemNotificationListener` Capacitor 插件连接前端。设置页可查询授权状态、跳转系统“通知使用权”页面，以及暂停或恢复监听。

第一版已经完成：

1. 原生 Service 提取包名、通知 key、时间、标题和正文，不保存完整通知对象。
2. 本机先排除自身通知、空内容、常驻/进度/系统通知、验证码与密码/账户类敏感内容，再以时间表达式预筛可能的日程文本。
3. 使用通知 key 与内容指纹执行两分钟窗口去重；后台或 WebView 不可用时写入最多 100 条的本地待处理队列。
4. App 前台通过 Bridge 投递，恢复前台时重放队列；解析成功或确定不是日程后确认出队，网络失败则保留重试。
5. 解析结果只进入现有候选/冲突状态，由用户确认后才创建正式日程。

后台候选链路已经接入：原生线程使用 App 设置中保存的后端地址调用 `/api/v1/task/parse`，优先走服务端大模型、失败时由服务端决定是否降级；成功响应写回本地队列并发送 Android 高优先级候选通知，点击或回到 App 后直接消费缓存结果，不重复调用模型。仍待完成：真机验证不同 App 的通知字段差异、通知更新、进程回收和横幅展示；增加按来源 App 开关和清空缓存；补充撤销事件处理。

### 3.3 “灵动岛”当前仅限 App 内部

现有 `ScheduleIsland.vue` 是 WebView 页面内组件，只有 App 可见且前端收到解析结果时才能展示。它不是 Android 系统悬浮窗，也不能调用 vivo 私有的“原子通知/系统灵动岛”。

推荐分两层交付：

- **第一层（推荐）：** App 前台展示现有灵动岛；App 后台使用 Android 高优先级横幅通知，点击后进入候选日程。
- **第二层（可选实验）：** 使用 `SYSTEM_ALERT_WINDOW`、前台服务和悬浮窗自绘胶囊。该方案权限敏感、耗电且受 vivo 后台策略影响，不作为 MVP 必选项。

### 3.4 手动输入未正确消费冲突结果

`handle_native_sniff()` 当前主要读取响应中的 `parsed`，而 `is_conflict`、`conflict` 和 `suggestions` 位于外层响应。手动输入可能已经被后端判定冲突，但前端仍按普通候选日程处理。

处理要求：统一 `handle_native_sniff()` 与 `sniffing_handler()` 的响应归一化逻辑，并为有冲突、无冲突和低置信度三种场景增加测试。

## 四、P1：能运行但不可靠或不适合发布

### 4.1 前后端缺少完整的日程更新闭环

前端已经调用 `PUT /api/v1/tasks/{task_id}`，后端没有对应路由。改期、修改地点以及本地通知重建无法闭环。

### 4.2 WebSocket 提醒存在丢失窗口

后端目前先写入 `reminded_offsets`，再发送 WebSocket。如果客户端离线或广播失败，会出现“数据库已标记提醒、用户实际未收到”的情况。

目标策略：Android 本地通知承担设备到点提醒；WebSocket 只承担前台状态刷新和跨端变更通知。

### 4.3 后端当前只适合单 worker

APScheduler 和 WebSocket 连接表均位于进程内。多个 Uvicorn worker 会导致：

- 每个进程各自运行调度器，可能重复提醒；
- WebSocket 客户端分散在不同进程，广播无法覆盖全部连接。

在调度器独立部署、引入共享消息总线或分布式锁之前，后端应保持单 worker。

### 4.4 生产配置未收口

部署时至少显式设置：

```env
DEBUG=false
LOG_LEVEL=INFO
APP_HOST=0.0.0.0
APP_PORT=8000
```

当前 `cors_origins` 配置没有真正传入 CORS 中间件；`allow_origins=["*"]` 仍为硬编码。

### 4.5 安全与隐私风险

- 后端没有用户认证或设备鉴权。
- Android 当前全局允许 HTTP 明文流量。
- CORS 允许全部来源。
- 日志记录用户原始文本、解析结果和部分 LLM 原始输出。
- 若后端端口暴露到公网，任何可访问者都可能读写任务。

正式发布前应使用 HTTPS/WSS、最小化 CORS、增加认证、脱敏日志，并设置日志保留和清理策略。

### 4.6 前端生产依赖告警

`npm audit --omit=dev` 当前报告两个高危生产依赖问题：

- `postcss`
- `nanoid`

二者均显示存在可用修复版本。升级后必须重新执行前端构建和 Android 构建回归。

### 4.7 SQLite 与部署运维

- 没有正式数据库迁移版本，当前依赖启动时 `ALTER TABLE` 并忽略重复字段异常。
- 没有备份、恢复和损坏处理流程。
- 多进程和高并发场景可能产生锁竞争。
- `.env.example` 当前缺失，新部署环境容易遗漏配置。

## 五、P2：正式发布前完善

- 将 `com.example.schedulehunter` 更换为正式且不可变的应用 ID。
- 配置正式签名证书、release signing、`versionCode` 和 `versionName`。
- 正式包关闭全局 `usesCleartextTraffic`，仅在 Debug 配置中允许必要的局域网 HTTP。
- 增加通知点击后的任务详情路由。
- 增加离线创建队列、幂等重放和同步失败提示。
- 增加 Android 端到端与真机测试。
- 部署前提交或保存当前工作区快照；当前存在大量未提交修改。

## 六、推荐实施顺序

1. 重新安装最新 Android 构建，完成 App 内 API/WS 连接和本地到点通知真机验收。
2. 在真机授权“通知使用权”，验证 Service → 本地队列 → Capacitor Bridge → 候选日程链路。
3. 增加来源 App 开关、清空捕获缓存和通知撤销处理。
4. 真机验收后台高优先级候选通知；确认是否确有必要再实验悬浮窗，不承诺接入厂商私有灵动岛。
5. 修复手动输入冲突字段映射，并补齐后端任务编辑/改期接口。
6. 覆盖监听权限拒绝、来源过滤、重复通知、更新通知、后台、息屏、断网、进程回收和重启测试。
7. 收口 HTTPS、认证、CORS、日志脱敏、依赖告警、签名和版本配置，最后完成 release 验收。

## 七、真机验收矩阵

| 场景 | 预期结果 |
|---|---|
| 手动输入无冲突日程 | 展示候选页，确认后仅创建一次 |
| 手动输入冲突日程 | 展示冲突证据，确认后真正写入数据库 |
| App 前台 | 到点展示系统通知并刷新灵动岛 |
| App 后台/息屏 | 系统通知按策略触发 |
| 断网 | 已注册本地通知仍触发 |
| 从最近任务划掉 App | 已注册本地通知仍触发 |
| 手机重启 | 启动或系统恢复后重新校准提醒 |
| 改期 | 旧通知取消，新通知按新时间触发 |
| 删除/完成 | 所有关联通知取消 |
| 拒绝通知权限 | 明确提示并保留站内提醒降级 |
| 拒绝精确提醒 | 使用非精确提醒并提示可能延迟 |
| 未授权通知使用权 | 不读取其他应用通知，保留手动输入/分享入口并显示授权引导 |
| 其他 App 发布普通日程通知 | 仅生成一个候选项，前台显示 App 内灵动岛 |
| 相同通知重复更新 | 不重复解析、不重复生成候选日程 |
| 监听到验证码或敏感通知 | 本地过滤，不发送到后端、不写入业务日志 |
| App 在后台监听到候选日程 | 使用标准高优先级通知提示，点击后进入候选页 |
| vivo 系统灵动岛 | 不承诺调用厂商私有能力；以 App 内灵动岛和标准横幅通知作为验收口径 |
