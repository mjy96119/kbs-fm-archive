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

    # 최근 3페이지까지 긁어옴
    for page in range(1, 4):
        url = f"https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,{page},0"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            posts = soup.select('.board_list li')

            for post in posts:
                title_tag = post.select_one('.title a')
                if not title_tag: continue
                
                title_text = title_tag.get_text(strip=True)
                date_match = re.findall(r'\d+', title_text)
                if len(date_match) >= 2:
                    month = date_match[0].zfill(2)
                    day = date_match[1].zfill(2)
                    date_key = f"2026-{month}-{day}"
                    
                    link = "https://program.kbs.co.kr" + title_tag['href']
                    post_res = requests.get(link, headers=headers, timeout=10)
                    post_soup = BeautifulSoup(post_res.text, 'html.parser')
                    content_area = post_soup.select_one('.board_content')
                    
                    if content_area:
                        content = content_area.get_text("\n", strip=True)
                        songs = []
                        idx = 1
                        for line in content.split('\n'):
                            line = line.strip()
                            # 구분자가 있거나 숫자로 시작하는 줄을 노래로 인식
                            if len(line) > 3 and (any(c in line for c in ['-', '/', ':', 'ㅣ']) or re.match(r'^\d', line)):
                                # 불필요한 번호 제거
                                clean_line = re.sub(r'^\d+[\s\.)]*', '', line).strip()
                                parts = re.split(r'[-/:]', clean_line, 1)
                                songs.append({
                                    "no": idx,
                                    "title": parts[0].strip(),
                                    "artist": parts[1].strip() if len(parts) > 1 else ""
                                })
                                idx += 1
                        if songs:
                            new_data[date_key] = songs
        except Exception as e:
            print(f"Error: {e}")
    return new_data

# 파일 저장 및 누적 로직
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try: total_data = json.load(f)
        except: total_data = {}

# 새로운 데이터 합치기
total_data.update(get_kbs_playlist())

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)

print(f"Updated {len(total_data)} dates.")
