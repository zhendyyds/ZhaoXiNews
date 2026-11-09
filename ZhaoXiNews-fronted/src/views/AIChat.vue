<template>
  <div class="ai-chat-container">
    <van-nav-bar title="AI问答" fixed />
    
    <div class="chat-content">
      <div class="messages-container" ref="messagesContainer">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-content">
            <div v-if="message.role === 'assistant' && message.content === '' && !message.error" class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
              <small>{{ message.status }}</small>
            </div>
            <div v-else v-html="formatMessage(message.content)"></div>
            <p v-if="message.error" class="message-error" role="alert">{{ message.error }}</p>
            <div v-if="message.sources?.length" class="news-sources">
              <strong>{{ message.mode === 'news' ? '报道时间线 · 原文' : '参考来源' }}</strong>
              <ol>
                <li v-for="source in message.sources" :key="source.number">
                  <template v-if="source.kind === 'document'">
                    <small>资料</small> {{ source.title }} · {{ source.page ? `第 ${source.page} 页` : `片段 ${source.chunk}` }}
                  </template>
                  <template v-else>
                    <small v-if="source.kind === 'favorite'">收藏</small>
                    <time :datetime="source.publishedAt">{{ source.publishedAt.slice(0, 10) }}</time>
                    <router-link :to="source.url">{{ source.title }}</router-link>
                  </template>
                </li>
              </ol>
            </div>
          </div>
        </div>
      </div>
      
      <div class="mode-picker">
        <label>问答范围
          <select v-model="mode" :disabled="isLoading">
            <option value="auto">智能选择</option>
            <option value="news">站内新闻</option>
            <option value="favorites">我的收藏</option>
            <option value="documents">我的资料</option>
          </select>
        </label>
        <van-button plain size="small" @click="openDocuments">管理资料</van-button>
      </div>
      <details v-if="usesDateFilter" class="date-filters">
        <summary>{{ mode === 'news' ? '按发布日期筛选（可选，最多 8 篇）' : '按收藏日期筛选（可选，最多 10 篇）' }}</summary>
        <div>
          <label>开始日期 <input v-model="startDate" type="date" :max="endDate || undefined" /></label>
          <label>结束日期 <input v-model="endDate" type="date" :min="startDate || undefined" /></label>
        </div>
      </details>
      <div class="input-container">
        <van-field
          v-model="userInput"
          rows="1"
          autosize
          type="textarea"
          placeholder="例如：梳理过去一周的新能源汽车报道"
          maxlength="6000"
          class="chat-input"
          @keydown.enter="handleEnter"
        />
        <van-button 
          type="primary" 
          class="send-button" 
          :disabled="isLoading || !userInput.trim()" 
          @click="sendMessage"
        >
          发送
        </van-button>
      </div>
    </div>

    <van-popup v-model:show="showDocuments" position="bottom" round closeable :style="{ maxHeight: '80vh' }">
      <AIDocuments v-if="showDocuments" :token="userStore.getToken" />
    </van-popup>
    
    <tab-bar />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AIDocuments from '../components/AIDocuments.vue';
import TabBar from '../components/TabBar.vue';
import { showToast } from 'vant';
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import { apiConfig } from '../config/api';
import { useUserStore } from '../store/user';

const welcome = { role: 'assistant', content: '可以查站内新闻、总结你的收藏，或根据你上传的资料回答问题。' };
const messages = ref([welcome]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
const startDate = ref('');
const endDate = ref('');
const mode = ref('auto');
const usesDateFilter = computed(() => mode.value === 'news' || mode.value === 'favorites');
const showDocuments = ref(false);
const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
let activeRequest;

const openDocuments = () => {
  if (userStore.getToken) showDocuments.value = true;
  else router.push('/login');
};

watch(() => route.query.preset, (preset) => {
  if (route.path !== '/aichat' || preset !== 'recent-favorites') return;
  mode.value = 'favorites';
  startDate.value = endDate.value = '';
  userInput.value = '总结我最近的收藏';
  const query = { ...route.query };
  delete query.preset;
  router.replace({ path: route.path, query });
}, { immediate: true });

watch(() => userStore.getToken, () => {
  activeRequest?.abort();
  showDocuments.value = false;
  messages.value = [welcome];
  userInput.value = '';
  startDate.value = endDate.value = '';
  mode.value = 'auto';
}, { flush: 'sync' });
onUnmounted(() => activeRequest?.abort());

const formatMessage = (content) => {
  if (!content) return '';
  return DOMPurify.sanitize(marked.parse(content), { FORBID_TAGS: ['a', 'img'] });
};

const handleEnter = (event) => {
  if (event.isComposing || event.shiftKey) return;
  event.preventDefault();
  sendMessage();
};

const sendMessage = async () => {
  const question = userInput.value.trim();
  if (!question || isLoading.value) return;
  if (!userStore.getToken) {
    showToast('请先登录后使用新闻助手');
    router.push('/login');
    return;
  }
  if (usesDateFilter.value && startDate.value && endDate.value && startDate.value > endDate.value) {
    showToast('开始日期不能晚于结束日期');
    return;
  }

  isLoading.value = true;
  const history = messages.value.filter(message => message.completed).slice(-8)
    .map(({ role, content }) => ({ role, content: content.slice(0, 6000) }));
  messages.value.push({ role: 'user', content: question });
  messages.value.push({ role: 'assistant', content: '', mode: mode.value, status: '正在分析问题…' });
  const userMessage = messages.value.at(-2);
  const answer = messages.value.at(-1);
  userInput.value = '';
  activeRequest = new AbortController();

  try {
    const response = await fetch(apiConfig.baseURL + '/api/ai/chat', {
      method: 'POST',
      signal: activeRequest.signal,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': userStore.getToken,
      },
      body: JSON.stringify({
        messages: [...history, { role: 'user', content: question }],
        mode: mode.value,
        startDate: usesDateFilter.value ? startDate.value || null : null,
        endDate: usesDateFilter.value ? endDate.value || null : null,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      if (response.status === 401) router.push('/login');
      throw new Error(error.message || error.detail?.[0]?.msg || '请求失败（' + response.status + '）');
    }
    await readChatStream(response.body, answer);
    userMessage.completed = true;
    answer.completed = true;
  } catch (error) {
    if (error.name !== 'AbortError') answer.error = error.message || '新闻助手暂时不可用，请稍后重试';
  } finally {
    isLoading.value = false;
    activeRequest = undefined;
  }
};

const readChatStream = async (body, answer) => {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) throw new Error('连接提前中断，请重试');
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop();
      for (const frame of frames) {
        const lines = frame.split(/\r?\n/);
        const event = lines.find(line => line.startsWith('event: '))?.slice(7);
        const data = lines.find(line => line.startsWith('data: '))?.slice(6);
        if (!event || data === undefined) continue;
        const payload = JSON.parse(data);
        if (event === 'status') answer.status = payload.text;
        if (event === 'delta') answer.content += payload.text;
        if (event === 'sources') {
          answer.sources = payload;
          answer.status = '正在整理回答…';
        }
        if (event === 'error') throw new Error(payload.message);
        if (event === 'done') return;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

watch(messages, () => {
  nextTick(scrollToBottom);
}, { deep: true });

onMounted(scrollToBottom);
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding-top: 46px;
  padding-bottom: 50px;
  box-sizing: border-box;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.message {
  margin-bottom: 10px;
  max-width: 80%;
}

.user-message {
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.message-content {
  padding: 10px;
  border-radius: 10px;
  word-break: break-word;
}

.user-message .message-content {
  background-color: #007aff;
  color: white;
}

.ai-message .message-content {
  background-color: #f2f2f2;
  color: #333;
}

.input-container {
  display: flex;
  padding: 10px;
  border-top: 1px solid #eee;
  background-color: #fff;
}

.chat-input {
  flex: 1;
  margin-right: 10px;
}

.send-button {
  align-self: flex-end;
}

.date-filters {
  padding: 8px 10px;
  font-size: 13px;
}

.mode-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  font-size: 13px;
}

.date-filters div {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 8px;
}

.news-sources {
  margin-top: 10px;
  border-top: 1px solid #ddd;
  padding-top: 8px;
  font-size: 13px;
}

.news-sources ol {
  list-style: decimal;
  padding-left: 1.5em;
  margin-bottom: 0;
}

.news-sources li + li {
  margin-top: 4px;
}

.news-sources time {
  margin-right: 6px;
  color: #646566;
}

.news-sources a {
  color: #0766bc;
}

.message-error {
  color: #a92525;
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.message-content img {
  max-width: 100%;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  padding: 5px;
}

.typing-indicator small {
  margin-left: 6px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  display: inline-block;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-5px);
  }
}

/* Markdown样式 */
:deep(pre) {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

:deep(code) {
  font-family: monospace;
  background-color: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

:deep(p) {
  margin: 8px 0;
}

:deep(ul), :deep(ol) {
  padding-left: 20px;
}

:deep(a) {
  color: #1989fa;
  text-decoration: none;
}
</style>
