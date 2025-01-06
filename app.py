import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import numpy as np
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    """두 지점 간의 거리를 계산하는 함수 (단위: km)"""
    R = 6371  # 지구의 반경(km)
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance

def get_area_bounds(center_lat, center_lon, radius_km):
    """주어진 중심점과 반경으로 검색 영역의 경계를 계산"""
    # 위도 1도 = 약 111km
    # 경도 1도 = 약 111km * cos(위도)
    lat_change = radius_km / 111.0
    lon_change = radius_km / (111.0 * cos(radians(center_lat)))
    
    return {
        'min_lat': center_lat - lat_change,
        'max_lat': center_lat + lat_change,
        'min_lon': center_lon - lon_change,
        'max_lon': center_lon + lon_change
    }

def divide_area(bounds, divisions=2):
    """검색 영역을 더 작은 구역으로 분할"""
    lat_step = (bounds['max_lat'] - bounds['min_lat']) / divisions
    lon_step = (bounds['max_lon'] - bounds['min_lon']) / divisions
    
    areas = []
    for i in range(divisions):
        for j in range(divisions):
            area = {
                'min_lat': bounds['min_lat'] + (i * lat_step),
                'max_lat': bounds['min_lat'] + ((i + 1) * lat_step),
                'min_lon': bounds['min_lon'] + (j * lon_step),
                'max_lon': bounds['min_lon'] + ((j + 1) * lon_step)
            }
            areas.append(area)
    
    return areas

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

def search_area(query, area, progress_bar, status_text, total_areas, current_area):
    """특정 영역에 대한 검색을 수행"""
    center_lat = (area['min_lat'] + area['max_lat']) / 2
    center_lon = (area['min_lon'] + area['max_lon']) / 2
    search_coord = f"{center_lon};{center_lat}"
    
    all_stores = []
    page = 1
    
    while True:
        status_text.text(f"구역 {current_area}/{total_areas} - 페이지 {page} 수집 중...")
        
        response_data = get_store_data(query, search_coord, page)
        if not response_data:
            break
            
        stores = process_store_data(response_data)
        if not stores:
            break
            
        # 결과 필터링 (해당 구역 내의 결과만 포함)
        filtered_stores = []
        for store in stores:
            try:
                lat = float(store['latitude'])
                lon = float(store['longitude'])
                if (area['min_lat'] <= lat <= area['max_lat'] and 
                    area['min_lon'] <= lon <= area['max_lon']):
                    filtered_stores.append(store)
            except (ValueError, TypeError):
                continue
                
        all_stores.extend(filtered_stores)
        
        if page >= 20:  # API 한도
            break
            
        page += 1
        time.sleep(0.5)  # API 호출 간격
        
    return all_stores

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
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 검색어", value="서울시 휴대폰 대리점", key="search_query")
        with col2:
            base_coord = st.text_input("📍 중심 좌표", value="126.921051;37.634983", key="search_coord")
        with col3:
            search_radius = st.number_input("검색 반경(km)", min_value=1, max_value=50, value=5, key="search_radius")
        with col4:
            search_button = st.button("🔍 검색", use_container_width=True, key="search_button")

        if search_button:
            try:
                # 중심 좌표 파싱
                center_lon, center_lat = map(float, base_coord.split(';'))
                
                # 검색 영역 계산
                bounds = get_area_bounds(center_lat, center_lon, search_radius)
                
                # 영역 분할 (4x4 그리드)
                areas = divide_area(bounds, divisions=4)
                
                # 진행 상황 표시
                progress_container = st.empty()
                status_text = st.empty()
                progress_bar = progress_container.progress(0)
                
                # 전체 결과 저장
                all_results = []
                
                # 각 구역별 검색 수행
                for idx, area in enumerate(areas, 1):
                    area_results = search_area(
                        search_query, 
                        area, 
                        progress_bar,
                        status_text,
                        len(areas),
                        idx
                    )
                    all_results.extend(area_results)
                    progress_bar.progress(idx / len(areas))
                    
                # 중복 제거
                df = pd.DataFrame(all_results).drop_duplicates(subset=['name', 'address'])
                
                # 결과 표시
                status_text.text(f"✅ 검색 완료: 총 {len(df)} 개의 매장 발견")
                
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
                
                # 시각화
                col_charts1, col_charts2 = st.columns(2)
                
                with col_charts1:
                    # 영업 상태 분포
                    status_counts = df['business_status'].value_counts()
                    fig_status = go.Figure(data=[go.Pie(
                        labels=status_counts.index,
                        values=status_counts.values,
                        hole=.4
                    )])
                    fig_status.update_layout(title="영업 상태 분포")
                    st.plotly_chart(fig_status, use_container_width=True)
                
                with col_charts2:
                    # 카테고리 분포
                    category_counts = df['category'].value_counts().head(10)
                    fig_category = go.Figure(data=[go.Bar(
                        x=category_counts.values,
                        y=category_counts.index,
                        orientation='h'
                    )])
                    fig_category.update_layout(title="상위 10개 카테고리")
                    st.plotly_chart(fig_category, use_container_width=True)
                
                # CSV 다운로드
                st.download_button(
                    "📥 CSV 다운로드",
                    df.to_csv(index=False, encoding='utf-8-sig'),
                    f"store_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()
