import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(
    page_title="Store Search", 
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Apple-like styling
st.markdown("""
<style>
    /* 전체 폰트 스타일링 */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 메인 컨테이너 스타일링 */
    .main {
        background-color: #f5f5f7;
        border-radius: 20px;
        padding: 2rem;
    }
    
    /* 헤더 스타일링 */
    h1 {
        font-weight: 600 !important;
        font-size: 2.5rem !important;
        color: #1d1d1f !important;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-weight: 500 !important;
        color: #1d1d1f !important;
        font-size: 1.8rem !important;
    }
    
    /* 버튼 스타일링 */
    .stButton > button {
        background-color: #0071e3 !important;
        color: white !important;
        border-radius: 20px !important;
        padding: 0.5rem 2rem !important;
        border: none !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #0077ED !important;
        transform: scale(1.02);
    }
    
    /* 입력 필드 스타일링 */
    .stTextInput > div > div > input {
        border-radius: 10px !important;
        border: 1px solid #d2d2d7 !important;
        padding: 0.5rem 1rem !important;
        background-color: white !important;
    }
    
    /* 데이터프레임 스타일링 */
    .dataframe {
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* 탭 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f5f5f7;
        border-radius: 15px;
        padding: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 20px;
        background-color: white;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding: 1rem 0;
    }
    
    /* 카드 스타일링 */
    div[data-testid="stExpander"] {
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 1rem !important;
    }
    
    /* 프로그레스 바 스타일링 */
    div.stProgress > div > div {
        background-color: #0071e3 !important;
        border-radius: 10px !important;
    }
    
    /* Plotly 차트 스타일링 */
    .js-plotly-plot {
        border-radius: 15px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state 초기화
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "search"

def get_store_data(query, search_coord, page=1):
    """네이버 지도 API로부터 데이터를 가져오는 함수"""
    cookies = {
        'NACT': '1',
        'NNB': '6AFU7H2YFVCGO',
        'ASID': '7329cb35000001937543587e0000006e',
        'NAC': 'LtUNBcQWCmCC',
        'NACT': '1',
        'SRT30': '1735978428',
        'SRT5': '1735978428',
        'BUC': 'F03Qm0vZYzmIJmR0ikQUPOkmCJ6-9dRlvlFDVy03dPE=',
    }

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ko-KR,ko;q=0.8,en-US;q=0.6,en;q=0.4',
        'cache-control': 'no-cache',
        'referer': 'https://map.naver.com/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    params = {
        'query': query,
        'type': 'all',
        'searchCoord': search_coord,
        'page': page,
    }

    response = requests.get(
        'https://map.naver.com/p/api/search/allSearch',
        params=params,
        cookies=cookies,
        headers=headers
    )
    
    return response.json()

def process_store_data(data):
    """API 응답 데이터를 처리하는 함수"""
    stores = []
    
    for store in data['result']['place']['list']:
        business_status = store.get('businessStatus', {})
        status = business_status.get('status', {})
        
        store_info = {
            'name': store.get('name', ''),
            'tel': store.get('tel', ''),
            'category': ','.join(store.get('category', [])),
            'address': store.get('address', ''),
            'road_address': store.get('roadAddress', ''),
            'business_status': status.get('text', ''),
            'business_hours': business_status.get('businessHours', ''),
        }
        stores.append(store_info)
    
    return stores

def create_charts(df, chart_id):
    """차트 생성 함수"""
    # 테마에 따른 색상 설정
    bg_color = "#1e1e1e" if st.session_state.dark_mode else "#ffffff"
    text_color = "#ffffff" if st.session_state.dark_mode else "#1d1d1f"
    
    # 영업 상태 차트
    status_counts = df['business_status'].value_counts()
    fig_status = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=.4,
        marker_colors=['#34C759', '#FF9500', '#FF3B30']
    )])
    
    fig_status.update_layout(
        title="영업 상태 분포",
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )

    # 카테고리 차트
    category_counts = df['category'].value_counts().head(10)
    fig_category = go.Figure(data=[go.Bar(
        x=category_counts.values,
        y=category_counts.index,
        orientation='h',
        marker_color='#0071e3'
    )])
    
    fig_category.update_layout(
        title="주요 카테고리",
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=400
    )
    
    return fig_status, fig_category

def main():
    st.title("Store Search")
    
    # 탭 생성
    tabs = st.tabs(["🔍 Search", "📋 History"])
    
    # Search 탭
    with tabs[0]:
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.markdown("### Search Settings")
            search_query = st.text_input("Search Query", value="서울시 휴대폰 대리점")
            search_coord = st.text_input("Coordinates", value="126.921051;37.634983")
            pages = st.slider("Number of Pages", 1, 10, 5)
            
            if st.button("Search", use_container_width=True):
                with col1:
                    st.markdown("### Search Progress")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # 데이터 수집
                    all_stores = []
                    for page in range(1, pages + 1):
                        try:
                            status_text.text(f"Collecting page {page}/{pages}...")
                            response_data = get_store_data(search_query, search_coord, page)
                            stores = process_store_data(response_data)
                            all_stores.extend(stores)
                            progress_bar.progress(page/pages)
                            time.sleep(0.5)
                        except Exception as e:
                            st.error(f"Error on page {page}: {str(e)}")
                            continue
                    
                    # 결과 처리
                    df = pd.DataFrame(all_stores)
                    
                    # 검색 기록 저장
                    st.session_state.search_history.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'query': search_query,
                        'data': df
                    })
                    
                    # 결과 표시
                    st.markdown(f"### Results ({len(df)} stores found)")
                    st.dataframe(df, height=300)
                    
                    # 차트 표시
                    fig_status, fig_category = create_charts(df)
                    
                    col_charts1, col_charts2 = st.columns(2)
                    with col_charts1:
                        st.plotly_chart(fig_status, use_container_width=True, key=f"status_chart_{datetime.now().timestamp()}")
                    with col_charts2:
                        st.plotly_chart(fig_category, use_container_width=True, key=f"category_chart_{datetime.now().timestamp()}")
                    
                    # CSV 다운로드
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"store_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
    
    # History 탭
    with tabs[1]:
        if not st.session_state.search_history:
            st.info("No search history yet. Try searching something!")
        else:
            for idx, record in enumerate(reversed(st.session_state.search_history)):
                with st.expander(f"🔍 {record['query']} ({record['timestamp']})"):
                    df_history = record['data']
                    st.dataframe(df_history, height=200)
                    
                    col_hist1, col_hist2 = st.columns(2)
                    fig_status, fig_category = create_charts(df_history)
                    
                    with col_hist1:
                        st.plotly_chart(fig_status, use_container_width=True, key=f"history_status_{idx}_{datetime.now().timestamp()}")
                    with col_hist2:
                        st.plotly_chart(fig_category, use_container_width=True, key=f"history_category_{idx}_{datetime.now().timestamp()}")
                    
                    # CSV 다운로드
                    csv_history = df_history.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "Download CSV",
                        csv_history,
                        f"search_history_{record['timestamp'].replace(' ', '_')}.csv",
                        "text/csv",
                        use_container_width=True
                    )

if __name__ == "__main__":
    main()
