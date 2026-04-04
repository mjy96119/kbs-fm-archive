import json
import os
import re
import time
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 1. 브라우저 실행 (진짜 사람처럼 보이기 위한 옵션 추가)
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print("KBS 게시판 접속 시도...")
            # 타임아웃을 늘리고 페이지가 완전히 로드될 때까지 대기
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="load", timeout=60000)
            
            # 목록이 뜰 때까지 대기 (Selector가 안 잡힐 경우를 대비해 5초 강제 대기)
            time.sleep(5) 
            
            # 모든 <a> 태그 중 상세글 링크 추출
            links = page.query_selector_all("a")
            targets = []
            for a in links:
                t = a.inner_text().strip()
                h = a.get_attribute("href")
                if h and "bbs_loc" in h and re.search(r'\d+월\s*\d+일', t):
                    targets.append({"title": t, "url": "https://program.kbs.co.kr" + h if h.startswith('/') else h})

            # 중복 제거
            unique_targets = {t['url']: t for t in targets}.values()
            print(f"분석 대상 게시글: {len(unique_targets)}개 발견")

            for target in list(unique_targets)[:5]:
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 읽는 중...")
                page.goto(target['url'], wait_until="load", timeout=60000)
                time.sleep(3) # 상세 페이지 로딩 대기
                
                content_el = page.query_selector(".board_content")
                if not content_el: continue
                
                raw_text = content_el.inner_text()
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        title = lines[i+1] if i+1 < len(lines) else "정보 없음"
                        artist = ""
                        if i+2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                            artist = lines[i+2].replace('-', '').strip()
                        
                        songs.append({
                            "no": len(songs) + 1,
                            "title": title,
                            "artist": f"{composer} / {artist}".strip(" /")
                        })
                
                if songs:
                    new_data[date_key] = songs
                    print(f"-> {date_key} 수집 성공")

        except Exception as e:
            print(f"오류 내용: {e}")
        finally:
            browser.close()
            
    return new_data

# 저장 로직 (생략 - 기존 코드와 동일)
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
