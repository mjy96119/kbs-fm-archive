import json
import os
import re
import time
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 1. 브라우저 실행 설정 (로봇 감지 회피 최적화)
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080'
        ])
        
        # 실제 사용자와 유사한 컨텍스트 설정
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        
        page = context.new_page()
        
        # 웹드라이버 흔적 제거 스크립트 주입
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print("KBS 게시판 접속 시도 (Stealth Mode)...")
            # 2. 게시판 목록 접속
            url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0"
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 자바스크립트가 게시판을 구성할 때까지 10초간 여유 있게 대기
            print("데이터 로딩 대기 중 (10초)...")
            time.sleep(10)

            # 3. 링크 추출 (더 공격적인 방식)
            # 화면의 모든 텍스트와 링크를 긁어 모음
            content_all = page.content()
            
            # 정규표현식으로 게시글 ID(bbs_loc 내부 번호) 추출 시도
            # 예: R2002-0282-03-537648,view,none,1,725439
            post_ids = re.findall(r'(\d{5,8})', content_all)
            post_ids = list(set(post_ids)) # 중복 제거
            
            targets = []
            # '선곡' 단어가 포함된 링크 요소를 직접 찾기
            links = page.query_selector_all("a")
            for link in links:
                text = link.inner_text().strip()
                href = link.get_attribute("href") or ""
                if re.search(r'\d+월\s*\d+일', text) or "선곡" in text:
                    full_url = href if href.startswith("http") else "https://program.kbs.co.kr" + href
                    targets.append({"title": text, "url": full_url})

            print(f"추출된 후보 링크 수: {len(targets)}개")

            # 4. 상세 페이지 탐색
            for target in targets[:5]:
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 상세 페이지 진입: {target['url']}")
                page.goto(target['url'], wait_until="networkidle", timeout=60000)
                time.sleep(5) # 본문 렌더링 대기

                # 본문 텍스트 추출
                body = page.query_selector(".board_content")
                if not body:
                    print(f"[{date_key}] 본문 영역(.board_content) 탐색 실패")
                    continue
                
                raw_text = body.inner_text()
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        title = lines[i+1] if i+1 < len(lines) else "제목 정보 없음"
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
                    print(f"-> {date_key} 업데이트 성공 ({len(songs)}곡)")

        except Exception as e:
            print(f"스크래핑 에러: {e}")
        finally:
            browser.close()
            
    return new_data

# --- 저장 및 기존 데이터 병합 ---
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
    print("완료: data.json이 갱신되었습니다.")
else:
    print("결과: 수집된 데이터가 없습니다.")
