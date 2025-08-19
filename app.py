import streamlit as st
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from streamlit_autorefresh import st_autorefresh
import os
from dotenv import load_dotenv
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ================= LOAD API KEY =================
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    st.error("API Key tidak ditemukan. Pastikan file .env berisi YOUTUBE_API_KEY=xxxx")
    st.stop()

youtube = build('youtube', 'v3', developerKey=API_KEY)
analyzer = SentimentIntensityAnalyzer()

def get_comments(video_id, max_results=50):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=max_results,
            textFormat="plainText",
            order="time"
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)
    except Exception as e:
        st.error(f"Gagal ambil komentar: {e}")
    return comments

def analyze_sentiment(text):
    score = analyzer.polarity_scores(text)
    if score['compound'] >= 0.05:
        return 'Positif'
    elif score['compound'] <= -0.05:
        return 'Negatif'
    else:
        return 'Netral'

# ================= STREAMLIT START =================
st.set_page_config(page_title="YouTube Sentiment Real-Time", layout="wide")
st.title("📺 Dashboard Realtime Analisis Sentimen Komentar YouTube")
st_autorefresh(interval=30000, key="refresh")  # refresh 30 detik

video_id = st.text_input("Masukkan Video ID YouTube:", value="dQw4w9WgXcQ")

if video_id:
    comments = get_comments(video_id)
    if comments:
        data = []
        for c in comments:
            label = analyze_sentiment(c)
            data.append({"Komentar": c, "Sentimen": label})

        df = pd.DataFrame(data)

        st.subheader("📋 Komentar & Sentimen")
        st.dataframe(df)

        st.subheader("📊 Grafik Sentimen")
        st.bar_chart(df['Sentimen'].value_counts())

        # ================= WORD CLOUD =================
        st.subheader("☁️ Word Cloud Komentar")
        option = st.radio("Pilih jenis sentimen untuk Word Cloud:",
                          ["Semua", "Positif", "Negatif", "Netral"], horizontal=True)

        if option == "Semua":
            filtered_text = " ".join(df["Komentar"].tolist())
        else:
            filtered_text = " ".join(df[df["Sentimen"] == option]["Komentar"].tolist())

        if filtered_text.strip():
            wordcloud = WordCloud(width=800, height=400, background_color="white").generate(filtered_text)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("Tidak ada kata yang bisa dibuat Word Cloud untuk filter ini.")

        # ================= DOWNLOAD =================
        st.subheader("⬇️ Download Hasil Analisis")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="sentiment_result.csv",
            mime="text/csv"
        )

    else:
        st.warning("Komentar tidak ditemukan atau ID salah.")
else:
    st.info("Masukkan Video ID.")