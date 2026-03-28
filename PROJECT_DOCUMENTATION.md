# Awaaz: Comprehensive Project Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Design](#architecture--design)
3. [Features & Functionality](#features--functionality)
4. [Technical Stack](#technical-stack)
5. [Project Structure](#project-structure)
6. [Installation & Setup](#installation--setup)
7. [Configuration](#configuration)
8. [API Documentation](#api-documentation)
9. [Security Features](#security-features)
10. [Performance Optimization](#performance-optimization)
11. [Deployment](#deployment)
12. [SEO & Web Standards](#seo--web-standards)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License](#license)

---

## Project Overview

**Awaaz** is a sophisticated Flask-based news aggregation web application that specializes in curating and displaying real-time news content focused on Kashmir. The application leverages Google's news API to fetch, process, and present news articles with advanced filtering capabilities and modern web technologies.

### Key Highlights
- **Real-time News Aggregation**: Fetches live news from multiple Kashmir-focused sources
- **Advanced Filtering**: Time-based filtering (hourly, daily, weekly, monthly, yearly)
- **Asynchronous Processing**: High-performance async data fetching
- **Security-First**: Encrypted API endpoints and rate limiting
- **Modern UI/UX**: Responsive design with Bootstrap 5
- **SEO Optimized**: Complete SEO implementation with sitemaps and meta tags

---

## Architecture & Design

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │───▶│   Flask App     │───▶│  Google News API│
│   (Frontend)    │    │   (Backend)     │    │   (Data Source) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         │              │   BeautifulSoup │              │
         │              │   (Parser)      │              │
         │              └─────────────────┘              │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Jinja2        │    │   Encryption    │    │   Rate Limiting │
│   Templates     │    │   (Fernet)      │    │   (Threading)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Design Patterns
- **MVC Pattern**: Model-View-Controller separation
- **Async/Await**: Non-blocking I/O operations
- **Factory Pattern**: Application factory for Flask
- **Decorator Pattern**: Route decorators and middleware
- **Observer Pattern**: Event-driven logging and monitoring

---

## Features & Functionality

### Core Features

#### 1. News Aggregation
- **Real-time Fetching**: Asynchronous news retrieval from Google News API
- **Multi-source Integration**: Aggregates from multiple Kashmir news sources
- **Content Filtering**: Intelligent filtering of irrelevant content
- **Time-based Filtering**: 5 different time ranges for news filtering

#### 2. User Interface
- **Responsive Design**: Mobile-first approach with Bootstrap 5
- **Modern UI**: Clean, intuitive interface with smooth animations
- **Accessibility**: WCAG compliant design elements
- **Cross-browser Compatibility**: Works on all modern browsers

#### 3. Performance Features
- **Compression**: Flask-Compress for reduced bandwidth usage
- **Caching**: Intelligent caching strategies
- **Async Processing**: Non-blocking operations for better performance
- **Resource Optimization**: Optimized static assets and CDN usage

#### 4. Security Features
- **Rate Limiting**: IP-based request limiting (20 requests per 12 hours)
- **Encryption**: Fernet encryption for sensitive API endpoints
- **Input Validation**: Sanitized user inputs
- **Error Handling**: Comprehensive error management

### Time Filter Options
| Filter Code | Description | Time Range |
|-------------|-------------|------------|
| `rf` | Recent News | Last Hour |
| `dn` | Day News | Past 24 Hours |
| `wn` | Week News | Past 7 Days |
| `mn` | Month News | Past 30 Days |
| `yn` | Year News | Past 365 Days |

---

## Technical Stack

### Backend Technologies
- **Framework**: Flask 3.1.0
- **Async Library**: aiohttp 3.11.10
- **HTML Parser**: BeautifulSoup4 4.12.3
- **Encryption**: cryptography 44.0.0
- **Compression**: Flask-Compress 1.17
- **WSGI Server**: Gunicorn 23.0.0

### Frontend Technologies
- **CSS Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.4.0
- **Fonts**: Google Fonts (Roboto)
- **JavaScript**: Vanilla JS with ES6+ features

### Development Tools
- **Package Manager**: pip
- **Version Control**: Git
- **Deployment**: Render.com
- **Monitoring**: Built-in logging system

---

## Project Structure

```
awaaz-main/
├── app.py                          # Main Flask application
├── wsgi.py                         # WSGI entry point
├── requirements.txt                # Python dependencies
├── Procfile                        # Deployment configuration
├── README.md                       # Basic project documentation
├── PROJECT_DOCUMENTATION.md        # This comprehensive documentation
├── awaaz-logo.svg                 # Project logo
├── encryption_key.key             # Encryption key (not in repo)
├── googlef376e0fa7802dd19.html    # Google verification file
│
├── templates/                      # Jinja2 HTML templates
│   ├── index.html                 # Homepage with filter selection
│   └── results.html               # News results display page
│
└── static/                        # Static assets
    ├── js/                        # JavaScript files
    │   ├── main.js               # Main JavaScript functionality
    │   └── keepAlive.js          # Keep-alive mechanism
    ├── robots.txt                # Search engine crawling rules
    ├── sitemap.xml               # XML sitemap for SEO
    └── googlef376e0fa7802dd19.html  # Google verification
```

---

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git (for cloning)

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/geekyfaahad/awaaz.git
cd awaaz
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Generate Encryption Key
```python
from cryptography.fernet import Fernet

# Generate a new key
key = Fernet.generate_key()

# Save the key to a file
with open("encryption_key.key", "wb") as key_file:
    key_file.write(key)
```

#### 5. Run the Application
```bash
python app.py
```

#### 6. Access the Application
Open your browser and navigate to:
```
http://127.0.0.1:55100
```

### Environment Variables
The application uses the following environment variables (if needed):
- `FLASK_ENV`: Set to 'development' or 'production'
- `PORT`: Application port (default: 55100)

---

## Configuration

### Application Configuration
```python
# Main application settings
app = Flask(__name__)
Compress(app)  # Enable compression

# Rate limiting configuration
rate_limit = 20  # Requests per window
rate_limit_window = 43200  # 12 hours in seconds

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Security Configuration
```python
# Encryption settings
def load_key():
    with open("encryption_key.key", "rb") as key_file:
        return key_file.read()

# Rate limiting settings
def is_rate_limited(ip):
    # Implementation details in app.py
    pass
```

---

## API Documentation

### Endpoints

#### 1. Homepage (`GET /`)
- **Purpose**: Display the main interface for news filtering
- **Method**: GET
- **Response**: HTML page with filter options

#### 2. News Results (`GET/POST /results`)
- **Purpose**: Fetch and display news articles
- **Method**: GET, POST
- **Parameters**: 
  - `filter` (string): Time filter option (rf, dn, wn, mn, yn)
- **Response**: HTML page with news results or JSON error response

#### 3. Rate Limit Status (`GET /rate_limit_status`)
- **Purpose**: Check current rate limit status
- **Method**: GET
- **Response**: JSON with rate limit information

#### 4. Static Files
- **Sitemap**: `GET /sitemap.xml`
- **Robots**: `GET /robots.txt`
- **Google Verification**: `GET /googlef376e0fa7802dd19.html`

### Response Formats

#### Success Response (HTML)
```html
<!-- Rendered Jinja2 template with news data -->
<div class="news-card">
    <h5>{{ news.headline }}</h5>
    <p>{{ news.summary }}</p>
    <a href="{{ news.link }}">Read More</a>
</div>
```

#### Error Response (JSON)
```json
{
    "error": "Rate limit exceeded",
    "message": "Please wait and try again later.",
    "status_code": 429,
    "retry_after": 3600
}
```

---

## Security Features

### 1. Rate Limiting
- **Implementation**: IP-based rate limiting with sliding window
- **Limit**: 20 requests per 12-hour window
- **Storage**: In-memory with automatic cleanup
- **Response**: HTTP 429 with retry-after header

### 2. Encryption
- **Algorithm**: Fernet (symmetric encryption)
- **Purpose**: Protect sensitive API endpoints
- **Key Management**: File-based key storage
- **Usage**: Encrypt/decrypt API URLs

### 3. Input Validation
- **Sanitization**: All user inputs are validated
- **XSS Prevention**: HTML escaping in templates
- **CSRF Protection**: Form-based protection

### 4. Error Handling
- **Comprehensive Logging**: All errors are logged
- **Graceful Degradation**: Application continues working on errors
- **No Information Leakage**: Generic error messages to users

---

## Performance Optimization

### 1. Asynchronous Processing
```python
async def fetch_news(time_range):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=10) as response:
            # Non-blocking I/O operations
            pass
```

### 2. Compression
- **Flask-Compress**: Automatic response compression
- **Gzip/Brotli**: Multiple compression algorithms
- **Bandwidth Reduction**: Up to 70% size reduction

### 3. Resource Optimization
- **CDN Usage**: Bootstrap and Font Awesome from CDN
- **Preloading**: Critical resources preloaded
- **DNS Prefetching**: Domain preconnection for faster loading

### 4. Caching Strategy
- **Static Assets**: Browser caching headers
- **API Responses**: Intelligent caching based on content type
- **Memory Management**: Automatic cleanup of old data

---

## Deployment

### Render.com Deployment

#### 1. Repository Setup
- Connect GitHub repository to Render
- Configure build settings

#### 2. Build Configuration
```bash
# Build command
pip install -r requirements.txt

# Start command
gunicorn app:app
```

#### 3. Environment Variables
- Set `FLASK_ENV=production`
- Configure encryption key securely
- Set appropriate port

#### 4. Domain Configuration
- Custom domain setup
- SSL certificate (automatic with Render)
- DNS configuration

### Alternative Deployment Options

#### Heroku
```bash
# Procfile already configured
web: gunicorn app:app

# Deploy
git push heroku main
```

#### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 55100
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:55100"]
```

---

## SEO & Web Standards

### 1. Meta Tags
```html
<meta name="description" content="Bringing Kashmir's Voice to the World">
<meta name="keywords" content="news aggregator, Kashmir news, real-time news">
<meta property="og:title" content="Awaaz 2.0 - Latest Kashmir News & Updates">
<meta property="og:description" content="Bringing Kashmir's Voice to the World">
```

### 2. Sitemap
- **Location**: `/sitemap.xml`
- **Format**: XML sitemap protocol
- **Update Frequency**: Daily
- **Priority**: Homepage (1.0), Results (0.9)

### 3. Robots.txt
```txt
User-agent: *
Allow: /
Crawl-delay: 1
Sitemap: https://awaaz.onrender.com/sitemap.xml
```

### 4. Schema Markup
- **NewsArticle**: For news content
- **WebSite**: For site information
- **Organization**: For site ownership

### 5. Performance Metrics
- **PageSpeed**: Optimized for Core Web Vitals
- **Mobile-Friendly**: Responsive design
- **Accessibility**: WCAG 2.1 AA compliant

---

## Troubleshooting

### Common Issues

#### 1. Encryption Key Error
**Problem**: `FileNotFoundError: encryption_key.key`
**Solution**: Generate encryption key using the provided script

#### 2. Rate Limiting
**Problem**: HTTP 429 errors
**Solution**: Wait for rate limit reset or check `/rate_limit_status`

#### 3. News Fetching Issues
**Problem**: No news results
**Solution**: Check API connectivity and time range parameters

#### 4. Deployment Issues
**Problem**: Application not starting
**Solution**: Check Procfile and gunicorn configuration

### Debug Mode
```python
# Enable debug mode for development
if __name__ == "__main__":
    app.run(debug=True, port=55100, host='0.0.0.0')
```

### Logging
```python
# Configure logging level
logging.basicConfig(level=logging.DEBUG)
```

---

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Include type hints where appropriate

### Testing
- Test all time filter options
- Verify rate limiting functionality
- Check responsive design
- Validate SEO elements

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

### Copyright
© 2025 Awaaz News | Connecting Kashmir

### Attribution
- **Author**: Hackyyy
- **Repository**: https://github.com/geekyfaahad/awaaz
- **Live Demo**: https://awaaz.onrender.com

---

## Additional Resources

### Documentation Links
- [Flask Documentation](https://flask.palletsprojects.com/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/)
- [Bootstrap Documentation](https://getbootstrap.com/docs/)

### Related Projects
- Similar news aggregation projects
- Kashmir-focused applications
- Flask-based web applications

### Community
- GitHub Issues: For bug reports and feature requests
- Discussions: For general questions and community interaction
- Wiki: For additional documentation and guides

---

*This documentation was last updated on March 12, 2025.* 