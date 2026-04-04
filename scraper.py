import requests
from bs4 import BeautifulSoup
import json
import os
import re

def get_kbs_playlist():
    # 페이지를 넉넉하게 3페이지까지 훑습니다.
    headers = {'User-Agent': 'Mozilla/5.0'}
    new_data = {}

    for page in [1, 2, 3]:
        url = f"https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,{page},0"
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            posts = soup.select('.board_list li')

            for post in posts:
                title_tag = post.select_one('.title')
                if not title_tag: continue
                
                title_text = title_tag.get_text(strip=True)
                link = "https://program.kbs.co.kr" + title_tag.find('a')['href']
                
                # 날짜 추출 (예: 4월 2일)
                date_match = re.search(r'(\d+)월\s*(\d+)일', title_text)
                if date_match:
                    month = date_match.group(1).zfill(2)
                    day = date_match.group(2).zfill(2)
                    date_key = f"2026-{month}-{day}"
                    
                    post_res = requests.get(link, headers=headers)
                    post_soup = BeautifulSoup(post_res.text, 'html.parser')
                    content = post_soup.select_one('.board_content').get_text("\n", strip=True)
                    
                    songs = []
                    lines = content.split('\n')
                    idx = 1
                    for line in lines:
                        clean_line = line.strip()
                        # 곡 번호로 시작하거나 구분자(-, /, :)가 있는 줄을 곡으로 간주
                        if re.match(r'^\d+[\s\.)]', clean_line) or '-' in clean_line or '/' in clean_line:
                            # 번호 제거 로직
                            item = re.sub(r'^\d+[\s\.)]*', '', clean_line).strip()
                            if '-' in item:
                                parts = item.split('-', 1)
                            elif '/' in item:
                                parts = item.split('/', 1)
                            else:
                                parts = [item, ""]
                            
                            songs.append({
                                "no": idx,
                                "title": parts[0].strip(),
                                "artist": parts[1].strip() if len(parts) > 1 else ""
                            })
                            idx += 1
                    
                    if songs:
                        new_data[date_key] = songs
        except:
            continue
    return new_data

# 데이터 로드 및 업데이트 (누적 보관)
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try: total_data = json.load(f)
        except: total_data = {}

total_data.update(get_kbs_playlist())
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)
