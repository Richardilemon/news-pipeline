import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'GroundNewsArticles')

def initialize_gsheets_client(credentials_path):
    """
    Initialize Google Sheets client using service account credentials.
    
    Args:
        credentials_path: Path to Google service account JSON key file.
    
    Returns:
        gspread.Client: Authorized client or None if failed.
    """
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        logger.info("Initializing Google Sheets client...")
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Error initializing Google Sheets client: {e}")
        return None

def store_articles(articles, credentials_path, spreadsheet_name):
    """
    Store articles in a Google Sheet.
    
    Args:
        articles: List of dictionaries with timestamp, category, headline, source, url, summary.
        credentials_path: Path to Google service account JSON key file.
        spreadsheet_name: Name of the Google Sheet.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    client = initialize_gsheets_client(credentials_path)
    if not client:
        return False

    try:
        # Open or create spreadsheet
        try:
            spreadsheet = client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            logger.info(f"Creating new spreadsheet: {spreadsheet_name}")
            spreadsheet = client.create(spreadsheet_name)
            # Share with your email (optional, uncomment if needed)
            # spreadsheet.share('your-email@example.com', perm_type='user', role='writer')

        # Select or create worksheet
        try:
            worksheet = spreadsheet.worksheet('Articles')
        except gspread.WorksheetNotFound:
            logger.info("Creating new worksheet: Articles")
            worksheet = spreadsheet.add_worksheet(title='Articles', rows=1000, cols=6)
            # Set headers
            headers = ['Headline', 'Source', 'URL', 'Category', 'Summary', 'Timestamp']
            worksheet.append_row(headers, table_range='A1:F1')

        # Get existing URLs to avoid duplicates
        existing_urls = set(worksheet.col_values(3)[1:])  # Column C (URL), skip header

        # Prepare rows to append
        rows_to_append = []
        for article in articles:
            if article.get('url') in existing_urls:
                logger.debug(f"Skipping duplicate article: {article.get('headline', 'Unknown')[:50]}...")
                continue
            row = [
                article.get('headline', ''),
                article.get('source', ''),
                article.get('url', ''),
                article.get('category', ''),
                article.get('summary', 'No summary available.'),
                article.get('timestamp', '')
            ]
            rows_to_append.append(row)
            existing_urls.add(article.get('url'))

        if not rows_to_append:
            logger.info("No new articles to append.")
            return True

        # Append rows
        logger.info(f"Appending {len(rows_to_append)} articles to Google Sheet...")
        worksheet.append_rows(rows_to_append, value_input_option='RAW')
        logger.info("Articles successfully stored in Google Sheet.")
        return True

    except Exception as e:
        logger.error(f"Error storing articles in Google Sheet: {e}")
        return False

def main():
    """Main function to test the Google Sheets output with sample data."""
    sample_articles = [
        {
            'timestamp': '2025-06-23 18:42:30',
            'category': 'UK',
            'headline': 'UK parliament votes for assisted dying paving way for historic law change',
            'source': '43% Center coverage: 222 sources',
            'url': 'https://ground.news/article/uk-parliament-votes-for-assisted-dying-paving-way-for-historic-law-change_81cdb3',
            'summary': 'The UK Parliament voted to legalize assisted dying, a historic step toward law reform.'
        },
        {
            'timestamp': '2025-06-23 18:42:30',
            'category': 'Israel-Hamas Conflict',
            'headline': 'Trump to decide on US action in Israel-Iran conflict within two weeks, White House says',
            'source': '37% Right coverage: 73 sources',
            'url': 'https://ground.news/article/trump-to-decide-on-us-action-in-israel-iran-conflict-within-two-weeks-white-house-says_53e046',
            'summary': 'The White House announced that President Trump will decide within two weeks on U.S. actions.'
        }
    ]

    credentials_path = GOOGLE_CREDENTIALS_PATH
    if not credentials_path or not os.path.exists(credentials_path):
        logger.error("Google credentials path not set or file not found. Set GOOGLE_CREDENTIALS_PATH in .env.")
        return

    success = store_articles(sample_articles, credentials_path, SPREADSHEET_NAME)
    if success:
        logger.info("Test storage completed successfully.")
    else:
        logger.error("Test storage failed.")

if __name__ == "__main__":
    main()