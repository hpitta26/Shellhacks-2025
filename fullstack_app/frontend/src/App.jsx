import { useState, useEffect } from 'react'
import { FiArrowRight, FiCheck } from 'react-icons/fi'

function App() {
  const [email, setEmail] = useState('')
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [stars, setStars] = useState([])

  // Generate stars on mount
  useEffect(() => {
    const generateStars = () => {
      const newStars = []
      for (let i = 0; i < 150; i++) {
        newStars.push({
          id: i,
          x: Math.random() * 100,
          y: Math.random() * 100,
          size: Math.random() * 2 + 0.5,
          opacity: Math.random() * 0.3 + 0.1,
          moveSpeed: Math.random() * 0.02 + 0.005,
          direction: Math.random() * Math.PI * 2
        })
      }
      setStars(newStars)
    }

    generateStars()
  }, [])

  // Animate stars
  useEffect(() => {
    const interval = setInterval(() => {
      setStars(prevStars => 
        prevStars.map(star => ({
          ...star,
          x: (star.x + Math.cos(star.direction) * star.moveSpeed + 100) % 100,
          y: (star.y + Math.sin(star.direction) * star.moveSpeed + 100) % 100,
          opacity: star.opacity + (Math.random() - 0.5) * 0.01
        }))
      )
    }, 50)

    return () => clearInterval(interval)
  }, [])

  const handleEmailSubmit = (e) => {
    e.preventDefault()
    if (email.trim()) {
      setIsSubmitted(true)
      console.log('Email submitted:', email)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      {/* Animated Stars Background */}
      <div className="fixed inset-0 pointer-events-none">
        {stars.map(star => (
          <div
            key={star.id}
            className="absolute w-px h-px bg-white rounded-full"
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              opacity: Math.max(0.05, Math.min(0.4, star.opacity)),
              transition: 'all 0.05s linear'
            }}
          />
        ))}
      </div>

      {/* Navigation */}
      <nav className="relative z-10 border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <div className="text-xl font-medium">TranslateFlow</div>
              <div className="hidden md:flex items-center space-x-6 text-sm text-gray-400">
                <a href="#" className="hover:text-white transition-colors">API</a>
                <a href="#" className="hover:text-white transition-colors">DOCS</a>
                <a href="#" className="hover:text-white transition-colors">PRICING</a>
                <a href="#" className="hover:text-white transition-colors">CONTACT</a>
              </div>
            </div>
            <button className="border border-gray-700 hover:border-gray-600 px-4 py-2 rounded text-sm transition-colors">
              TRY TRANSLATEFLOW
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 px-6 py-32">
        <div className="max-w-4xl mx-auto text-center">
          {/* Logo/Icon */}
          <div className="w-20 h-20 mx-auto mb-12 flex items-center justify-center">
            <svg className="w-full h-full text-white" viewBox="0 0 100 100" fill="currentColor">
              <circle cx="50" cy="30" r="8"/>
              <circle cx="30" cy="60" r="8"/>
              <circle cx="70" cy="60" r="8"/>
              <path d="M42 38L58 52M58 38L42 52" stroke="currentColor" strokeWidth="3" fill="none"/>
            </svg>
          </div>

          <h1 className="text-5xl md:text-6xl font-light mb-8 tracking-tight">
            Translate Your Website
          </h1>
          
          <p className="text-xl md:text-2xl text-gray-400 mb-4 font-light">
            Transform any website into 100+ languages.
          </p>
          
          <p className="text-lg text-gray-500 mb-16 font-light">
            Context-aware AI that preserves meaning, tone, and brand voice across cultures.
          </p>

          <button 
            onClick={() => document.getElementById('signup').scrollIntoView()}
            className="inline-flex items-center border border-gray-700 hover:border-gray-600 px-6 py-3 rounded text-sm transition-colors"
          >
            SIGN UP NOW <FiArrowRight className="ml-2 w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Simple Feature Grid */}
      <section className="relative z-10 px-6 py-24 border-t border-gray-800">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-16">
            <div>
              <h3 className="text-lg font-medium mb-4">Context Intelligence</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Advanced AI analyzes context, cultural nuances, and brand voice 
                to deliver translations that feel natural in every language.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-4">Developer First</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Simple REST API integration. Deploy translations instantly 
                with comprehensive documentation and SDKs.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-4">Enterprise Ready</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Handle millions of words with consistent quality. 
                Built for scale with security and compliance standards.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Process */}
      <section className="relative z-10 px-6 py-24 border-t border-gray-800">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-light mb-16 text-center">How it works</h2>
          
          <div className="space-y-12">
            <div className="flex items-start space-x-6">
              <div className="text-gray-500 text-sm mt-1">01</div>
              <div>
                <h3 className="text-lg font-medium mb-2">Upload content</h3>
                <p className="text-gray-400 text-sm">
                  Send us your website content via API or file upload. 
                  We support all major formats and content management systems.
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-6">
              <div className="text-gray-500 text-sm mt-1">02</div>
              <div>
                <h3 className="text-lg font-medium mb-2">AI processing</h3>
                <p className="text-gray-400 text-sm">
                  Our models analyze context, tone, and cultural relevance 
                  to produce accurate translations that maintain your brand voice.
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-6">
              <div className="text-gray-500 text-sm mt-1">03</div>
              <div>
                <h3 className="text-lg font-medium mb-2">Deploy instantly</h3>
                <p className="text-gray-400 text-sm">
                  Receive translations in minutes, not weeks. 
                  Integrate directly into your workflow or download files.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="relative z-10 px-6 py-24 border-t border-gray-800">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-3xl font-light mb-2">99.7%</div>
              <div className="text-gray-500 text-sm">Accuracy</div>
            </div>
            <div>
              <div className="text-3xl font-light mb-2">100+</div>
              <div className="text-gray-500 text-sm">Languages</div>
            </div>
            <div>
              <div className="text-3xl font-light mb-2">&lt;5min</div>
              <div className="text-gray-500 text-sm">Processing</div>
            </div>
          </div>
        </div>
      </section>

      {/* Signup */}
      <section id="signup" className="relative z-10 px-6 py-32 border-t border-gray-800">
        <div className="max-w-md mx-auto text-center">
          <h2 className="text-2xl font-light mb-8">Ready to go global?</h2>
          
          {!isSubmitted ? (
            <form onSubmit={handleEmailSubmit} className="space-y-4">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full px-4 py-3 bg-black border border-gray-700 rounded text-sm focus:outline-none focus:border-gray-600 transition-colors"
                required
              />
              <button
                type="submit"
                className="w-full border border-gray-700 hover:border-gray-600 py-3 rounded text-sm transition-colors"
              >
                START FREE TRIAL
              </button>
            </form>
          ) : (
            <div className="flex items-center justify-center text-gray-400">
              <FiCheck className="w-5 h-5 mr-2" />
              <span>Thanks! We'll be in touch.</span>
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-gray-800 px-6 py-8">
        <div className="max-w-6xl mx-auto flex justify-between items-center text-sm text-gray-500">
          <div>© 2025 TranslateFlow</div>
          <div className="flex space-x-6">
            <a href="#" className="hover:text-gray-400 transition-colors">Privacy</a>
            <a href="#" className="hover:text-gray-400 transition-colors">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App