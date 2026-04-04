import requests
from bs4 import BeautifulSoup
import json
import os
import re

def get_kbs_playlist():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    new_data = {}

    # 1페이지부터 3페이지까지 탐색
    for page in range(1, 4):
        url = f"https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,{page},0"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            posts = soup.select('.board_list li')

            for post in posts:
                title_tag = post.select_one('.title a')
                if not title_tag: continue
                
                title_text = title_tag.get_text(strip=True)
                # "2026년 4월 6일(월) 선곡내용"에서 날짜 추출
                date_match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', title_text)
                
                if date_match:
                    year = date_match.group(1)
                    month = date_match.group(2).zfill(2)
                    day = date_match.group(3).zfill(2)
                    date_key = f"{year}-{month}-{day}"
                    
                    link = "https://program.kbs.co.kr" + title_tag['href']
                    post_res = requests.get(link, headers=headers, timeout=15)
                    post_soup = BeautifulSoup(post_res.text, 'html.parser')
                    content_area = post_soup.select_one('.board_content')
                    
                    if content_area:
                        # HTML 태그를 줄바꿈으로 변환하여 텍스트 추출
                        content = content_area.get_text("\n", strip=True)
                        songs = []
                        current_song = {}
                        idx = 1
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if not line: continue

                            # 1. 숫자로 시작하는 라인 (작곡가 정보)
                            if re.match(r'^\d+\.', line):
                                if current_song: # 이전 곡 저장
                                    songs.append(current_song)
                                    idx += 1
                                
                                composer = re.sub(r'^\d+\.\s*', '', line)
                                current_song = {"no": idx, "title": "정보 없음", "artist": composer}
                                
                                # 2. 다음 줄이 제목일 확률이 높음
                                if i + 1 < len(lines):
                                    current_song["title"] = lines[i+1].strip()
                                
                                # 3. 그 다음 줄이 연주자(-로 시작)일 확률이 높음
                                if i + 2 < len(lines) and lines[i+2].strip().startswith('-'):
                                    current_song["artist"] = f"{composer} / {lines[i+2].strip().replace('-', '').strip()}"

                        if current_song:
                            songs.append(current_song)
                        
                        if songs:
                            new_data[date_key] = songs
        except Exception as e:
            print(f"Error: {e}")
            
    return new_data

# 데이터 누적 저장 로직
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            total_data = json.load(f)
        except:
            total_data = {}

# 새로운 데이터로 덮어쓰거나 추가
new_records = get_kbs_playlist()
total_data.update(new_records)

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)

print(f"Successfully updated {len(new_records)} dates.")
