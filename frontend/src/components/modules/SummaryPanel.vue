<template>
  <div class="scroll-area">
    <h3 class="module-title">摘要与标签分类</h3>
    <el-button type="primary" size="small" :disabled="!state.fileId" :loading="loading" @click="run">
      分析当前文档
    </el-button>
    <div v-if="!state.fileId" class="hint" style="margin-top:8px">请先上传文件或输入文本</div>

    <template v-if="result">
      <div class="card-box" style="margin-top:14px">
        <div style="font-weight:700;font-size:15px">{{ result.title }}</div>
        <div class="tag-line">
          <el-tag size="small" type="warning">{{ result.category }}</el-tag>
          <el-tag v-for="t in result.tags" :key="t" size="small" type="info">{{ t }}</el-tag>
        </div>
        <p style="font-size:13px;line-height:1.8;color:#444">{{ result.summary }}</p>
        <div class="hint">关键词：{{ result.keywords?.join(' / ') }}　|　内容形态：{{ result.content_type }}　|　建议主题：{{ result.suggested_theme }}</div>
        <el-button size="small" style="margin-top:8px" @click="applyTheme">应用建议主题</el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '../../api'
import { withWave } from '../../loading'

const state = inject('appState')
const loading = ref(false)
const result = ref(null)

async function run() {
  loading.value = true
  try {
    result.value = await withWave('正在生成摘要…', 'AI 阅读全文并提炼要点', () => api.summarize({ file_id: state.fileId, model_id: state.modelId || null }))
  } finally { loading.value = false }
}
function applyTheme() {
  if (result.value?.suggested_theme) state.theme = result.value.suggested_theme
}
</script>
