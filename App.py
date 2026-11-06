import os
import streamlit as st
import yt_dlp
from google import genai

# ------------------------------------------------------------------------------
# 1. Page Configuration & Setup
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Shorts & Video Keyword Extractor",
    page_icon="🔍",
    layout="wide"
)

# Gemini API Key 설정 (Streamlit Secrets 또는 환경 변수 지원)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key and "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

# ------------------------------------------------------------------------------
# 2. Helper Functions
# ------------------------------------------------------------------------------
def extract_video_info(url: str, max_comments: int = 30):
    """
    yt-dlp를 이용하여 영상의 제목과 상위 댓글을 수집합니다.
    """
    ydl_opts = {
        'extract_flat': False,
        'skip_download': True,
        'getcomments': True,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', '제목 없음')
        description = info.get('description', '')
        
        # 댓글 데이터 추출
        raw_comments = info.get('comments', [])
        comments = []
        if raw_comments:
            for c in raw_comments[:max_comments]:
                text = c.get('text', '').strip()
                if text:
                    comments.append(text)

    return title, description, comments


def analyze_keywords_with_gemini(api_key: str, title: str, description: str, comments: list):
    """
    Gemini API를 호출하여 영상 데이터 및 댓글 기반 키워드 추론 및 확장을 수행합니다.
    """
    client = genai.Client(api_key=api_key)

    comments_text = "\n".join([f"- {c}" for c in comments]) if comments else "댓글 없음"
    description_snippet = description[:300] if description else "설명 없음"

    prompt = f"""
역할: 전문 콘텐츠 분석가 및 SEO 키워드 마케터

다음 영상의 제목, 설명 일부, 그리고 시청자 댓글 목록을 분석하여 카테고리 추론 및 연관 확장 키워드를 추출해 주세요.

[영상 데이터]
- 제목: {title}
- 설명 요약: {description_snippet}
- 시청자 주요 댓글:
{comments_text}

---

위 정보를 바탕으로 아래 형식에 맞춰 한국어로 답변해 주세요:

1. **대표 카테고리**: (예: 목공, 다이어트, 피트니스, 뷰티 등 메인 분야)
2. **핵심 분석**: (시청자들이 실제로 주목하는 포인트나 니즈를 1-2줄로 요약)
3. **핵심 키워드**: (제목과 댓글에서 뽑아낸 가장 본질적인 키워드 5개 이상, 콤마로 구분)
4. **확장/연관 키워드**: (시청자 반응, 관련 검색어, 연관 장비/부작용/효과/영문키워드 등 시청자가 추가로 검색할 만한 키워드 8개 이상, 콤마로 구분)
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt
    )
    return response.text

# ------------------------------------------------------------------------------
# 3. Streamlit User Interface
# ------------------------------------------------------------------------------
st.title("🎬 영상 주소 기반 키워드 추론 & 확장기")
st.caption("YouTube 영상의 제목과 댓글 반응을 분석하여 핵심 주제와 세부 확장 키워드를 도출합니다.")

# 사이드바 API Key 수동 입력 창 (Secrets 미설정 시 대응)
with st.sidebar:
    st.header("⚙️ 설정")
    if not api_key:
        api_key_input = st.text_input("Gemini API Key를 입력하세요", type="password")
        if api_key_input:
            api_key = api_key_input
    else:
        st.success("API Key가 정상적으로 로드되었습니다.")
    
    max_comments = st.slider("수집할 최대 댓글 수", min_value=10, max_value=50, value=30, step=10)

# 메인 입력 폼
url_input = st.text_input("YouTube 영상 URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 키워드 분석 실행", type="primary"):
    if not url_input:
        st.warning("분석할 영상 URL을 입력해 주세요.")
    elif not api_key:
        st.error("Gemini API Key가 필요합니다. 사이드바에 입력하거나 Secrets를 설정해 주세요.")
    else:
        try:
            with st.spinner("1/2. 영상 데이터 및 댓글 수집 중..."):
                title, description, comments = extract_video_info(url_input, max_comments=max_comments)
            
            st.success(f"데이터 수집 완료! (수집된 댓글: {len(comments)}개)")

            # 데이터 미리보기 UI
            with st.expander("📌 수집된 원본 데이터 확인"):
                st.write(f"**제목:** {title}")
                st.write("**댓글 샘플:**")
                for c in comments[:5]:
                    st.write(f"- {c}")

            with st.spinner("2/2. Gemini AI로 키워드 추론 및 확장 중..."):
                analysis_result = analyze_keywords_with_gemini(api_key, title, description, comments)

            st.markdown("---")
            st.markdown("### 💡 AI 분석 및 키워드 확장 결과")
            st.markdown(analysis_result)

        except Exception as e:
            st.error(f"처리 중 오류가 발생했습니다: {e}")
