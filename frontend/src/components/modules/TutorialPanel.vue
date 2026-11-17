<template>
  <div class="scroll-area">
    <h3 class="module-title">新手教程</h3>
    <div class="hint" style="margin-bottom:12px">
      从第一次上传到进阶玩法，三步上手、逐项精讲。
      推荐先看「快速上手」，再按需查阅「功能详解」与「进阶技巧」。
    </div>

    <!-- 章节切换 -->
    <div class="tut-tabs">
      <div v-for="c in chapters" :key="c.key" class="tut-tab"
           :class="{ active: tab === c.key }" role="button" tabindex="0"
           @click="tab = c.key" @keyup.enter="tab = c.key">
        {{ c.emoji }} {{ c.name }}
      </div>
    </div>

    <!-- 重放引导 -->
    <div class="card-box" style="display:flex;align-items:center;gap:10px">
      <div style="flex:1">
        <div style="font-weight:600;font-size:13px">🧭 交互式引导</div>
        <div class="hint">逐个高亮界面区域，带你绕工作台走一圈（约 30 秒）。</div>
      </div>
      <el-button size="small" type="primary" round @click="startTour">开始引导</el-button>
    </div>

    <!-- 步骤列表 -->
    <div v-for="(s, i) in current.steps" :key="tab + i" class="tut-step">
      <div class="tut-step-head" role="button" tabindex="0" :aria-expanded="open === i"
           @click="open = open === i ? -1 : i" @keyup.enter="open = open === i ? -1 : i">
        <span class="tut-num">{{ i + 1 }}</span>
        <span class="tut-step-title">{{ s.title }}</span>
        <el-icon style="color:var(--text-sub)"><ArrowDown v-if="open === i" /><ArrowRight v-else /></el-icon>
      </div>
      <div v-if="open === i" class="tut-step-body">
        <div v-html="s.body"></div>
        <div v-if="s.goto" class="tut-try">
          <el-button size="small" round @click="goto(s.goto)">前往体验 →</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'

const state = inject('appState')

const tab = ref('basic')
const open = ref(0)
const chapters = [
  { key: 'basic',   name: '快速上手', emoji: '🚀' },
  { key: 'modules', name: '功能详解', emoji: '🧩' },
  { key: 'pro',     name: '进阶技巧', emoji: '🎓' },
]

const basic = [
  { title: '上传文件或直接粘贴文本', goto: 'upload', body:
    `把 Word / PPT / PDF / Excel / CSV / TXT / Markdown / JSON / HTML 拖进上传框（≤30MB），<br>
     或者在「在线输入文本」里直接粘贴任意内容再点「解析文本」。<br>
     📷 图片也能传：自动 OCR，长图会智能切片后按序合并，低清图会先增强再识别。` },
  { title: '查看解析原文', goto: 'upload', body:
    `解析完成后，中间「解析原文」浮岛会展示全文与字数统计。<br>
     确认内容无误后，点右上角 <b>生成可视化</b> 即可开始。` },
  { title: '挑一个喜欢的主题', goto: 'template', body:
    `在「模板与主题中心」选主题：默认 <span class="tut-kbd">智能选型</span> 由 AI 根据内容自动配色。<br>
     选择后顶部徽标会实时同步；若已有生成结果，会提示重新生成以应用新主题。` },
  { title: '生成并观察进度', goto: 'upload', body:
    `生成通常需要 1~4 分钟。右侧浮岛会实时显示阶段、进度环与预计剩余时间。<br>
     AI 会逐段设计版式、配色与图表，完成后自动展示，<b>期间请勿关闭页面</b>。` },
  { title: '导出与分享', goto: 'export', body:
    `支持导出 PDF（右上角按钮，打印级版式）、下载 HTML、生成公开分享链接。<br>
     所有生成结果都会自动存入「历史记录」，可随时回看或收藏。` },
]

const modules = [
  { title: '文件上传与在线输入', goto: 'upload', body: `支持 9 种格式上传与 OCR；在线输入适合短文本、随手记录与表格粘贴。` },
  { title: '批量处理', goto: 'batch', body: `一次拖入多个文件排队生成，逐个出结果，适合批量报表场景。` },
  { title: '格式转换', goto: 'convert', body: `Word/PPT/PDF/TXT/Markdown/Excel/CSV 互转。旧版 .doc 请先另存为 .docx 再转。` },
  { title: '简历转化', goto: 'resume', body: `粘贴简历文本 → AI 提取结构化档案 → 生成 ATS 友好简历，可导出 PDF 与 Word。` },
  { title: '模板与主题中心', goto: 'template', body: `7 套视觉主题 + 附加要求输入。主题实时同步到全站状态。` },
  { title: '摘要与标签分类', goto: 'summary', body: `对已解析文档一键生成摘要与标签，快速判断内容价值。` },
  { title: '图表洞察', goto: 'insight', body: `AI 分析数据特征，推荐合适图表类型并给出洞察结论。` },
  { title: '历史记录', goto: 'history', body: `全部生成记录按时间排列，可回看、收藏、重命名、移入回收站。` },
  { title: '收藏', goto: 'fav', body: `星标的结果集中在这里，常用报告一秒直达。` },
  { title: '回收站', goto: 'trash', body: `删除的记录保留在回收站，可恢复或彻底清除（清除后不可找回）。` },
  { title: '导出与分享', goto: 'export', body: `HTML / PDF 导出、公开链接分享。分享链接可随时在历史记录中管理。` },
  { title: 'Agent 模型接入', goto: 'model', body: `内置 Agnes 大模型开箱即用；也可接入任意 OpenAI 兼容 API（可探活验证）。` },
  { title: '案例查看', goto: 'cases', body: `内置示例案例，没数据也能先感受生成效果。` },
  { title: '系统设置', goto: 'settings', body: `站点标题、生成温度、上下文长度、自动摘要开关等全局参数。` },
]

const pro = [
  { title: '附加要求：用「要求句」精确控版', goto: 'template', body:
    `在模板中心底部输入附加要求，越具体越好：<br>
     ✅ 「重点突出数据表格，用时间线呈现发展历程，整体商务风」<br>
     ❌ 「好看一点」（AI 无法执行的模糊表述）` },
  { title: '大文件自动分页', goto: 'upload', body:
    `超过 1000 行的 Excel/CSV 会自动切换大数据模式：页面分页加载、按列筛选，
     服务端只传当前页数据，万行级文件也能秒开。` },
  { title: '图片 OCR 的两个隐藏增强', goto: 'upload', body:
    `<b>长图切片</b>：聊天记录截图等超长图片会自动切片识别后按序合并，不漏字；<br>
     <b>低清增强</b>：模糊截图会先做对比度与锐化增强再识别，显著提升准确率。` },
  { title: '接入私有模型', goto: 'model', body:
    `「Agent 模型接入」中填入 OpenAI 兼容的 base_url 与 API key，
     点「探活」验证连通后设为默认即可；密钥只保存在你自己的服务端。` },
  { title: '主题 × 附加要求组合拳', goto: 'template', body:
    `先选 <span class="tut-kbd">商务黑金</span>，再附加「标题用衬线体、图表用金色渐变」，
     风格一致性远好于单独使用。生成不满意时换个组合再生成即可，历史不会丢失。` },
  { title: '分享链接与公开访问', goto: 'export', body:
    `「公开链接」生成的是只读分享地址，对方无需登录即可查看；
     源文件与可编辑权限始终留在你的账号里。` },
]

const current = computed(() => {
  if (tab.value === 'basic') return { steps: basic }
  if (tab.value === 'modules') return { steps: modules }
  return { steps: pro }
})

function goto(mod) {
  state.activeModule = mod
  // 面板切换后把视口带到功能岛顶部，形成「点了就到」的反馈
  document.querySelector('.island-feature')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function startTour() { window.__uvStartTour?.() }
</script>
