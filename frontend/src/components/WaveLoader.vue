<template>
  <!-- 全屏海浪加载遮罩：毛玻璃 + 三层涌浪 + 浮沫气泡，遮挡等待期操作，杜绝重复点击 -->
  <Transition name="wave-fade">
    <div v-if="waveLoading.visible" class="wave-mask" role="alert" aria-live="polite">
      <div class="wave-stage">
        <WaveArt :w="230" :h="130" />
        <div class="wave-text">{{ waveLoading.text }}</div>
        <div v-if="waveLoading.sub" class="wave-sub">{{ waveLoading.sub }}</div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import WaveArt from './WaveArt.vue'
import { waveLoading } from '../loading'
</script>

<style scoped>
.wave-mask {
  position: fixed; inset: 0; z-index: 2600;
  background: rgba(6, 26, 51, .42);
  backdrop-filter: blur(10px) saturate(1.3);
  -webkit-backdrop-filter: blur(10px) saturate(1.3);
  display: flex; align-items: center; justify-content: center;
}
.wave-stage {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 34px 46px 28px; border-radius: 24px;
  background: rgba(255, 255, 255, .14);
  border: 1px solid rgba(255, 255, 255, .35);
  box-shadow: 0 18px 60px rgba(3, 16, 34, .45), inset 0 1px 0 rgba(255,255,255,.4);
  animation: stage-in .5s cubic-bezier(.22,1.3,.5,1);
}
@keyframes stage-in { from { opacity: 0; transform: translateY(26px) scale(.94); } }
.wave-text { margin-top: 14px; font-size: 15px; font-weight: 700; color: #fff; letter-spacing: .5px; }
.wave-sub { font-size: 12px; color: rgba(255,255,255,.75); }
.wave-fade-enter-active, .wave-fade-leave-active { transition: opacity .35s var(--ease, ease); }
.wave-fade-enter-from, .wave-fade-leave-to { opacity: 0; }
</style>
