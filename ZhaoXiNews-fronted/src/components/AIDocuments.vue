<template>
  <section class="documents-panel">
    <h2>我的资料</h2>
    <p>支持 PDF 和 UTF-8 TXT，单文件最大 10 MB。文件片段会交给通义生成向量。</p>
    <div class="document-actions">
      <label>上传文件 <input type="file" accept=".pdf,.txt" :disabled="!!busy" @change="upload" /></label>
      <van-button size="small" :disabled="!!busy" @click="refresh">刷新</van-button>
    </div>
    <p v-if="busy" role="status">{{ busy }}</p>
    <p v-if="error" role="alert" class="document-error">{{ error }}</p>
    <ul v-if="documents.length" class="documents-list">
      <li v-for="document in documents" :key="document.id">
        <div>
          <strong>{{ document.filename }}</strong>
          <small>{{ statuses[document.status] }}</small>
        </div>
        <van-button size="small" plain type="danger" :disabled="!!busy" @click="remove(document)">删除</van-button>
      </li>
    </ul>
    <p v-else-if="!busy && !error">还没有上传资料。</p>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { showConfirmDialog } from 'vant';
import { apiConfig } from '../config/api';

const props = defineProps({ token: { type: String, required: true } });
const documents = ref([]);
const error = ref('');
const busy = ref('');
const controller = new AbortController();
const statuses = { indexing: '等待入库完成，可重新上传以恢复', ready: '可检索', failed: '入库失败，可重新上传', deleting: '等待清理，可重试删除' };
const endpoint = apiConfig.baseURL + '/api/ai/documents';

const request = async (path = '', options = {}) => {
  const response = await fetch(endpoint + path, {
    ...options,
    signal: controller.signal,
    headers: { Authorization: props.token, ...options.headers },
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.message || result.detail?.[0]?.msg || `资料请求失败（${response.status}）`);
  }
  return response.status === 204 ? null : response.json();
};

const refresh = async () => {
  if (busy.value) return;
  busy.value = '正在读取资料列表…';
  error.value = '';
  try {
    documents.value = await request();
  } catch (cause) {
    error.value = cause.message;
  } finally {
    busy.value = '';
  }
};

const upload = async (event) => {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file || busy.value) return;
  if (file.size > 10 * 1024 * 1024) {
    error.value = '文件大小不能超过 10 MB';
    return;
  }
  busy.value = '正在解析并索引文件…';
  error.value = '';
  try {
    await request('', {
      method: 'POST', body: file,
      headers: { 'Content-Type': 'application/octet-stream', 'X-Document-Name': encodeURIComponent(file.name) },
    });
  } catch (cause) {
    error.value = cause.message;
  } finally {
    try {
      documents.value = await request();
    } catch (cause) {
      error.value ||= cause.message;
    }
    busy.value = '';
  }
};

const remove = async (document) => {
  try {
    await showConfirmDialog({ title: '删除资料', message: `删除「${document.filename}」及其索引？` });
  } catch {
    return;
  }
  busy.value = '正在清理资料…';
  error.value = '';
  try {
    await request('/' + document.id, { method: 'DELETE' });
  } catch (cause) {
    error.value = cause.message;
  } finally {
    try {
      documents.value = await request();
    } catch (cause) {
      error.value ||= cause.message;
    }
    busy.value = '';
  }
};

onMounted(refresh);
onUnmounted(() => controller.abort());
</script>

<style scoped>
.documents-panel { padding: 20px 16px; }
.documents-panel p, .document-actions { margin: 12px 0; }
.document-actions, .documents-list li { display: flex; gap: 12px; align-items: center; justify-content: space-between; }
.document-actions input { display: block; width: 100%; margin-top: 6px; }
.documents-list li { padding: 10px 0; border-top: 1px solid #e7e7e7; overflow-wrap: anywhere; }
.documents-list small { display: block; margin-top: 4px; color: #646566; }
.document-error { color: #a92525; }
</style>
