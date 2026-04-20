const MOCK_TASKS = {
  normal: [
    {
      id: 'mock_001',
      title: '产品评审会议',
      start_time: '2026-04-20T14:00:00.000Z',
      end_time: '2026-04-20T15:30:00.000Z',
      location: '望京 SOHO T3',
      is_conflict: false,
      has_warning: false,
      difficulty: 'easy'
    },
    {
      id: 'mock_002',
      title: '技术方案评审',
      start_time: '2026-04-21T10:00:00.000Z',
      end_time: '2026-04-21T11:30:00.000Z',
      location: '中关村软件园',
      is_conflict: false,
      has_warning: false,
      difficulty: 'medium'
    },
    {
      id: 'mock_003',
      title: '客户需求沟通',
      start_time: '2026-04-22T15:00:00.000Z',
      end_time: '2026-04-22T16:00:00.000Z',
      location: '线上会议',
      is_conflict: false,
      has_warning: false,
      difficulty: 'easy'
    }
  ],
  conflict: [
    {
      id: 'mock_101',
      title: '客户演示',
      start_time: '2026-04-20T15:00:00.000Z',
      end_time: '2026-04-20T16:00:00.000Z',
      location: '客户公司',
      is_conflict: true,
      has_warning: true,
      difficulty: 'hard',
      conflict_with: 'mock_001',
      conflict_detail: '与"产品评审会议"时间重叠'
    },
    {
      id: 'mock_102',
      title: '紧急问题修复',
      start_time: '2026-04-21T10:00:00.000Z',
      end_time: '2026-04-21T12:00:00.000Z',
      location: '远程',
      is_conflict: true,
      has_warning: true,
      difficulty: 'hard',
      conflict_with: 'mock_002',
      conflict_detail: '与"技术方案评审"时间重叠'
    }
  ],
  overnight: [
    {
      id: 'mock_201',
      title: '项目交付冲刺',
      start_time: '2026-04-20T22:00:00.000Z',
      end_time: '2026-04-21T06:00:00.000Z',
      location: '公司',
      is_conflict: false,
      has_warning: true,
      difficulty: 'hard',
      is_overnight: true
    },
    {
      id: 'mock_202',
      title: '国际会议',
      start_time: '2026-04-21T22:00:00.000Z',
      end_time: '2026-04-22T02:00:00.000Z',
      location: '线上',
      is_conflict: false,
      has_warning: true,
      difficulty: 'medium',
      is_overnight: true
    }
  ]
}

const AI_SUGGESTIONS = [
  '建议将会议提前30分钟，避免与午休时间冲突',
  '考虑将任务拆分，选择时间冲突较少的时段执行',
  '此任务与您的专注时间重叠，建议调整优先级',
  '检测到可能的疲劳时段，建议安排休息',
  '任务难度较高，建议预留更多缓冲时间'
]

function generateRandomId() {
  return `mock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

function getRandomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateAIDetail() {
  return getRandomItem(AI_SUGGESTIONS)
}

function parseNaturalLanguage(text) {
  const now = new Date()
  let hoursLater = 1
  let title = text
  let hasTime = false

  const timePatterns = [
    /(\d{1,2})点(\d{0,2})?/,
    /(\d{1,2}):(\d{2})/,
    /(\d{1,2})\s*[Hh]/,
    /下午(\d{1,2})/,
    /上午(\d{1,2})/,
    /明天(\d{1,2})/
  ]

  for (const pattern of timePatterns) {
    const match = text.match(pattern)
    if (match) {
      hasTime = true
      if (pattern.source.includes('下午') && match[1]) {
        hoursLater = parseInt(match[1]) + 12 - now.getHours()
      } else if (pattern.source.includes('上午') && match[1]) {
        hoursLater = parseInt(match[1]) - now.getHours()
      } else if (match[1]) {
        hoursLater = parseInt(match[1]) - now.getHours()
        if (hoursLater < 0) hoursLater += 24
      }
      break
    }
  }

  const locationPatterns = [
    /在([^。,，]+)/,
    /(?:在|位于)([^。,，]+)/,
    /([^。,，]+)举行/
  ]

  let location = ''
  for (const pattern of locationPatterns) {
    const match = text.match(pattern)
    if (match) {
      location = match[1].trim()
      title = text.replace(match[0], '').trim()
      break
    }
  }

  return {
    title: title || '新任务',
    start_time: new Date(now.getTime() + hoursLater * 3600000).toISOString(),
    end_time: new Date(now.getTime() + (hoursLater + 1) * 3600000).toISOString(),
    location: location,
    confidence: 0.85 + Math.random() * 0.15,
    has_warning: hoursLater < 2,
    is_conflict: Math.random() > 0.7,
    ai_suggestion: generateAIDetail()
  }
}

export async function mockParseText(rawText) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const parsed = parseNaturalLanguage(rawText)
      const isConflict = parsed.is_conflict

      resolve({
        success: true,
        data: {
          parsed: {
            ...parsed,
            id: generateRandomId()
          },
          is_conflict: isConflict,
          conflict: isConflict ? {
            detail: '检测到与其他日程存在时间冲突',
            suggestions: [
              generateAIDetail(),
              '建议延后30分钟'
            ]
          } : null
        }
      })
    }, 800 + Math.random() * 400)
  })
}

export async function mockFetchTasks() {
  return new Promise((resolve) => {
    setTimeout(() => {
      const allTasks = [
        ...MOCK_TASKS.normal,
        ...MOCK_TASKS.conflict,
        ...MOCK_TASKS.overnight
      ]
      resolve({
        success: true,
        data: allTasks
      })
    }, 500)
  })
}

export async function mockSyncCalendar(month) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const tasks = mockFetchTasks().then(r => r.data)
      resolve({
        success: true,
        data: {
          month,
          tasks: tasks,
          summary: {
            total: 8,
            conflicts: 2,
            warnings: 3
          }
        }
      })
    }, 600)
  })
}

export async function mockCheckConflict(task) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const hasConflict = Math.random() > 0.5
      resolve({
        success: true,
        data: {
          conflict: hasConflict ? {
            detail: '与现有日程存在时间冲突',
            suggestions: [
              generateAIDetail()
            ]
          } : null
        }
      })
    }, 300)
  })
}

export { MOCK_TASKS }
