import { useState } from 'react';
import LandingPage from './components/LandingPage';
import TranslationApp from './components/TranslationApp';

function App() {
  const [currentView, setCurrentView] = useState('landing');

  if (currentView === 'app') {
    return <TranslationApp onBackToLanding={() => setCurrentView('landing')} />;
  }

  return <LandingPage onTestApp={() => setCurrentView('app')} />;
}

export default App;