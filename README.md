# Reddit Sync

A modern Python application for monitoring Reddit threads, downloading media content, and storing everything in a local SQLite database. Built with asynchronous architecture and intelligent scheduling for optimal performance and scalability.

## ✨ Features

- **Automated Scheduling**: Background scheduler with configurable intervals for continuous monitoring
- **Thread Monitoring**: Automatically tracks specified Reddit threads and subreddits
- **Enhanced Metrics**: Collects upvotes, comment counts, and engagement statistics
- **Media Download**: Downloads images, videos, and other media content from posts
- **SQLite Storage**: Stores all data in a structured SQLite database with SQLAlchemy ORM
- **Concurrent Processing**: Supports concurrent media downloads with configurable limits
- **OAuth2 Authentication**: Secure Reddit API access using refresh tokens
- **Web Interface**: Modern web interface for browsing downloaded content with metrics
- **Error Handling**: Robust error handling with exponential backoff retry logic
- **Content Filtering**: Intelligent duplicate detection and content validation

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Reddit API credentials (client ID and secret)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/RedditSync.git
   cd RedditSync
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Reddit API credentials**:
   ```bash
   # Run the interactive token setup script
   python tools/1_get_refresh_token.py --save
   
   # Verify your environment configuration
   python tools/2_check_env.py
   ```

5. **Database migration (if upgrading from older version)**:
   ```bash
   # If you have an existing database, migrate it to the new schema
   python tools/migrate_add_metrics.py
   
   # Test the scheduler implementation (optional)
   python tools/test_scheduler.py
   ```

### Configuration

Create a `.env` file in the project root based on `env.example`:

```env
# Required Reddit API settings
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=python:redditsync:v1.0 (by /u/yourusername)
REDDIT_REFRESH_TOKEN=your_refresh_token_here

# Optional configuration (with defaults)
DB_PATH=db.sqlite
MEDIA_DIR=media
MAX_MEDIA_SIZE=52428800  # 50MB
MAX_CONCURRENT_DOWNLOADS=5
REDIRECT_PORT=8000
```

### Running the Application

```bash
# Run the main sync application with scheduler
python app/main.py

# Or run the web interface (optional)
cd web && python app.py
```

## 📅 Scheduler Configuration

Reddit Sync runs with an intelligent background scheduler:

- **Initial Sync**: Starts 10 seconds after application launch
- **Regular Sync**: Every 2 minutes, processes up to 5 new posts
- **Automatic Database Setup**: Creates tables automatically on first run
- **Metrics Update**: Automatically updates scores and comment counts for existing posts

The scheduler prevents overlapping tasks and includes rate limiting to respect Reddit's API guidelines.

## 📁 Project Structure

```
RedditSync/
├── app/                      # Core application modules
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Application entry point with scheduler
│   ├── config.py            # Configuration management
│   ├── db.py                # Database operations (SQLAlchemy ORM)
│   ├── models.py            # Database models (SQLAlchemy)
│   ├── reddit_client.py     # Reddit API client
│   ├── media_downloader.py  # Media download functionality
│   ├── sync_worker.py       # Synchronization orchestration
│   └── utils.py             # Utility functions
├── docs/                     # Documentation
│   ├── spec.md              # Technical specification
│   ├── get_token.md         # OAuth2 setup guide
│   └── CODE_STYLE_EN.md     # Code style guidelines
├── tools/                    # Utility scripts
│   ├── 1_get_refresh_token.py  # OAuth2 token generator
│   ├── 2_check_env.py          # Environment validator
├── web/                      # Web interface (optional)
│   ├── app.py               # Flask web application
│   └── templates/           # HTML templates
├── media/                    # Downloaded media files (created automatically)
├── requirements.txt          # Python dependencies
├── env.example              # Environment template
└── README.md               # This file
```

## 🗄️ Database Technology

The application uses **SQLAlchemy 2.0** with async support as the ORM (Object-Relational Mapping) layer:

- **Database Engine**: SQLite with aiosqlite for async operations
- **ORM**: SQLAlchemy 2.0 with modern async/await syntax
- **Models**: Fully typed SQLAlchemy models with relationships
- **Migrations**: Built-in migration tool for upgrading from raw SQL

### Database Schema

The application uses three main tables:

- **`subscriptions`**: List of monitored Reddit threads/subreddits
- **`news`**: Posts and comments with metadata and content  
- **`media`**: Downloaded media files with metadata and references

The ORM models provide:
- **Type safety** with Python type hints
- **Relationship mapping** between tables
- **Automatic query generation** and optimization
- **Connection pooling** and session management

## ⚙️ Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `REDDIT_CLIENT_ID` | Reddit API client ID | *Required* |
| `REDDIT_CLIENT_SECRET` | Reddit API client secret | *Required* |
| `REDDIT_USER_AGENT` | User agent string for API requests | *Required* |
| `REDDIT_REFRESH_TOKEN` | OAuth2 refresh token | *Required* |
| `DB_PATH` | SQLite database file path | `db.sqlite` |
| `MEDIA_DIR` | Directory for downloaded media | `media` |
| `MAX_MEDIA_SIZE` | Maximum file size for downloads (bytes) | `52428800` (50MB) |
| `MAX_CONCURRENT_DOWNLOADS` | Concurrent download limit | `5` |
| `REDIRECT_PORT` | Port for OAuth2 redirect | `8000` |

## 🛡️ Error Handling & Resilience

- **Network errors**: Automatic retry with exponential backoff
- **Rate limiting**: Respects Reddit API rate limits
- **Large files**: Configurable size limits to prevent storage issues
- **Duplicate detection**: Prevents duplicate downloads and storage
- **Logging**: Comprehensive logging for debugging and monitoring

## 🔧 Development

### Code Style

This project follows **PEP 8** standards with a **99-character line limit**. See `docs/CODE_STYLE_EN.md` for detailed guidelines.

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=app
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the code style guidelines
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Report bugs and feature requests via GitHub Issues
- **Reddit API**: Refer to [Reddit API Documentation](https://www.reddit.com/dev/api/) for API-related questions

## 🎯 Roadmap

- [x] **SQLAlchemy ORM integration** 
- [x] **Background scheduler with automated tasks**
- [x] **Enhanced metrics collection (scores, comments)**
- [ ] Notifications for new content
- [ ] Advanced content filtering and categorization
- [ ] Multi-subreddit batch operations
- [ ] Export functionality (JSON, CSV)
- [ ] Docker containerization
- [ ] RESTful API for external integrations
- [ ] Database performance optimizations and indexing