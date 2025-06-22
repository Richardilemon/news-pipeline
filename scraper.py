import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime  # Added for date

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def load_keywords(file_path='config/keywords.txt'):
    """Load keywords from a file."""
    try:
        if not os.path.exists(file_path):
            logger.info(f"Creating keywords file at {file_path}")
            os.makedirs('config', exist_ok=True)
            with open(file_path, 'w') as f:
                f.write("Iran\nIsrael\nHamas\nwar\nclimate\nUK\nUS\nIsraeli")
        with open(file_path, 'r') as f:
            keywords = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded keywords: {keywords}")
            return keywords
    except Exception as e:
        logger.error(f"Error loading keywords: {e}")
        return ["Iran", "Israel", "Hamas", "war", "climate", "UK", "US", "Israeli"]

def scrape_ground_news(keywords, max_articles=50, source_type='coverage'):
    """
    Scrape headlines from Ground.news landing page, filtering by keywords.
    
    Args:
        keywords: List of keywords to filter headlines.
        max_articles: Maximum number of article containers to process.
        source_type: 'coverage' for bias coverage, 'category' for category.
    
    Returns:
        List of dictionaries with headline, source, URL, category, and date.
    """
    base_url = "https://ground.news"
    news_data = []
    seen_urls = set()
    seen_headlines = set()
    scrape_date = datetime.now().strftime('%Y-%m-%d')  # Added: Current date as YYYY-MM-DD

    # Set up headless Chrome
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    
    # Initialize WebDriver
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        logger.error(f"Error initializing WebDriver: {e}")
        return news_data

    try:
        logger.info("Scraping articles from Ground.news landing page...")
        driver.get(base_url)
        # Wait for articles to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.flex.justify-between a.relative, div.group a.flex"))
        )
        # Scroll multiple times
        for i in range(5):
            logger.debug(f"Scrolling page, attempt {i+1}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)

        # Parse rendered HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articles = soup.select('div.flex.justify-between a.relative, div.group a.flex')
        logger.info(f"Found {len(articles)} article containers")

        if not articles:
            logger.warning("No articles found on landing page. Check selectors or site structure.")

        for index, article in enumerate(articles[:max_articles]):
            try:
                logger.debug(f"Processing article {index+1}")
                # Extract headline
                headline_elem = article.select_one('h2:not(.hidden), h4') or article.select_one('h2, h4')
                headline = headline_elem.text.strip() if headline_elem else None
                if not headline:
                    logger.debug("Skipping article with no valid headline")
                    continue
                logger.debug(f"Headline found: {headline[:50]}...")

                # Skip duplicate headlines
                if headline in seen_headlines:
                    logger.debug(f"Skipping duplicate headline: {headline[:50]}...")
                    continue
                seen_headlines.add(headline)

                # Extract URL
                url = article['href'] if article.get('href') else None
                if url and url.startswith('/'):
                    url = base_url + url
                elif url and not url.startswith('http'):
                    logger.debug(f"Invalid URL found: {url}")
                    url = None
                if not url:
                    logger.debug(f"Skipping article with no valid URL: {headline[:50]}...")
                    continue
                logger.debug(f"URL found: {url}")

                # Skip duplicate URLs
                if url in seen_urls:
                    logger.debug(f"Skipping duplicate article: {headline[:50]}...")
                    continue
                seen_urls.add(url)

                # Check for keywords
                matching_keyword = None
                headline_lower = headline.lower()
                for kw in keywords:
                    if kw.lower() in headline_lower:
                        if kw.lower() in ["israel", "hamas", "war", "israeli"]:
                            matching_keyword = "Israel-Hamas Conflict"
                            break
                        elif not matching_keyword:
                            matching_keyword = kw
                if not matching_keyword:
                    logger.debug(f"Skipping article with no matching keyword: {headline[:50]}...")
                    continue
                logger.debug(f"Matching keyword: {matching_keyword}")

                # Extract source
                source = 'Unknown'
                if source_type == 'coverage':
                    source_elem = article.select_one('div.text-12.leading-6 > span')
                    if source_elem:
                        source = source_elem.text.strip()
                    else:
                        source_elem = article.select_one('span.text-12.leading-6')
                        if source_elem:
                            source = source_elem.text.strip()
                else:
                    source_elem = article.select_one('span.text-12.leading-6')
                    if source_elem:
                        source = source_elem.text.strip()
                    else:
                        source_elem = article.select_one('div.text-12.leading-6 > span')
                        if source_elem:
                            source = source_elem.text.strip()
                logger.debug(f"Source found: {source}")

                news_data.append({
                    'headline': headline,
                    'source': source,
                    'url': url,
                    'category': matching_keyword,
                    'date': scrape_date  # Added: Date field
                })
                logger.info(f"Scraped article: {headline} ({matching_keyword})")
            except Exception as e:
                logger.error(f"Error processing article {index+1}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error fetching landing page: {e}")
    finally:
        driver.quit()

    return news_data

def main():
    """Main function to test the scraper."""
    keywords = load_keywords()
    news_data = scrape_ground_news(keywords, source_type='coverage')
    
    # Print results for verification
    if not news_data:
        logger.warning("No articles scraped. Please check selectors, keywords, or site structure.")
    else:
        logger.info(f"Scraped {len(news_data)} articles:")
        for item in news_data:
            print(f"Date: {item['date']}")  # Added: Display date
            print(f"Category: {item['category']}")
            print(f"Headline: {item['headline']}")
            print(f"Source: {item['source']}")
            print(f"URL: {item['url']}")
            print("-" * 50)

if __name__ == "__main__":
    main()