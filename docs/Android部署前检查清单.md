# 日程猎人 Android 部署前检查清单

> 审计日期：2026-09-24
> 适用范围：当前 Vue 3 + Capacitor 8 Android 容器与 FastAPI 后端
> 结论：前端生产构建、后端基础集成测试、Android Debug APK 构建和 APK 后端地址配置已完成；当前主要阻断为本地通知业务接线和冲突确认闭环，暂不建议直接发布。

## 一、已验证通过

| 检查项 | 结果 | 说明 |
|---|---|---|
| 前端生产构建 | ✅ 通过 | Vite 成功构建 34 个模块 |
| Python 语法检查 | ✅ 通过 | `compileall` 未发现语法错误 |
| 后端依赖导入 | ✅ 通过 | 项目 `.venv` 可导入 FastAPI、Pydantic、httpx、APScheduler 和 regex |
| 后端集成测试 | ✅ 5/5 通过 | 覆盖 CRUD、冲突、降级解析、提醒策略和过期处理 |
| Android APK 构建 | ✅ 通过 | Gradle Daemon 固定使用 Android Studio JDK 21，Debug APK 已成功生成 |
| Capacitor 原生同步 | ✅ 通过 | Web 资源已复制，本地通知插件已进入 Android 工程 |
| APK 后端地址 | ✅ 已配置 | 生产构建已写入局域网后端地址，并支持用户在设置页覆盖 |
| 真实 DS LLM 调用 | ✅ 通过 | `deepseek-flash` 返回 HTTP 200，解析结果 `ai_fallback=false` |

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

`frontend/.env.production` 已设置 `VITE_NATIVE_API_BASE_URL=http://192.168.1.104:8000`。生产构建产物和 Android Web 资源中均已包含该地址；App 设置页还支持保存并测试其他后端地址，WebSocket 会根据 API 地址自动生成 `/ws/tasks` 连接。

这项不再属于“地址缺失”阻断。仍需在后端服务运行时完成真机连通验收，确认手机与服务器网络互通、防火墙已放行，并验证 HTTP API 与 WebSocket 都可连接。本次文档更新时从开发电脑探测该端口得到“连接被拒绝”，因此只确认配置已进入构建，未把在线可达性标记为通过。

## 三、P0：部署前必须解决

### 3.1 Android 本地通知尚未接线

`@capacitor/local-notifications@8.3.1` 已加入依赖并同步到 Android 工程。合并 Manifest 已包含 `POST_NOTIFICATIONS`、`SCHEDULE_EXACT_ALARM` 和 `RECEIVE_BOOT_COMPLETED`；但业务层仍未完成：

- Android 13+ 运行时通知授权；
- Android 12+ 精确提醒能力检查与设置引导；
- 创建任务后按 `30/10/5/0` 分钟注册本地通知；
- 改期时取消旧通知并重建；
- 删除、完成和过期时取消关联通知；
- App 启动、恢复前台和手机重启后的通知校准；
- Web 环境的 `Capacitor.isNativePlatform()` 隔离；
- 本地通知与 WebSocket 提醒去重。

未完成以上链路前，后台、息屏、断网或进程回收场景不能保证提醒送达。

### 3.2 手动输入未正确消费冲突结果

`handle_native_sniff()` 当前主要读取响应中的 `parsed`，而 `is_conflict`、`conflict` 和 `suggestions` 位于外层响应。手动输入可能已经被后端判定冲突，但前端仍按普通候选日程处理。

处理要求：统一 `handle_native_sniff()` 与 `sniffing_handler()` 的响应归一化逻辑，并为有冲突、无冲突和低置信度三种场景增加测试。

### 3.3 冲突卡片“确认创建”未持久化

当前冲突卡片的“确认创建”只清除冲突标志并切换为 `tracking`，没有调用创建接口。用户会看到类似创建成功的状态，但数据库中可能没有该任务。

处理要求：确认操作必须调用唯一的任务创建动作；创建成功后再切换状态，失败时保留候选数据和错误提示。

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

1. 修复手动输入冲突映射和冲突确认持久化。
2. 补齐后端任务更新接口。
3. 完成 Android 本地通知权限、注册、取消、改期、恢复和去重逻辑。
4. 重新执行 `npm run build`、`npx cap sync android` 和 Debug APK 构建。
5. 在后端运行时完成真机 API/WS 网络连通测试。
6. 真机覆盖前台、后台、息屏、断网、进程回收和重启场景。
7. 收口 HTTPS、认证、CORS、日志、依赖告警、签名和版本配置。
8. 完成 release 构建与安装验收。

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
