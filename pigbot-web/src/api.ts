import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1/agent';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * 发送聊天消息
   */
  chat: async (messages: any[], imageUrls: string[] = []) => {
    const response = await api.post('/chat/v2', {
      user_id: 'web_demo_user',
      messages,
      image_urls: imageUrls,
      metadata: {},
    });
    return response.data;
  },

  /**
   * 上传录音文件并转文字
   */
  transcribeVoice: async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'record.webm');
    
    const response = await axios.post(`${API_BASE_URL}/voice/transcribe`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
