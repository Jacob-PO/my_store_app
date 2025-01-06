import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import json

# 지역별 중심 좌표 정의
REGION_COORDS = {
    "서울": [
        "127.0016985;37.5642135",  # 중구
        "127.0495556;37.5838012",  # 동대문구
        "127.0817589;37.5492077",  # 광진구
        "127.0147000;37.5757637",  # 종로구
        "126.9897140;37.5562557",  # 용산구
        "126.9139242;37.5492077",  # 마포구
        "127.0363456;37.6016745",  # 성동구
        "127.0232185;37.6176125",  # 동대문구
        "127.0495556;37.6397533",  # 중랑구
        "127.1464824;37.6024380",  # 강동구
        "127.1258639;37.5492077",  # 송파구
        "127.0927015;37.5184097",  # 강남구
        "126.9810742;37.5177624",  # 용산구
        "126.9139242;37.5270616",  # 마포구
    ],
    "부산": [
        "129.0756416;35.1795543",
        "129.0364044;35.1547153",
        "129.0756416;35.1295663"
    ],
    "대구": [
        "128.5911940;35.8714354",
        "128.6019569;35.8241179",
        "128.5517936;35.8241179"
    ],
    "인천": [
        "126.7052062;37.4562557",
        "126.6575060;37.4562557",
        "126.7052062;37.4786440"
    ],
    "광주": [
        "126.8526012;35.1595454",
        "126.8914954;35.1595454",
        "126.8526012;35.1847107"
    ],
    "대전": [
        "127.3845475;36.3504119",
        "127.4205666;36.3504119",
        "127.3845475;36.3240685"
    ]
}

def get_store_data(query, search_coord, page=1):
    """네이버 지도 API로부터 데이터를 가져오는 함수"""
    try:
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'referer': 'https://map.naver.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        params = {
            'query': query,
            'type': 'all',
            'searchCoord': search_coord,
            'page': page,
            'displayCount': 100
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
        st.error(f"데이터 수집 오류: {str(e)}")
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
    for store in store_list:
        try:
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
            continue
    
    return stores

def create_charts(df):
    """차트 생성 함수"""
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
        showlegend=False
    )
    
    return fig_status, fig_category

def search_all_regions(query, progress_bar, status_text):
    """모든 지역에서 검색을 수행하는 함수"""
    all_stores = []
    total_regions = sum(len(coords) for coords in REGION_COORDS.values())
    current_region = 0
    
    for region_name, coords_list in REGION_COORDS.items():
        for coord in coords_list:
            current_region += 1
            page = 1
            
            while True:
                status_text.text(f"📍 {region_name} 지역 검색 중 (페이지 {page})...")
                progress_bar.progress(current_region / total_regions)
                
                response_data = get_store_data(query, coord, page)
                if not response_data:
                    break
                    
                stores = process_store_data(response_data)
                if not stores:
                    break
                    
                all_stores.extend(stores)
                page += 1
                
                time.sleep(0.5)  # API 호출 간격 조절
    
    return all_stores

def main():
    st.set_page_config(page_title="Store Search Pro", page_icon="📊", layout="wide")
    
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    
    col_title, col_theme = st.columns([4, 1])
    with col_title:
        st.title("📊 Store Search Pro")
    with col_theme:
        st.session_state.dark_mode = st.toggle('다크 모드', value=st.session_state.dark_mode)
    
    # 검색 인터페이스
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_query = st.text_input(
                "🔍 검색어",
                placeholder="검색어를 입력하세요",
                key="search_query"
            )
        with col2:
            search_button = st.button("🔍 검색", use_container_width=True)

        if search_button and search_query:
            progress_container = st.empty()
            status_text = st.empty()
            progress_bar = progress_container.progress(0)
            
            # 전국 검색 수행
            with st.spinner('데이터 수집 중...'):
                all_stores = search_all_regions(search_query, progress_bar, status_text)
            
            if all_stores:
                # 데이터프레임 생성 및 중복 제거
                df = pd.DataFrame(all_stores).drop_duplicates(subset=['name', 'address'])
                
                # 검색 기록 저장
                if 'search_history' not in st.session_state:
                    st.session_state.search_history = []
                
                search_record = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'query': search_query,
                    'data': df
                }
                
                st.session_state.search_history.append(search_record)
                
                # 결과 표시
                status_text.text(f"✅ 검색 완료: 총 {len(df)}개 매장 발견")
                
                # 데이터 테이블 표시
                st.markdown(f"### 📊 검색 결과 ({len(df)} 개 매장)")
                with st.expander("📋 데이터 테이블", expanded=True):
                    st.dataframe(df, height=400, use_container_width=True)
                
                # 차트 표시
                col_charts1, col_charts2 = st.columns(2)
                fig_status, fig_category = create_charts(df)
                
                with col_charts1:
                    st.plotly_chart(fig_status, use_container_width=True)
                with col_charts2:
                    st.plotly_chart(fig_category, use_container_width=True)
                
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
                fig_status, fig_category = create_charts(record['data'])
                
                with col_hist1:
                    st.plotly_chart(fig_status, use_container_width=True)
                with col_hist2:
                    st.plotly_chart(fig_category, use_container_width=True)
                
                st.download_button(
                    "📥 기록 데이터 다운로드",
                    record['data'].to_csv(index=False, encoding='utf-8-sig'),
                    f"search_history_{record['timestamp'].replace(' ', '_')}.csv",
                    "text/csv",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
