// News functionality for Awaaz
class NewsManager {
    constructor() {
        this.filterMap = {
            'hour': 'rf',
            'day': 'dn',
            'week': 'wn',
            'month': 'mn',
            'year': 'yn'
        };

        this.isLoading = {};
        this.cache = {};
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes

        this.init();
    }

    init() {
        // Load initial news for active tab
        this.loadNews('hour');

        // Set up tab event listeners
        this.setupTabListeners();

        // Set up auto-refresh
        this.setupAutoRefresh();

        // Set up keyboard shortcuts
        this.setupKeyboardShortcuts();

        // Set up network status monitoring
        this.setupNetworkMonitoring();

        // Update stats
        this.updateStats();
    }

    setupTabListeners() {
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (event) => {
                const targetId = event.target.getAttribute('data-bs-target').substring(1);
                if (targetId && !this.isLoading[targetId]) {
                    this.loadNews(targetId);
                }
            });
        });
    }

    setupAutoRefresh() {
        // Auto-refresh every 5 minutes
        setInterval(() => {
            const activeTab = document.querySelector('.tab-pane.active');
            if (activeTab) {
                const category = activeTab.id;
                if (!this.isLoading[category]) {
                    this.loadNews(category);
                }
            }
        }, 5 * 60 * 1000);
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + R to refresh current tab
            if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
                event.preventDefault();
                const activeTab = document.querySelector('.tab-pane.active');
                if (activeTab) {
                    this.loadNews(activeTab.id);
                }
            }

            // Number keys 1-5 to switch tabs
            if (event.key >= '1' && event.key <= '5') {
                const tabIndex = parseInt(event.key) - 1;
                const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
                if (tabButtons[tabIndex]) {
                    tabButtons[tabIndex].click();
                }
            }
        });
    }

    showLoading(category) {
        const content = document.getElementById(`${category}-content`);
        const refreshBtn = document.getElementById(`${category}-refresh`);

        this.isLoading[category] = true;
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        }

        content.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>Loading ${this.getCategoryDisplayName(category)} news...</p>
            </div>
        `;
    }

    showError(category, message) {
        const content = document.getElementById(`${category}-content`);
        const refreshBtn = document.getElementById(`${category}-refresh`);

        this.isLoading[category] = false;
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }

        content.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
                <br><br>
                <button class="btn btn-outline-primary btn-sm" onclick="newsManager.loadNews('${category}')">
                    <i class="fas fa-redo"></i> Try Again
                </button>
            </div>
        `;
    }

    showNoNews(category) {
        const content = document.getElementById(`${category}-content`);
        const refreshBtn = document.getElementById(`${category}-refresh`);

        this.isLoading[category] = false;
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }

        content.innerHTML = `
            <div class="no-news">
                <i class="fas fa-newspaper"></i>
                <h4>No News Available</h4>
                <p>There are no news articles available for ${this.getCategoryDisplayName(category)}.</p>
                <button class="btn btn-outline-primary btn-sm" onclick="newsManager.loadNews('${category}')">
                    <i class="fas fa-redo"></i> Refresh
                </button>
            </div>
        `;
    }

    getCategoryDisplayName(category) {
        const names = {
            'hour': 'recent',
            'day': 'today\'s',
            'week': 'this week\'s',
            'month': 'this month\'s',
            'year': 'this year\'s'
        };
        return names[category] || category;
    }

    renderNews(category, newsData) {
        const content = document.getElementById(`${category}-content`);
        const countElement = document.getElementById(`${category}-count`);
        const refreshBtn = document.getElementById(`${category}-refresh`);

        this.isLoading[category] = false;
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }

        if (!newsData || newsData.length === 0) {
            this.showNoNews(category);
            if (countElement) countElement.textContent = '0';
            return;
        }

        if (countElement) countElement.textContent = newsData.length;

        const newsHTML = newsData.map(news => this.createNewsCard(news)).join('');
        content.innerHTML = `<div class="news-grid">${newsHTML}</div>`;

        // Add lazy loading for images
        this.setupLazyLoading();

        // Update stats after rendering
        this.updateStats();
    }

    createNewsCard(news) {
        const imageHTML = news.image && news.image !== 'No image available'
            ? `<div style="overflow: hidden;">
                   <img src="${news.image}" class="card-img-top" alt="${news.headline || 'News Image'}" loading="lazy" onerror="this.onerror=null; this.src='https://placehold.co/400x200/e0e0e0/000000?text=No+Image';">
               </div>`
            : '';

        return `
            <div class="news-card-wrapper mb-4">
                <div class="card position-relative" data-news-id="${this.generateNewsId(news)}">
                    ${imageHTML}
                    <div class="card-body">
                        <h5 class="card-title">${this.escapeHtml(news.headline || 'No Title')}</h5>
                        <p class="card-text">${this.escapeHtml(news.summary || 'No Summary Available')}</p>
                        
                        <div class="card-footer-custom">
                            <a href="${this.escapeHtml(news.link || '#')}" target="_blank" rel="noopener noreferrer" class="btn-read stretched-link">
                                Read Story <i class="fas fa-arrow-right ms-2" style="font-size: 0.8em;"></i>
                            </a>
                            <p class="timestamp mb-0">
                                <i class="far fa-clock"></i>
                                ${this.escapeHtml(news.time || 'Just now')}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    generateNewsId(news) {
        return btoa(news.headline + news.link).replace(/[^a-zA-Z0-9]/g, '').substring(0, 10);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    setupLazyLoading() {
        const images = document.querySelectorAll('.news-image[loading="lazy"]');
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.src; // Trigger load
                        observer.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        }
    }

    async loadNews(category) {
        if (this.isLoading[category]) return;

        // Check cache first
        const cached = this.getCachedNews(category);
        if (cached) {
            this.renderNews(category, cached);
            this.updateStats();
            return;
        }

        this.showLoading(category);

        try {
            const filter = this.filterMap[category];
            const response = await fetch(`/api/news?filter=${filter}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.cacheNews(category, data.data);
                this.renderNews(category, data.data);
                this.updateStats();
            } else {
                throw new Error(data.message || 'Failed to load news');
            }
        } catch (error) {
            console.error(`Error loading news for ${category}:`, error);
            this.showError(category, 'Network error. Please try again.');
        }
    }

    cacheNews(category, data) {
        this.cache[category] = {
            data: data,
            timestamp: Date.now()
        };
    }

    getCachedNews(category) {
        const cached = this.cache[category];
        if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
            return cached.data;
        }
        return null;
    }

    clearCache(category = null) {
        if (category) {
            delete this.cache[category];
        } else {
            this.cache = {};
        }
    }

    refreshAll() {
        const categories = Object.keys(this.filterMap);
        categories.forEach(category => {
            this.clearCache(category);
            this.loadNews(category);
        });
    }

    getNewsStats() {
        const stats = {};
        Object.keys(this.filterMap).forEach(category => {
            const countElement = document.getElementById(`${category}-count`);
            stats[category] = countElement ? parseInt(countElement.textContent) || 0 : 0;
        });
        return stats;
    }

    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.hideOfflineIndicator();
            // Refresh current tab when back online
            const activeTab = document.querySelector('.tab-pane.active');
            if (activeTab) {
                this.loadNews(activeTab.id);
            }
        });

        window.addEventListener('offline', () => {
            this.showOfflineIndicator();
        });

        // Check initial status
        if (!navigator.onLine) {
            this.showOfflineIndicator();
        }
    }

    showOfflineIndicator() {
        const indicator = document.getElementById('offlineIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }

    hideOfflineIndicator() {
        const indicator = document.getElementById('offlineIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    showLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('show');
        }
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }

    updateStats() {
        const stats = this.getNewsStats();
        const totalCount = Object.values(stats).reduce((sum, count) => sum + count, 0);

        // Update total news count
        const totalElement = document.getElementById('total-news-count');
        if (totalElement) {
            totalElement.textContent = totalCount;
        }

        // Update last updated time
        const lastUpdatedElement = document.getElementById('last-updated');
        if (lastUpdatedElement) {
            const now = new Date();
            lastUpdatedElement.textContent = now.toLocaleTimeString();
        }

        // Update cache status
        const cacheStatusElement = document.getElementById('cache-status');
        if (cacheStatusElement) {
            const cachedCategories = Object.keys(this.filterMap).filter(cat => this.isCached(cat));
            cacheStatusElement.textContent = `${cachedCategories.length}/${Object.keys(this.filterMap).length}`;
        }

        // Update active sources (placeholder - could be enhanced with actual source data)
        const activeSourcesElement = document.getElementById('active-sources');
        if (activeSourcesElement) {
            activeSourcesElement.textContent = '11'; // Default number of sources
        }
    }
}

// Initialize NewsManager when DOM is loaded
let newsManager;
document.addEventListener('DOMContentLoaded', function () {
    newsManager = new NewsManager();
});

// Global function for refresh buttons
function loadNews(category) {
    if (newsManager) {
        newsManager.loadNews(category);
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { NewsManager };
} 