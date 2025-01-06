import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(
    page_title="Store Search Pro", 
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# CSS with simplified theme support
st.markdown("""
<style>
    /* Base theme */
    [data-testid="stAppViewContainer"] {
        background: var(--background-color);
        color: var(--text-color);
    }
    
    .main {
        background-color: var(--background-color);
    }
    
    /* Cards */
    div[data-testid="stExpander"] {
        background-color: var(--card-background);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: var(--text-color) !important;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        background-color: var(--input-bg);
        color: var(--text-color);
        border-color: var(--border-color);
        border-radius: 8px;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background-color: var(--primary-color);
    }
    
    /* Light theme */
    :root {
        --background-color: #ffffff;
        --text-color: #1d1d1f;
        --card-background: #f8f9fa;
        --border-color: #e6e6e6;
        --input-bg: #ffffff;
        --primary-color: #0071e3;
    }
    
    /* Dark theme */
    [data-theme="dark"] {
        --background-color: #1e1e1e;
        --text-color: #ffffff;
        --card-background: #2d2d2d;
        --border-color: #404040;
        --input-bg: #2d2d2d;
        --primary-color: #0A84FF;
    }
</style>
""", unsafe_allow_html=True)

def get_store_data(query, search_coord, page=1):
    """네이버 지도 API로부터 데이터를 가져오는 함수"""
    try:
        cookies = {
            'NID_AUT': 'your_cookie_here',  # Replace with actual cookies if needed
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://map.naver.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
        
        data = response.json()
        
        # No results check
        if not data.get('result', {}).get('place', {}).get('list'):
            return None
        
        return data
    except Exception as e:
        st.error(f"데이터 수집 중 오류 발생: {str(e)}")
        return None

def process_store_data(data):
    """API 응답 데이터를 처리하는 함수"""
    if not data or 'result' not in data:
        return []
        
    stores = []
    try:
        for store in data['result']['place']['list']:
            business_status = store.get('businessStatus', {})
            status = business_status.get('status', {})
            
            store_info = {
                'name': store.get('name', ''),
                'tel': store.get('tel', ''),
                'category': ','.join(store.get('category', [])),
                'address': store.get('address', ''),
                'road_address': store.get('roadAddress', ''),
                'business_status': status.get('text', '영업 상태 미상'),
                'business_hours': business_status.get('businessHours', ''),
                'latitude': store.get('y', ''),
                'longitude': store.get('x', ''),
            }
            stores.append(store_info)
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {str(e)}")
    
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
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font_color=text_color,
        showlegend=True,
        margin=dict(t=30, b=0, l=0, r=0)
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
        title="상위 10개 카테고리",
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font_color=text_color,
        showlegend=False,
        margin=dict(t=30, b=0, l=0, r=0)
    )
    
    return fig_status, fig_category

def main():
    col_title, col_theme = st.columns([4, 1])
    with col_title:
        st.title("📊 Store Search Pro")
    with col_theme:
        st.session_state.dark_mode = st.toggle('다크 모드', value=st.session_state.dark_mode, key='theme_toggle')
    
    # Search interface
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            search_query = st.text_input("🔍 검색어", value="서울시 휴대폰 대리점", key="search_query")
        with col2:
            search_coord = st.text_input("📍 좌표", value="126.921051;37.634983", key="search_coord")
        with col3:
            search_button = st.button("🔍 검색", use_container_width=True, key="search_button")

        if search_button:
            all_stores = []
            page = 1
            
            # Progress tracking
            progress_container = st.empty()
            status_text = st.empty()
            progress_bar = progress_container.progress(0)
            
            while True:
                status_text.text(f"📥 페이지 {page} 수집 중...")
                
                response_data = get_store_data(search_query, search_coord, page)
                if not response_data:
                    status_text.text("✅ 모든 데이터 수집 완료")
                    break
                
                stores = process_store_data(response_data)
                if not stores:
                    break
                    
                all_stores.extend(stores)
                
                # Update progress
                progress = min(page/20, 1.0)
                progress_bar.progress(progress)
                
                if page >= 20:
                    status_text.text("✅ 최대 페이지(20) 도달")
                    break
                    
                page += 1
                time.sleep(0.5)
            
            if all_stores:
                df = pd.DataFrame(all_stores)
                
                # Save to history
                st.session_state.search_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'query': search_query,
                    'data': df
                })
                
                # Results display
                st.markdown(f"### 📊 검색 결과 ({len(df)} 개 매장)")
                
                with st.expander("📋 데이터 테이블", expanded=True):
                    st.dataframe(
                        df.style.set_properties(**{
                            'background-color': 'var(--background-color)',
                            'color': 'var(--text-color)'
                        }),
                        height=400,
                        use_container_width=True
                    )
                
                # Charts
                col_charts1, col_charts2 = st.columns(2)
                fig_status, fig_category = create_charts(df, 'current')
                
                with col_charts1:
                    st.plotly_chart(fig_status, use_container_width=True, key=f"status_current")
                with col_charts2:
                    st.plotly_chart(fig_category, use_container_width=True, key=f"category_current")
                
                # Export options
                st.download_button(
                    "📥 CSV 다운로드",
                    df.to_csv(index=False, encoding='utf-8-sig'),
                    f"store_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("검색 결과가 없습니다.")
    
    # Show search history
    if st.session_state.search_history:
        st.markdown("### 📜 검색 기록")
        
        for idx, record in enumerate(reversed(st.session_state.search_history)):
            with st.expander(f"🔍 {record['query']} ({record['timestamp']})", expanded=False):
                st.dataframe(record['data'], height=200)
                
                col_hist1, col_hist2 = st.columns(2)
                fig_status, fig_category = create_charts(record['data'], f'history_{idx}')
                
                with col_hist1:
                    st.plotly_chart(fig_status, use_container_width=True, key=f"status_history_{idx}")
                with col_hist2:
                    st.plotly_chart(fig_category, use_container_width=True, key=f"category_history_{idx}")
                
                st.download_button(
                    "📥 기록 데이터 다운로드",
                    record['data'].to_csv(index=False, encoding='utf-8-sig'),
                    f"search_history_{record['timestamp'].replace(' ', '_')}.csv",
                    "text/csv",
                    use_container_width=True,
                    key=f"download_history_{idx}"
                )

if __name__ == "__main__":
    main()
