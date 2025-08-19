import streamlit as st
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build
from streamlit_autorefresh import st_autorefresh
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO

# ================= LOAD API KEY =================
if "YOUTUBE_API_KEY" not in st.secrets:
    st.error("⚠️ API Key belum diatur di Streamlit Cloud → Secrets")
    st.stop()

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build('youtube', 'v3', developerKey=API_KEY)
analyzer = SentimentIntensityAnalyzer()

# ================= FUNCTION GET COMMENT =================
def get_comments(video_id, max_results=200):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,
            textFormat="plainText",
            order="time"
        )
        while request and len(comments) < max_results:
            response = request.execute()
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment)
            request = youtube.commentThreads().list_next(request, response)
    except Exception as e:
        st.error(f"Gagal ambil komentar: {e}")
    return comments[:max_results]

def analyze_sentiment(text):
    score = analyzer.polarity_scores(text)
    if score['compound'] >= 0.05:
        return 'Positif'
    elif score['compound'] <= -0.05:
        return 'Negatif'
    else:
        return 'Netral'

@st.cache_data(ttl=300)  # cache 5 menit
def fetch_and_analyze(video_id):
    comments = get_comments(video_id)
    data = []
    for c in comments:
        label = analyze_sentiment(c)
        data.append({"VideoID": video_id, "Komentar": c, "Sentimen": label})
    return pd.DataFrame(data)

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
            if "v=" in v:
                video_ids.append(v.split("v=")[1].split("&")[0])
            elif "youtu.be/" in v:
                video_ids.append(v.split("youtu.be/")[1].split("?")[0])
        else:
            video_ids.append(v)

    all_data = []
    summary = {}

    for vid in video_ids:
        df_video = fetch_and_analyze(vid)
        if not df_video.empty:
            all_data.append(df_video)
            summary[vid] = len(df_video)

    if all_data:
        df = pd.concat(all_data, ignore_index=True)

        # ================= STAT BOX =================
        st.subheader("📊 Statistik Komentar")

        colors = ["#FF9999", "#99CCFF", "#99FF99", "#FFD966", "#FFB266", "#CC99FF"]

        cols = st.columns(len(summary))
        for i, (vid, count) in enumerate(summary.items()):
            color = colors[i % len(colors)]
            with cols[i]:
                st.markdown(
                    f"""
                    <div style='background-color:{color}; 
                                padding:20px; 
                                border-radius:15px; 
                                text-align:center;
                                box-shadow:2px 2px 10px rgba(0,0,0,0.2);'>
                        <h4 style='margin:0; color:black;'>Video {i+1}</h4>
                        <h2 style='margin:0; color:black;'>{count}</h2>
                        <p style='margin:0; color:black;'>Komentar</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # total kotak
        total_comments = len(df)
        st.metric(label="Total Semua Komentar", value=f"{total_comments} Komentar")

        # ================= KOMENTAR & SENTIMEN =================
        st.subheader("📋 Komentar & Sentimen")
        st.dataframe(df)

        # ================= WORD CLOUD =================
        st.subheader("☁️ Word Cloud Komentar")
        all_text = " ".join(df["Komentar"].tolist())
        all_text = all_text.encode("utf-8", "ignore").decode("utf-8")
        if all_text.strip():
            wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_text)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("Tidak ada kata yang bisa dibuat Word Cloud.")

                # ================= GRAFIK =================
        st.subheader("📊 Grafik Sentimen Total")
        st.bar_chart(df['Sentimen'].value_counts())

        st.subheader("📊 Distribusi Sentimen (Pie Chart)")
        sentiment_counts = df['Sentimen'].value_counts()
        fig, ax = plt.subplots()
        ax.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', startangle=90)
        ax.axis("equal")
        st.pyplot(fig)


        # ========== Tombol Download ==========
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Hasil (CSV)",
            data=csv,
            file_name="sentimen_youtube.csv",
            mime="text/csv",
        )

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Sentimen")
        st.download_button(
            label="⬇️ Download Hasil (Excel)",
            data=output.getvalue(),
            file_name="sentimen_youtube.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    else:
        st.warning("Komentar tidak ditemukan atau ID salah.")
else:
    st.info("Masukkan Video ID atau URL.")