import requests
import json
import os
import re

def get_kbs_playlist():
    # 게시판 목록 API 주소
    list_url = "https://program.kbs.co.kr/api/v1/notice"
    params = {
        "program_id": "R2002-0282",
        "section_id": "03-537648",
        "page": 1,
        "page_size": 20
    }
    # 브라우저인 척하기 위한 헤더 강화
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html',
        'Origin': 'https://program.kbs.co.kr'
    }

    new_data = {}

    try:
        res = requests.get(list_url, params=params, headers=headers, timeout=15)
        res.raise_for_status() # 접속 에러 시 중단
        post_list = res.json().get('data', {}).get('list', [])

        for post in post_list:
            title = post.get('title', '')
            post_id = post.get('id', '')
            
            # "2026년 4월 6일(월) 선곡내용"에서 숫자만 모두 추출
            date_nums = re.findall(r'\d+', title)
            if len(date_nums) >= 3 and post_id:
                year = date_nums[0]
                month = date_nums[1].zfill(2)
                day = date_nums[2].zfill(2)
                date_key = f"{year}-{month}-{day}"

                # 상세 본문 API 호출
                detail_url = f"https://program.kbs.co.kr/api/v1/notice/{post_id}"
                detail_res = requests.get(detail_url, headers=headers, timeout=15)
                detail_res.raise_for_status()
                content_html = detail_res.json().get('data', {}).get('content', '')
                
                # HTML 태그 제거 및 텍스트 정리
                content = re.sub(r'<[^>]+>', '\n', content_html)
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                songs = []
                idx = 1
                for i, line in enumerate(lines):
                    # "1. 작곡가" 또는 "1 작곡가" 형태 탐색
                    if re.match(r'^\d+[\.\s]', line):
                        composer = re.sub(r'^\d+[\.\s]*', '', line)
                        title_info = lines[i+1] if i + 1 < len(lines) else "제목 정보 없음"
                        
                        # 연주자 정보 탐색 (다음 줄이 제목이 아닐 경우 등 대비)
                        artist_info = ""
                        if i + 2 < len(lines):
                            next_line = lines[i+2]
                            if next_line.startswith('-') or '/' in next_line or '(' in next_line:
                                artist_info = next_line.replace('-', '').strip()
                        
                        songs.append({
                            "no": idx,
                            "title": title_info,
                            "artist": f"{composer} / {artist_info}".strip(' / ')
                        })
                        idx += 1
                
                if songs:
                    new_data[date_key] = songs
    except Exception as e:
        print(f"오류 발생: {e}")
            
    return new_data

# --- 저장 로직 ---
data_file = 'data.json'
total_data = {}

if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            total_data = json.load(f)
        except:
            total_data = {}

# 데이터 합치기
new_records = get_kbs_playlist()
if new_records:
    total_data.update(new_records)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(total_data, f, ensure_ascii=False, indent=4)
    print(f"성공: {len(new_records)}일치 데이터 업데이트 완료")
else:
    print("실패: 가져온 데이터가 없습니다. 제목 형식을 다시 확인하세요.")
