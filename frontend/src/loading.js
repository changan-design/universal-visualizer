// 全局海浪加载层：任何等待操作（上传解析 / 格式转换 / 摘要洞察 / 批量等）统一唤起，
// 全屏毛玻璃遮罩 + 海浪拍岸动画，防止用户在等待期间重复操作。
import { reactive } from 'vue'

export const waveLoading = reactive({
  visible: false,
  text: '',
  sub: '',
  count: 0,        // 支持并发调用：最后一个 hide 才真正关闭
})

export function waveShow(text = '处理中…', sub = '') {
  waveLoading.count++
  waveLoading.text = text
  waveLoading.sub = sub
  waveLoading.visible = true
}

export function waveHide() {
  waveLoading.count = Math.max(0, waveLoading.count - 1)
  if (waveLoading.count === 0) waveLoading.visible = false
}

// 包装异步任务：自动显示/关闭海浪加载层
export async function withWave(text, sub, fn) {
  waveShow(text, sub)
  try {
    return await fn()
  } finally {
    waveHide()
  }
}
