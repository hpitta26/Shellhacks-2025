const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_TIMEOUT = import.meta.env.VITE_API_TIMEOUT || 30000;

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.timeout = API_TIMEOUT;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      timeout: this.timeout,
      ...options,
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorDetail = response.statusText;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorDetail = errorData.detail;
          }
        } catch (e) {
          // If we can't parse the error response, use the status text
        }
        throw new Error(`HTTP ${response.status}: ${errorDetail}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed: ${error.message}`);
      throw error;
    }
  }

  // Translation API Methods
  async translateText(sourceText, targetLanguage = 'Spanish') {
    const response = await this.request('/translate', {
      method: 'POST',
      body: {
        source_text: sourceText,
        target_language: targetLanguage
      },
    });
    
    return {
      originalText: response.original_text,
      translatedText: response.translated_text,
      targetLanguage: response.target_language,
      sessionId: response.session_id
    };
  }

  // Health Check Methods
  async getHealth() {
    const response = await this.request('/health', {
      method: 'GET',
    });
    
    return {
      status: response.status,
      service: response.service,
      agent: response.agent,
      version: response.version
    };
  }

  // Utility Methods
  getSupportedLanguages() {
    return [
      'Spanish', 'French', 'German', 'Italian', 'Portuguese', 
      'Chinese (Mandarin)', 'Japanese', 'Korean', 'Arabic', 
      'Russian', 'Hindi', 'Dutch', 'Swedish', 'Polish', 'Turkish'
    ];
  }

  getErrorMessage(error) {
    if (error.message.includes('fetch') || error.message.includes('network')) {
      return 'Network error. Please check your connection and try again.';
    }
    
    if (error.message.includes('timeout')) {
      return 'Request timed out. The translation is taking longer than expected.';
    }
    
    if (error.message.includes('HTTP 5')) {
      return 'Server error. Please try again later.';
    }
    
    // Extract the actual error message if it's from our API
    if (error.message.includes('HTTP')) {
      const match = error.message.match(/HTTP \d+: (.+)/);
      return match ? match[1] : 'Translation failed. Please try again.';
    }
    
    return error.message || 'An unexpected error occurred.';
  }
}

export default new ApiClient();