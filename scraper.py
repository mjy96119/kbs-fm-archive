import requests
import json
import os
import re

def get_kbs_data():
    # 1. KBS 선곡표 데이터를 관리하는 실제 API 주소입니다.
    api_url = "https://program.kbs.co.kr/api/v1/notice"
    params = {
        "program_id": "R2002-0282", # 출발 FM 프로그램 ID
        "section_id": "03-537648", # 선곡표 게시판 ID
        "page": 1,
        "page_size": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html"
    }

    new_data = {}

    try:
        print("KBS API에 직접 데이터 요청 중...")
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        data = response.json()
        post_list = data.get("data", {}).get("list", [])

        print(f"추출된 게시글 후보: {len(post_list)}개")

        for post in post_list:
            title = post.get("title", "")
            post_id = post.get("id", "")
            
            # 제목에서 날짜 추출 (예: 2026년 4월 6일)
            date_match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', title)
            if date_match:
                date_key = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                
                # 2. 게시글 상세 본문 API 호출
                detail_url = f"https://program.kbs.co.kr/api/v1/notice/{post_id}"
                detail_res = requests.get(detail_url, headers=headers, timeout=10)
                content_html = detail_res.json().get("data", {}).get("content", "")
                
                # HTML 태그 제거 및 텍스트 정리
                clean_text = re.sub(r'<[^>]+>', '\n', content_html)
                lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
                
                songs = []
                idx = 1
                for i, line in enumerate(lines):
                    # 번호(1.)로 시작하는 줄 찾기
                    if re.match(r'^\d+[\.\s]', line):
                        composer = re.sub(r'^\d+[\.\s]*', '', line).strip()
                        title_info = lines[i+1] if i+1 < len(lines) else "제목 정보 없음"
                        artist_info = ""
                        
                        # 다음 줄이 연주자 정보(보통 '-'로 시작)인지 확인
                        if i+2 < len(lines) and (lines[i+2].startswith('-') or '/' in lines[i+2]):
                            artist_info = lines[i+2].replace('-', '').strip()
                        
                        songs.append({
                            "no": idx,
                            "title": title_info,
                            "artist": f"{composer} / {artist_info}".strip(" /")
                        })
                        idx += 1
                
                if songs:
                    new_data[date_key] = songs
                    print(f"-> {date_key}: {len(songs)}곡 수집 완료")

    except Exception as e:
        print(f"오류 발생: {e}")
            
    return new_data

# --- 파일 저장 및 병합 로직 ---
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
    with open(data_file, 'r', encoding='utf-8') as f:
        try: total_data = json.load(f)
        except: total_data = {}

new_records = get_kbs_data()
if new_records:
    total_data.update(new_records)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(total_data, f, ensure_ascii=False, indent=4)
    print("성공: data.json이 업데이트되었습니다.")
else:
    print("실패: 수집된 데이터가 없습니다.")
