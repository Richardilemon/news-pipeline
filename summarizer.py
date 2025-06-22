import os
import logging
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
    raise ValueError("Missing OpenAI API key")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_article_content(url):
    """
    Fetch and extract article text from a given URL.
    
    Args:
        url: URL of the article.
    
    Returns:
        str: Extracted article text or None if failed.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }
    try:
        logger.debug(f"Fetching article: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Target article body (adjust selector based on Ground.news structure)
        article_body = soup.select_one('article, div.content, div.article-body')
        if not article_body:
            logger.warning(f"No article body found for {url}")
            return None
        
        # Extract paragraphs
        paragraphs = article_body.find_all('p')
        if not paragraphs:
            logger.warning(f"No paragraphs found for {url}")
            return None
        
        # Combine text, limiting to ~2000 tokens (~8000 chars) for API
        text = ' '.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        text = text[:8000]  # Truncate to avoid API limits
        if not text:
            logger.warning(f"No valid text extracted for {url}")
            return None
        
        logger.debug(f"Extracted {len(text)} characters from {url}")
        return text
    except Exception as e:
        logger.error(f"Error fetching article {url}: {e}")
        return None

def summarize_article(text):
    """
    Summarize article text using OpenAI API.
    
    Args:
        text: Article text to summarize.
    
    Returns:
        str: Summary (2-3 sentences) or None if failed.
    """
    try:
        logger.debug("Sending text to OpenAI for summarization")
        prompt = (
            "Summarize the following article in 2-3 concise sentences, focusing on the main points. "
            "Keep the summary under 100 words:\n\n" + text
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes news articles concisely."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5
        )
        summary = response.choices[0].message.content.strip()
        logger.debug(f"Generated summary: {summary[:50]}...")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing article: {e}")
        return None

def summarize_articles(articles):
    """
    Add summaries to a list of articles.
    
    Args:
        articles: List of dictionaries with headline, source, url, category.
    
    Returns:
        List of dictionaries with added summary field.
    """
    summarized_articles = []
    for index, article in enumerate(articles, 1):
        try:
            logger.info(f"Processing article {index}: {article['headline'][:50]}...")
            content = fetch_article_content(article['url'])
            if not content:
                logger.warning(f"Skipping article {index} due to no content")
                summarized_articles.append({**article, 'summary': None})
                continue
            
            summary = summarize_article(content)
            if not summary:
                logger.warning(f"Skipping summary for article {index}")
                summarized_articles.append({**article, 'summary': None})
                continue
            
            summarized_articles.append({
                **article,
                'summary': summary
            })
            logger.info(f"Summarized article {index}: {summary[:50]}...")
        except Exception as e:
            logger.error(f"Error processing article {index}: {e}")
            summarized_articles.append({**article, 'summary': None})
            continue
    
    return summarized_articles

def main():
    """Main function to test the summarizer with sample data."""
    # Sample input from scraper.py (replace with actual scraper output)
    sample_articles = [
        {
            'headline': 'UK parliament votes for assisted dying paving way for historic law change',
            'source': '43% Center coverage: 222 sources',
            'url': 'https://ground.news/article/uk-parliament-votes-for-assisted-dying-paving-way-for-historic-law-change_81cdb3',
            'category': 'UK'
        },
        {
            'headline': 'Trump to decide on US action in Israel-Iran conflict within two weeks, White House says',
            'source': '37% Right coverage: 73 sources',
            'url': 'https://ground.news/article/trump-to-decide-on-us-action-in-israel-iran-conflict-within-two-weeks-white-house-says_53e046',
            'category': 'Israel-Hamas Conflict'
        }
    ]
    
    summarized_articles = summarize_articles(sample_articles)
    
    # Print results
    if not summarized_articles:
        logger.warning("No articles summarized.")
    else:
        logger.info(f"Summarized {len(summarized_articles)} articles:")
        for item in summarized_articles:
            print(f"Category: {item['category']}")
            print(f"Headline: {item['headline']}")
            print(f"Source: {item['source']}")
            print(f"URL: {item['url']}")
            print(f"Summary: {item['summary']}")
            print("-" * 50)

if __name__ == "__main__":
    main()