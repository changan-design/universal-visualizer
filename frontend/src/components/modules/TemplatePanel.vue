<template>
  <div class="scroll-area">
    <h3 class="module-title">模板与主题中心</h3>
    <div class="hint" style="margin-bottom:12px">
      选择生成页面的视觉主题。「智能选型」由 AI 根据内容主题自动匹配最合适的风格。
      选择后 <b>全站实时同步</b>：顶部徽标即时更新；已有生成结果时会提示重新生成以应用新主题。
    </div>

    <div v-for="t in themes" :key="t.key"
         class="theme-card" :class="{ active: state.theme === t.key }"
         role="button" tabindex="0" :aria-label="t.name"
         @click="pick(t.key)" @keyup.enter="pick(t.key)">
      <div class="swatch" :style="{ background: t.bg }">
        <span v-for="c in t.dots" :key="c" class="dot" :style="{ background: c }"></span>
      </div>
      <div>
        <div style="font-weight:600;font-size:13px">{{ t.name }}</div>
        <div class="hint">{{ t.desc }}</div>
      </div>
      <el-icon v-if="state.theme === t.key" color="var(--primary)" style="margin-left:auto" class="check-pop"><Check /></el-icon>
    </div>

    <el-input v-model="state.extraReq" type="textarea" :rows="3" size="small"
              style="margin-top:12px" placeholder="附加要求（可选）：如“重点突出数据表格”“加入时间线”…" />

    <!-- 联动提示：已有结果时切换主题 -->
    <transition name="fade-slide">
      <div v-if="regenHint" class="card-box regen-box">
        <div style="font-weight:600;font-size:12.5px;margin-bottom:4px">🔄 主题已切换为「{{ currentName }}」</div>
        <div class="hint" style="margin-bottom:8px">新生成将使用新主题；右侧已有结果保持原样。</div>
        <el-button size="small" type="primary" round @click="regen">用新主题重新生成</el-button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { inject, computed, ref } from 'vue'
import { Check } from '@element-plus/icons-vue'
import * as api from '../../api'
import { themeName } from '../../theme'

const state = inject('appState')
const themes = [
  { key: 'auto',        name: '🎯 智能选型', desc: 'AI 根据内容主题自动匹配最佳风格', bg: 'linear-gradient(135deg,#667eea,#764ba2)', dots: ['#fff','#ffd'] },
  { key: 'tech-blue',   name: '科技蓝', desc: '深蓝底 + 电光蓝，玻璃拟态', bg: 'linear-gradient(135deg,#0B1220,#1D4ED8)', dots: ['#3B82F6','#93C5FD'] },
  { key: 'biz-gold',    name: '商务黑金', desc: '炭黑 + 香槟金，衬线标题', bg: 'linear-gradient(135deg,#111,#3a2f0b)', dots: ['#C9A227','#E7C873'] },
  { key: 'fresh-green', name: '清新自然', desc: '米白 + 森林绿', bg: 'linear-gradient(135deg,#F7F5EF,#2F6B4F)', dots: ['#2F6B4F','#86C99B'] },
  { key: 'warm-orange', name: '暖橙活力', desc: '奶油白 + 珊瑚橙', bg: 'linear-gradient(135deg,#FFF8F0,#E8622C)', dots: ['#E8622C','#FFB380'] },
  { key: 'minimal',     name: '极简杂志', desc: '纯白 + 留白 + 一处强调色', bg: 'linear-gradient(135deg,#fff,#e5e5e5)', dots: ['#111','#E11D48'] },
  { key: 'dark-neon',   name: '暗黑霓虹', desc: '深底 + 霓虹紫青渐变', bg: 'linear-gradient(135deg,#0A0A12,#7C3AED)', dots: ['#A78BFA','#22D3EE'] },
]

const currentName = computed(() => themeName(state.theme))
const regenHint = ref(false)
const lastPicked = ref('')

// 主题选择：立即写全局状态（App watch 负责徽标闪光与跨面板同步），
// 且当已有生成结果、新主题与生成时主题不同时，在本面板给出「重新生成」引导。
function pick(key) {
  if (state.theme === key) return
  state.theme = key
  lastPicked.value = key
  regenHint.value = !!(state.previewSrc && state.generatedTheme && key !== state.generatedTheme)
}

async function regen() {
  if (!state.fileId) return
  regenHint.value = false
  // 直接复用主生成流程（进度展示在右侧预览岛）
  window.__uvRegenerate?.()
}
</script>

<style scoped>
.theme-card {
  display: flex; gap: 12px; align-items: center; padding: 10px 12px; border: 1.5px solid rgba(120,140,175,.22);
  border-radius: 10px; margin-bottom: 8px; cursor: pointer; transition: all .18s var(--ease);
  background: rgba(255,255,255,.78); user-select: none;
}
.theme-card:hover { border-color: rgba(79,110,247,.45); transform: translateY(-1px); box-shadow: var(--shadow); }
.theme-card:active { transform: scale(.985); }
.theme-card.active { border-color: var(--primary); background: var(--primary-soft); }
.swatch {
  width: 52px; height: 36px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: flex-end; gap: 4px; padding: 5px;
  transition: transform .25s var(--ease-wave);
}
.theme-card:hover .swatch { transform: scale(1.06) rotate(-1deg); }
.dot { width: 9px; height: 9px; border-radius: 50%; }
.check-pop { animation: pop .4s var(--ease-wave); }
@keyframes pop { from { transform: scale(0); } to { transform: scale(1); } }
.regen-box { border-color: rgba(79,110,247,.4); background: var(--primary-soft); }
.fade-slide-enter-active, .fade-slide-leave-active { transition: all .3s var(--ease); }
.fade-slide-enter-from, .fade-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
