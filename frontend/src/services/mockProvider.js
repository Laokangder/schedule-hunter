const MOCK_SCENARIOS = {
  normal: {
    request_id: "req_20260420_0001",
    source_text: "明天下午三点去望京 SOHO 找张总谈合作",
    context: {
      recent_tasks: [],
      user_preferences: {
        default_duration_minutes: 60,
        timezone: "Asia/Shanghai"
      }
    },
    meta: {
      input_type: "notification",
      client_timestamp: "2026-04-20T16:30:00+08:00",
      app_version: "1.0.0"
    }
  },
  conflict: {
    request_id: "req_20260420_0002",
    source_text: "明天下午两点拜访李总",
    context: {
      recent_tasks: [
        {
          task_id: "task_991200",
          title: "产品评审会",
          start_time: "2026-04-21T14:00:00+08:00",
          end_time: "2026-04-21T15:30:00+08:00"
        }
      ],
      user_preferences: {
        default_duration_minutes: 60,
        timezone: "Asia/Shanghai"
      }
    },
    meta: {
      input_type: "clipboard",
      client_timestamp: "2026-04-20T16:35:00+08:00",
      app_version: "1.0.0"
    }
  },
  ambiguous: {
    request_id: "req_20260420_0003",
    source_text: "下周开会",
    context: {
      recent_tasks: [],
      user_preferences: {
        default_duration_minutes: 60,
        timezone: "Asia/Shanghai"
      }
    },
    meta: {
      input_type: "intent",
      client_timestamp: "2026-04-20T16:40:00+08:00",
      app_version: "1.0.0"
    }
  }
}

const MOCK_RESPONSES = {
  normal: {
    code: 0,
    message: "parsed",
    data: {
      parsed: {
        title: "与张总在望京 SOHO 谈合作",
        start_time: "2026-04-21T15:00:00+08:00",
        end_time: "2026-04-21T16:00:00+08:00",
        location: "望京 SOHO",
        participants: ["张总"],
        timezone: "Asia/Shanghai",
        confidence: 0.94
      },
      is_conflict: false,
      conflict: null,
      suggestions: [
        {
          action: "reschedule",
          suggested_time: "2026-04-21T16:30:00+08:00",
          description: "推迟 1.5 小时避免与午休时间重叠"
        }
      ],
      needs_confirmation: false,
      ambiguities: []
    },
    trace_id: "trace_20260420_aaa001"
  },
  conflict_time_overlap: {
    code: 0,
    message: "parsed",
    data: {
      parsed: {
        title: "拜访李总",
        start_time: "2026-04-21T14:00:00+08:00",
        end_time: "2026-04-21T15:00:00+08:00",
        location: "客户公司",
        participants: ["李总"],
        timezone: "Asia/Shanghai",
        confidence: 0.87
      },
      is_conflict: true,
      conflict: {
        conflict_type: "time_overlap",
        conflict_level: "high",
        conflicting_task_id: "task_991200",
        detail: "14:00-15:00 与「产品评审会」时间完全重叠"
      },
      suggestions: [
        {
          action: "reschedule",
          suggested_time: "2026-04-21T16:30:00+08:00",
          description: "推迟 2.5 小时避免重叠"
        },
        {
          action: "shorten",
          suggested_duration_minutes: 45,
          description: "压缩至 45 分钟，留出缓冲"
        },
        {
          action: "dismiss",
          description: "忽略此次检测，不创建任务"
        }
      ],
      needs_confirmation: true,
      ambiguities: []
    },
    trace_id: "trace_20260420_aaa002"
  },
  conflict_travel: {
    code: 0,
    message: "parsed",
    data: {
      parsed: {
        title: "北京出差会议",
        start_time: "2026-04-22T09:00:00+08:00",
        end_time: "2026-04-22T11:00:00+08:00",
        location: "北京国际会议中心",
        participants: ["王总", "赵总"],
        timezone: "Asia/Shanghai",
        confidence: 0.91
      },
      is_conflict: true,
      conflict: {
        conflict_type: "travel_conflict",
        conflict_level: "medium",
        conflicting_task_id: "task_882100",
        detail: "上一场会议在望京 SOHO 结束时间 08:45，与本会议地点相距 25 公里，预计出行时间 50 分钟"
      },
      suggestions: [
        {
          action: "reschedule",
          suggested_time: "2026-04-22T10:30:00+08:00",
          description: "推迟 1.5 小时，留出充足出行时间"
        },
        {
          action: "dismiss",
          description: "忽略此次检测，不创建任务"
        }
      ],
      needs_confirmation: false,
      ambiguities: []
    },
    trace_id: "trace_20260420_aaa003"
  },
  conflict_priority: {
    code: 0,
    message: "parsed",
    data: {
      parsed: {
        title: "周会汇报",
        start_time: "2026-04-23T14:00:00+08:00",
        end_time: "2026-04-23T15:00:00+08:00",
        location: "总部会议室 A",
        participants: ["全体同事"],
        timezone: "Asia/Shanghai",
        confidence: 0.89
      },
      is_conflict: true,
      conflict: {
        conflict_type: "priority_conflict",
        conflict_level: "high",
        conflicting_task_id: "task_773300",
        detail: "「季度评审」为高优先级任务，不能被「周会汇报」打断"
      },
      suggestions: [
        {
          action: "reschedule",
          suggested_time: "2026-04-23T16:00:00+08:00",
          description: "推迟 2 小时，在季度评审结束后进行"
        },
        {
          action: "shorten",
          suggested_duration_minutes: 30,
          description: "压缩至 30 分钟快速汇报"
        },
        {
          action: "dismiss",
          description: "忽略此次检测，不创建任务"
        }
      ],
      needs_confirmation: true,
      ambiguities: []
    },
    trace_id: "trace_20260420_aaa004"
  },
  ambiguous: {
    code: 0,
    message: "parsed",
    data: {
      parsed: {
        title: null,
        start_time: null,
        end_time: null,
        location: null,
        participants: [],
        timezone: "Asia/Shanghai",
        confidence: 0.35
      },
      is_conflict: false,
      conflict: null,
      suggestions: [],
      needs_confirmation: true,
      ambiguities: ["title", "start_time"]
    },
    trace_id: "trace_20260420_aaa005"
  }
}

const MOCK_TASKS = [
  {
    task_id: "task_001001",
    title: "与张总在望京 SOHO 谈合作",
    start_time: "2026-04-21T15:00:00+08:00",
    end_time: "2026-04-21T16:00:00+08:00",
    status: "scheduled",
    reminder_state: "counting_down",
    location: "望京 SOHO",
    participants: ["张总"],
    priority: "normal"
  },
  {
    task_id: "task_001002",
    title: "产品评审会议",
    start_time: "2026-04-21T14:00:00+08:00",
    end_time: "2026-04-21T15:30:00+08:00",
    status: "scheduled",
    reminder_state: "idle",
    location: "望京 SOHO T3",
    participants: ["产品团队"],
    priority: "high"
  },
  {
    task_id: "task_001003",
    title: "客户需求沟通",
    start_time: "2026-04-22T10:00:00+08:00",
    end_time: "2026-04-22T11:00:00+08:00",
    status: "scheduled",
    reminder_state: "idle",
    location: "线上会议",
    participants: ["客户方"],
    priority: "normal"
  }
]

const MOCK_CONFLICT_CHECK = {
  has_conflict: true,
  conflicts: [
    {
      task_id: "task_991200",
      conflict_type: "time_overlap",
      conflict_level: "high",
      detail: "14:00-15:00 与已有会议重叠",
      suggestions: [
        "自动改期到 16:30",
        "保留新任务并取消旧任务",
        "拆分为提醒类事项"
      ]
    }
  ],
  ai_summary: "该日程与现有会议存在直接时间重叠，建议改期或调整时长。"
}

function generate_request_id() {
  const now = new Date()
  const date_str = now.toISOString().slice(0, 10).replace(/-/g, '')
  const random = Math.random().toString(36).substr(2, 6)
  return `req_${date_str}_${random}`
}

function generate_trace_id() {
  const now = new Date()
  const date_str = now.toISOString().slice(0, 10).replace(/-/g, '')
  const random = Math.random().toString(36).substr(2, 6)
  return `trace_${date_str}_${random}`
}

export async function mock_parse_text(request_body) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const text = request_body.source_text || request_body.text || ""
      let response

      if (text.includes("下周")) {
        response = { ...MOCK_RESPONSES.ambiguous }
        response.trace_id = generate_trace_id()
      } else if (text.includes("出差") || text.includes("北京")) {
        response = { ...MOCK_RESPONSES.conflict_travel }
        response.trace_id = generate_trace_id()
      } else if (text.includes("周会")) {
        response = { ...MOCK_RESPONSES.conflict_priority }
        response.trace_id = generate_trace_id()
      } else if (text.includes("两点") || text.includes("14:")) {
        response = { ...MOCK_RESPONSES.conflict_time_overlap }
        response.trace_id = generate_trace_id()
      } else {
        response = { ...MOCK_RESPONSES.normal }
        response.trace_id = generate_trace_id()
        response.data.parsed.start_time = get_future_time(1, "hour")
        response.data.parsed.end_time = get_future_time(2, "hour")
      }

      resolve({ success: true, data: response })
    }, 600 + Math.random() * 400)
  })
}

export async function mock_fetch_tasks(date, status) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const target_date = date || new Date().toISOString().slice(0, 10)
      const filtered_tasks = MOCK_TASKS.filter(task => {
        const task_date = task.start_time.slice(0, 10)
        return task_date === target_date
      })

      const nearest_task = filtered_tasks.find(task => {
        const start = new Date(task.start_time).getTime()
        return start > Date.now()
      })

      let island_state = {
        mode: "silent",
        display_text: "",
        severity: "info"
      }

      if (nearest_task) {
        const start = new Date(nearest_task.start_time).getTime()
        const diff = start - Date.now()
        const hours = Math.floor(diff / 3600000)
        const minutes = Math.floor((diff % 3600000) / 60000)

        if (diff > 30 * 60 * 1000) {
          island_state = {
            mode: "countdown",
            display_text: `还有 ${hours}h ${minutes}m`,
            severity: "info"
          }
        } else if (diff > 0) {
          island_state = {
            mode: "countdown",
            display_text: `还有 ${minutes}m`,
            severity: "warning"
          }
        } else {
          island_state = {
            mode: "reminder",
            display_text: "即将开始",
            severity: "urgent"
          }
        }
      }

      resolve({
        success: true,
        data: {
          code: 0,
          message: "ok",
          data: {
            tasks: filtered_tasks.length > 0 ? filtered_tasks : MOCK_TASKS,
            island_state: island_state
          },
          trace_id: generate_trace_id()
        }
      })
    }, 400)
  })
}

export async function mock_create_task(request_body) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const task_id = `task_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`
      const parsed = request_body.parsed || {}

      resolve({
        success: true,
        data: {
          code: 0,
          message: "created",
          data: {
            task_id: task_id,
            status: "scheduled",
            normalized: {
              start_time: parsed.start_time || get_future_time(1, "hour"),
              end_time: parsed.end_time || get_future_time(2, "hour")
            },
            is_conflict: request_body.is_conflict || false
          },
          trace_id: generate_trace_id()
        }
      })
    }, 300)
  })
}

export async function mock_check_conflict(candidate, scope) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const has_conflict = Math.random() > 0.4
      const conflict_types = ["time_overlap", "travel_conflict", "priority_conflict"]
      const conflict_type = conflict_types[Math.floor(Math.random() * conflict_types.length)]

      if (has_conflict) {
        resolve({
          success: true,
          data: {
            code: 0,
            message: "checked",
            data: {
              ...MOCK_CONFLICT_CHECK,
              conflicts: [{
                ...MOCK_CONFLICT_CHECK.conflicts[0],
                conflict_type: conflict_type,
                conflict_level: Math.random() > 0.5 ? "high" : "medium"
              }]
            },
            trace_id: generate_trace_id()
          }
        })
      } else {
        resolve({
          success: true,
          data: {
            code: 0,
            message: "checked",
            data: {
              has_conflict: false,
              conflicts: [],
              ai_summary: "未检测到冲突，日程安排合理。"
            },
            trace_id: generate_trace_id()
          }
        })
      }
    }, 400)
  })
}

function get_future_time(hours, unit) {
  const now = new Date()
  if (unit === "hour") {
    now.setHours(now.getHours() + hours)
  } else if (unit === "day") {
    now.setDate(now.getDate() + hours)
  }
  return now.toISOString()
}

export { MOCK_SCENARIOS, MOCK_RESPONSES, MOCK_TASKS }
