from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from geotext import GeoText
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os

def generate_explainer_script():
    load_dotenv()
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found")

    credentials_path = 'credentials.json'
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"{credentials_path} not found in {os.getcwd()}")
    creds = Credentials.from_service_account_file(credentials_path)
    service = build('sheets', 'v4', credentials=creds)
    spreadsheet_id = '1CmeiZuIMbgVss2x4R1zGIvYjTenI6E3Jpn_F96iTJKA'

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='Articles!A1:F1000'
    ).execute()
    data = result.get('values', [])
    df = pd.DataFrame(data[1:], columns=data[0])

    category_counts = df['Category'].value_counts().head(2)
    locations = df['Summary'].apply(lambda x: GeoText(x).cities).explode().value_counts().head(2)
    latest_date = pd.to_datetime(df['Date']).max().strftime('%B %d, %Y')
    sample_headline = df['Headline'].iloc[0]

    client = OpenAI(api_key=openai_api_key)
    locations_str = ', '.join(locations.index) if not locations.empty else 'None'
    prompt = f"""
    You are a professional scriptwriter creating a 60-second explainer video script (120-150 words) summarizing news articles. Use the following insights from 20 articles scraped from Ground.news:

    - Top categories: {category_counts.index[0]} ({category_counts[0]} articles), {category_counts.index[1]} ({category_counts[1]} articles).
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

    with open('explainer_script.txt', 'w') as f:
        f.write(script)
    print("Script saved as explainer_script.txt")
    return script

if __name__ == '__main__':
    generate_explainer_script()