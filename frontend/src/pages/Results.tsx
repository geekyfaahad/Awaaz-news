import React, { useState } from 'react';
import { useLocation, Link, Navigate } from 'react-router-dom';

const Results: React.FC = () => {
  const location = useLocation();
  const { newsData, city } = location.state || { newsData: null, city: '' };
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState('latest');
  const itemsPerPage = 8; // 4 columns * 2 rows

  if (!newsData) {
    return <Navigate to="/" replace />;
  }

  // Sorting logic
  const sortedNews = [...newsData].sort((a: any, b: any) => {
    if (sortBy === 'latest') return 0;
    const titleA = a.headline || "";
    const titleB = b.headline || "";
    return titleA.localeCompare(titleB);
  });

  const totalPages = Math.ceil(sortedNews.length / itemsPerPage);
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = sortedNews.slice(indexOfFirstItem, indexOfLastItem);

  const handlePageChange = (n: number) => {
    setCurrentPage(n);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const formatMeta = (headline: string, time: string) => {
    const parts = headline.split(' - ');
    const source = parts.length > 1 ? parts.pop() : "Awaaz Source";
    const cleanHeadline = parts.join(' - ');
    
    // Simple date cleanup (e.g. "Sat, 28 Mar 2026..." -> "Mar 28, 2026")
    let displayDate = time;
    try {
      if (time.includes(',')) {
        const dParts = time.split(',');
        if (dParts.length > 1) {
          const dateOnly = dParts[1].trim().split(' ');
          displayDate = `${dateOnly[1]} ${dateOnly[0]}, ${dateOnly[2]}`;
        }
      }
    } catch(e) {}

    return { source, date: displayDate, cleanHeadline };
  };

  return (
    <div className="container results-section">
      <div className="pt-4">
        <Link to="/" className="back-home-top">
          <i className="fas fa-arrow-left"></i> Back to Home
        </Link>
      </div>

      <header className="mb-5">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-end gap-3">
          <div>
            <h1 className="h1 mb-2">Search Results</h1>
            <p className="text-muted mb-0">
              Showing <span className="text-primary fw-bold">{indexOfFirstItem + 1}–{Math.min(indexOfLastItem, sortedNews.length)}</span> of {sortedNews.length} curated stories for <span className="text-primary fw-bold">{city}</span>
            </p>
          </div>
          
          <div className="d-flex align-items-center gap-3">
            <span className="text-meta">Sort by:</span>
            <select 
              className="form-select form-select-sm sort-select shadow-sm" 
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="latest">Latest first</option>
              <option value="relevance">Most Relevant</option>
              <option value="az">A–Z Title</option>
            </select>
          </div>
        </div>
        <hr className="mt-4 border-light opacity-50" />
      </header>

      {currentItems.length > 0 ? (
        <div className="news-pages-stack">
          <div className="news-grid">
            {currentItems.map((news: any, index: number) => {
              const { source, date, cleanHeadline } = formatMeta(news.headline, news.time || '');
              return (
                <a 
                  key={index} 
                  href={news.link || '#'} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="card h-100 card-clickable border-light"
                >
                  {news.image && !news.image.includes('placehold.co') && (
                    <div className="card-img-wrapper" style={{ height: '160px' }}>
                      <img 
                        src={news.image} 
                        className="card-img-top"
                        alt={cleanHeadline}
                        loading="lazy"
                        onError={(e: any) => { e.target.parentElement.style.display = 'none'; }}
                      />
                    </div>
                  )}
                  <div className="card-body d-flex flex-column p-4">
                    <h5 className="h4 mb-3 card-title-limit">{cleanHeadline || 'No Title'}</h5>
                    <p className="text-body-sm mb-4 line-clamp-2">{news.summary || 'No Summary Available'}</p>

                    <div className="mt-auto">
                      <div className="card-meta-inline">
                        <span className="text-primary">{source}</span>
                        <div className="card-meta-separator"></div>
                        <span>{date}</span>
                      </div>
                      <div className="d-flex align-items-center justify-content-between mt-3">
                        <span className="text-primary fw-bold small">Read Article <i className="fas fa-arrow-right ms-1"></i></span>
                      </div>
                    </div>
                  </div>
                </a>
              );
            })}
          </div>

          {totalPages > 1 && (
            <nav className="news-pagination mt-5 pt-5" aria-label="News pages">
              <button 
                className="pagination-nav-btn shadow-sm"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <i className="fas fa-chevron-left" /> Prev
              </button>
              
              <div className="d-none d-md-flex gap-2">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
                  <button
                    key={n}
                    className={`news-pagination__btn shadow-sm ${currentPage === n ? 'is-current' : ''}`}
                    onClick={() => handlePageChange(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>

              <div className="d-md-none px-3 font-weight-bold">
                Page {currentPage} / {totalPages}
              </div>

              <button 
                className="pagination-nav-btn shadow-sm"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next <i className="fas fa-chevron-right" />
              </button>
            </nav>
          )}
        </div>
      ) : (
        <div className="no-results shadow-lg border-0 animate-bounce py-5">
          <div className="bg-icon-circle mb-4" style={{ background: '#f8fafc' }}>
            <i className="fas fa-newspaper map-icon" style={{ opacity: 0.2 }}></i>
          </div>
          <h2 className="fw-bold mb-3">Silent in {city}</h2>
          <p className="text-muted mb-5 px-4">Our systems couldn't find any significant news activity in your region for this timeframe.</p>
          <Link to="/" className="btn btn-primary shadow-sm px-5 py-3" style={{ borderRadius: '12px' }}>
            Try another location
          </Link>
        </div>
      )}

      <footer className="text-center mt-5 pt-5 border-top border-light opacity-50">
        <p className="small text-muted mb-0">© 2026 Awaaz News  | Empowering Truth in the Valley</p>
      </footer>
    </div>
  );
};

export default Results;
