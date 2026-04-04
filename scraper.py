import json
import os
import re
import time
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print("KBS 게시판 접속 시도...")
            url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0"
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(10) # 자바스크립트 실행 대기

            # 1. 모든 링크를 뒤져서 날짜가 포함된 선곡표 게시글 찾기
            all_links = page.query_selector_all("a")
            targets = []
            for a in all_links:
                text = a.inner_text().strip()
                href = a.get_attribute("href") or ""
                # 날짜(숫자)와 '선곡' 혹은 '내용'이 포함된 링크 필터링
                if re.search(r'\d+월\s*\d+일', text) or "선곡" in text or "내용" in text:
                    full_url = href if href.startswith("http") else "https://program.kbs.co.kr" + href
                    targets.append({"title": text, "url": full_url})

            # 중복 제거
            unique_targets = {t['url']: t for t in targets}.values()
            print(f"후보 게시글 발견: {len(unique_targets)}개")

            # 2. 상세 페이지 순회
            for target in list(unique_targets)[:5]:
                # 날짜 추출
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 데이터 수집 시도...")
                page.goto(target['url'], wait_until="networkidle", timeout=60000)
                time.sleep(5)

                # 3. 본문 텍스트 강제 추출 (태그 무시, 화면에 보이는 모든 텍스트)
                # 특정 클래스가 아닌 body 전체에서 텍스트를 뽑아낸 뒤 정제합니다.
                raw_text = page.evaluate("() => document.body.innerText")
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    # 숫자로 시작하는 라인(1. 또는 1 )을 찾습니다.
                    if re.match(r'^\d+[\.\s\)]', line):
                        # 작곡가 정보 추출
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        
                        # 다음 1~2줄 내에서 제목과 연주자를 찾습니다.
                        song_title = "제목 정보 없음"
                        artist_info = ""
                        
                        if i + 1 < len(lines):
                            song_title = lines[i+1]
                        if i + 2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                            artist_info = lines[i+2].replace('-', '').strip()
                        
                        # 최소한의 데이터가 있을 때만 추가
                        if len(composer) > 1 or len(song_title) > 1:
                            songs.append({
                                "no": len(songs) + 1,
                                "title": song_title,
                                "artist": f"{composer} / {artist_info}".strip(" /")
                            })

                if songs:
                    new_data[date_key] = songs
                    print(f"-> {date_key}: {len(songs)}곡 저장 완료")

        except Exception as e:
            print(f"스크래핑 오류: {e}")
        finally:
            browser.close()
            
    return new_data

# --- 파일 병합 및 저장 로직 ---
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
    print("최종 성공: data.json에 데이터가 기록되었습니다.")
else:
    print("최종 실패: 수집된 데이터가 없습니다.")
