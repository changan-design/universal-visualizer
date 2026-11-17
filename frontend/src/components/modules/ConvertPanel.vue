<template>
  <div class="scroll-area">
    <h3 class="module-title">格式转换</h3>
    <div class="card-box">
      <el-upload drag :show-file-list="false" :before-upload="pick" accept=".docx,.pptx,.pdf,.txt,.md,.markdown,.json,.html,.csv,.xlsx,.xls">
        <el-icon size="32" style="color:var(--primary)"><UploadFilled /></el-icon>
        <div style="margin-top:4px">选择要转换的文件</div>
        <template #tip>
          <div class="hint" style="margin-top:6px">支持 Word / PPT / PDF / TXT / Markdown / Excel / CSV · 单文件 ≤30MB</div>
        </template>
      </el-upload>

      <div v-if="file" class="hint" style="margin:8px 0">
        已选择：{{ file.name }}
        <span v-if="ext"> · 可转为 {{ labelsText || '—' }}</span>
      </div>

      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
        <el-button v-for="t in targets" :key="t" size="small"
                   :disabled="!file || loading" :loading="loading && pending === t"
                   @click="convert(t)">转为 {{ label(t) }}</el-button>
      </div>
      <div v-if="file && !targets.length && !loading" class="hint" style="margin-top:8px;color:#e05666">
        该格式暂不支持转换（旧版 .doc 请先另存为 .docx 或 PDF）
      </div>
      <div v-if="done.length" class="hint" style="margin-top:10px">
        <div v-for="d in done" :key="d">✓ {{ d }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as api from '../../api'
import { withWave } from '../../loading'

const file = ref(null)
const loading = ref(false)
const pending = ref('')
const targets = ref([])
const labels = ref({})
const done = ref([])
const ext = computed(() => {
  const n = file.value?.name || ''
  const i = n.lastIndexOf('.')
  return i >= 0 ? n.slice(i).toLowerCase() : ''
})
const labelsText = computed(() => targets.value.map(label).join(' / '))

function label(t) { return labels.value[t] || t.replace('.', '').toUpperCase() }

async function pick(f) {
  file.value = f
  done.value = []
  targets.value = []
  try {
    const res = await api.convertTargets(ext.value)
    targets.value = res.targets || []
    labels.value = res.labels || {}
    if (!targets.value.length) ElMessage.warning('该格式暂不支持转换，请另存为 .docx / PDF 后重试')
  } catch { /* 拦截器已提示 */ }
  return false // 阻止 el-upload 自动上传
}

async function convert(target) {
  if (!file.value || loading.value) return
  loading.value = true
  pending.value = target
  try {
    const blob = await withWave(`正在转换为 ${label(target)}…`, `${file.value.name} · 浪涌处理中，请勿重复点击`,
                                () => api.convertFile(file.value, target))
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.value.name.replace(/\.[^.]+$/, '') + target
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 4000)
    done.value.push(`${file.value.name} → ${label(target)}`)
    ElMessage.success('转换完成，已开始下载')
  } catch { /* 拦截器已展示后端原因 */ } finally {
    loading.value = false
    pending.value = ''
  }
}
</script>
