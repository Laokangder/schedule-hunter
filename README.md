# Schedule Hunter

日程猎人 - 智能日程管理 App

## 项目结构

```
schedule-hunter/
├── frontend/          # 前端 (Vue 3 + Uni-app)
│   ├── src/
│   │   ├── components/
│   │   │   └── Island/ScheduleIsland.vue
│   │   ├── stores/useTaskStore.js
│   │   └── services/apiService.js
│   ├── package.json
│   └── vite.config.js
├── backend/           # 后端 (FastAPI)
│   ├── main.py
│   ├── requirements.txt
│   └── .env
└── README.md
```

## 技术栈

### 前端
- Vue 3 (Composition API)
- Tailwind CSS
- Pinia
- Uni-app

### 后端
- FastAPI
- Python 3.10+
- SQLite

## 快速开始

### 前端
```bash
cd frontend
npm install
npm run dev
```

### 后端
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
