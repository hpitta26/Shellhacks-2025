import { useState } from "react";

const TranslationApp = ({ onBackToLanding }) => {
  const [originalContent] = useState({
    sections: [
      {
        section_id: "hero",
        title: "Hero Section",
        display_title: "Our Mission",
        image:
          "https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800&q=80",
        content: [
          { type: "section_title", value: "Our Mission" },
          {
            type: "header",
            value: "Protecting Wildlife for Future Generations",
          },
          {
            type: "content",
            value:
              "Join our global mission to preserve endangered species and their natural habitats. Through innovative conservation strategies, community engagement, and cutting-edge research, we're making a real difference for wildlife across the planet.",
          },
          { type: "button", value: "Start Your Conservation Journey" },
        ],
      },
      {
        section_id: "programs",
        title: "Conservation Programs",
        display_title: "Conservation Programs",
        image:
          "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80",
        content: [
          { type: "section_title", value: "Conservation Programs" },
          { type: "header", value: "Our Conservation Programs" },
          {
            type: "dual_box",
            value: JSON.stringify({
              left: {
                title: "Field Research",
                content:
                  "Our field teams conduct vital research on endangered species behavior, migration patterns, and habitat needs. This data directly informs our conservation strategies and helps us understand how to best protect vulnerable wildlife populations.",
              },
              right: {
                title: "Community Outreach",
                content:
                  "We work directly with local communities to develop sustainable practices that benefit both people and wildlife. Through education programs and economic incentives, we create partnerships that ensure long-term conservation success.",
              },
            }),
          },
          { type: "button", value: "Learn About All Programs" },
        ],
      },
      {
        section_id: "mission",
        title: "Mission Section",
        display_title: "Conservation Efforts",
        image:
          "https://images.unsplash.com/photo-1547036967-23d11aacaee0?w=800&q=80",
        content: [
          { type: "section_title", value: "Conservation Efforts" },
          { type: "header", value: "Our Conservation Mission" },
          {
            type: "content",
            value:
              "WildGuard Conservation works tirelessly to protect endangered species through habitat restoration, anti-poaching initiatives, and sustainable community development programs.",
          },
          {
            type: "content",
            value:
              "Our comprehensive approach includes wildlife rehabilitation centers, educational outreach programs, and partnerships with local communities to create lasting conservation solutions.",
          },
          {
            type: "content",
            value:
              "From the African savanna to the Amazon rainforest, our dedicated team of biologists, veterinarians, and conservationists work around the clock to ensure wildlife thrives in their natural environments.",
          },
          { type: "button", value: "Explore Our Projects" },
        ],
      },
      {
        section_id: "species",
        title: "Species Focus Section",
        display_title: "Protected Species",
        image:
          "https://images.unsplash.com/photo-1564349683136-77e08dba1ef7?w=800&q=80",
        content: [
          { type: "section_title", value: "Protected Species" },
          { type: "header", value: "Priority Species Protection" },
          {
            type: "content",
            value:
              "African Elephants: With only 415,000 elephants remaining in the wild, we're implementing advanced anti-poaching technology and community-based conservation programs across 12 African countries.",
          },
          {
            type: "content",
            value:
              "Snow Leopards: Our high-altitude camera networks and livestock protection programs help safeguard the remaining 4,000 snow leopards in Central and South Asia's mountain ranges.",
          },
          {
            type: "content",
            value:
              "Marine Turtles: Through beach protection initiatives and fishing gear innovation, we've helped increase sea turtle nesting success rates by 40% across the Pacific and Atlantic oceans.",
          },
          {
            type: "content",
            value:
              "Sumatran Orangutans: Our rainforest restoration project has created 15,000 hectares of protected habitat for the critically endangered Sumatran orangutan population.",
          },
          { type: "button", value: "Adopt an Animal" },
        ],
      },
      {
        section_id: "impact",
        title: "Impact Section",
        display_title: "Global Impact",
        image:
          "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",
        content: [
          { type: "section_title", value: "Global Impact" },
          { type: "header", value: "Conservation Impact by the Numbers" },
          {
            type: "content",
            value:
              "Since 2015, WildGuard Conservation has achieved remarkable results: 47 species moved from 'Critically Endangered' to 'Vulnerable' status, 120,000 hectares of habitat restored, and over 2.5 million people educated about wildlife conservation.",
          },
          {
            type: "content",
            value:
              "Our innovative tracking technology has reduced poaching incidents by 67% in protected areas, while our community programs have created sustainable livelihoods for 18,000 families living near wildlife corridors.",
          },
          { type: "button", value: "View Full Impact Report" },
        ],
      },
      {
        section_id: "involvement",
        title: "Get Involved Section",
        display_title: "Get Involved",
        image:
          "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&q=80",
        content: [
          { type: "section_title", value: "Get Involved" },
          { type: "header", value: "Join the Conservation Movement" },
          {
            type: "content",
            value:
              "Every action counts in wildlife conservation. Whether you're passionate about field research, community education, or digital advocacy, there's a meaningful way for you to contribute to our mission.",
          },
          {
            type: "content",
            value:
              "From monthly donations that fund critical research to volunteer opportunities in the field, your support directly translates into protected habitats and saved species.",
          },
          { type: "button", value: "Get Involved Today" },
        ],
      },
      {
        section_id: "footer",
        title: "Footer Section",
        display_title: "Footer",
        content: [
          { type: "footer_title", value: "WildGuard Conservation" },
          {
            type: "footer_description",
            value:
              "Demo translation app showcasing context-aware AI translation for wildlife conservation content.",
          },
          { type: "footer_nav_title", value: "Navigation" },
          {
            type: "footer_nav_links",
            value: JSON.stringify([
              "Conservation Projects",
              "Species Protection",
              "Get Involved",
              "Impact Reports",
            ]),
          },
          { type: "footer_tech_title", value: "Translation Technology" },
          {
            type: "footer_tech_description",
            value:
              "Real-time multi-language translation system supporting 15+ languages with context-aware processing.",
          },
          { type: "footer_copyright", value: "TranslateFlow Demo" },
        ],
      },
    ],
  });

  const [translatedContent, setTranslatedContent] = useState(null);
  const [targetLanguage, setTargetLanguage] = useState("Spanish");
  const [isTranslating, setIsTranslating] = useState(false);
  const [showTranslated, setShowTranslated] = useState(false);
  const [error, setError] = useState("");

  const supportedLanguages = [
    "Spanish",
    "French",
    "German",
    "Italian",
    "Portuguese",
    "Chinese (Mandarin)",
    "Japanese",
    "Korean",
    "Arabic",
    "Russian",
    "Hindi",
    "Dutch",
    "Swedish",
    "Polish",
    "Turkish",
  ];

  const translatePage = async () => {
    setIsTranslating(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/translate-sections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sections: originalContent.sections,
          target_language: targetLanguage,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `Request failed with status ${response.status}`
        );
      }

      const result = await response.json();
      setTranslatedContent(result);
      setShowTranslated(true);
    } catch (err) {
      setError(err.message);
      console.error("Translation error:", err);
    } finally {
      setIsTranslating(false);
    }
  };

  const getSectionTitle = (section, isTranslated = false) => {
    if (isTranslated && translatedContent) {
      const translatedSection = translatedContent.translated_sections.find(
        (s) => s.section_id === section.section_id
      );
      if (translatedSection) {
        const titleItem = translatedSection.content.find(
          (item) => item.type === "section_title"
        );
        return titleItem?.value || section.display_title;
      }
    }

    const titleItem = section.content.find(
      (item) => item.type === "section_title"
    );
    return titleItem?.value || section.display_title;
  };

  const getFooterContent = (isTranslated = false) => {
    const sections = isTranslated
      ? translatedContent.translated_sections
      : originalContent.sections;
    return sections.find((section) => section.section_id === "footer");
  };

  const renderFooter = (isTranslated = false) => {
    const footerSection = getFooterContent(isTranslated);
    if (!footerSection) return null;

    const footerData = {};
    footerSection.content.forEach((item) => {
      if (item.type === "footer_nav_links") {
        footerData[item.type] = JSON.parse(item.value);
      } else {
        footerData[item.type] = item.value;
      }
    });

    return (
      <footer className="bg-stone-900 text-stone-300 py-20 mt-32">
        <div className="max-w-7xl mx-auto px-8">
          <div className="grid md:grid-cols-3 gap-16">
            <div className="space-y-6">
              <h3 className="text-2xl font-light text-stone-50">
                {footerData.footer_title}
              </h3>
              <p className="leading-relaxed font-light">
                {footerData.footer_description}
              </p>
            </div>

            <div className="space-y-6">
              <h4 className="text-lg font-medium text-stone-50">
                {footerData.footer_nav_title}
              </h4>
              <div className="space-y-3 font-light">
                {footerData.footer_nav_links?.map((link, index) => (
                  <div key={index}>
                    <a
                      href="#"
                      className="hover:text-stone-50 transition-colors"
                    >
                      {link}
                    </a>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-6">
              <h4 className="text-lg font-medium text-stone-50">
                {footerData.footer_tech_title}
              </h4>
              <p className="font-light leading-relaxed">
                {footerData.footer_tech_description}
              </p>
              <div className="text-sm text-stone-400 font-light tracking-wide">
                © {new Date().getFullYear()} {footerData.footer_copyright}
              </div>
            </div>
          </div>
        </div>
      </footer>
    );
  };

  const renderContent = (content, isTranslated = false) => {
    const sections = isTranslated
      ? translatedContent.translated_sections
      : originalContent.sections;
    const originalSections = originalContent.sections;

    // Filter out footer section from main content rendering
    const contentSections = sections.filter(
      (section) => section.section_id !== "footer"
    );
    const originalContentSections = originalSections.filter(
      (section) => section.section_id !== "footer"
    );

    return (
      <div className="space-y-24">
        {contentSections.map((section, sectionIndex) => {
          const originalSection = originalContentSections.find(
            (orig) => orig.section_id === section.section_id
          );
          const imageUrl = originalSection?.image;

          return (
            <section
              key={section.section_id}
              className={`${
                sectionIndex % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } flex flex-col md:gap-16 gap-8 items-start`}
            >
              {/* Title + Image Column */}
              <div className="md:w-1/3 md:sticky md:top-32 space-y-6">
                <div className="bg-stone-900 p-8 text-stone-50">
                  <h2 className="text-2xl font-light tracking-wide mb-3">
                    {getSectionTitle(section, isTranslated)}
                  </h2>
                </div>
                {imageUrl && (
                  <div className="aspect-square overflow-hidden">
                    <img
                      src={imageUrl}
                      alt={getSectionTitle(section, isTranslated)}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
              </div>

              {/* Content Column */}
              <div className="md:w-2/3 bg-stone-50 p-12">
                <div className="max-w-2xl space-y-8">
                  {section.content.map((item, itemIndex) => (
                    <div key={itemIndex}>
                      {item.type === "section_title" &&
                        // Skip rendering section_title here as it's handled in the sidebar
                        null}
                      {item.type === "header" && (
                        <h3 className="text-3xl font-light text-stone-900 leading-tight mb-8">
                          {item.value}
                        </h3>
                      )}
                      {item.type === "content" && (
                        <p className="text-stone-700 leading-loose text-lg font-light">
                          {item.value}
                        </p>
                      )}
                      {item.type === "dual_box" && (
                        <div className="grid md:grid-cols-2 gap-12 my-12">
                          {(() => {
                            const boxData = JSON.parse(item.value);
                            return (
                              <>
                                <div className="space-y-4">
                                  <h4 className="text-xl font-medium text-stone-900">
                                    {boxData.left.title}
                                  </h4>
                                  <p className="text-stone-600 leading-relaxed font-light">
                                    {boxData.left.content}
                                  </p>
                                </div>
                                <div className="space-y-4">
                                  <h4 className="text-xl font-medium text-stone-900">
                                    {boxData.right.title}
                                  </h4>
                                  <p className="text-stone-600 leading-relaxed font-light">
                                    {boxData.right.content}
                                  </p>
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      )}
                      {item.type === "button" && (
                        <button className="bg-amber-500 hover:bg-amber-600 text-stone-900 px-8 py-4 font-medium text-lg tracking-wide transition-colors duration-300 mt-8">
                          {item.value}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </section>
          );
        })}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-stone-100">
      {/* Header */}
      <header className="bg-stone-50 border-b-2 border-stone-900 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-8 py-8">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onBackToLanding}
                className="text-stone-600 hover:text-stone-900 text-sm font-medium transition-colors"
              >
                ← Back to Home
              </button>
              <div className="space-y-2">
                <h1 className="text-5xl font-light text-stone-900 tracking-tight">
                  WildGuard
                </h1>
                <p className="text-stone-600 text-lg font-light tracking-wide">
                  Demo Translation App
                </p>
              </div>
            </div>

            {/* Translation Controls */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-4">
                <label className="text-stone-700 font-medium">Language:</label>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  disabled={isTranslating}
                  className="border border-stone-300 px-4 py-3 text-stone-700 bg-stone-50 focus:outline-none focus:border-stone-900 disabled:opacity-50 min-w-[140px] font-medium"
                >
                  {supportedLanguages.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={translatePage}
                disabled={isTranslating}
                className="bg-stone-900 hover:bg-stone-800 text-stone-50 px-6 py-3 font-medium tracking-wide focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-300 min-w-[140px]"
              >
                {isTranslating ? (
                  <div className="flex items-center justify-center gap-3">
                    <div className="w-4 h-4 border-2 border-stone-50 border-t-transparent animate-spin"></div>
                    <span>Working...</span>
                  </div>
                ) : (
                  <span>Translate</span>
                )}
              </button>

              {translatedContent && (
                <button
                  onClick={() => setShowTranslated(!showTranslated)}
                  className="border border-stone-900 hover:bg-stone-900 hover:text-stone-50 text-stone-900 px-6 py-3 font-medium tracking-wide transition-colors duration-300"
                >
                  {showTranslated ? "English" : "Translated"}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Error Display */}
      {error && (
        <div className="max-w-7xl mx-auto px-8 py-6">
          <div className="bg-red-100 border-l-4 border-red-500 p-6">
            <div className="text-red-800">
              <h3 className="font-medium text-lg mb-2">Translation Error</h3>
              <p className="font-light">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Status Bar */}
      {translatedContent && (
        <div className="bg-amber-500 text-stone-900 py-3">
          <div className="max-w-7xl mx-auto px-8">
            <div className="flex items-center justify-center gap-4">
              <div className="w-2 h-2 bg-stone-900"></div>
              <span className="font-medium tracking-wide">
                {showTranslated
                  ? `Viewing ${targetLanguage} Translation`
                  : "Viewing Original Content"}
              </span>
              <span className="text-sm">
                ({translatedContent.total_sections} sections)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-8 py-16">
        {renderContent(
          showTranslated ? translatedContent : originalContent,
          showTranslated
        )}
      </main>

      {/* Footer - Now translatable */}
      {renderFooter(showTranslated && translatedContent)}
    </div>
  );
};

export default TranslationApp;
