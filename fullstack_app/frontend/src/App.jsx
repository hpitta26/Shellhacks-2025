import { useState } from 'react'
import apiClient from './api'

function App() {
  const [inputText, setInputText] = useState('')
  const [sourceText, setSourceText] = useState('')
  const [translatedText, setTranslatedText] = useState('')
  const [targetLanguage, setTargetLanguage] = useState('Spanish')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const SUPPORTED_LANGUAGES = apiClient.getSupportedLanguages()

  const handleTranslate = async () => {
    if (!inputText.trim()) {
      setError('Please enter some text to translate')
      return
    }

    setIsLoading(true)
    setError('')
    setSourceText(inputText)
    setTranslatedText('')

    try {
      const response = await apiClient.translateText(inputText, targetLanguage)
      setTranslatedText(response.translatedText)
    } catch (err) {
      setError(apiClient.getErrorMessage(err))
      console.error('Translation error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleTranslate()
    }
  }

  const clearAll = () => {
    setInputText('')
    setSourceText('')
    setTranslatedText('')
    setError('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col">
      {/* Header */}
      <header className="text-center py-8 px-4">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-3">
          🌐 AI Translation
        </h1>
        <p className="text-gray-600 text-lg">
          Powered by Google ADK with iterative refinement
        </p>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto px-4 w-full">
        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Left Column - Source Text */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-blue-500 text-white px-6 py-4 flex justify-between items-center">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                📝 Source Text
              </h3>
              <span className="bg-blue-600 px-3 py-1 rounded-full text-sm font-medium">
                English
              </span>
            </div>
            <div className="p-6 min-h-[200px] flex items-center justify-center">
              {sourceText ? (
                <p className="text-gray-800 text-lg leading-relaxed break-words w-full">
                  {sourceText}
                </p>
              ) : (
                <p className="text-gray-400 italic text-center">
                  Enter text below to see source text here...
                </p>
              )}
            </div>
          </div>

          {/* Right Column - Translation */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="bg-red-500 text-white px-6 py-4 flex justify-between items-center">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                🎯 Translation
              </h3>
              <select 
                value={targetLanguage} 
                onChange={(e) => setTargetLanguage(e.target.value)}
                disabled={isLoading}
                className="bg-red-600 text-white border-none rounded-full px-3 py-1 text-sm font-medium cursor-pointer hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-300 disabled:opacity-50"
              >
                {SUPPORTED_LANGUAGES.map(lang => (
                  <option key={lang} value={lang} className="text-gray-800">
                    {lang}
                  </option>
                ))}
              </select>
            </div>
            <div className="p-6 min-h-[200px] flex items-center justify-center">
              {isLoading ? (
                <div className="flex flex-col items-center gap-4 text-gray-500">
                  <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-center">Translating with AI refinement...</p>
                </div>
              ) : translatedText ? (
                <p className="text-green-600 text-lg font-medium leading-relaxed break-words w-full">
                  {translatedText}
                </p>
              ) : (
                <p className="text-gray-400 italic text-center">
                  Translation will appear here...
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <span className="text-red-500 text-xl">⚠️</span>
            <span className="text-red-700 font-medium">{error}</span>
          </div>
        )}

        {/* Input Section */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 mb-8">
          <div className="space-y-4">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your text here and press Enter to translate..."
              disabled={isLoading}
              rows={4}
              className="w-full p-4 border-2 border-gray-200 rounded-lg text-lg resize-none focus:border-blue-500 focus:outline-none transition-colors disabled:bg-gray-50 disabled:cursor-not-allowed"
            />
            <div className="flex justify-end gap-3">
              <button 
                onClick={clearAll} 
                disabled={isLoading}
                className="px-6 py-3 bg-gray-500 text-white rounded-lg font-medium hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Clear
              </button>
              <button 
                onClick={handleTranslate} 
                disabled={isLoading || !inputText.trim()}
                className="px-8 py-3 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 min-w-[120px]"
              >
                {isLoading ? 'Translating...' : 'Translate'}
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-6 text-gray-500">
        <p>Press Enter to translate • Shift+Enter for new line • Built with ⚡ Vite + Tailwind</p>
      </footer>
    </div>
  )
}

export default App
