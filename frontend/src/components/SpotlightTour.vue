<template>
  <Teleport to="body">
    <div v-if="visible" class="tour-mask">
      <!-- 高亮框：跟随目标元素移动 -->
      <div class="tour-hole" :style="holeStyle"></div>
      <!-- 讲解卡片 -->
      <div class="tour-card" :style="cardStyle">
        <div class="tour-step-tag">第 {{ step + 1 }} / {{ steps.length }} 步</div>
        <div class="tour-title">{{ current.title }}</div>
        <div class="tour-desc">{{ current.desc }}</div>
        <div class="tour-actions">
          <el-button size="small" round @click="prev" :disabled="step === 0">上一步</el-button>
          <el-button size="small" type="primary" round @click="next">
            {{ step === steps.length - 1 ? '完成' : '下一步' }}
          </el-button>
          <div class="tour-dots">
            <i v-for="(s, i) in steps" :key="i" :class="{ on: i === step }"></i>
          </div>
          <div class="tour-skip" role="button" tabindex="0" @click="finish" @keyup.enter="finish">跳过引导</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// 首次访问聚光灯引导：半透明遮罩挖洞高亮目标区域，逐区讲解。
// 健壮性：目标元素可能因模块未激活而缺失 → 先切模块再等渲染，找不到则跳过该步；
// 窗口缩放/滚动时重新计算位置；ESC 可退出。
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const visible = ref(false)
const step = ref(0)
const hole = ref({ top: 0, left: 0, width: 0, height: 0 })
const card = ref({ top: 0, left: 0 })

const steps = [
  { sel: '.brand-chip', title: '这里是品牌区', desc: '随时可以看到当前站点身份。旁边浮坞是全部功能的入口。' },
  { sel: '.dock', title: '浮坞导航：全部功能入口', desc: '14 个功能模块按「输入 → 分析设计 → 管理」分三组排列，点击图标切换，悬停有放大反馈。' },
  { sel: '.status-chip', title: '状态浮标', desc: '实时显示模型接入状态与当前主题；点主题徽标可直达模板中心，随时可重放本引导。' },
  { sel: '.island-feature', title: '功能面板：操作都从这里发起', desc: '上传、转换、教程……当前选中模块的操作区。新来的话先到「新手教程」走一遍三分钟入门。' },
  { sel: '.island-doc', title: '解析原文：确认内容再生成', desc: '上传解析后的全文与统计信息展示在这里，确认无误后点「生成可视化」。' },
  { sel: '.island-preview', title: '可视化结果：主舞台', desc: '生成的可视化页面在此展示，支持缩放、刷新、导出 PDF 与公开分享。' },
]

const current = computed(() => steps[step.value])

function locate() {
  const el = document.querySelector(steps[step.value].sel)
  if (!el) { nextStep(); return }
  const r = el.getBoundingClientRect()
  hole.value = { top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 }
  // 卡片默认放高亮框下方，放不下则放上方；横向夹在视口内
  const below = r.bottom + 16
  const ch = 190
  card.value = {
    top: below + ch > window.innerHeight - 12 ? Math.max(12, r.top - ch - 16) : below,
    left: Math.min(Math.max(12, r.left), window.innerWidth - 302),
  }
}

const holeStyle = computed(() => ({
  top: hole.value.top + 'px', left: hole.value.left + 'px',
  width: hole.value.width + 'px', height: hole.value.height + 'px',
}))
const cardStyle = computed(() => ({ top: card.value.top + 'px', left: card.value.left + 'px' }))

function next() { step.value === steps.length - 1 ? finish() : (step.value++, locate()) }
function prev() { if (step.value > 0) { step.value--, locate() } }
function nextStep() {
  if (step.value < steps.length - 1) { step.value++; locate() } else finish()
}
function finish() {
  visible.value = false
  try { localStorage.setItem('uv-tour-done', '1') } catch { /* ignore */ }
}
function start() {
  step.value = 0
  visible.value = true
  nextTick(locate)
}

function onKey(e) { if (visible.value && e.key === 'Escape') finish() }
function onRe() { if (visible.value) locate() }

onMounted(() => {
  window.__uvStartTour = start
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onRe)
  // 首次进入工作台自动弹出
  try { if (!localStorage.getItem('uv-tour-done')) setTimeout(start, 900) } catch { /* ignore */ }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onRe)
})
watch(visible, v => { if (v) nextTick(locate) })
</script>
