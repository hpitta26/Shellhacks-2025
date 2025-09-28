import { useState } from 'react';

const App = () => {
  // Professional animal conservation website content
  const [originalContent] = useState({
    sections: [
      {
        section_id: "hero",
        title: "Hero Section",
        content: [
          { type: "header", value: "Protecting Wildlife for Future Generations" },
          { type: "content", value: "Join our global mission to preserve endangered species and their natural habitats. Through innovative conservation strategies, community engagement, and cutting-edge research, we're making a real difference for wildlife across the planet." },
          { type: "button", value: "Start Your Conservation Journey" }
        ]
      },

      {
        section_id: "mission",
        title: "Mission Section",
        content: [
          { type: "header", value: "Our Conservation Mission" },
          { type: "content", value: "WildGuard Conservation works tirelessly to protect endangered species through habitat restoration, anti-poaching initiatives, and sustainable community development programs." },
          { type: "content", value: "Our comprehensive approach includes wildlife rehabilitation centers, educational outreach programs, and partnerships with local communities to create lasting conservation solutions." },
          { type: "content", value: "From the African savanna to the Amazon rainforest, our dedicated team of biologists, veterinarians, and conservationists work around the clock to ensure wildlife thrives in their natural environments." },
          { type: "button", value: "Explore Our Projects" }
        ]
      },
      {
        section_id: "species",
        title: "Species Focus Section",
        content: [
          { type: "header", value: "Priority Species Protection" },
          { type: "content", value: "African Elephants: With only 415,000 elephants remaining in the wild, we're implementing advanced anti-poaching technology and community-based conservation programs across 12 African countries." },
          { type: "content", value: "Snow Leopards: Our high-altitude camera networks and livestock protection programs help safeguard the remaining 4,000 snow leopards in Central and South Asia's mountain ranges." },
          { type: "content", value: "Marine Turtles: Through beach protection initiatives and fishing gear innovation, we've helped increase sea turtle nesting success rates by 40% across the Pacific and Atlantic oceans." },
          { type: "content", value: "Sumatran Orangutans: Our rainforest restoration project has created 15,000 hectares of protected habitat for the critically endangered Sumatran orangutan population." },
          { type: "button", value: "Adopt an Animal" }
        ]
      },
      {
        section_id: "impact",
        title: "Impact Section",
        content: [
          { type: "header", value: "Conservation Impact by the Numbers" },
          { type: "content", value: "Since 2015, WildGuard Conservation has achieved remarkable results: 47 species moved from 'Critically Endangered' to 'Vulnerable' status, 120,000 hectares of habitat restored, and over 2.5 million people educated about wildlife conservation." },
          { type: "content", value: "Our innovative tracking technology has reduced poaching incidents by 67% in protected areas, while our community programs have created sustainable livelihoods for 18,000 families living near wildlife corridors." },
          { type: "button", value: "View Full Impact Report" }
        ]
      },
      {
        section_id: "involvement",
        title: "Get Involved Section",
        content: [
          { type: "header", value: "Join the Conservation Movement" },
          { type: "content", value: "Every action counts in wildlife conservation. Whether you're passionate about field research, community education, or digital advocacy, there's a meaningful way for you to contribute to our mission." },
          { type: "content", value: "From monthly donations that fund critical research to volunteer opportunities in the field, your support directly translates into protected habitats and saved species." },
          { type: "button", value: "Get Involved Today" }
        ]
      }
    ]
  });

  const [translatedContent, setTranslatedContent] = useState(null);
  const [targetLanguage, setTargetLanguage] = useState('Spanish');
  const [isTranslating, setIsTranslating] = useState(false);
  const [showTranslated, setShowTranslated] = useState(false);
  const [error, setError] = useState('');

  const supportedLanguages = [
    'Spanish', 'French', 'German', 'Italian', 'Portuguese',
    'Chinese (Mandarin)', 'Japanese', 'Korean', 'Arabic',
    'Russian', 'Hindi', 'Dutch', 'Swedish', 'Polish', 'Turkish'
  ];

  const translatePage = async () => {
  setIsTranslating(true);
  setError('');

  try {
    const response = await fetch('http://localhost:8000/translate-sections', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sections: originalContent.sections,
        target_language: targetLanguage
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    const result = await response.json();
    setTranslatedContent(result);
    setShowTranslated(true);
  } catch (err) {
    setError(err.message);
    console.error('Translation error:', err);
  } finally {
    setIsTranslating(false);
  }
};

  const renderContent = (content, isTranslated = false) => {
    const sections = isTranslated ? translatedContent.translated_sections : originalContent.sections;

    return (
      <div className="space-y-8">
        {sections.map((section, sectionIndex) => (
          <section key={section.section_id} className="group">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1">
              <div className={`px-8 py-6 ${getSectionGradient(sectionIndex)} relative overflow-hidden`}>
                <div className="absolute inset-0 bg-black bg-opacity-10"></div>
                <div className="relative z-10 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="text-4xl">{getSectionIcon(section.section_id)}</div>
                    <div>
                      <h2 className="text-2xl font-bold text-white tracking-wide">
                        {getSectionDisplayTitle(section.section_id)}
                      </h2>
                      {isTranslated && (
                        <span className="inline-block mt-1 bg-white bg-opacity-20 px-3 py-1 rounded-full text-sm font-medium text-white">
                          Translated to {targetLanguage}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="hidden md:block text-white text-opacity-60">
                    <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="p-8 space-y-6">
                {section.content.map((item, itemIndex) => (
                  <div key={itemIndex} className={getContentStyle(item.type)}>
                    {item.type === 'header' && (
                      <h3 className="text-3xl font-bold text-gray-800 mb-4 leading-tight">
                        {item.value}
                      </h3>
                    )}
                    {item.type === 'content' && (
                      <div className="prose prose-lg max-w-none">
                        <p className="text-gray-700 leading-relaxed text-lg font-light">
                          {item.value}
                        </p>
                      </div>
                    )}
                   {item.type === 'dual_box' && (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-6">
    {(() => {
      try {
        const boxData = JSON.parse(item.value);
        return (
          <>
            <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-6 hover:shadow-lg transition-all duration-300">
              <h4 className="text-xl font-bold text-emerald-800 mb-3">{boxData.left.title}</h4>
              <p className="text-gray-700 leading-relaxed">{boxData.left.content}</p>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6 hover:shadow-lg transition-all duration-300">
              <h4 className="text-xl font-bold text-blue-800 mb-3">{boxData.right.title}</h4>
              <p className="text-gray-700 leading-relaxed">{boxData.right.content}</p>
            </div>
          </>
        );
      } catch (error) {
        // Handle invalid JSON (translation failed)
        return (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6">
            <h4 className="text-xl font-bold text-red-800 mb-3">Translation Error</h4>
            <p className="text-gray-700">{item.value}</p>
          </div>
        );
      }
    })()}
  </div>
)}
                    {item.type === 'button' && (
                      <button className={`${getButtonStyle(sectionIndex)} group-button`}>
                        <span className="relative z-10 flex items-center gap-2">
                          {item.value}
                          <svg className="w-5 h-5 transform transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                          </svg>
                        </span>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        ))}
      </div>
    );
  };

  const getSectionGradient = (index) => {
    const gradients = [
      'bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500',
      'bg-gradient-to-br from-blue-600 via-indigo-500 to-purple-500',
      'bg-gradient-to-br from-orange-500 via-red-500 to-pink-500',
      'bg-gradient-to-br from-green-600 via-emerald-500 to-teal-500',
      'bg-gradient-to-br from-purple-600 via-violet-500 to-indigo-500',
      'bg-gradient-to-br from-cyan-600 via-blue-500 to-indigo-500'
    ];
    return gradients[index % gradients.length];
  };

  const getSectionIcon = (sectionId) => {
    const icons = {
      hero: '🌍',
      mission: '🦁',
      programs: '🔬',
      species: '🐘',
      impact: '📊',
      involvement: '🤝'
    };
    return icons[sectionId] || '🌿';
  };

  const getSectionDisplayTitle = (sectionId) => {
    const titles = {
      hero: 'Our Mission',
      mission: 'Conservation Efforts',
      programs: 'Conservation Programs',
      species: 'Protected Species',
      impact: 'Global Impact',
      involvement: 'Get Involved'
    };
    return titles[sectionId] || 'Wildlife Conservation';
  };

  const getContentStyle = (type) => {
    switch (type) {
      case 'header':
        return 'mb-6';
      case 'content':
        return 'mb-4';
      case 'dual_box':
        return 'mb-6';
      case 'button':
        return 'mt-6';
      default:
        return '';
    }
  };

  const getButtonStyle = (sectionIndex) => {
    const styles = [
      'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600',
      'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600',
      'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600',
      'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600',
      'bg-gradient-to-r from-purple-500 to-violet-500 hover:from-purple-600 hover:to-violet-600',
      'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600'
    ];
    const baseStyle = 'text-white px-8 py-4 rounded-xl font-semibold transition-all duration-300 transform hover:scale-105 hover:shadow-lg relative overflow-hidden group';
    return `${baseStyle} ${styles[sectionIndex % styles.length]}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Professional Header */}
      <header className="bg-white shadow-lg sticky top-0 z-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-4xl">🌿</div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                  WildGuard Conservation
                </h1>
                <p className="text-gray-600 text-lg font-medium">Protecting Wildlife for Future Generations</p>
              </div>
            </div>

            {/* Translation Controls */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <label className="text-gray-700 font-medium">Translate to:</label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  disabled={isTranslating}
                  className="border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:opacity-50 bg-white shadow-sm min-w-[160px]"
                >
                  {supportedLanguages.map(lang => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>

              <button
                onClick={translatePage}
                disabled={isTranslating}
                className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-8 py-3 rounded-xl font-semibold hover:from-emerald-600 hover:to-teal-600 focus:outline-none focus:ring-2 focus:ring-emerald-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform hover:scale-105 shadow-lg min-w-[180px]"
              >
                {isTranslating ? (
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Translating...</span>
                  </div>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                    </svg>
                    Translate Website
                  </span>
                )}
              </button>

              {translatedContent && (
                <button
                  onClick={() => setShowTranslated(!showTranslated)}
                  className="bg-gradient-to-r from-gray-600 to-gray-700 text-white px-6 py-3 rounded-xl font-semibold hover:from-gray-700 hover:to-gray-800 transition-all transform hover:scale-105 shadow-lg"
                >
                  {showTranslated ? (
                    <span className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                      </svg>
                      Show Original
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                      </svg>
                      Show Translation
                    </span>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Error Display */}
      {error && (
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="bg-red-50 border-l-4 border-red-400 rounded-lg p-6 flex items-center gap-4 shadow-sm">
            <div className="text-red-500 text-2xl">⚠️</div>
            <div>
              <h3 className="text-red-800 font-semibold">Translation Error</h3>
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Status Indicator */}
        <div className="mb-12 text-center">
          <div className="inline-flex items-center gap-4 bg-white rounded-2xl px-8 py-4 shadow-lg border border-gray-100">
            <div className={`w-4 h-4 rounded-full ${showTranslated ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'}`}></div>
            <span className="text-gray-800 font-semibold text-lg">
              {showTranslated ? `Viewing ${targetLanguage} Translation` : 'Viewing Original English Content'}
            </span>
            {translatedContent && (
              <span className="bg-gradient-to-r from-emerald-100 to-teal-100 text-emerald-800 px-4 py-2 rounded-xl text-sm font-medium border border-emerald-200">
                ✓ {translatedContent.total_sections} sections translated
              </span>
            )}
          </div>
        </div>

        {/* Content Sections */}
        {renderContent(showTranslated ? translatedContent : originalContent, showTranslated)}
      </main>

      {/* Professional Footer */}
      <footer className="bg-gradient-to-r from-gray-800 via-gray-900 to-black text-white py-16 mt-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="text-3xl">🌿</div>
                <h3 className="text-2xl font-bold">WildGuard Conservation</h3>
              </div>
              <p className="text-gray-300 leading-relaxed">
                Dedicated to protecting endangered species and preserving natural habitats for future generations through innovative conservation strategies.
              </p>
            </div>

            <div>
              <h4 className="text-xl font-semibold mb-6 text-emerald-400">Quick Links</h4>
              <ul className="space-y-3 text-gray-300">
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Conservation Projects</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Species Protection</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Get Involved</a></li>
                <li><a href="#" className="hover:text-emerald-400 transition-colors">Impact Reports</a></li>
              </ul>
            </div>

            <div>
              <h4 className="text-xl font-semibold mb-6 text-emerald-400">Translation Powered By</h4>
              <p className="text-gray-300 leading-relaxed">
                Advanced AI translation using Google ADK Agent V2 • Support for 15+ languages • Real-time multi-section translation
              </p>
              <div className="mt-6 text-sm text-gray-400">
                © {new Date().getFullYear()} WildGuard Conservation. Built with React & FastAPI.
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;