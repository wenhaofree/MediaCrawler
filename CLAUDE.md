# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaCrawler is a multi-platform social media crawler that supports data collection from Xiaohongshu (Little Red Book), Douyin, Kuaishou, Bilibili, Weibo, Tieba, and Zhihu. It uses Playwright for browser automation and avoids complex JS reverse engineering by maintaining login states through browser contexts.

## Development Environment Setup

### Prerequisites
- **Python**: 3.9+ (recommended 3.9.6)
- **Node.js**: 16+ (required for Douyin and Zhihu)
- **uv**: Modern Python package manager (recommended)

### Installation
```bash
# Clone and navigate to project
cd MediaCrawler

# Install dependencies using uv (recommended)
uv sync

# Install browser drivers
uv run playwright install

# Alternative: Using traditional venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install
```

## Running the Crawler

### Basic Commands
```bash
# Search by keywords
uv run main.py --platform xhs --lt qrcode --type search

# Crawl specific posts
uv run main.py --platform xhs --lt qrcode --type detail

# Crawl creator pages
uv run main.py --platform xhs --lt qrcode --type creator

# View help
uv run main.py --help
```

### Database Initialization
```bash
# Initialize SQLite database
uv run main.py --init_db sqlite

# Initialize MySQL database
uv run main.py --init_db mysql
```

### Supported Platforms
- `xhs`: Xiaohongshu (Little Red Book)
- `dy`: Douyin
- `ks`: Kuaishou
- `bili`: Bilibili
- `wb`: Weibo
- `tieba`: Baidu Tieba
- `zhihu`: Zhihu

## Configuration

### Main Configuration File: `config/base_config.py`

Key configuration parameters:
- `PLATFORM`: Target platform (default: "xhs")
- `KEYWORDS`: Search keywords (comma-separated)
- `LOGIN_TYPE`: Login method ("qrcode", "phone", "cookie")
- `CRAWLER_TYPE`: Crawl type ("search", "detail", "creator")
- `SAVE_DATA_OPTION`: Data storage ("csv", "db", "json", "sqlite")
- `ENABLE_IP_PROXY`: Enable proxy support
- `HEADLESS`: Run browser in headless mode
- `MAX_CONCURRENCY_NUM`: Concurrency control
- `CRAWLER_MAX_NOTES_COUNT`: Max posts to crawl

### CDP Mode (Chrome DevTools Protocol)
Enable CDP mode for better anti-detection:
```python
ENABLE_CDP_MODE = True
CDP_DEBUG_PORT = 9222
CDP_HEADLESS = False
```

### Platform-Specific Configurations
Each platform has its own config file in `config/` directory:
- `xhs_config.py`: Xiaohongshu settings
- `dy_config.py`: Douyin settings
- `bili_config.py`: Bilibili settings
- etc.

## Architecture Overview

### Core Components

1. **Abstract Base Classes** (`base/`):
   - `AbstractCrawler`: Base crawler interface
   - `AbstractLogin`: Login method abstraction
   - `AbstractStore`: Data storage abstraction
   - `AbstractApiClient`: API client abstraction

2. **Platform Implementations** (`media_platform/`):
   - Each platform has its own directory with:
     - `core.py`: Main crawler implementation
     - `client.py`: API client
     - `login.py`: Login handling
     - `field.py`: Data field definitions
     - `help.py`: Utility functions
     - `exception.py`: Custom exceptions

3. **Data Storage** (`store/`):
   - CSV, JSON, database storage implementations
   - Supports SQLite and MySQL

4. **Database Layer** (`database/`):
   - SQLAlchemy models
   - Database connection management
   - Session handling

5. **Tools** (`tools/`):
   - Browser utilities
   - File writers
   - Time utilities
   - Slider captcha utilities

### Data Flow
1. Configuration loading from `config/base_config.py`
2. Platform-specific crawler initialization via `CrawlerFactory`
3. Browser context creation with login state
4. Data crawling (search/detail/creator modes)
5. Data processing and storage
6. Comment crawling (if enabled)

## Common Development Tasks

### Adding a New Platform
1. Create platform directory in `media_platform/`
2. Implement required abstract classes:
   - `core.py` (main crawler)
   - `client.py` (API client)
   - `login.py` (login handling)
   - `field.py` (data models)
3. Add platform to `CrawlerFactory.CRAWLERS` in `main.py`
4. Create platform-specific config file

### Modifying Crawler Behavior
- Edit `config/base_config.py` for general settings
- Modify platform-specific config files for platform behavior
- Adjust concurrency and rate limits in base config

### Debugging Issues
- Set `HEADLESS = False` to see browser actions
- Use `ENABLE_CDP_MODE = True` for better anti-detection
- Check logs for detailed error information
- Use browser dev tools when CDP mode is enabled

## Code Quality and Standards

### Type Checking
- Project uses mypy for type checking
- Configuration in `mypy.ini`
- Run with: `mypy .`

### Code Style
- Follow existing code patterns
- Use async/await patterns consistently
- Implement abstract methods properly
- Add appropriate error handling

### Testing
- No formal test framework is currently set up
- Manual testing through command line execution
- Test different platforms and crawl types

## Important Notes

### Legal Compliance
- This code is for educational and research purposes only
- Comply with platform terms of service and robots.txt
- Control request frequency to avoid platform disruption
- Not for commercial use or large-scale crawling

### Platform Detection
- Different platforms have different detection mechanisms
- Xiaohongshu may force logout if crawling too fast
- Use appropriate delays and proxy settings
- Consider using CDP mode for better stealth

### Performance Considerations
- Adjust `MAX_CONCURRENCY_NUM` based on your system
- Use `CRAWLER_MAX_SLEEP_SEC` to control request frequency
- Enable proxy rotation if doing large-scale crawling
- Monitor memory usage with browser contexts

## Troubleshooting

### Common Issues
1. **Login failures**: Try different login methods, manual verification
2. **Detection blocks**: Enable CDP mode, use proxies, reduce frequency
3. **Database errors**: Check database configuration, initialize with `--init_db`
4. **Browser issues**: Ensure Playwright drivers are installed, try CDP mode

### Debug Commands
```bash
# Check Python environment
python --version
pip list

# Test Playwright installation
uv run playwright --version

# Verify database connection
python test_db_connection.py
```

## Project Structure
```
MediaCrawler/
├── base/                    # Abstract base classes
├── config/                  # Configuration files
├── database/               # Database models and connections
├── media_platform/         # Platform-specific implementations
├── store/                  # Data storage implementations
├── tools/                  # Utility functions
├── data/                   # Output data directory
├── docs/                   # Documentation
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
└── pyproject.toml          # Project configuration
```