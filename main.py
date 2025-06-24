import os
import logging
from scraper import scrape_ground_news, load_keywords
from summarizer import summarize_articles
from sheets import store_articles
from explainer import generate_explainer_script

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to scrape, summarize, store articles, and generate explainer script."""
    try:
        # Load keywords
        keywords = load_keywords('config/keywords.txt')
        if not keywords:
            logger.error("No keywords loaded. Exiting.")
            return

        # Scrape articles
        logger.info("Running scraper...")
        articles = scrape_ground_news(keywords, max_articles=50, source_type='coverage')
        if not articles:
            logger.warning("No articles scraped. Exiting.")
            return
        logger.info(f"Scraped {len(articles)} articles.")

        # Summarize articles
        logger.info("Running summarizer...")
        summarized_articles = summarize_articles(articles)
        if not summarized_articles:
            logger.error("No articles summarized. Exiting.")
            return
        logger.info(f"Summarized {len(summarized_articles)} articles.")

        # Store in Google Sheets
        logger.info("Storing articles in Google Sheets...")
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'GroundNewsArticles')
        if not credentials_path or not os.path.exists(credentials_path):
            logger.error("Google credentials path not set or file not found.")
            return
        success = store_articles(summarized_articles, credentials_path, spreadsheet_name)
        if not success:
            logger.error("Failed to store articles in Google Sheets.")
            return

        # Generate explainer script
        logger.info("Generating explainer script...")
        success = generate_explainer_script()
        if success:
            logger.info("Explainer script generated and saved as explainer_script.txt")
        else:
            logger.error("Failed to generate explainer script.")

        # Print results
        logger.info(f"Processed {len(summarized_articles)} articles:")
        for item in summarized_articles:
            logger.info(f"Article keys: {item.keys()}")  # Debug keys
            date = item.get('Timestamp', 'Unknown')  # Use Timestamp with fallback
            print(f"Timestamp: {date}")
            print(f"Category: {item['category']}")
            print(f"Headline: {item['headline']}")
            print(f"Source: {item['source']}")
            print(f"URL: {item['url']}")
            print(f"Summary: {item['summary']}")
            print("-" * 100)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()