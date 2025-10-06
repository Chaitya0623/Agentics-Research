import streamlit as st
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field
from typing import Optional
from agentics import AG
import datetime
import asyncio
from agentics.core.atype import import_pydantic_from_string

class OilPriceChangeEvent(BaseModel):
    """Represents an event of oil price change."""
    date: Optional[str] = Field(None, description="The date of the oil price change event in YYYY-MM-DD format.")
    price_change_percentage: Optional[float] = Field(None, description="The percentage change in oil prices on that date.")
    impact_on_market: Optional[str] = Field(None, description="A brief description of the impact of the oil price change on the stock market.")



example_class = """
class NewsHeadline(BaseModel):
    headline: Optional[str] = Field(None, description="A news headline relevant to the stock market for the day.")
    date: Optional[str] = Field(None, description="The date of the news headline in YYYY-MM-DD format.")
    sentiment: Optional[str] = Field(None, description="The sentiment of the news headline, e.g., Positive, Negative, Neutral.")    

class MarketSentiment(BaseModel):
    market_sentiment: Optional[str] = Field(None, description="The general market sentiment for the day, e.g., Positive, Negative, Neutral.")
    market_sentiment_explanation:Optional[str] = Field(None, description="Explain the main reason for the market sentiment judgment you just expressed.")
    relevant_factors: Optional[list[str]] = Field(None, description="List the most relevant factors (e.g., economic indicators, geopolitical events) that influenced your market sentiment assessment.")
    relevant_news_selection: Optional[list[NewsHeadline]] = Field(None, description="List the specific news headlines that had a significant impact on your market sentiment evaluation.")
    confidence_level: Optional[float] = Field(None, description="Rate your confidence in the market sentiment assessment on a scale from 0 to 1, where 1 indicates absolute confidence.")
"""

if "market_dataset" not in st.session_state:
    st.session_state.market_dataset = AG.from_csv("/Users/gliozzo/Code/agentics911/agentics/data/macro_economic_analysis/market_factors_new.csv")

if "market_dataset_index" not in st.session_state:
    st.session_state.market_dataset_index={s.Date : i for i, s in enumerate(st.session_state.market_dataset.states)}



start = datetime.date(2008, 7, 1)
end = datetime.date(2025, 10, 3)


outer_tabs = st.tabs(["📈 Analytics", "⚙️ Settings"])

with st.form("Selection"):
   
    selected_start = st.selectbox("start date", options=sorted(st.session_state.market_dataset_index.keys()), index=0)
    selected_end = st.selectbox("end date", options=sorted(st.session_state.market_dataset_index.keys()), index=0)
    type_code = st.text_area("Insert a Pydantic Type to focus your analysis", value=example_class, height=300)
    class_name= st.text_input("Class Name", value="MarketSentiment")
    areduce_batch_size = st.number_input("areduce_batch_size", value=10, min_value=1, max_value=50, step=1)
    
    market_sentiment_analysis= st.form_submit_button("Perform Market Sentiment Analysis")
if market_sentiment_analysis:
    target_atype= import_pydantic_from_string(type_code, class_name)
    start_index= st.session_state.market_dataset_index[str(selected_start)]
    end_index= st.session_state.market_dataset_index[str(selected_end)]

    sentiment = asyncio.run((AG(atype=target_atype,
                                 transduction_type="areduce",
                                 areduce_batch_size=areduce_batch_size) \
                            << st.session_state.market_dataset.filter_states(
                                start=start_index, end=end_index+1)))
#     st.markdown(f"""
# ## 🧭 Market Sentiment Analysis

# | **Field** | **Value** |
# |------------|------------|
# | **Period** | {selected_start} – {selected_end} |
# | **Sentiment** | {sentiment[0].market_sentiment} |
# | **Explanation** | {sentiment[0].market_sentiment_explanation} |
# | **Relevant Factors** | {', '.join(sentiment[0].relevant_factors) if sentiment[0].relevant_factors else 'N/A'} |
# | **Relevant News** | {', '.join([f"{news.date}: {news.headline}" for news in sentiment[0].relevant_news_selection]) if sentiment[0].relevant_news_selection else 'N/A'} |
# | **Confidence Level** | {sentiment[0].confidence_level if sentiment[0].confidence_level is not None else 'N/A'} |
# """, unsafe_allow_html=True)
    st.write(sentiment.pretty_print())
    st.write(sentiment.areduce_batches)
import os