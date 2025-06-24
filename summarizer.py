import os
import logging
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

def summarize_article(article):
    """
    Summarize article using OpenAI API based on headline and metadata.
    
    Args:
        article: Dictionary with headline, source, url, category, date.
    
    Returns:
        str: Summary (2-3 sentences) or default if failed.
    """
    try:
        logger.debug(f"Summarizing article: {article['headline'][:50]}...")
        prompt = (
            "Summarize the following news article in 2-3 concise sentences based on its headline, category, and source. "
            "Focus on key events and potential locations, keeping the summary under 100 words.\n\n"
            f"Headline: {article['headline']}\n"
            f"Category: {article['category']}\n"
            f"Source: {article['source']}\n"
            f"URL: {article['url']}"
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
        return summary if summary else 'No summary available.'
    except Exception as e:
        logger.error(f"Error summarizing article: {e}")
        return 'No summary available.'

def summarize_articles(articles):
    """
    Add summaries to a list of articles.
    
    Args:
        articles: List of dictionaries with headline, source, url, category, date.
    
    Returns:
        List of dictionaries with added summary field.
    """
    summarized_articles = []
    for index, article in enumerate(articles, 1):
        try:
            logger.info(f"Processing article {index}: {article['headline'][:50]}...")
            summary = summarize_article(article)
            summarized_articles.append({
                **article,
                'summary': summary
            })
            logger.info(f"Summarized article {index}: {summary[:50]}...")
        except Exception as e:
            logger.error(f"Error processing article {index}: {e}")
            summarized_articles.append({**article, 'summary': 'No summary available.'})
    
    logger.info(f"Summarized {len(summarized_articles)} articles.")
    return summarized_articles

def main():
    """Main function to test the summarizer with sample data."""
    sample_articles = [
        {
            'headline': 'UK parliament votes for assisted dying paving way for historic law change',
            'source': '43% Center coverage: 222 sources',
            'url': 'https://ground.news/article/uk-parliament-votes-for-assisted-dying-paving-way-for-historic-law-change_81cdb3',
            'category': 'UK',
            'date': '2025-06-23 18:42:30'
        },
        {
            'headline': 'Trump to decide on US action in Israel-Iran conflict within two weeks, White House says',
            'source': '37% Right coverage: 73 sources',
            'url': 'https://ground.news/article/trump-to-decide-on-us-action-in-israel-iran-conflict-within-two-weeks-white-house-says_53e046',
            'category': 'Israel-Hamas Conflict',
            'date': '2025-06-23 18:42:30'
        }
    ]
    
    summarized_articles = summarize_articles(sample_articles)
    
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
            print("-" * 100)

if __name__ == "__main__":
    main()