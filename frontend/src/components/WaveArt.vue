<template>
  <!-- 三层涌浪 + 浪尖白沫 + 上升浮沫：海浪主题核心视觉（供全局加载层 / 生成进度卡复用） -->
  <div class="wa-visual" :style="{ width: w + 'px', height: h + 'px' }" aria-hidden="true">
    <svg class="wa-svg" viewBox="0 0 240 90" preserveAspectRatio="none">
      <defs>
        <linearGradient :id="uid + '-back'" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#7fd4cf" stop-opacity=".38"/>
          <stop offset="1" stop-color="#14798f" stop-opacity=".05"/>
        </linearGradient>
        <linearGradient :id="uid + '-mid'" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#38b6c9" stop-opacity=".62"/>
          <stop offset="1" stop-color="#0f3d5c" stop-opacity=".12"/>
        </linearGradient>
        <linearGradient :id="uid + '-front'" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#1f7fa0" stop-opacity=".92"/>
          <stop offset="1" stop-color="#071a33" stop-opacity=".55"/>
        </linearGradient>
      </defs>
      <g class="wa wa-back">
        <path :d="wavePath(34, 14)" :fill="`url(#${uid}-back)`"/>
      </g>
      <g class="wa wa-mid">
        <path :d="wavePath(26, 11)" :fill="`url(#${uid}-mid)`"/>
      </g>
      <g class="wa wa-front">
        <path :d="wavePath(20, 8)" :fill="`url(#${uid}-front)`"/>
        <path :d="wavePath(20, 8, true)" fill="none" stroke="rgba(255,255,255,.85)"
              stroke-width="1.6" stroke-linecap="round"/>
      </g>
    </svg>
    <i v-for="n in 7" :key="n" class="wa-bubble" :style="bubbleStyle(n)"></i>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  w: { type: Number, default: 230 },
  h: { type: Number, default: 143 },
})
// 多实例同屏时渐变 id 冲突防护
const uid = ref('wa' + Math.random().toString(36).slice(2, 8))

// 生成「两倍宽」的重复波形路径（滚动一个周期即可无缝循环）
function wavePath(baseY, amp, strokeOnly = false) {
  const seg = (x0, dir) => {
    const s = dir ? 1 : -1
    return `C ${x0 + 15} ${baseY - s * amp}, ${x0 + 45} ${baseY - s * amp}, ${x0 + 60} ${baseY}`
  }
  let d = `M 0 ${baseY}`
  for (let i = 0; i < 8; i++) d += seg(i * 60, i % 2 === 0)
  return strokeOnly ? d : d + ` L 480 100 L 0 100 Z`
}

function bubbleStyle(n) {
  return {
    left: 8 + (n * 13) % 84 + '%',
    width: 3 + (n % 3) * 2 + 'px',
    height: 3 + (n % 3) * 2 + 'px',
    animationDuration: 2.2 + (n % 4) * 0.7 + 's',
    animationDelay: -(n * 0.6) + 's',
  }
}
</script>

<style scoped>
.wa-visual { position: relative; overflow: hidden; border-radius: 14px; }
.wa-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
/* 三层浪不同相位/速度：back 慢、front 快，制造纵深 */
.wa { animation: wa-slide 3.2s linear infinite; }
.wa-back  { animation-duration: 4.6s; }
.wa-mid   { animation-duration: 3.6s; animation-direction: reverse; }
.wa-front { animation-duration: 2.7s; }
@keyframes wa-slide {
  from { transform: translateX(0); }
  to   { transform: translateX(-240px); }
}
.wa-bubble {
  position: absolute; bottom: 6px; border-radius: 50%;
  border: 1px solid rgba(255,255,255,.55);
  background: radial-gradient(circle at 32% 30%, rgba(255,255,255,.5), rgba(255,255,255,.06) 65%);
  animation: wa-bubble-rise linear infinite;
}
@keyframes wa-bubble-rise {
  from { transform: translateY(0); opacity: 0; }
  15%  { opacity: .9; }
  to   { transform: translateY(-110px); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .wa, .wa-bubble { animation-duration: .01ms !important; }
}
</style>
