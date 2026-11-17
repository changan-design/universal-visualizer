<template>
  <!-- 首页进入页：真实海浪拍岸视频入场 -->
  <Transition name="ld-fade">
    <LandingPage v-if="!entered" @enter="entered = true" />
  </Transition>

  <template v-if="entered">
  <!-- 背景：海洋渐变 + 浮沫 + 颗粒 -->
  <div class="bg-ocean" aria-hidden="true"></div>
  <div class="bg-foam" aria-hidden="true"><i v-for="n in 10" :key="n" :style="foamStyle(n)"></i></div>
  <div class="bg-grain" aria-hidden="true"></div>

  <div class="layout" :class="{ 'resume-mode': activeModule === 'resume' }">
    <!-- ===== 顶栏：品牌浮标 + 浮坞导航 + 状态浮标 ===== -->
    <header class="topbar">
      <div class="chip brand-chip">
        <div class="logo">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
            <defs>
              <linearGradient id="prism-g" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dfe6ff"/>
              </linearGradient>
            </defs>
            <path d="M12 2.4 L21 12 L12 21.6 L3 12 Z" fill="url(#prism-g)" opacity=".92"/>
            <path d="M12 6.8 L16.4 12 L12 17.2 L7.6 12 Z" fill="url(#prism-g)" opacity=".55"/>
            <path d="M12 9.4 L14.4 12 L12 14.6 L9.6 12 Z" fill="#4f6ef7"/>
            <circle cx="20.2" cy="4.6" r="1.5" fill="#8be9ff"/>
          </svg>
        </div>
        <div>
          <div class="brand-name">万能可视化</div>
          <div class="brand-sub">UNIVERSAL VISUALIZER</div>
        </div>
      </div>

      <!-- 浮坞：分组图标导航，点击涟漪反馈 -->
      <div class="dock-wrap">
        <nav class="dock" aria-label="功能导航">
          <div v-for="m in dockGroups[0]" :key="m.key" class="dock-item"
               :class="{ active: activeModule === m.key }" role="button" tabindex="0"
               :aria-label="m.label" :title="m.label"
               @click="switchModule(m.key, $event)" @keyup.enter="switchModule(m.key, $event)">
            <span class="di-icon"><el-icon><component :is="m.icon" /></el-icon></span>
            <span class="di-label">{{ m.short || m.label }}</span>
          </div>
          <span class="dock-sep"></span>
          <div v-for="m in dockGroups[1]" :key="m.key" class="dock-item"
               :class="{ active: activeModule === m.key }" role="button" tabindex="0"
               :aria-label="m.label" :title="m.label"
               @click="switchModule(m.key, $event)" @keyup.enter="switchModule(m.key, $event)">
            <span class="di-icon"><el-icon><component :is="m.icon" /></el-icon></span>
            <span class="di-label">{{ m.short || m.label }}</span>
          </div>
          <span class="dock-sep"></span>
          <div v-for="m in dockGroups[2]" :key="m.key" class="dock-item"
               :class="{ active: activeModule === m.key }" role="button" tabindex="0"
               :aria-label="m.label" :title="m.label"
               @click="switchModule(m.key, $event)" @keyup.enter="switchModule(m.key, $event)">
            <span class="di-icon"><el-icon><component :is="m.icon" /></el-icon></span>
            <span class="di-label">{{ m.short || m.label }}</span>
          </div>
        </nav>
      </div>

      <!-- 状态浮标：模型 + 当前主题（实时联动） + 教程入口 -->
      <div class="chip status-chip">
        <span class="dot" aria-hidden="true"></span>
        <span class="sc-model-text">{{ currentModelName }}</span>
        <span class="sc-sep" aria-hidden="true"></span>
        <span class="theme-badge" :class="{ flash: themeFlash }" role="button" tabindex="0"
              :title="'当前主题：' + currentThemeName + '，点击前往模板中心'"
              @click="switchModule('template')" @keyup.enter="switchModule('template')">
          {{ currentThemeEmoji }} {{ currentThemeName }}
        </span>
        <span class="sc-sep" aria-hidden="true"></span>
        <span class="tour-btn" role="button" tabindex="0" title="交互式新手引导"
              @click="startTour" @keyup.enter="startTour">🧭 引导</span>
      </div>
    </header>

    <!-- ===== 浮岛工作区 ===== -->
    <main class="workspace">
      <!-- 功能面板岛 -->
      <section class="island island-feature" aria-label="功能面板">
        <div class="island-head">
          <el-icon><Grid /></el-icon>{{ activeLabel }}
        </div>
        <div class="island-body" :key="activeModule">
          <div class="wave-in"><component :is="moduleComponents[activeModule]" /></div>
        </div>
      </section>

      <!-- 解析原文岛（简历转化为两段式布局，隐藏本岛） -->
      <section v-if="activeModule !== 'resume'" class="island island-doc" aria-label="解析原文">
        <div class="island-head">
          <el-icon><Document /></el-icon>解析原文
          <el-tag v-if="docMeta.ext" size="small" type="info" effect="plain" round style="margin-left:auto">{{ docMeta.ext }}</el-tag>
        </div>
        <div class="island-body">
          <template v-if="docText">
            <div class="doc-toolbar">
              <div class="doc-meta">
                <span class="doc-name">{{ docMeta.file_name }}</span>
                <span class="doc-stat">{{ docMeta.char_count }} 字<span v-if="docMeta.total"> · {{ Number(docMeta.total).toLocaleString() }} 条数据</span></span>
              </div>
              <el-button size="small" type="primary" round :loading="genLoading" @click="doGenerate">生成可视化</el-button>
            </div>
            <pre class="doc-text">{{ docText }}</pre>
          </template>
          <div v-else class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">尚未解析文件</div>
            <div class="empty-hint">从功能面板「文件上传 / 在线输入」开始<br>支持 Word · PPT · PDF · Excel · 图片 OCR</div>
          </div>
        </div>
      </section>

      <!-- 可视化预览岛（主舞台） -->
      <section class="island island-preview" aria-label="可视化结果">
        <div class="island-head">
          <el-icon><MagicStick /></el-icon>可视化结果
          <div class="toolbar">
            <el-select v-model="currentRecordId" size="small" style="width:170px" placeholder="历史结果"
                       @change="loadRecord(currentRecordId)">
              <el-option v-for="r in recentRecords" :key="r.id" :value="r.id" :label="r.title" />
            </el-select>
            <el-button-group size="small">
              <el-button @click="zoom(0.9)">−</el-button>
              <el-button style="width:58px;font-variant-numeric:tabular-nums" @click="zoom(0)">{{ Math.round(scale * 100) }}%</el-button>
              <el-button @click="zoom(1.1)">+</el-button>
            </el-button-group>
            <el-button size="small" @click="reloadFrame">刷新</el-button>
            <el-button size="small" @click="openLocal">本地预览</el-button>
            <el-button size="small" @click="exportPdf" :disabled="!previewSrc">导出 PDF</el-button>
            <el-button size="small" @click="openBlank">新窗口</el-button>
            <el-button size="small" type="primary" :loading="shareLoading" @click="makeShare">公开链接</el-button>
          </div>
        </div>
        <div class="preview-wrap">
          <iframe v-if="previewSrc" ref="frameRef" :src="previewSrc + '?t=' + frameKey" class="preview-frame"
                  :style="{ width: (100 / scale) + '%', height: (100 / scale) + '%', transform: `scale(${scale})` }"></iframe>

          <!-- 主题已切换：提示重新生成以应用 -->
          <transition name="fade-up">
            <div v-if="themeHint" class="theme-hint">
              <span>主题已切换为「{{ currentThemeName }}」，重新生成即可应用</span>
              <el-button size="small" type="primary" round :loading="genLoading" @click="doGenerate">重新生成</el-button>
              <el-button size="small" text @click="themeHint = false">知道了</el-button>
            </div>
          </transition>

          <!-- 生成进度遮罩：海浪主题（涌浪推进 = 生成进度） -->
          <div v-if="genLoading" class="gen-overlay">
            <div class="gen-card">
              <div class="gen-wave-wrap">
                <WaveArt :w="300" :h="120" />
                <!-- 浪高随进度上涨：潮位条 -->
                <div class="gen-tide" :style="{ height: genProgress + '%' }"></div>
                <span class="gen-pct">{{ genProgress }}<small>%</small></span>
              </div>
              <div class="gen-stage">{{ genMessage }}</div>
              <div class="gen-time">
                已用时 <b>{{ genElapsedText }}</b>
                <template v-if="genProgress > 3 && genProgress < 99 && genElapsed > 15"> · 预计还需 {{ genEtaText }}</template>
              </div>
              <div class="gen-bar"><div class="gen-bar-fill" :style="{ width: genProgress + '%' }"></div></div>
              <div class="gen-tips">AI 正在逐段设计版式、配色与图表，完成后自动展示 · 请勿关闭页面</div>
            </div>
          </div>

          <div v-else-if="!previewSrc" class="empty-state" style="height:100%">
            <div class="empty-icon">✨</div>
            <div class="empty-title">生成的可视化 HTML 将展示在这里</div>
            <div class="empty-hint">智能选型主题 · 缩放 · 本地预览 · 导出 PDF · 公开分享</div>
          </div>
        </div>
      </section>
    </main>
  </div>

  <!-- 首次访问聚光灯引导 -->
  <SpotlightTour />

  <!-- 全局海浪加载层：所有等待操作统一唤起（防重复操作） -->
  <WaveLoader />

  <!-- 右下角玻璃通透度调节浮标 -->
  <GlassTuner />
  </template>
</template>

<script setup>
import { ref, reactive, provide, onMounted, computed, markRaw, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, Document, MagicStick,
         Upload, Lightning, Switch, User, Brush, Reading, DataAnalysis,
         Clock, Star, Delete, Share, Cpu, Files, Setting, School } from '@element-plus/icons-vue'
import * as api from './api'
import SpotlightTour from './components/SpotlightTour.vue'
import LandingPage from './components/LandingPage.vue'
import WaveLoader from './components/WaveLoader.vue'
import WaveArt from './components/WaveArt.vue'
import GlassTuner from './components/GlassTuner.vue'
import { themeName, themeEmoji } from './theme'

const entered = ref(
  // 支持 ?app=1 / #app 直接进入工作台（便于收藏书签、分享直达链接）
  new URLSearchParams(location.search).has('app') || location.hash === '#app'
)

import UploadPanel from './components/modules/UploadPanel.vue'
import ConvertPanel from './components/modules/ConvertPanel.vue'
import CasesPanel from './components/modules/CasesPanel.vue'
import HistoryPanel from './components/modules/HistoryPanel.vue'
import BatchPanel from './components/modules/BatchPanel.vue'
import TemplatePanel from './components/modules/TemplatePanel.vue'
import SummaryPanel from './components/modules/SummaryPanel.vue'
import InsightPanel from './components/modules/InsightPanel.vue'
import ExportPanel from './components/modules/ExportPanel.vue'
import FavPanel from './components/modules/FavPanel.vue'
import TrashPanel from './components/modules/TrashPanel.vue'
import ModelPanel from './components/modules/ModelPanel.vue'
import SettingsPanel from './components/modules/SettingsPanel.vue'
import ResumePanel from './components/modules/ResumePanel.vue'
import TutorialPanel from './components/modules/TutorialPanel.vue'

const modules = [
  { key: 'upload',   icon: markRaw(Upload),        label: '文件上传与在线输入', short: '上传输入' },
  { key: 'batch',    icon: markRaw(Lightning),     label: '批量处理', short: '批量处理' },
  { key: 'convert',  icon: markRaw(Switch),        label: '格式转换', short: '格式转换' },
  { key: 'resume',   icon: markRaw(User),          label: '简历转化', short: '简历转化' },
  { key: 'template', icon: markRaw(Brush),         label: '模板与主题中心', short: '模板主题' },
  { key: 'summary',  icon: markRaw(Reading),       label: '摘要与标签分类', short: '摘要分类' },
  { key: 'insight',  icon: markRaw(DataAnalysis),  label: '图表洞察', short: '图表洞察' },
  { key: 'history',  icon: markRaw(Clock),         label: '历史记录', short: '历史记录' },
  { key: 'fav',      icon: markRaw(Star),          label: '收藏', short: '收藏' },
  { key: 'trash',    icon: markRaw(Delete),        label: '回收站', short: '回收站' },
  { key: 'export',   icon: markRaw(Share),         label: '导出与分享', short: '导出分享' },
  { key: 'model',    icon: markRaw(Cpu),           label: 'Agent 模型接入', short: '模型接入' },
  { key: 'cases',    icon: markRaw(Files),         label: '案例查看', short: '案例' },
  { key: 'settings', icon: markRaw(Setting),       label: '系统设置', short: '系统设置' },
]
// 浮坞分组：教程固定首位；输入 / 分析设计 / 管理 三组
const TUTORIAL = { key: 'tutorial', icon: markRaw(School), label: '新手教程', short: '新手教程' }
const byKey = Object.fromEntries(modules.map(m => [m.key, m]))
const dockGroups = [
  [TUTORIAL, byKey.upload, byKey.batch, byKey.convert, byKey.resume],
  [byKey.template, byKey.summary, byKey.insight],
  [byKey.history, byKey.fav, byKey.trash, byKey.export, byKey.model, byKey.cases, byKey.settings],
]
const moduleComponents = {
  upload: UploadPanel, batch: BatchPanel, convert: ConvertPanel, resume: ResumePanel,
  template: TemplatePanel, summary: SummaryPanel, insight: InsightPanel, history: HistoryPanel,
  fav: FavPanel, trash: TrashPanel, export: ExportPanel, model: ModelPanel,
  cases: CasesPanel, settings: SettingsPanel, tutorial: TutorialPanel,
}

// ---- 全局共享状态 ----
const state = reactive({
  fileId: '', docText: '', docMeta: {},
  theme: 'auto', modelId: '', extraReq: '',
  previewSrc: '', currentRecordId: '',
  recentRecords: [], settings: {},
  activeModule: 'upload',          // 进入共享状态：教程等模块可导航
  generatedTheme: '',              // 最近一次生成所用主题（联动判断）
})
provide('appState', state)

const currentModelName = computed(() => state.modelId || 'Agnes 大模型（默认）')
// 模板作用域代理（state 内字段需显式暴露给 template）
const docText = computed(() => state.docText)
const docMeta = computed(() => state.docMeta)
const previewSrc = computed(() => state.previewSrc)
const currentRecordId = computed({
  get: () => state.currentRecordId,
  set: v => { state.currentRecordId = v },
})
const recentRecords = computed(() => state.recentRecords)
const activeModule = computed(() => state.activeModule)
const activeLabel = computed(() =>
  (state.activeModule === 'tutorial' ? TUTORIAL : byKey[state.activeModule])?.label || '')
const currentThemeName = computed(() => themeName(state.theme))
const currentThemeEmoji = computed(() => themeEmoji(state.theme))
const scale = ref(1)
const frameKey = ref(Date.now())
const genLoading = ref(false)
const shareLoading = ref(false)
const frameRef = ref(null)

// ---- 主题联动：切换即反馈，跨面板实时同步 ----
const themeFlash = ref(false)
const themeHint = ref(false)
watch(() => state.theme, (nv, ov) => {
  if (nv === ov) return
  // 顶部徽标闪光反馈
  themeFlash.value = false
  requestAnimationFrame(() => { themeFlash.value = true })
  setTimeout(() => { themeFlash.value = false }, 700)
  // 已有生成结果且主题变化 → 提示重新生成（「auto」在生成时解析，视为一致）
  if (state.previewSrc && state.generatedTheme && nv !== state.generatedTheme) themeHint.value = true
  else themeHint.value = false
})

// ---- 浮坞切换：涟漪反馈 ----
function switchModule(key, e) {
  state.activeModule = key
  const host = e?.currentTarget
  if (host) {
    const r = host.getBoundingClientRect()
    const rip = document.createElement('span')
    rip.className = 'ripple'
    rip.style.left = (e.clientX - r.left) + 'px'
    rip.style.top = (e.clientY - r.top) + 'px'
    host.appendChild(rip)
    setTimeout(() => rip.remove(), 600)
  }
}
function startTour() { window.__uvStartTour?.() }

// ---- 浮沫装饰 ----
function foamStyle(n) {
  const size = 5 + (n * 5) % 12
  return {
    left: (n * 9.7) % 100 + 'vw',
    width: size + 'px', height: size + 'px',
    animationDuration: 14 + (n % 5) * 3 + 's',
    animationDelay: -(n * 2.3) % 16 + 's',
  }
}

// ---- 生成进度状态 ----
const genProgress = ref(0)
const genMessage = ref('')
const genElapsed = ref(0)

const genElapsedText = computed(() => {
  const s = Math.round(genElapsed.value)
  return s >= 60 ? `${Math.floor(s / 60)} 分 ${s % 60} 秒` : `${s} 秒`
})
const genEtaText = computed(() => {
  // 按当前进度线性外推剩余时间
  if (genProgress.value <= 3) return '计算中…'
  const remain = Math.max(0, (100 - genProgress.value) / genProgress.value * genElapsed.value)
  const s = Math.round(remain)
  return s >= 60 ? `${Math.floor(s / 60)} 分 ${s % 60} 秒` : `${s} 秒`
})

function zoom(factor) {
  // factor=0 → 复位 100%；0.9 / 1.1 → 缩小 / 放大
  scale.value = factor === 0 ? 1 : Math.min(2, Math.max(0.4, +(scale.value * factor).toFixed(2)))
}
function reloadFrame() { frameKey.value = Date.now() }
function openLocal() {
  // 本地预览：直接以独立标签页打开预览地址
  if (!state.previewSrc) return ElMessage.warning('暂无可预览结果')
  window.open(state.previewSrc, '_blank')
}
function openBlank() { openLocal() }

// 全局 PDF 导出钩子：功能面板（如简历转化）复用预览 iframe 的打印导出能力
window.__uvAppExportPdf = exportPdf
// 主题面板「用新主题重新生成」钩子：复用主生成流程（带进度遮罩）
window.__uvRegenerate = doGenerate

// 导出 PDF：对 iframe 同源文档直接调起打印（版式与页面显示一致）
function exportPdf() {
  const win = frameRef.value?.contentWindow
  if (!win) return ElMessage.warning('请先生成或选择一个可视化结果')
  try {
    win.focus()
    win.__uvExportPdf ? win.__uvExportPdf() : win.print()
    ElMessage.info('已调起打印，在弹窗中选择「另存为 PDF」')
  } catch {
    window.open(state.previewSrc, '_blank')
    ElMessage.info('已在新窗口打开，点击页面右下角「导出 PDF」按钮')
  }
}

async function doGenerate() {
  if (!state.fileId) return ElMessage.warning('请先上传文件或输入文本')
  genLoading.value = true
  genProgress.value = 2
  genMessage.value = '任务创建中…'
  genElapsed.value = 0
  themeHint.value = false
  try {
    const res = await api.generateWait(
      { file_id: state.fileId, theme: state.theme, model_id: state.modelId || null, extra_req: state.extraReq },
      (p, msg, elapsed) => {
        genProgress.value = Math.max(genProgress.value, p)
        genMessage.value = msg || genMessage.value
        genElapsed.value = elapsed || genElapsed.value
      })
    genProgress.value = 100
    state.previewSrc = api.previewUrl(res.id)
    state.currentRecordId = res.id
    // 记录本次生成所用主题（重新生成时「auto」解析为实际选型）
    state.generatedTheme = res.suggested_theme && state.theme === 'auto' ? res.suggested_theme : state.theme
    frameKey.value = Date.now()
    ElMessage.success('生成完成：' + (res.suggested_theme ? `智能选型「${res.suggested_theme}」` : 'OK'))
    refreshRecent()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '生成失败')
  } finally { genLoading.value = false }
}

async function makeShare() {
  if (!state.currentRecordId) return ElMessage.warning('请先生成或选择一个结果')
  shareLoading.value = true
  try {
    const res = await api.share(state.currentRecordId)
    const full = location.origin + res.share_url
    await ElMessageBox.alert(
      `<a href="${full}" target="_blank" style="word-break:break-all">${full}</a>`,
      '公开访问链接（已复制入口）', { dangerouslyUseHTMLString: true })
    navigator.clipboard?.writeText(full).catch(() => {})
  } finally { shareLoading.value = false }
}

async function loadRecord(id) {
  state.previewSrc = api.previewUrl(id)
  state.currentRecordId = id
  // 同步该记录生成时所用主题：保证后续切主题联动判断正确
  const rec = state.recentRecords.find(r => r.id === id)
  state.generatedTheme = rec?.theme || state.theme
  frameKey.value = Date.now()
}

async function refreshRecent() {
  try {
    state.recentRecords = (await api.history()).slice(0, 30)
  } catch { /* ignore */ }
}

onMounted(async () => {
  refreshRecent()
  try { state.settings = await api.getSettings() } catch { /* ignore */ }
})
onMounted(() => { window.__refreshRecent = refreshRecent })
</script>

<style scoped>
/* 首页进入页淡出过渡 */
.ld-fade-leave-active { transition: opacity .5s var(--ease); }
.ld-fade-leave-to { opacity: 0; }

.doc-toolbar {
  padding: 10px 14px; border-bottom: 1px solid rgba(120, 140, 175, .16);
  display: flex; gap: 10px; align-items: center; position: sticky; top: 0;
  background: rgba(255, 255, 255, .85); backdrop-filter: blur(10px); z-index: 2;
}
.doc-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.doc-name { font-size: 12.5px; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-stat { font-size: 11px; color: var(--text-sub); font-variant-numeric: tabular-nums; }
.doc-text {
  margin: 0; padding: 14px 16px; white-space: pre-wrap; word-break: break-word;
  font-family: inherit; font-size: 12.5px; line-height: 1.85; color: #39414e;
}
.preview-wrap { flex: 1; overflow: hidden; position: relative; }
.preview-frame {
  border: 0; background: #fff; transform-origin: top left;
  box-shadow: 0 4px 24px rgba(0,0,0,.10); border-radius: 6px 0 0 0; position: absolute; left: 0; top: 0;
}
.toolbar { margin-left: auto; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }

/* 主题切换提示浮条 */
.theme-hint {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%); z-index: 12;
  display: flex; align-items: center; gap: 8px; padding: 8px 10px 8px 16px;
  background: rgba(255,255,255,.94); backdrop-filter: blur(12px);
  border: 1px solid rgba(79,110,247,.3); border-radius: 999px;
  box-shadow: var(--shadow-lg); font-size: 12.5px; color: #2c3e56; white-space: nowrap;
}
.fade-up-enter-active, .fade-up-leave-active { transition: all .35s var(--ease); }
.fade-up-enter-from, .fade-up-leave-to { opacity: 0; transform: translateX(-50%) translateY(-10px); }

/* ---- 生成进度遮罩 ---- */
.gen-overlay {
  position: absolute; inset: 0; z-index: 10;
  background: rgba(240, 245, 250, .82); backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
}
.gen-card {
  width: 420px; padding: 30px 36px 26px; border-radius: 20px; overflow: hidden;
  background: var(--glass-island); backdrop-filter: blur(22px) saturate(1.6);
  -webkit-backdrop-filter: blur(22px) saturate(1.6);
  box-shadow: var(--shadow-lg); border: 1px solid var(--glass-edge); text-align: center;
  animation: cardIn .45s cubic-bezier(.22,.61,.36,1);
}
@keyframes cardIn { from { opacity: 0; transform: translateY(18px) scale(.97); } }
.gen-wave-wrap {
  position: relative; width: 100%; height: 120px; border-radius: 14px; overflow: hidden;
  margin-bottom: 18px; box-shadow: inset 0 1px 6px rgba(10,30,60,.10);
}
/* 潮位条：随进度上涨的半透明海水 */
.gen-tide {
  position: absolute; left: 0; right: 0; bottom: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(79,110,247,.38), rgba(56,88,222,.55));
  transition: height .9s cubic-bezier(.22,.61,.36,1);
}
.gen-tide::before {
  content: ''; position: absolute; top: -7px; left: -50%; width: 200%; height: 14px;
  background: radial-gradient(ellipse 12px 9px at 50% 100%, transparent 62%, rgba(79,110,247,.45) 63%) repeat-x;
  background-size: 36px 14px; animation: tideWave 2.4s linear infinite;
}
@keyframes tideWave { from { transform: translateX(0); } to { transform: translateX(36px); } }
.gen-pct {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 30px; font-weight: 800; color: #fff; text-shadow: 0 2px 10px rgba(20,50,120,.45);
  font-variant-numeric: tabular-nums; pointer-events: none; z-index: 2;
}
.gen-pct small { font-size: 15px; font-weight: 600; margin-left: 2px; }
.gen-stage { font-size: 13.5px; font-weight: 600; color: var(--text); margin-bottom: 8px; line-height: 1.6; }
.gen-time { font-size: 12px; color: var(--text-sub); margin-bottom: 14px; font-variant-numeric: tabular-nums; }
.gen-time b { color: var(--primary); font-weight: 600; }
.gen-bar { height: 6px; border-radius: 99px; background: #edf0f7; overflow: hidden; }
.gen-bar-fill {
  height: 100%; border-radius: 99px;
  background: linear-gradient(90deg, #4f6ef7, #8b5cf6);
  transition: width .8s cubic-bezier(.22,.61,.36,1);
}
.gen-tips { margin-top: 14px; font-size: 11.5px; color: #9aa4b5; line-height: 1.7; }

.empty-state { height: 100%; }
.empty-icon { font-size: 42px; opacity: .45; filter: saturate(.8); }
.empty-title { font-size: 14px; font-weight: 600; color: #5b6472; letter-spacing: .3px; }
.empty-hint { font-size: 12px; color: var(--text-sub); line-height: 1.9; }

@media (max-width: 1120px) {
  .topbar { gap: 8px; }
  .dock-wrap { order: 3; width: 100%; justify-content: flex-start; }
  .theme-hint { white-space: normal; border-radius: 14px; width: max-content; max-width: 92%; }
}
</style>
