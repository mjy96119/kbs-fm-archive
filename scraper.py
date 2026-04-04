import json
import os
import re
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 1. 브라우저 실행 및 접속
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        print("KBS 게시판 접속 중...")
        page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="networkidle")
        
        # 2. 게시글 목록 로딩 대기
        page.wait_for_selector(".board_list li", timeout=15000)
        posts = page.query_selector_all(".board_list li")
        
        targets = []
        for post in posts:
            title_el = post.query_selector(".title a")
            if title_el:
                title_text = title_el.inner_text()
                # 날짜가 포함된 제목인지 확인
                if "선곡" in title_text and re.search(r'\d+월\s*\d+일', title_text):
                    targets.append({
                        "title": title_text,
                        "url": "https://program.kbs.co.kr" + title_el.get_attribute("href")
                    })

        # 3. 상세 페이지 접속하여 데이터 추출 (최신 5개)
        for target in targets[:5]:
            date_match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', target['title'])
            if not date_match: continue
            
            date_key = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
            print(f"{date_key} 데이터 읽는 중...")
            
            page.goto(target['url'], wait_until="networkidle")
            content_el = page.wait_for_selector(".board_content", timeout=10000)
            
            if content_el:
                content = content_el.inner_text()
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                songs = []
                
                # 번호(1.) -> 제목 -> 연주자 순서로 파싱
                for i, line in enumerate(lines):
                    if re.match(r'^\d+[\.\s]', line):
                        composer = re.sub(r'^\d+[\.\s]*', '', line)
                        title = lines[i+1] if i+1 < len(lines) else ""
                        artist = lines[i+2] if i+2 < len(lines) else ""
                        
                        songs.append({
                            "no": len(songs) + 1,
                            "title": title,
                            "artist": f"{composer} / {artist.replace('-', '').strip()}"
                        })
                
                if songs:
                    new_data[date_key] = songs

        browser.close()
    return new_data

# --- 저장 및 기존 데이터 병합 ---
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file):
    with open(data_file, 'r', encoding='utf-8') as f:
        try: total_data = json.load(f)
        except: total_data = {}

new_records = get_kbs_data()
total_data.update(new_records)

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)
print(f"업데이트 완료: {len(new_records)}개 날짜 수집됨.")
