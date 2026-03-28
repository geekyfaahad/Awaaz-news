# Awaaz: Asynchronous News Aggregator

**Awaaz** is a **Flask-based web application** that gathers and displays curated news articles using the **Google Open API**. The application focuses on delivering real-time updates based on the keyword **"Kashmir news"**, with user-friendly options to filter content by timeframe.

## Project Structure
```plaintext
├── app.py                # Main Flask application
├── templates/            # Jinja2 templates for the web interface
│   ├── index.html        # Homepage for filter selection
│   ├── results.html      # Displays fetched news
│   ├── error.html        # Error display page
├── static/               # Folder for static assets (CSS, images, JS)
├── encryption_key.key    # Encryption key for sensitive API data
├── requirements.txt      # Project dependencies
└── README.md             # Project documentation
```

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Screenshots](#screenshots)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Google Open API Integration:** Gathers real-time news updates with a focus on **"Kashmir news"**
- **Timeframe Filtering:** Enables filtering by recent, daily, weekly, or monthly news
- **Asynchronous Fetching:** Uses `aiohttp` and `asyncio` for fast and efficient data retrieval
- **Secure Data Handling:** Implements encryption using `cryptography.fernet` to protect sensitive URLs
- **Performance Optimization:** Uses Flask-Compress to reduce data transfer size and enhance speed
- **Custom Parsing:** Extracts and displays relevant information using `BeautifulSoup`

## Tech Stack
- **Backend:** Flask
- **Frontend:** HTML5, CSS3, Jinja2 templates
- **Libraries:**
  - `aiohttp`
  - `asyncio`
  - `BeautifulSoup`
  - `Flask-Compress`
  - `cryptography`
  - 'Flask[async]`
## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/geekyfaahad/awaaz.git
   cd awaaz
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Generate Encryption Key**
   Create an encryption key by running the following Python script:
   ```python
   from cryptography.fernet import Fernet
   
   # Generate a key
   key = Fernet.generate_key()
   
   # Save the key to a file
   with open("encryption_key.key", "wb") as key_file:
       key_file.write(key)
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

5. **Access the Application**
   Open your web browser and navigate to:
   ```
   http://127.0.0.1:55100
   ```

## Usage

1. **Select Time Filter:**
   - Choose from Recent, Daily, Weekly, or Monthly news updates
   - Click "Apply Filter" to update results

2. **View News Articles:**
   - Browse through headlines, summaries, and timestamps
   - Click on article links to read full stories
   - Use the refresh button to fetch latest updates

## How It Works

1. **Data Fetching:**
   - Application connects to Google Open API
   - Asynchronously retrieves news data using `aiohttp`
   - Implements rate limiting and error handling

2. **Data Processing:**
   - Parses raw API response using `BeautifulSoup`
   - Extracts relevant information (headlines, summaries, timestamps)
   - Encrypts sensitive URLs for security

3. **Display:**
   - Renders processed data using Jinja2 templates
   - Implements responsive design for various screen sizes
   - Optimizes content delivery using Flask-Compress

## Security Features

- **API Key Protection:** Sensitive API keys are encrypted using Fernet
- **URL Encryption:** News article URLs are encrypted before storage
- **Error Handling:** Robust error handling to prevent data leaks
- **Rate Limiting:** Implements API rate limiting to prevent abuse
- 

[![YouTube Video](https://img.youtube.com/vi/4M0XiQqS-ds/0.jpg)](https://www.youtube.com/watch?v=4M0XiQqS-ds)
<iframe width="560" height="315" src="https://www.youtube.com/embed/4M0XiQqS-ds?si=glDhjSFzJ7HKr4yg" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>


