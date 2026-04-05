import requests
import json
import os
import re

def get_kbs_data():
    api_url = "https://program.kbs.co.kr/api/v1/notice"
    params = {
        "program_id": "R2002-0282",
        "section_id": "03-537648",
        "page": 1,
        "page_size": 10
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html"
    }

    new_data = {}

    try:
        print("KBS API 호출 중...")
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        post_list = data.get("data", {}).get("list", [])

        print(f"발견된 게시글: {len(post_list)}개")

        for post in post_list:
            title = post.get("title", "")
            post_id = post.get("id", "")
            
            # 날짜 추출
            date_nums = re.findall(r'\d+', title)
            if len(date_nums) >= 2:
                # 연도가 없으면 2026으로 가정
                y = date_nums[0] if len(date_nums) >= 3 else "2026"
                m = date_nums[1] if len(date_nums) >= 3 else date_nums[0]
                d = date_nums[2] if len(date_nums) >= 3 else date_nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                
                print(f"[{date_key}] 상세 데이터 읽는 중...")
                detail_url = f"https://program.kbs.co.kr/api/v1/notice/{post_id}"
                detail_res = requests.get(detail_url, headers=headers, timeout=15)
                content_html = detail_res.json().get("data", {}).get("content", "")
                
                # 텍스트 정제
                clean_text = re.sub(r'<[^>]+>', '\n', content_html)
                lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        song_title = lines[i+1] if i+1 < len(lines) else "정보 없음"
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
                    print(f"-> {date_key}: {len(songs)}곡 저장")

    except Exception as e:
        print(f"에러 발생: {e}")
            
    return new_data

# 저장 및 병합
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
    print("성공: data.json 업데이트 완료")
else:
    print("수집된 데이터가 없습니다.")
