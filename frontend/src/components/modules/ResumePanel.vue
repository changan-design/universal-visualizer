<template>
  <div class="resume-panel">
    <!-- 面板头 -->
    <header class="rp-head">
      <h3 class="rp-title">简历转化</h3>
      <div class="rp-title-bar" aria-hidden="true"></div>
      <p class="rp-sub">口语化经历 → AI 专业化改写 → 高质感简历<br>支持 HTML / Word / PDF 三格式导出</p>
    </header>

    <!-- 第一步：口语化经历 -->
    <section class="step-card">
      <div class="step-head">
        <span class="step-no" aria-hidden="true">01</span>
        <div>
          <div class="step-title">整体经历</div>
          <div class="step-desc">口语化描述即可，想到什么写什么</div>
        </div>
      </div>
      <el-input v-model="story" type="textarea" :rows="6" maxlength="8000" show-word-limit
                class="rp-textarea"
                placeholder="例：我在山东做了 8 年项目管理，管过 5 个工地，最多带过 40 个人，考了一建，去年项目提前 2 个月完工还省了 200 万预算……" />
      <div class="opt-row">
        <el-input v-model="industry" placeholder="所属行业（如：建筑工程）" />
        <el-input v-model="position" placeholder="目标岗位（如：项目总监）" />
      </div>
      <el-input v-model="target" type="textarea" :rows="2" class="opt-jd"
                placeholder="目标 JD / 岗位要求（选填，粘贴进去改写更精准）" />
      <button class="btn-hero" :disabled="optLoading" @click="doOptimize">
        <span v-if="optLoading" class="btn-spin" aria-hidden="true"></span>
        {{ optLoading ? 'AI 改写中，约 1~2 分钟…' : 'AI 专业化改写 → 填入第二步' }}
      </button>
      <div v-if="advice.length" class="advice-box" role="list" aria-label="AI 改写建议">
        <div class="advice-title">改写建议</div>
        <div v-for="(a, i) in advice" :key="i" class="advice-item" role="listitem">{{ a }}</div>
      </div>
    </section>

    <!-- 第二步：结构化信息 -->
    <section class="step-card">
      <div class="step-head">
        <span class="step-no" aria-hidden="true">02</span>
        <div>
          <div class="step-title">结构化信息</div>
          <div class="step-desc">AI 改写结果自动填入，可随时手工微调</div>
        </div>
        <div class="profile-actions">
          <el-button size="small" round @click="fillProfile">一键填入个人资料</el-button>
          <el-button size="small" round @click="saveProfile">保存为个人资料</el-button>
        </div>
      </div>

      <!-- 头像上传：点击选择 / 拖拽图片，圆形压缩预览 -->
      <div class="avatar-row" :class="{ 'drag-over': dragOver }"
           @dragover.prevent="dragOver = true"
           @dragenter.prevent="dragOver = true"
           @dragleave.prevent="dragOver = false"
           @drop.prevent="onDrop">
        <div class="avatar-box" :class="{ 'has-img': !!form.basics.avatar }"
             role="button" tabindex="0" aria-label="上传头像：点击选择或拖拽图片到此处"
             @click="pickAvatar" @keyup.enter="pickAvatar" @keyup.space.prevent="pickAvatar">
          <img v-if="form.basics.avatar" :src="form.basics.avatar" class="avatar-img" alt="头像预览" />
          <svg v-else viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
               stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1l1.2-1.6A2 2 0 0 1 10.3 3.5h3.4a2 2 0 0 1 1.6.9L16.5 6h1A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5z"/>
            <circle cx="12" cy="12.2" r="3.2"/>
          </svg>
          <span v-if="form.basics.avatar" class="avatar-mask" aria-hidden="true">更换头像</span>
          <input ref="avatarInput" type="file" accept="image/*" hidden
                 @change="e => onAvatarFile(e.target.files?.[0])" />
        </div>
        <div class="avatar-meta">
          <div class="avatar-title">个人头像 <span class="avatar-optional">选填</span></div>
          <div class="avatar-desc">点击左侧圆框选择图片，或直接<b>拖拽图片到虚线区内</b><br>自动等比压缩至 512px，仅可视化版与 Word 显示（ATS 版不含照片）</div>
          <button v-if="form.basics.avatar" class="avatar-remove" @click.stop="removeAvatar">移除头像</button>
        </div>
      </div>

      <div class="sec-label">基本信息</div>
      <div class="grid-2">
        <el-input v-model="form.basics.name" placeholder="姓名 *" />
        <el-input v-model="form.basics.position" placeholder="求职意向岗位" />
        <el-input v-model="form.basics.phone" placeholder="联系电话" />
        <el-input v-model="form.basics.email" placeholder="邮箱" />
        <el-input v-model="form.basics.city" placeholder="所在城市" />
      </div>

      <div class="sec-label">个人优势概述</div>
      <el-input v-model="form.summary" type="textarea" :rows="3"
                placeholder="2~3 行：年限 + 领域 + 核心战绩（可由 AI 改写生成）" />

      <div class="sec-label">核心技能关键词 <span class="sec-tip">ATS 机器筛选重点，逗号分隔</span></div>
      <el-input v-model="form.keywordsText" placeholder="如：一级建造师, P6 进度管理, 造价控制, BIM" />

      <div class="sec-row-head">
        <span class="sec-label">工作经历</span>
        <el-button size="small" text type="primary" @click="addRow('work')">+ 添加</el-button>
      </div>
      <div v-for="(w, i) in form.work" :key="'w' + i" class="row-card">
        <div class="grid-3">
          <el-input v-model="w.company" placeholder="公司" />
          <el-input v-model="w.title" placeholder="职位" />
          <el-input v-model="w.period" placeholder="2020.03 - 2024.05" />
        </div>
        <el-input v-model="w.highlights" type="textarea" :rows="3"
                  placeholder="量化成果，每行一条：主导 XX 项目，提前 2 个月完工、节省预算 200 万（+9%）" />
        <el-button class="row-del" size="small" text type="danger" @click="delRow('work', i)" aria-label="删除这条工作经历">删除</el-button>
      </div>

      <div class="sec-row-head">
        <span class="sec-label">项目经历</span>
        <el-button size="small" text type="primary" @click="addRow('projects')">+ 添加</el-button>
      </div>
      <div v-for="(p, i) in form.projects" :key="'p' + i" class="row-card">
        <div class="grid-3">
          <el-input v-model="p.name" placeholder="项目名" />
          <el-input v-model="p.role" placeholder="角色" />
          <el-input v-model="p.period" placeholder="时间" />
        </div>
        <el-input v-model="p.desc" type="textarea" :rows="2" placeholder="一句话说明 + 量化结果" />
        <el-button class="row-del" size="small" text type="danger" @click="delRow('projects', i)" aria-label="删除这个项目">删除</el-button>
      </div>

      <div class="sec-row-head">
        <span class="sec-label">教育背景</span>
        <el-button size="small" text type="primary" @click="addRow('education')">+ 添加</el-button>
      </div>
      <div v-for="(e, i) in form.education" :key="'e' + i" class="row-card">
        <div class="grid-2">
          <el-input v-model="e.school" placeholder="学校" />
          <el-input v-model="e.degree" placeholder="学历 / 专业" />
          <el-input v-model="e.period" placeholder="2012 - 2016" />
          <el-input v-model="e.note" placeholder="荣誉 / 相关课程（选填）" />
        </div>
        <el-button class="row-del" size="small" text type="danger" @click="delRow('education', i)" aria-label="删除这条教育经历">删除</el-button>
      </div>

      <div class="sec-row-head">
        <span class="sec-label">专业技能分组</span>
        <el-button size="small" text type="primary" @click="addRow('skills')">+ 添加</el-button>
      </div>
      <div v-for="(s, i) in form.skills" :key="'s' + i" class="row-card">
        <div class="grid-2">
          <el-input v-model="s.category" placeholder="分类（如：项目管理工具）" />
          <el-input v-model="s.items" placeholder="技能，逗号分隔（如：P6, Project, BIM）" />
        </div>
        <el-button class="row-del" size="small" text type="danger" @click="delRow('skills', i)" aria-label="删除这个技能分组">删除</el-button>
      </div>

      <div class="sec-label">证书 <span class="sec-tip">每行一个</span></div>
      <el-input v-model="form.certifications" type="textarea" :rows="2" placeholder="一级建造师&#10;PMP" />
    </section>

    <!-- 第三步：生成与导出 -->
    <section class="step-card step-final">
      <div class="step-head">
        <span class="step-no" aria-hidden="true">03</span>
        <div>
          <div class="step-title">生成与导出</div>
          <div class="step-desc">生成结果展示在右侧预览区，并写入历史记录</div>
        </div>
      </div>
      <div class="gen-row">
        <el-switch v-model="visual" active-text="可视化" inactive-text="ATS 极简"
                   aria-label="可视化开关：开启生成高质感页面，关闭生成机器友好单栏版" />
        <span class="gen-tip">{{ visual ? '高质感页面 · 适合投递 PDF 与展示' : '单栏纯文本版 · 机器解析零损耗' }}</span>
      </div>
      <button class="btn-hero btn-hero-lg" :disabled="genLoading || !form.basics.name" @click="doGenerate">
        <span v-if="genLoading" class="btn-spin" aria-hidden="true"></span>
        {{ genLoading ? '生成中，约 1~3 分钟…' : '生成简历' }}
      </button>
      <div v-if="resultId" class="export-row">
        <button class="btn-ghost" @click="exportHtml">导出 HTML</button>
        <button class="btn-ghost" @click="exportDocx">导出 Word</button>
        <button class="btn-ghost btn-ghost-primary" @click="exportPdf">导出 PDF</button>
        <button class="btn-ghost" @click="openPreview">新窗口</button>
      </div>
      <div class="rp-foot-hint">支持收藏与公开分享，链接可发给任何人</div>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, inject, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '../../api'
import { withWave } from '../../loading'

const appState = inject('appState')

// ---- 输入区 ----
const story = ref('')
const industry = ref('')
const position = ref('')
const target = ref('')
const advice = ref([])
const optLoading = ref(false)

// ---- 结构化表单 ----
const blankWork = () => ({ company: '', title: '', period: '', highlights: '' })
const blankProj = () => ({ name: '', role: '', period: '', desc: '' })
const blankEdu = () => ({ school: '', degree: '', period: '', note: '' })
const blankSkill = () => ({ category: '', items: '' })
const emptyForm = () => ({
  basics: { name: '', phone: '', email: '', position: '', city: '', avatar: '' },
  summary: '', keywordsText: '',
  work: [blankWork()], projects: [blankProj()], education: [blankEdu()], skills: [blankSkill()],
  certifications: '',
})
const form = reactive(emptyForm())

const ROW_KEYS = { work: blankWork, projects: blankProj, education: blankEdu, skills: blankSkill }
function addRow(key) { form[key].push(ROW_KEYS[key]()) }
function delRow(key, i) { form[key].splice(i, 1) }

// ---- 头像上传：点击选择 + 拖拽，canvas 等比压缩至 512px ----
const avatarInput = ref(null)
const dragOver = ref(false)

function pickAvatar() { avatarInput.value?.click() }

function compressAvatar(file) {
  return new Promise(resolve => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const scale = Math.min(1, 512 / Math.max(img.width, img.height))
      const c = document.createElement('canvas')
      c.width = Math.max(1, Math.round(img.width * scale))
      c.height = Math.max(1, Math.round(img.height * scale))
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height)
      URL.revokeObjectURL(url)
      resolve(c.toDataURL('image/jpeg', 0.85))
    }
    img.onerror = () => { URL.revokeObjectURL(url); resolve('') }
    img.src = url
  })
}

async function onAvatarFile(file) {
  if (!file) return
  if (!file.type.startsWith('image/')) return ElMessage.warning('请选择图片文件（JPG / PNG / WebP）')
  if (file.size > 8 * 1024 * 1024) return ElMessage.warning('图片不能超过 8MB')
  const dataUrl = await compressAvatar(file)
  if (!dataUrl) return ElMessage.error('图片解析失败，请换一张试试')
  form.basics.avatar = dataUrl
  if (avatarInput.value) avatarInput.value.value = ''  // 允许重复选择同一文件
  ElMessage.success('头像已就绪，将用于可视化简历与 Word 导出')
}

function onDrop(e) {
  dragOver.value = false
  onAvatarFile(e.dataTransfer?.files?.[0])
}

function removeAvatar() { form.basics.avatar = '' }

// ---- 生成与导出 ----
const visual = ref(true)
const genLoading = ref(false)
const resultId = ref('')

// ---- 个人资料（一键填入 / 保存，云端 settings 表持久化）----
function applyProfile(p) {
  if (!p || !p.basics) return false
  const { avatar: savedAvatar = undefined, ...rest } = p.basics
  Object.assign(form.basics, rest)
  // 头像单独处理：资料里有就用资料的；资料没有头像字段时保留当前头像
  if (savedAvatar !== undefined) form.basics.avatar = savedAvatar || ''
  form.summary = p.summary || ''
  form.keywordsText = p.keywordsText || ''
  form.certifications = p.certifications || ''
  const pick = (arr, blank) => (Array.isArray(arr) && arr.length ? arr : null) || [blank()]
  const rows = (arr, keys, blank) => pick(arr, blank).map(r => {
    const o = blank()
    keys.forEach(k => { o[k] = r?.[k] || '' })
    return o
  })
  form.work = rows(p.work, ['company', 'title', 'period', 'highlights'], blankWork)
  form.projects = rows(p.projects, ['name', 'role', 'period', 'desc'], blankProj)
  form.education = rows(p.education, ['school', 'degree', 'period', 'note'], blankEdu)
  form.skills = rows(p.skills, ['category', 'items'], blankSkill)
  return true
}
const snapshot = () => JSON.parse(JSON.stringify({
  basics: form.basics, summary: form.summary, keywordsText: form.keywordsText,
  work: form.work, projects: form.projects, education: form.education, skills: form.skills,
  certifications: form.certifications,
}))

async function fillProfile() {
  try {
    if (applyProfile(await api.getResumeProfile())) ElMessage.success('已填入个人资料')
    else ElMessage.info('暂无保存的个人资料，填写后点「保存为个人资料」')
  } catch { /* 拦截器已提示 */ }
}
async function saveProfile() {
  await api.saveResumeProfile(snapshot())
  ElMessage.success('个人资料已保存，下次一键填入')
}
onMounted(async () => {
  try { applyProfile(await api.getResumeProfile()) } catch { /* ignore */ }
})

// ---- AI 改写：经历长文 → 结构化 + 量化 + 关键词 ----
async function doOptimize() {
  if (!story.value.trim() && !form.basics.name) return ElMessage.warning('请先在上方写下经历，或填好基本信息')
  optLoading.value = true
  try {
    const res = await withWave('AI 正在优化简历…', '量化经历 · 提炼关键词 · 匹配行业表达', () => api.resumeOptimize({
      story: story.value, industry: industry.value, position: position.value,
      target: target.value, form: snapshot(),
    }))
    applyOptimized(res)
    advice.value = res.advice || []
    ElMessage.success('改写完成，已填入第二步表单，请核对后微调')
  } catch { /* 拦截器已提示 */ } finally { optLoading.value = false }
}

function applyOptimized(res) {
  const b = res.basics || {}
  // AI 只回填文本字段，头像等本地资源不受改写影响
  Object.keys(form.basics).forEach(k => { if (b[k] && k !== 'avatar') form.basics[k] = b[k] })
  if (res.summary) form.summary = res.summary
  if (Array.isArray(res.keywords) && res.keywords.length) form.keywordsText = res.keywords.join(', ')
  if (Array.isArray(res.work) && res.work.length)
    form.work = res.work.map(w => ({ company: w.company || '', title: w.title || '', period: w.period || '', highlights: (w.highlights || []).join('\n') }))
  if (Array.isArray(res.projects) && res.projects.length)
    form.projects = res.projects.map(p => ({ name: p.name || '', role: p.role || '', period: p.period || '', desc: p.desc || '' }))
  if (Array.isArray(res.education) && res.education.length)
    form.education = res.education.map(e => ({ school: e.school || '', degree: e.degree || '', period: e.period || '', note: e.note || '' }))
  if (Array.isArray(res.skills) && res.skills.length)
    form.skills = res.skills.map(s => ({ category: s.category || '', items: (s.items || []).join(', ') }))
  if (Array.isArray(res.certifications) && res.certifications.length)
    form.certifications = res.certifications.join('\n')
}

// ---- 组装结构化数据 → 生成 ----
function buildData() {
  const split = (s, re) => (s || '').split(re).map(x => x.trim()).filter(Boolean)
  return {
    basics: { ...form.basics },
    summary: form.summary.trim(),
    keywords: split(form.keywordsText, /[,，、]/),
    work: form.work.filter(w => w.company || w.title).map(w => ({ ...w, highlights: split(w.highlights, /\n+/) })),
    projects: form.projects.filter(p => p.name).map(p => ({ ...p })),
    education: form.education.filter(e => e.school).map(e => ({ ...e })),
    skills: form.skills.filter(s => s.category || s.items).map(s => ({ category: s.category, items: split(s.items, /[,，、]/) })),
    certifications: split(form.certifications, /\n+/),
  }
}

async function doGenerate() {
  if (!form.basics.name.trim()) return ElMessage.warning('请先填写姓名')
  genLoading.value = true
  try {
    const res = await api.resumeGenerate({ data: buildData(), visual: visual.value })
    resultId.value = res.id
    appState.previewSrc = res.preview_url
    appState.currentRecordId = res.id
    window.__refreshRecent?.()
    ElMessage.success('简历生成完成，已在右侧预览')
  } catch { /* 拦截器已提示 */ } finally { genLoading.value = false }
}

function download(url, filename) {
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
}
function exportHtml() {
  download(api.exportUrl(resultId.value), `${form.basics.name}_简历.html`)
  ElMessage.success('HTML 已开始下载')
}
function exportDocx() {
  download(api.resumeDocxUrl(resultId.value), `${form.basics.name}_简历.docx`)
  ElMessage.success('Word 已开始下载')
}
function exportPdf() {
  // 复用全局导出：对右侧预览 iframe 调起打印（版式与显示一致）
  if (window.__uvAppExportPdf) return window.__uvAppExportPdf()
  if (appState.previewSrc) window.open(appState.previewSrc, '_blank')
  ElMessage.info('已打开预览，点击页面右下角「导出 PDF」')
}
function openPreview() {
  if (appState.previewSrc) window.open(appState.previewSrc, '_blank')
}
</script>

<style scoped>
.resume-panel { padding: 18px 18px 28px; }

/* ---- 面板头 ---- */
.rp-head { margin-bottom: 16px; }
.rp-title {
  font-size: 18px; font-weight: 700; margin: 0; letter-spacing: .5px;
  background: linear-gradient(120deg, var(--text-strong), #3d4d8f);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.rp-title-bar {
  width: 42px; height: 3px; border-radius: 2px; margin: 7px 0 9px;
  background: linear-gradient(90deg, var(--primary), #8b5cf6);
}
.rp-sub { font-size: 12px; color: var(--text-sub); margin: 0; line-height: 1.75; }

/* ---- 步骤卡片：渐变描边 + 玻璃质感 + 悬浮微升 ---- */
.step-card {
  position: relative;
  background: linear-gradient(180deg, rgba(255, 255, 255, .94), rgba(255, 255, 255, .88));
  backdrop-filter: blur(10px);
  border: 1px solid rgba(213, 219, 232, .9); border-radius: 15px;
  padding: 17px; margin-bottom: 14px; box-shadow: var(--shadow);
  transition: box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease), border-color var(--dur) var(--ease);
}
.step-card::before {  /* 顶部 1px 渐变高光：玻璃厚度感 */
  content: ''; position: absolute; top: 0; left: 14px; right: 14px; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .9), transparent);
  pointer-events: none;
}
.step-card:hover { box-shadow: var(--shadow-lg); border-color: var(--border-strong); transform: translateY(-1px); }
.step-head { display: flex; align-items: center; gap: 11px; margin-bottom: 13px; }
.step-no {
  position: relative;
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12.5px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  box-shadow: 0 3px 10px rgba(79, 110, 247, .35), inset 0 1px 0 rgba(255, 255, 255, .35);
}
.step-no::after {  /* 徽章底部内阴影：立体感 */
  content: ''; position: absolute; inset: 0; border-radius: 10px;
  box-shadow: inset 0 -6px 10px rgba(30, 40, 120, .18); pointer-events: none;
}
.step-title { font-size: 13.5px; font-weight: 650; color: var(--text-strong); letter-spacing: .3px; }
.step-desc { font-size: 11.5px; color: var(--text-sub); margin-top: 1px; }
.step-final { border-color: #dbe2ff; background: linear-gradient(180deg, rgba(251, 252, 255, .95), rgba(247, 249, 255, .9)); }

/* ---- 头像上传区 ---- */
.avatar-row {
  display: flex; align-items: center; gap: 14px;
  padding: 13px 14px; margin-bottom: 4px; border-radius: 12px;
  border: 1.5px dashed #c8d2e6; background: rgba(240, 244, 252, .55);
  transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.avatar-row.drag-over {
  border-color: var(--primary); background: var(--primary-soft);
  box-shadow: 0 0 0 4px rgba(79, 110, 247, .12);
}
.avatar-box {
  position: relative; width: 76px; height: 76px; flex-shrink: 0; cursor: pointer;
  border-radius: 50%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  color: #8b96ad;
  background:
    radial-gradient(120% 120% at 30% 22%, rgba(255, 255, 255, .95), rgba(233, 238, 248, .9));
  border: 1.5px dashed #b6c2da;
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.avatar-box:hover, .avatar-box:focus-visible {
  border-color: var(--primary); color: var(--primary);
  box-shadow: 0 6px 18px rgba(79, 110, 247, .22);
  transform: translateY(-1px);
}
.avatar-box:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.avatar-row.drag-over .avatar-box { border-color: var(--primary); transform: scale(1.04); }
.avatar-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.avatar-box.has-img { border: 0; box-shadow: 0 4px 14px rgba(20, 30, 60, .16), inset 0 0 0 1px rgba(255, 255, 255, .5); }
.avatar-mask {
  position: absolute; inset: auto 0 0 0; padding: 4px 0; text-align: center;
  font-size: 10px; font-weight: 600; color: #fff; letter-spacing: 1px;
  background: linear-gradient(180deg, transparent, rgba(10, 18, 40, .68));
  opacity: 0; transition: opacity var(--dur) var(--ease);
}
.avatar-box.has-img:hover .avatar-mask, .avatar-box.has-img:focus-visible .avatar-mask { opacity: 1; }
.avatar-meta { min-width: 0; }
.avatar-title { font-size: 12.5px; font-weight: 650; color: var(--text-strong); display: flex; align-items: center; gap: 6px; }
.avatar-optional {
  font-size: 10px; font-weight: 600; color: #8b96ad; letter-spacing: 1px;
  border: 1px solid #d5dbe8; border-radius: 99px; padding: 0 7px; line-height: 1.5;
}
.avatar-desc { font-size: 11px; color: var(--text-sub); line-height: 1.8; margin-top: 3px; }
.avatar-desc b { color: #4a5568; }
.avatar-remove {
  margin-top: 6px; border: 0; background: none; padding: 0; cursor: pointer;
  font-size: 11.5px; font-family: inherit; color: #e05666; font-weight: 550;
}
.avatar-remove:hover { text-decoration: underline; }

/* ---- 输入编排 ---- */
.opt-row { display: flex; gap: 8px; margin-top: 8px; }
.opt-jd { margin-top: 8px; }
.profile-actions { margin-left: auto; display: flex; gap: 6px; flex-shrink: 0; }
.sec-label {
  font-size: 12.5px; font-weight: 600; color: var(--text); margin: 14px 0 6px;
  display: flex; align-items: baseline; gap: 6px; letter-spacing: .2px;
}
.sec-tip { font-weight: 400; color: var(--text-sub); font-size: 11px; }
.sec-row-head { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; }
.sec-row-head .sec-label { margin: 0; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-bottom: 7px; }
.grid-3 { display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 7px; margin-bottom: 7px; }
.row-card {
  border: 1px solid var(--border); border-radius: 10px; padding: 9px; margin-bottom: 8px;
  background: rgba(250, 251, 253, .8); transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.row-card:hover { border-color: var(--border-strong); box-shadow: 0 2px 8px rgba(20, 30, 60, .06); }
.row-del { margin-top: 4px; }

/* ---- 主按钮（渐变 CTA + 流光扫过） ---- */
.btn-hero {
  position: relative; overflow: hidden;
  width: 100%; margin-top: 12px; padding: 10px 0; border: 0; border-radius: 10px;
  font-size: 13.5px; font-weight: 600; font-family: inherit; color: #fff; cursor: pointer;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  box-shadow: 0 4px 14px rgba(79, 110, 247, .35), inset 0 1px 0 rgba(255, 255, 255, .3);
  transition: box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease), opacity var(--dur);
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.btn-hero::after {  /* 悬停流光 */
  content: ''; position: absolute; top: 0; bottom: 0; width: 46%;
  left: -60%; background: linear-gradient(105deg, transparent, rgba(255, 255, 255, .35), transparent);
  transform: skewX(-18deg); transition: left .55s var(--ease); pointer-events: none;
}
.btn-hero:hover:not(:disabled)::after { left: 120%; }
.btn-hero:hover:not(:disabled) { box-shadow: 0 7px 20px rgba(79, 110, 247, .45); transform: translateY(-1px); }
.btn-hero:active:not(:disabled) { transform: translateY(0) scale(.99); }
.btn-hero:disabled { opacity: .55; cursor: not-allowed; }
.btn-hero-lg { padding: 12px 0; font-size: 14.5px; }
.btn-hero:focus-visible { outline: 2px solid var(--primary-deep); outline-offset: 2px; }
.btn-spin {
  width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, .4); border-top-color: #fff;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ---- 改写建议 ---- */
.advice-box {
  margin-top: 12px; padding: 11px 13px; border-radius: 10px;
  background: var(--primary-soft); border: 1px solid #dfe5ff;
}
.advice-title { font-size: 12px; font-weight: 650; color: var(--primary); margin-bottom: 4px; }
.advice-item { font-size: 12px; color: #4a5568; line-height: 1.85; }
.advice-item::before { content: '· '; font-weight: 700; }

/* ---- 生成与导出 ---- */
.gen-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.gen-tip { font-size: 12px; color: var(--text-sub); }
.export-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.btn-ghost {
  flex: 1; min-width: 86px; padding: 8px 0; border-radius: 9px; cursor: pointer;
  border: 1px solid var(--border-strong); background: var(--panel);
  font-size: 12.5px; font-weight: 550; font-family: inherit; color: var(--text);
  transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease), color var(--dur), transform var(--dur) var(--ease);
}
.btn-ghost:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-soft); transform: translateY(-1px); }
.btn-ghost:active { transform: translateY(0); }
.btn-ghost:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }
.btn-ghost-primary {
  background: var(--primary); border-color: var(--primary); color: #fff;
  box-shadow: 0 3px 10px rgba(79, 110, 247, .3);
}
.btn-ghost-primary:hover { background: var(--primary-deep); border-color: var(--primary-deep); color: #fff; }
.rp-foot-hint { margin-top: 10px; font-size: 11.5px; color: #9aa4b5; text-align: center; }

@media (max-width: 640px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .opt-row { flex-direction: column; }
  .profile-actions { margin-left: 0; }
  .avatar-row { flex-direction: column; text-align: center; }
  .avatar-title { justify-content: center; }
}
</style>
