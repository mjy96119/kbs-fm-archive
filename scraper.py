import requests
import json
import os
import re
import time

def get_kbs_data():
    # 1. API 엔드포인트 (파라미터를 분리하여 차단 가능성 감소)
    url = "https://program.kbs.co.kr/api/v1/notice"
    params = {
        "program_id": "R2002-0282",
        "section_id": "03-537648",
        "page": "1",
        "page_size": "10"
    }
    
    # 실제 크롬 브라우저의 최신 헤더 세트
    headers = {
        "authority": "program.kbs.co.kr",
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "referer": "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html",
    }

    new_data = {}

    try:
        session = requests.Session()
        # 첫 접속인 것처럼 쿠키를 먼저 받기 위해 메인 페이지 접속 시도
        session.get("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html", headers=headers, timeout=10)
        time.sleep(2) # 사람처럼 보이게 2초 대기

        print("보안 우회 API 호출 시도...")
        response = session.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 403:
            print(f"결과: 여전히 403 차단됨. (IP 차단 가능성 높음)")
            return {}

        response.raise_for_status()
        post_list = response.json().get("data", {}).get("list", [])
        print(f"성공! 발견된 게시글: {len(post_list)}개")

        for post in post_list:
            title = post.get("title", "")
            post_id = str(post.get("id", ""))
            
            # 날짜 추출 (2026-04-06 형식)
            nums = re.findall(r'\d+', title)
            if len(nums) >= 2:
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                
                print(f"[{date_key}] 상세 데이터 수집 중...")
                detail_url = f"{url}/{post_id}"
                detail_res = session.get(detail_url, headers=headers, timeout=15)
                
                if detail_res.status_code == 200:
                    content_html = detail_res.json().get("data", {}).get("content", "")
                    # HTML 태그 제거 및 정제
                    clean_text = re.sub(r'<[^>]+>', '\n', content_html)
                    lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
                    
                    songs = []
                    for i, line in enumerate(lines):
                        if re.match(r'^\d+[\.\s\)]', line):
                            composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                            song_title = lines[i+1] if i+1 < len(lines) else "제목 없음"
                            artist = ""
                            if i+2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                                artist = lines[i+2].replace('-', '').strip()
                            
                            songs.append({
                                "no": len(songs) + 1,
                                "title": song_title,
                                "artist": f"{composer} / {artist}".strip(" /")
                            })
                    if songs:
                        new_data[date_key] = songs
                        print(f"-> {date_key}: {len(songs)}곡 완료")

    except Exception as e:
        print(f"에러 발생: {e}")
            
    return new_data

# 저장 로직 (생략 - 이전과 동일)
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
    print("완료: data.json 업데이트 성공")
else:
    print("수집 실패: 다른 우회 전략이 필요합니다.")
