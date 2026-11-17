<template>
  <canvas ref="cv" class="particle-canvas" aria-hidden="true"></canvas>
</template>

<script setup>
// 背景 3D 氛围层：漂浮光点 + 大型柔光球 + 细线几何体（三角/圆环），低透明度不干扰前景。
// 性能与可访问性：dPR 封顶 2、标签页隐藏自动暂停、prefers-reduced-motion 静态呈现。
import { ref, onMounted, onBeforeUnmount } from 'vue'

const cv = ref(null)
let ctx = null, raf = 0, W = 0, H = 0, dpr = 1
let particles = [], orbs = [], shapes = []
const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// 品牌协调的色相带：靛蓝/紫罗兰/青碧，避免满屏彩虹
const HUES = [222, 232, 248, 262, 172]
const rand = (a, b) => a + Math.random() * (b - a)

function resize() {
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  W = window.innerWidth; H = window.innerHeight
  cv.value.width = W * dpr; cv.value.height = H * dpr
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function seed() {
  const n = Math.min(56, Math.round(W * H / 30000))
  particles = Array.from({ length: n }, () => ({
    x: rand(0, W), y: rand(0, H),
    r: rand(0.7, 2.4),
    vx: rand(-0.12, 0.12), vy: rand(-0.2, -0.04),
    hue: HUES[Math.floor(Math.random() * HUES.length)],
    tw: rand(0.4, 1.4), ph: rand(0, Math.PI * 2),
  }))
  // 大型柔光球：极慢漂移，营造纵深
  orbs = Array.from({ length: 4 }, (_, i) => ({
    x: rand(0.1, 0.9), y: rand(0.15, 0.85),
    r: rand(120, 220),
    hue: HUES[i % HUES.length],
    vx: rand(-0.02, 0.02), vy: rand(-0.012, 0.012),
    a: rand(0.05, 0.1),
  }))
  // 细线几何体：慢速自旋 + 轻微浮动
  shapes = Array.from({ length: 6 }, () => ({
    x: rand(0.06, 0.94), y: rand(0.08, 0.92),
    s: rand(14, 34),                       // 尺寸
    kind: Math.random() < 0.5 ? 'tri' : 'ring',
    rot: rand(0, Math.PI * 2), vr: rand(-0.0016, 0.0016),
    vy: rand(-0.02, -0.006), sway: rand(0, Math.PI * 2),
    a: rand(0.08, 0.16),
  }))
}

function draw(t) {
  ctx.clearRect(0, 0, W, H)

  // 1) 柔光球（径向渐变，最底层）
  for (const o of orbs) {
    if (!reduced) {
      o.x += o.vx / W * 60; o.y += o.vy / H * 60
      if (o.x < 0.02 || o.x > 0.98) o.vx *= -1
      if (o.y < 0.05 || o.y > 0.95) o.vy *= -1
    }
    const g = ctx.createRadialGradient(o.x * W, o.y * H, 0, o.x * W, o.y * H, o.r)
    g.addColorStop(0, `hsla(${o.hue}, 80%, 66%, ${o.a})`)
    g.addColorStop(1, `hsla(${o.hue}, 80%, 66%, 0)`)
    ctx.fillStyle = g
    ctx.beginPath(); ctx.arc(o.x * W, o.y * H, o.r, 0, Math.PI * 2); ctx.fill()
  }

  // 2) 细线几何体（线框三角 / 圆环）
  for (const s of shapes) {
    if (!reduced) {
      s.rot += s.vr
      s.y += s.vy / H * 60
      if (s.y < -0.06) { s.y = 1.06; s.x = rand(0.06, 0.94) }
    }
    const x = s.x * W + Math.sin(t / 2400 + s.sway) * 10
    const y = s.y * H
    ctx.save()
    ctx.translate(x, y); ctx.rotate(s.rot)
    ctx.strokeStyle = `hsla(232, 60%, 58%, ${s.a})`
    ctx.lineWidth = 1
    if (s.kind === 'tri') {
      ctx.beginPath()
      for (let k = 0; k < 3; k++) {
        const ang = -Math.PI / 2 + k * Math.PI * 2 / 3
        k === 0 ? ctx.moveTo(Math.cos(ang) * s.s, Math.sin(ang) * s.s)
                : ctx.lineTo(Math.cos(ang) * s.s, Math.sin(ang) * s.s)
      }
      ctx.closePath(); ctx.stroke()
    } else {
      ctx.beginPath(); ctx.arc(0, 0, s.s, 0, Math.PI * 2); ctx.stroke()
      ctx.beginPath(); ctx.arc(0, 0, s.s * 0.55, 0, Math.PI * 2); ctx.stroke()
    }
    ctx.restore()
  }

  // 3) 炫彩光点
  for (const p of particles) {
    if (!reduced) {
      p.x += p.vx; p.y += p.vy
      if (p.y < -8) { p.y = H + 8; p.x = rand(0, W) }
      if (p.x < -8) p.x = W + 8
      if (p.x > W + 8) p.x = -8
    }
    const a = 0.14 + 0.13 * (0.5 + 0.5 * Math.sin(t / 1400 * p.tw + p.ph))
    const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3.2)
    g.addColorStop(0, `hsla(${p.hue}, 85%, 62%, ${a})`)
    g.addColorStop(1, `hsla(${p.hue}, 85%, 62%, 0)`)
    ctx.fillStyle = g
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 3.2, 0, Math.PI * 2); ctx.fill()
    ctx.fillStyle = `hsla(${p.hue}, 80%, 58%, ${Math.min(0.5, a + 0.16)})`
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 0.75, 0, Math.PI * 2); ctx.fill()
  }
}

function loop(t) {
  draw(t)
  raf = requestAnimationFrame(loop)
}

function onVis() {
  cancelAnimationFrame(raf)
  if (!document.hidden && !reduced) raf = requestAnimationFrame(loop)
}

onMounted(() => {
  ctx = cv.value.getContext('2d')
  resize(); seed()
  if (reduced) draw(0)
  else raf = requestAnimationFrame(loop)
  window.addEventListener('resize', resize)
  window.addEventListener('resize', seed)
  document.addEventListener('visibilitychange', onVis)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
  window.removeEventListener('resize', seed)
  document.removeEventListener('visibilitychange', onVis)
})
</script>

<style scoped>
.particle-canvas {
  position: fixed; inset: 0; z-index: 1;
  width: 100vw; height: 100vh;
  pointer-events: none;
}
</style>
