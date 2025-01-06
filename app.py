import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

def get_store_data(query, page=1):
    """네이버 지도 API로부터 데이터를 가져오는 함수"""
    try:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://map.naver.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        params = {
            'query': query,
            'type': 'all',
            'page': page,
            'searchCoord': '126.97828899999999;37.566778',  # 서울 중심 좌표
            'display': 100  # 페이지당 결과 수 증가
        }

        response = requests.get(
            'https://map.naver.com/p/api/search/allSearch',
            params=params,
            headers=headers
        )
        
        data = response.json()
        
        if not data.get('result', {}).get('place', {}).get('list'):
            return None
        
        return data
    except Exception as e:
        st.error(f"데이터 수집 중 오류 발생: {str(e)}")
        return None

def process_store_data(data):
    """API 응답 데이터를 처리하는 함수"""
    if not data or not isinstance(data, dict):
        return []
    
    result = data.get('result', {})
    if not result or not isinstance(result, dict):
        return []
    
    place_data = result.get('place', {})
    if not place_data or not isinstance(place_data, dict):
        return []
    
    store_list = place_data.get('list', [])
    if not store_list or not isinstance(store_list, list):
        return []
        
    stores = []
    try:
        for store in store_list:
            if not isinstance(store, dict):
                continue
                
            business_status = store.get('businessStatus', {})
            if not isinstance(business_status, dict):
                business_status = {}
                
            status = business_status.get('status', {})
            if not isinstance(status, dict):
                status = {}
            
            category = store.get('category', [])
            if isinstance(category, list):
                category_str = ','.join(category)
            else:
                category_str = str(category) if category else ''
            
            store_info = {
                'name': str(store.get('name', '')),
                'tel': str(store.get('tel', '')),
                'category': category_str,
                'address': str(store.get('address', '')),
                'road_address': str(store.get('roadAddress', '')),
                'business_status': str(status.get('text', '영업 상태 미상')),
                'business_hours': str(business_status.get('businessHours', '')),
                'x': str(store.get('x', '')),
                'y': str(store.get('y', ''))
            }
            stores.append(store_info)
    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {str(e)}")
        st.error(f"문제가 발생한 데이터: {store}")
    
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
        showlegend=True
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
        showlegend=False
    )
    
    return fig_status, fig_category

def main():
    # UI 설정
    st.set_page_config(page_title="Store Search Pro", page_icon="📊", layout="wide")
    
    # 다크모드 설정
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
        
    col_title, col_theme = st.columns([4, 1])
    with col_title:
        st.title("📊 Store Search Pro")
    with col_theme:
        st.session_state.dark_mode = st.toggle('다크 모드', value=st.session_state.dark_mode, key='theme_toggle')
    
    # 검색 인터페이스
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input("🔍 검색어", value="서울시 휴대폰 대리점", key="search_query",
                                       placeholder="검색어를 입력하세요")
        with col2:
            search_button = st.button("🔍 검색", use_container_width=True, key="search_button")

        if search_button and search_query:
            # 진행 상황 표시
            progress_container = st.empty()
            status_text = st.empty()
            progress_bar = progress_container.progress(0)
            
            # 데이터 수집
            all_stores = []
            page = 1
            max_pages = 45  # 최대 페이지 수 설정
            
            with st.spinner('데이터 수집 중...'):
                while True:
                    status_text.text(f"📥 {page}페이지 수집 중...")
                    
                    response_data = get_store_data(search_query, page)
                    if not response_data:
                        break
                        
                    stores = process_store_data(response_data)
                    if not stores:
                        break
                        
                    all_stores.extend(stores)
                    progress = min(page/max_pages, 1.0)
                    progress_bar.progress(progress)
                    
                    if page >= max_pages:
                        status_text.text(f"✅ 최대 페이지 도달: {len(all_stores)}개 매장 수집 완료")
                        break
                        
                    page += 1
                    time.sleep(0.5)  # API 호출 간격 조절
            
            if all_stores:
                # 결과를 DataFrame으로 변환
                df = pd.DataFrame(all_stores).drop_duplicates()
                
                # 검색 기록 저장
                if 'search_history' not in st.session_state:
                    st.session_state.search_history = []
                
                st.session_state.search_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'query': search_query,
                    'data': df
                })
                
                # 결과 표시
                st.markdown(f"### 📊 검색 결과 ({len(df)} 개 매장)")
                
                # 데이터 테이블
                with st.expander("📋 데이터 테이블", expanded=True):
                    styled_df = df.style.set_properties(**{
                        'background-color': 'transparent',
                        'color': 'black' if not st.session_state.dark_mode else 'white',
                        'font-family': '-apple-system, BlinkMacSystemFont, sans-serif',
                        'font-size': '14px',
                        'padding': '8px'
                    })
                    
                    st.dataframe(
                        styled_df,
                        height=400,
                        use_container_width=True
                    )
                
                # 차트 표시
                col_charts1, col_charts2 = st.columns(2)
                fig_status, fig_category = create_charts(df, 'current')
                
                with col_charts1:
                    st.plotly_chart(fig_status, use_container_width=True, key=f"status_current")
                with col_charts2:
                    st.plotly_chart(fig_category, use_container_width=True, key=f"category_current")
                
                # CSV 다운로드
                st.download_button(
                    "📥 CSV 다운로드",
                    df.to_csv(index=False, encoding='utf-8-sig'),
                    f"store_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("검색 결과가 없습니다.")
        elif search_button and not search_query:
            st.warning("검색어를 입력해주세요.")
    
    # 검색 기록 표시
    if 'search_history' in st.session_state and st.session_state.search_history:
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
