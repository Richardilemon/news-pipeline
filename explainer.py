from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from geotext import GeoText
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((HttpError, TimeoutError)),
    before_sleep=lambda retry_state: logger.info(f"Retrying API call (attempt {retry_state.attempt_number})...")
)
def fetch_sheets_data(service, spreadsheet_id, range_name):
    """Fetch data from Google Sheets with retry logic."""
    return service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

def generate_explainer_script():
    logger.info("Generating explainer script...")
    try:
        # Load environment variables
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found")
            raise ValueError("Missing OPENAI_API_KEY")

        # Initialize Google Sheets client
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        if not os.path.exists(credentials_path):
            logger.error(f"{credentials_path} not found in {os.getcwd()}")
            raise FileNotFoundError(f"{credentials_path} not found")
        creds = Credentials.from_service_account_file(credentials_path)
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)  # Disable file_cache
        spreadsheet_id = '1CmeiZuIMbgVss2x4R1zGIvYjTenI6E3Jpn_F96iTJKA'

        # Fetch data with retry
        try:
            result = fetch_sheets_data(service, spreadsheet_id, 'Articles!A1:F1000')
        except Exception as e:
            logger.error(f"Failed to fetch data from Google Sheets after retries: {e}")
            return False
        data = result.get('values', [])
        if not data or len(data) <= 1:
            logger.error("No articles found in Google Sheet.")
            return False
        
        # Create DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        logger.info(f"Loaded {len(df)} articles from Google Sheet.")
        logger.info(f"DataFrame columns: {df.columns.tolist()}")  # Debug column names

        # Handle empty DataFrame
        if df.empty:
            logger.error("DataFrame is empty. No articles found in Google Sheet.")
            return False

        # Handle empty summaries
        df['Summary'] = df['Summary'].fillna('No summary available.')

        # Validate required column
        if 'Timestamp' not in df.columns:
            logger.error(f"Expected 'Timestamp' column, but found: {df.columns.tolist()}")
            return False

        # Clean and convert Timestamp column
        def parse_date(date_str):
            try:
                return pd.to_datetime(date_str, format='mixed', errors='coerce')
            except Exception as e:
                logger.debug(f"Invalid date format for '{date_str}': {e}")
                return pd.NaT

        df['Date'] = df['Timestamp'].apply(parse_date)
        if df['Date'].isna().all():
            logger.error("All dates are invalid or missing in the 'Timestamp' column.")
            return False
        if df['Date'].isna().any():
            logger.warning(f"{df['Date'].isna().sum()} invalid dates found in 'Timestamp' column.")

        # Compute insights
        category_counts = df['Category'].value_counts().head(2)
        locations = df['Summary'].apply(lambda x: GeoText(x).cities if isinstance(x, str) else []).explode().value_counts().head(3)
        latest_date = df['Date'].max().strftime('%B %d, %Y %I:%M %p WAT')
        sample_headline = df['Headline'].iloc[0] if not df['Headline'].empty else 'No headline available.'

        # Initialize OpenAI client
        client = OpenAI(api_key=openai_api_key)
        locations_str = ', '.join(locations.index) if not locations.empty else 'None'
        article_count = len(df)

        # Generate script
        prompt = f"""
        You are a professional scriptwriter creating a 60-second explainer video script (120-150 words) summarizing news articles. Use the following insights from {article_count} articles scraped from Ground.news:

        - Top categories: {category_counts.index[0] if len(category_counts) > 0 else 'None'} ({category_counts[0] if len(category_counts) > 0 else 0} articles), {category_counts.index[1] if len(category_counts) > 1 else 'None'} ({category_counts[1] if len(category_counts) > 1 else 0} articles).
        - Latest article date: {latest_date}.
        - Locations mentioned (if any): {locations_str}.
        - Sample headline: {sample_headline}.

        Write a script with:
        - Intro (10s): Engage the audience and state the purpose.
        - Body (40s): Highlight key trends, categories, and locations (if available).
        - Outro (10s): Summarize and include a call-to-action (visit GroundNewsArticles.com).

        Keep it concise, engaging, and suitable for a general audience. Emphasize geospatial trends if locations are provided.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a skilled scriptwriter for explainer videos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        script = response.choices[0].message.content.strip()

        # Save script
        file_path = 'explainer_script.txt'
        with open(file_path, 'w') as f:
            f.write(f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{script}")
        logger.info(f"Script saved as {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error generating explainer script: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    generate_explainer_script()