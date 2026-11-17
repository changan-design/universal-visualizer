<template>
  <div class="landing" :class="{ leaving }" role="dialog" aria-label="欢迎页：真实海浪拍岸入场动画">
    <!-- 底色：深海渐变（视频加载前与失败时的兜底，保证任何网络状况下都成立） -->
    <div class="ld-fallback" aria-hidden="true">
      <span class="fb-glow g1"></span><span class="fb-glow g2"></span><span class="fb-glow g3"></span>
      <i v-for="n in 14" :key="n" class="fb-bubble" :style="bubbleStyle(n)"></i>
    </div>

    <!-- 主视觉：真实海浪拍岸视频（免费商用素材，Mixkit License，无需署名） -->
    <video ref="video" class="ld-video" :class="{ ready: videoReady }" src="/waves.mp4" muted loop playsinline
           autoplay preload="auto" @canplay="videoReady = true" @error="videoFailed = true"
           aria-hidden="true"></video>

    <!-- 渐变遮罩：上深下浅，保证品牌文字可读且与工作台色调衔接 -->
    <div class="ld-veil" aria-hidden="true"></div>

    <!-- UI 层 -->
    <div class="ld-ui" :class="{ hide: leaving }">
      <div class="ld-brand">
        <div class="ld-logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none">
            <defs><linearGradient id="ld-g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#cfe0ff"/>
            </linearGradient></defs>
            <path d="M12 2.4 L21 12 L12 21.6 L3 12 Z" fill="url(#ld-g)" opacity=".95"/>
            <path d="M12 6.8 L16.4 12 L12 17.2 L7.6 12 Z" fill="#4f6ef7"/>
          </svg>
        </div>
        <div class="ld-title">万能可视化</div>
        <div class="ld-sub">UNIVERSAL VISUALIZER</div>
      </div>
      <p class="ld-slogan">潮起之处，<br>文档与数据化作流动的光。</p>

      <button class="ld-enter" @click="enter">
        进入工作台
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M5 12h13"/><path d="M12 5l7 7-7 7"/>
        </svg>
      </button>
      <div class="ld-skip" role="button" tabindex="0" @click="enter" @keyup.enter="enter">跳过动画</div>
    </div>

    <!-- 底部浪潮线：与视频浪线呼应的装饰性 SVG 波纹 -->
    <svg class="ld-wave-line" viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0 50 C 180 20 360 76 540 52 C 720 28 900 72 1080 50 C 1260 28 1360 58 1440 44 L 1440 90 L 0 90 Z"
            fill="rgba(255,255,255,.10)"/>
      <path d="M0 62 C 200 36 400 84 620 60 C 840 38 1020 78 1220 58 C 1330 48 1400 62 1440 56 L 1440 90 L 0 90 Z"
            fill="rgba(255,255,255,.14)"/>
    </svg>
  </div>
</template>

<script setup>
// 首页进入页 v3：真实海浪拍岸视频 + 涨潮过渡。
// 可靠性设计：视频异步加载，加载完成前显示深海渐变兜底层；
// 视频加载失败（离线/格式不支持）时停留在兜底层，功能不受影响。
// 可访问性：prefers-reduced-motion 时不播视频，直接呈现静态首帧式布局。
import { ref, onMounted, onBeforeUnmount } from 'vue'

const emit = defineEmits(['enter'])

const video = ref(null)
const videoReady = ref(false)
const videoFailed = ref(false)
const leaving = ref(false)
let leavingTimer = 0

const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// 兜底层的装饰气泡位置（SSR 安全：纯客户端渲染，直接取随机值）
function bubbleStyle(n) {
  const size = 4 + (n * 7) % 14
  return {
    left: (n * 7.3) % 100 + 'vw',
    width: size + 'px', height: size + 'px',
    animationDuration: 9 + (n % 6) * 2.4 + 's',
    animationDelay: -(n * 1.7) % 12 + 's',
  }
}

function enter() {
  if (leaving.value) return
  leaving.value = true
  // 涨潮过渡：UI 先沉入，620ms 后通知父组件切换（过渡时间与 CSS 对齐）
  leavingTimer = setTimeout(() => emit('enter'), 620)
  try { sessionStorage.setItem('uv-landing-seen', '1') } catch { /* ignore */ }
}

function onKey(e) {
  if (e.key === 'Enter' || e.key === ' ') enter()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  if (reduced) { video.value?.removeAttribute('autoplay') }
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  clearTimeout(leavingTimer)
})
</script>

<style scoped>
.landing {
  position: fixed; inset: 0; z-index: 60; overflow: hidden;
  background: linear-gradient(168deg, #06182f 0%, #0a2c4d 40%, #0f4a67 100%);
  transition: filter .62s var(--ease), transform .62s var(--ease), opacity .62s var(--ease);
}
/* 涨潮离场：整个画面被「浪头」推近并上浮淡出 */
.landing.leaving { filter: brightness(1.35) blur(2px); transform: scale(1.06) translateY(-2.5%); opacity: 0; }

/* ---- 视频层 ---- */
.ld-video {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; opacity: 0; transform: scale(1.04);
  transition: opacity 1.1s ease, transform 1.4s var(--ease);
}
.ld-video.ready { opacity: 1; transform: scale(1); }

/* ---- 兜底层：深海渐变 + 光斑 + 气泡（视频未就绪/失败时可见） ---- */
.ld-fallback { position: absolute; inset: 0; overflow: hidden; }
.fb-glow { position: absolute; border-radius: 50%; filter: blur(70px); }
.fb-glow.g1 { width: 560px; height: 560px; left: -8%; top: -12%; background: radial-gradient(circle, rgba(64,140,255,.34), transparent 66%); animation: fb-drift 17s ease-in-out infinite alternate; }
.fb-glow.g2 { width: 640px; height: 640px; right: -10%; top: 22%; background: radial-gradient(circle, rgba(38,208,206,.26), transparent 64%); animation: fb-drift 21s ease-in-out infinite alternate-reverse; }
.fb-glow.g3 { width: 520px; height: 520px; left: 30%; bottom: -18%; background: radial-gradient(circle, rgba(20,121,143,.4), transparent 66%); animation: fb-drift 24s ease-in-out infinite alternate; }
@keyframes fb-drift { to { transform: translate(46px, 30px) scale(1.1); } }
.fb-bubble {
  position: absolute; bottom: -16px; border-radius: 50%;
  border: 1px solid rgba(255,255,255,.25);
  background: radial-gradient(circle at 32% 30%, rgba(255,255,255,.34), rgba(255,255,255,.05) 62%);
  animation: fb-rise linear infinite;
}
@keyframes fb-rise { from { transform: translateY(0); opacity: 0; } 10% { opacity: .75; } to { transform: translateY(-104vh); opacity: 0; } }

/* ---- 遮罩：顶部压暗保证标题可读，底部衔接工作台色系 ---- */
.ld-veil {
  position: absolute; inset: 0;
  background:
    linear-gradient(180deg, rgba(5, 20, 40, .52) 0%, rgba(5, 20, 40, .10) 34%, rgba(5, 24, 44, .16) 62%, rgba(7, 26, 51, .58) 100%);
}

/* ---- UI 层 ---- */
.ld-ui {
  position: absolute; inset: 0; z-index: 3; pointer-events: none;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; color: #fff;
  transition: opacity .45s ease, transform .45s var(--ease);
}
.ld-ui.hide { opacity: 0; transform: translateY(-26px); }
.ld-brand { display: flex; flex-direction: column; align-items: center; gap: 8px; animation: ld-rise .9s var(--ease) both; }
.ld-logo {
  width: 56px; height: 56px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #4f6ef7 0%, #7c5cf7 55%, #8b5cf6 100%);
  box-shadow: 0 10px 34px rgba(79, 110, 247, .5), inset 0 1px 0 rgba(255, 255, 255, .4);
}
.ld-title { font-size: 34px; font-weight: 800; letter-spacing: 6px; text-shadow: 0 2px 24px rgba(5, 22, 44, .55); }
.ld-sub { font-size: 10.5px; letter-spacing: 5px; opacity: .75; font-weight: 550; }
.ld-slogan {
  margin: 26px 0 0; font-size: 15px; line-height: 2; letter-spacing: 2px; opacity: .92;
  text-shadow: 0 2px 18px rgba(5, 22, 44, .6);
  animation: ld-rise .9s .18s var(--ease) both;
}
.ld-enter {
  margin-top: 34px; pointer-events: auto; position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 9px;
  padding: 13px 36px; border: 1px solid rgba(255,255,255,.5); border-radius: 999px; cursor: pointer;
  font-size: 14.5px; font-weight: 650; font-family: inherit; letter-spacing: 2px; color: #fff;
  background: linear-gradient(135deg, rgba(79,110,247,.92), rgba(139,92,246,.88));
  box-shadow: 0 8px 30px rgba(30, 70, 160, .55), inset 0 1px 0 rgba(255,255,255,.4);
  animation: ld-rise .9s .34s var(--ease) both;
  transition: transform .22s var(--ease-wave), box-shadow .22s var(--ease);
}
.ld-enter::after {   /* 按钮内的流动光带：呼应海面反光 */
  content: ''; position: absolute; top: 0; left: -70%; width: 55%; height: 100%;
  background: linear-gradient(105deg, transparent, rgba(255,255,255,.35), transparent);
  transform: skewX(-18deg); animation: ld-shine 3.4s var(--ease) infinite;
}
@keyframes ld-shine { 0%, 55% { left: -70%; } 100% { left: 130%; } }
.ld-enter:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 14px 42px rgba(30, 70, 160, .7); }
.ld-enter:active { transform: translateY(-1px) scale(.98); }
.ld-enter:focus-visible { outline: 2px solid #fff; outline-offset: 3px; }
.ld-skip {
  margin-top: 14px; pointer-events: auto; cursor: pointer; user-select: none;
  font-size: 11.5px; letter-spacing: 2px; opacity: .62; padding: 5px 12px; border-radius: 999px;
  transition: opacity .2s;
  animation: ld-rise .9s .5s var(--ease) both;
}
.ld-skip:hover { opacity: 1; }
@keyframes ld-rise { from { opacity: 0; transform: translateY(22px); } }

/* 底部装饰浪潮线 */
.ld-wave-line { position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: 90px; z-index: 2; pointer-events: none; }

@media (max-width: 640px) {
  .ld-title { font-size: 26px; letter-spacing: 4px; }
  .ld-slogan { font-size: 13.5px; }
}
@media (prefers-reduced-motion: reduce) {
  .ld-video { transition: none; }
  .ld-brand, .ld-slogan, .ld-enter, .ld-skip { animation: none; }
  .ld-enter::after { animation: none; }
}
</style>
