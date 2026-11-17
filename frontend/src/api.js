import axios from 'axios'
import { ElMessage } from 'element-plus'

// 同源留空；静态部署时由 VITE_API_BASE 指向后端服务
const API_BASE = import.meta.env.VITE_API_BASE || ''
const http = axios.create({ baseURL: API_BASE, timeout: 600000 })

http.interceptors.response.use(
  r => r.data,
  async err => {
    // 二进制响应（格式转换）出错时 body 是 Blob，需先读出 JSON 才能拿到后端的中文原因
    let msg = err.response?.data?.detail || err.message || '请求失败'
    if (err.response?.data instanceof Blob) {
      try {
        const text = await err.response.data.text()
        msg = JSON.parse(text)?.detail || text.slice(0, 200) || msg
      } catch { /* 保留原始信息 */ }
    }
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(err)
  }
)

// ---- 文件 ----
export const uploadFile = (file) => {
  const fd = new FormData(); fd.append('file', file)
  return http.post('/api/upload', fd)
}
export const parseText = (text, title) => {
  const fd = new FormData(); fd.append('text', text); fd.append('title', title)
  return http.post('/api/parse-text', fd)
}
export const generate = (data) => http.post('/api/generate', data)  // 返回 {job_id}
export const generateProgress = (jobId) => http.get(`/api/generate/progress/${jobId}`)

// 启动生成任务并轮询进度直至完成；onProgress(progress 0-100, message, elapsed) 实时回调
export async function generateWait(data, onProgress) {
  const { job_id } = await generate(data)
  const t0 = Date.now()                       // 本地计时兜底：服务器 elapsed 异常时也能正常走秒
  let lastP = 0
  while (true) {
    await new Promise(r => setTimeout(r, 1500))
    const p = await generateProgress(job_id)
    const elapsed = Math.max(p.elapsed || 0, (Date.now() - t0) / 1000)
    // 生成阶段（10~86%）按真实耗时平滑插值，避免进度条长时间停滞
    let display = p.percent
    if (p.stage === 'design') {
      const t = Math.min(elapsed / 210, 1)          // 预计 210 秒到顶
      display = Math.min(86, 10 + t * 72)
      lastP = Math.max(lastP, display)
    } else if (p.percent > 0) {
      lastP = Math.max(lastP, p.percent)
    }
    onProgress?.(Math.round(display), p.message, elapsed)
    if (p.status === 'done') return p.result
    if (p.status === 'failed') throw new Error(p.error || '生成失败')
  }
}
export const summarize = (data) => http.post('/api/summarize', data)
export const insight = (data) => http.post('/api/insight', data)
export const previewUrl = (id) => `${API_BASE}/api/preview/${id}`

// ---- 记录 ----
export const history = (params) => http.get('/api/history', { params })
export const trashList = () => http.get('/api/trash')
export const toggleFav = (id) => http.post(`/api/records/${id}/favorite`)
export const toTrash = (id) => http.delete(`/api/records/${id}`)
export const restore = (id) => http.post(`/api/records/${id}/restore`)
export const purge = (id) => http.delete(`/api/records/${id}/purge`)
export const share = (id) => http.post(`/api/records/${id}/share`)
export const exportUrl = (id) => `${API_BASE}/api/records/${id}/export`

// ---- 模型 ----
export const listModels = () => http.get('/api/models')
export const addModel = (d) => http.post('/api/models', d)
export const delModel = (id) => http.delete(`/api/models/${id}`)
export const setDefault = (id) => http.post(`/api/models/${id}/default`)
export const probe = (d) => http.post('/api/models/probe', d)
export const builtinInfo = () => http.get('/api/models/builtin-info')

// ---- 设置 / 案例 / 转换 ----
export const getSettings = () => http.get('/api/settings')
export const saveSettings = (d) => http.post('/api/settings', d)
export const getCases = () => http.get('/api/cases')
export const convertTargets = (ext) => http.get('/api/convert/targets', { params: { ext } })
export const convertFile = (file, target) => {
  const fd = new FormData(); fd.append('file', file); fd.append('target', target)
  return http.post('/api/convert', fd, { responseType: 'blob' })
}

// ---- 简历转化 ----
export const getResumeProfile = () => http.get('/api/resume/profile')
export const saveResumeProfile = (d) => http.post('/api/resume/profile', d)
export const resumeOptimize = (d) => http.post('/api/resume/optimize', d)
export const resumeGenerate = (d) => http.post('/api/resume/generate', d)
export const resumeDocxUrl = (id) => `${API_BASE}/api/resume/records/${id}/export/docx`
