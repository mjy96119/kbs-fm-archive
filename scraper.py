import json
import os
import re
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            # 1. 게시판 목록 접속
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="domcontentloaded")
            page.wait_for_selector(".board_list li", timeout=15000)
            
            posts = page.query_selector_all(".board_list li")
            targets = []
            for post in posts:
                title_el = post.query_selector(".title a")
                if title_el:
                    title_text = title_el.inner_text()
                    if "선곡" in title_text:
                        targets.append({"title": title_text, "url": "https://program.kbs.co.kr" + title_el.get_attribute("href")})

            # 2. 상세 페이지 분석 (최신 5개)
            for target in targets[:5]:
                date_nums = re.findall(r'\d+', target['title'])
                if len(date_nums) < 3: continue
                date_key = f"{date_nums[0]}-{date_nums[1].zfill(2)}-{date_nums[2].zfill(2)}"
                
                print(f"{date_key} 추출 시도 중...")
                page.goto(target['url'], wait_until="domcontentloaded")
                # 본문 영역이 나타날 때까지 대기
                page.wait_for_selector(".board_content", timeout=15000)
                
                # HTML 구조 내부의 모든 텍스트 라인을 가져옴
                content_html = page.inner_html(".board_content")
                # <br>, <p>, <div> 등을 줄바꿈 문자로 변환하여 파싱하기 쉽게 만듦
                text = re.sub(r'<(br|p|div)[^>]*>', '\n', content_html)
                text = re.sub(r'<[^>]+>', '', text) # 나머지 태그 제거
                
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                songs = []
                
                for i, line in enumerate(lines):
                    # "1." 또는 "1 "로 시작하는 라인을 곡의 시작점으로 인식
                    if re.match(r'^\d+[\.\s]', line):
                        composer = re.sub(r'^\d+[\.\s]*', '', line).strip()
                        # 보통 다음 줄에 제목, 그 다음 줄에 연주자가 옴
                        title = lines[i+1] if i+1 < len(lines) else "제목 정보 없음"
                        artist = ""
                        # 연주자 라인은 보통 '-'로 시작하거나 '/'를 포함함
                        if i+2 < len(lines):
                            if lines[i+2].startswith('-') or '/' in lines[i+2]:
                                artist = lines[i+2].lstrip('-').strip()
                        
                        songs.append({
                            "no": len(songs) + 1,
                            "title": title,
                            "artist": f"{composer} / {artist}".strip(" /")
                        })
                
                if songs:
                    new_data[date_key] = songs
                    print(f"{date_key}: {len(songs)}곡 수집 완료")

        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            browser.close()
            
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
    print("성공적으로 data.json이 업데이트되었습니다.")
else:
    print("데이터를 찾지 못했습니다. 파싱 규칙을 점검해야 합니다.")
