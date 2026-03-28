import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home.tsx';
import Results from './pages/Results.tsx';
import './index.css';

function App() {
  return (
    <Router>
      <header className="header">
        <div className="container">
          <div className="d-flex flex-column align-items-center">
            <a href="/" className="logo-link">
              <h1 className="logo">Awaaz</h1>
            </a>
            <p className="tagline">Trust Issues? Same. We Verify</p>
          </div>
        </div>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/results" element={<Results />} />
        </Routes>
      </main>

      <footer className="footer">
        <div className="container">
          <p className="mb-0">© 2025 Awaaz News Foundation | Empowering Truth in the Valley</p>
        </div>
      </footer>
    </Router>
  );
}

export default App;
