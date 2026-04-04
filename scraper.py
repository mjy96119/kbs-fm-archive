import json
import os
import re
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 가상 브라우저 실행 (샌드박스 옵션 추가로 보안 에러 방지)
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print("KBS 게시판 접속 중...")
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="networkidle", timeout=30000)
            
            # 목록 뜰 때까지 충분히 대기
            page.wait_for_selector(".board_list li", timeout=20000)
            posts = page.query_selector_all(".board_list li")
            
            targets = []
            for post in posts:
                title_el = post.query_selector(".title a")
                if title_el:
                    title_text = title_el.inner_text()
                    if "선곡" in title_text:
                        targets.append({"title": title_text, "url": "https://program.kbs.co.kr" + title_el.get_attribute("href")})

            for target in targets[:5]:
                date_match = re.search(r'(\d+)년\s*(\d+)월\s*(\d+)일', target['title'])
                if not date_match: continue
                
                date_key = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
                print(f"{date_key} 데이터 읽는 중...")
                
                page.goto(target['url'], wait_until="networkidle", timeout=30000)
                content_el = page.wait_for_selector(".board_content", timeout=20000)
                
                if content_el:
                    content = content_el.inner_text()
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    songs = []
                    
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
        except Exception as e:
            print(f"상세 에러 발생: {e}")
        finally:
            browser.close()
            
    return new_data

# 파일 병합 저장 로직
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
    print(f"업데이트 성공: {len(new_records)}개 날짜 반영됨")
else:
    print("데이터를 가져오지 못했습니다. 게시판 구조를 다시 확인해야 합니다.")
