import requests
from bs4 import BeautifulSoup
import json
import os
import re


def get_kbs_playlist():
    # 페이지 번호를 1, 2 정도까지 훑도록 수정하면 과거 데이터 누락을 방지합니다.
    base_url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,{page},0"
    headers = {'User-Agent': 'Mozilla/5.0'}
    new_data = {}

    for page in [1, 2]: # 최근 2페이지까지 확인
        res = requests.get(base_url.format(page=page), headers=headers)
    ##

    
    # KBS '출발 FM과 함께' 선곡표 게시판 주소
    url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시글 목록 가져오기
        posts = soup.select('.board_list li')
        new_data = {}

        for post in posts:
            title_tag = post.select_one('.title')
            if not title_tag: continue
            
            title_text = title_tag.get_text(strip=True)
            link = "https://program.kbs.co.kr" + title_tag.find('a')['href']
            
            # 제목에서 날짜 추출 (예: 2026-04-04 형태)
            date_match = re.search(r'(\d+)월\s*(\d+)일', title_text)
            if date_match:
                month = date_match.group(1).zfill(2)
                day = date_match.group(2).zfill(2)
                date_key = f"2026-{month}-{day}" # 연도는 현재 연도 기준
                
                # 상세 페이지 접속하여 선곡 목록 긁기
                post_res = requests.get(link, headers=headers)
                post_soup = BeautifulSoup(post_res.text, 'html.parser')
                content = post_soup.select_one('.board_content').get_text("\n", strip=True)
                
                # 곡 정보 파싱 (간단하게 줄 단위로 정리)
                songs = []
                lines = content.split('\n')
                idx = 1
                for line in lines:
                    if '-' in line or ':' in line: # 제목 - 가수 형태인 경우
                        songs.append({"no": idx, "title": line.strip(), "artist": ""})
                        idx += 1
                
                if songs:
                    new_data[date_key] = songs

        return new_data
    except Exception as e:
        print(f"Error: {e}")
        return {}

# 기존 데이터 불러오기 (데이터 누적을 위함)
data_file = 'data.json'
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            total_data = json.load(f)
        except:
            total_data = {}
else:
    total_data = {}

# 새로운 데이터 추가 및 저장
new_records = get_kbs_playlist()
total_data.update(new_records)

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)

print("Update Complete!")
