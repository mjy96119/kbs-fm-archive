import requests
import json
import os
import re

def get_kbs_data():
    # 1. 목록을 가져오는 정확한 API 엔드포인트 (파라미터를 URL에 직접 결합)
    list_url = "https://program.kbs.co.kr/api/v1/notice?program_id=R2002-0282&section_id=03-537648&page=1&page_size=10"
    
    # 서버가 봇으로 인식하지 못하도록 헤더를 더 정교하게 구성합니다.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html",
        "Origin": "https://program.kbs.co.kr",
        "Connection": "keep-alive"
    }

    new_data = {}

    try:
        print("KBS 목록 API 호출 중...")
        # 세션을 사용하여 실제 브라우저의 흐름을 흉내냅니다.
        session = requests.Session()
        response = session.get(list_url, headers=headers, timeout=15)
        
        # 403 에러 발생 시 상세 로그 출력
        if response.status_code == 403:
            print("에러: 403 Forbidden. 서버가 접속을 차단했습니다.")
            return {}
            
        response.raise_for_status()
        post_list = response.json().get("data", {}).get("list", [])
        print(f"발견된 게시글: {len(post_list)}개")

        for post in post_list:
            title = post.get("title", "")
            post_id = str(post.get("id", "")) 
            
            if not post_id: continue

            # 날짜 추출 (정규표현식 강화)
            date_nums = re.findall(r'\d+', title)
            if len(date_nums) >= 2:
                # 연도가 제목에 없으면 현재 연도(2026) 사용
                y = date_nums[0] if len(date_nums) >= 3 else "2026"
                m = date_nums[1] if len(date_nums) >= 3 else date_nums[0]
                d = date_nums[2] if len(date_nums) >= 3 else date_nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                
                print(f"[{date_key}] 상세 내용(ID: {post_id}) 읽는 중...")
                
                # 2. 상세 페이지 API (불필요한 경로가 붙지 않도록 절대 경로 사용)
                detail_url = f"https://program.kbs.co.kr/api/v1/notice/{post_id}"
                detail_res = session.get(detail_url, headers=headers, timeout=15)
                
                if detail_res.status_code == 200:
                    content_html = detail_res.json().get("data", {}).get("content", "")
                    
                    # HTML 태그 제거 및 줄바꿈 정제
                    clean_text = re.sub(r'<[^>]+>', '\n', content_html)
                    lines = [l.strip() for l in clean_text.strip().split('\n') if l.strip()]
                    
                    songs = []
                    for i, line in enumerate(lines):
                        # "1." 또는 "01." 패턴으로 시작하는 줄 찾기
                        if re.match(r'^\d+[\.\s\)]', line):
                            composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                            song_title = lines[i+1] if i+1 < len(lines) else "제목 정보 없음"
                            artist = ""
                            # 다음 줄이 숫자로 시작하지 않으면 연주자 정보로 간주
                            if i+2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                                artist = lines[i+2].replace('-', '').strip()
                            
                            songs.append({
                                "no": len(songs) + 1,
                                "title": song_title,
                                "artist": f"{composer} / {artist}".strip(" /")
                            })
                    
                    if songs:
                        new_data[date_key] = songs
                        print(f"-> {date_key}: {len(songs)}곡 수집 완료")
                else:
                    print(f"-> {date_key} 상세 페이지 접근 실패 (Status: {detail_res.status_code})")

    except Exception as e:
        print(f"에러 발생 상세: {e}")
            
    return new_data

# 저장 및 병합 로직
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
    print("성공: data.json 업데이트가 완료되었습니다.")
else:
    print("수집된 새로운 데이터가 없습니다.")
