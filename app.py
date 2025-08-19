import streamlit as st
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from streamlit_autorefresh import st_autorefresh
import os
from dotenv import load_dotenv
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import base64

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

video_input = st.text_input("Masukkan Video ID atau URL YouTube (pisahkan dengan koma):", value="dQw4w9WgXcQ")

if video_input:
    video_ids = []
    for v in video_input.split(","):
        v = v.strip()
        if "youtube.com" in v or "youtu.be" in v:
            # Ambil ID dari URL
            if "v=" in v:
                video_ids.append(v.split("v=")[1].split("&")[0])
            elif "youtu.be/" in v:
                video_ids.append(v.split("youtu.be/")[1].split("?")[0])
        else:
            video_ids.append(v)

    all_data = []
    summary = {}

    for vid in video_ids:
        comments = get_comments(vid)
        if comments:
            data = []
            for c in comments:
                label = analyze_sentiment(c)
                data.append({"VideoID": vid, "Komentar": c, "Sentimen": label})

            df_video = pd.DataFrame(data)
            all_data.append(df_video)

            summary[vid] = len(comments)

    if all_data:
        df = pd.concat(all_data, ignore_index=True)

        st.subheader("📋 Komentar & Sentimen")
        st.dataframe(df)

                # ================= WORD CLOUD =================
        st.subheader("☁️ Word Cloud Komentar")
        all_text = " ".join(df["Komentar"].tolist())
        if all_text.strip():
            wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_text)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("Tidak ada kata yang bisa dibuat Word Cloud.")

        # ========== Tambahkan tombol download ==========
        # Download CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Hasil (CSV)",
            data=csv,
            file_name="sentimen_youtube.csv",
            mime="text/csv",
        )

        # Download Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Sentimen")
        st.download_button(
            label="⬇️ Download Hasil (Excel)",
            data=output.getvalue(),
            file_name="sentimen_youtube.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.subheader("📊 Grafik Sentimen Total")
        st.bar_chart(df['Sentimen'].value_counts())

        st.subheader("📌 Insight")
        total_comments = len(df)
        st.write(f"Total komentar dianalisis: **{total_comments}**")
        st.write(f"Jumlah video dianalisis: **{len(video_ids)}**")
        for vid, count in summary.items():
            st.write(f"- Video `{vid}`: {count} komentar")
    else:
        st.warning("Komentar tidak ditemukan atau ID salah.")
else:
    st.info("Masukkan Video ID atau URL.")