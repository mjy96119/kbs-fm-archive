import requests
import json
import os
import re

def get_kbs_playlist():
    # 게시판 목록을 가져오는 실제 데이터 API 주소
    list_url = "https://program.kbs.co.kr/api/v1/notice"
    params = {
        "program_id": "R2002-0282",
        "section_id": "03-537648",
        "page": 1,
        "page_size": 20
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html'
    }

    new_data = {}

    try:
        # 1. 게시글 목록 API 호출
        res = requests.get(list_url, params=params, headers=headers, timeout=15)
        post_list = res.json().get('data', {}).get('list', [])

        for post in post_list:
            title = post.get('title', '')
            post_id = post.get('id', '')
            
            # 날짜 추출 (예: 2026년 4월 6일)
            date_match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', title)
            if date_match and post_id:
                year = date_match.group(1)
                month = date_match.group(2).zfill(2)
                day = date_match.group(3).zfill(2)
                date_key = f"{year}-{month}-{day}"

                # 2. 게시글 상세 본문 API 호출
                detail_url = f"https://program.kbs.co.kr/api/v1/notice/{post_id}"
                detail_res = requests.get(detail_url, headers=headers, timeout=15)
                content_html = detail_res.json().get('data', {}).get('content', '')
                
                # HTML 태그 제거 및 줄바꿈 정리
                content = re.sub(r'<[^>]+>', '\n', content_html)
                
                songs = []
                idx = 1
                # 줄바꿈 기준으로 나누고 공백 제거
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                for i, line in enumerate(lines):
                    # "1. 작곡가" 형태의 줄 찾기
                    if re.match(r'^\d+[\.\s]', line):
                        composer = re.sub(r'^\d+[\.\s]*', '', line)
                        title_info = "정보 없음"
                        artist_info = ""
                        
                        # 다음 줄을 제목으로 추정
                        if i + 1 < len(lines):
                            title_info = lines[i+1]
                        
                        # 그 다음 줄을 연주자(-로 시작하거나 / 포함)로 추정
                        if i + 2 < len(lines) and (lines[i+2].startswith('-') or '/' in lines[i+2]):
                            artist_info = lines[i+2].replace('-', '').strip()
                        
                        songs.append({
                            "no": idx,
                            "title": title_info,
                            "artist": f"{composer} / {artist_info}".strip(' / ')
                        })
                        idx += 1
                
                if songs:
                    new_data[date_key] = songs
                    
    except Exception as e:
        print(f"스크래핑 오류: {e}")
            
    return new_data

# --- 데이터 저장 및 누적 로직 ---
data_file = 'data.json'
total_data = {}

# 기존 데이터가 있으면 불러오기
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            total_data = json.load(f)
        except:
            total_data = {}

# 신규 데이터 업데이트 (기존 데이터와 합침)
new_records = get_kbs_playlist()
total_data.update(new_records)

# 최종 파일 저장
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)

print(f"업데이트 완료! 현재 총 {len(total_data)}일치의 데이터가 저장되어 있습니다.")
