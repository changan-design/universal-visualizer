<template>
  <!-- 右下角玻璃调节浮标：实时调整整站玻璃透明度（毛玻璃通透感），localStorage 记忆 -->
  <div class="gt-host" :class="{ open }">
    <Transition name="gt-pop">
      <div v-if="open" class="gt-panel">
        <div class="gt-title">🌊 玻璃通透度</div>
        <div class="gt-row">
          <el-slider v-model="alphaPct" :min="55" :max="100" :step="1"
                     :show-tooltip="false" style="flex:1" size="small" />
          <span class="gt-val">{{ alphaPct }}%</span>
        </div>
        <div class="gt-presets">
          <button v-for="p in presets" :key="p.v" class="gt-preset"
                  :class="{ on: alphaPct === p.v }" @click="alphaPct = p.v">{{ p.t }}</button>
        </div>
        <div class="gt-hint">实时生效 · 偏好自动保存</div>
      </div>
    </Transition>
    <button class="gt-fab" :title="open ? '收起透明度调节' : '调节页面玻璃透明度'"
            :aria-expanded="open" @click="open = !open">
      <span class="gt-icon">◐</span>
    </button>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const open = ref(false)
const alphaPct = ref(82)     // 默认与原设计一致
const presets = [
  { t: '朦胧', v: 60 }, { t: '通透', v: 74 }, { t: '标准', v: 82 }, { t: '凝实', v: 94 },
]
const KEY = 'uv-glass-alpha'

function apply(v) {
  // 三层玻璃同步联动：浮岛 / 浮坞 / 卡片按基准值派生，保证层级关系不变
  const a = Math.min(1, Math.max(0.55, v / 100))
  const root = document.documentElement.style
  root.setProperty('--glass-alpha', a.toFixed(3))
  root.setProperty('--glass-dock-alpha', Math.max(0.5, a - 0.06).toFixed(3))
  root.setProperty('--card-alpha', Math.max(0.5, a - 0.04).toFixed(3))
}

watch(alphaPct, v => {
  apply(v)
  try { localStorage.setItem(KEY, String(v)) } catch { /* ignore */ }
})

onMounted(() => {
  try {
    const saved = Number(localStorage.getItem(KEY))
    if (saved >= 55 && saved <= 100) alphaPct.value = saved
    else apply(alphaPct.value)
  } catch { apply(alphaPct.value) }
})
</script>

<style scoped>
.gt-host { position: fixed; right: 20px; bottom: 22px; z-index: 2400; display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
.gt-fab {
  width: 46px; height: 46px; border-radius: 50%; border: 1px solid rgba(255,255,255,.55);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, rgba(30, 90, 130, .78), rgba(10, 44, 76, .82));
  backdrop-filter: blur(14px) saturate(1.6); -webkit-backdrop-filter: blur(14px) saturate(1.6);
  color: #fff; font-size: 18px;
  box-shadow: 0 8px 26px rgba(3, 16, 34, .45), inset 0 1px 0 rgba(255,255,255,.35);
  transition: transform .22s var(--ease-wave, ease), box-shadow .22s;
}
.gt-fab:hover { transform: translateY(-3px) rotate(-14deg); box-shadow: 0 12px 32px rgba(3, 16, 34, .55); }
.gt-host.open .gt-fab { transform: rotate(0); }
.gt-panel {
  width: 240px; padding: 14px 16px 12px; border-radius: 18px;
  background: rgba(12, 36, 62, .78); backdrop-filter: blur(20px) saturate(1.6);
  -webkit-backdrop-filter: blur(20px) saturate(1.6);
  border: 1px solid rgba(255,255,255,.30);
  box-shadow: 0 14px 44px rgba(3, 16, 34, .5), inset 0 1px 0 rgba(255,255,255,.28);
}
.gt-title { font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 10px; letter-spacing: .5px; }
.gt-row { display: flex; align-items: center; gap: 10px; }
.gt-val { font-size: 12px; font-weight: 600; color: #9fe3de; min-width: 38px; text-align: right; font-variant-numeric: tabular-nums; }
.gt-presets { display: flex; gap: 6px; margin-top: 10px; }
.gt-preset {
  flex: 1; padding: 4px 0; border-radius: 8px; cursor: pointer; font-size: 11.5px;
  border: 1px solid rgba(255,255,255,.25); background: rgba(255,255,255,.10); color: rgba(255,255,255,.85);
  transition: all .18s;
}
.gt-preset:hover { background: rgba(255,255,255,.2); }
.gt-preset.on { border-color: #7fd4cf; background: rgba(127, 212, 207, .28); color: #fff; font-weight: 600; }
.gt-hint { margin-top: 9px; font-size: 10.5px; color: rgba(255,255,255,.55); }
.gt-pop-enter-active, .gt-pop-leave-active { transition: all .28s cubic-bezier(.22,1.3,.5,1); }
.gt-pop-enter-from, .gt-pop-leave-to { opacity: 0; transform: translateY(12px) scale(.92); }
/* 滑块配色融入深色面板 */
.gt-panel :deep(.el-slider__runway) { background: rgba(255,255,255,.18); }
.gt-panel :deep(.el-slider__bar) { background: linear-gradient(90deg, #38b6c9, #7fd4cf); }
</style>
