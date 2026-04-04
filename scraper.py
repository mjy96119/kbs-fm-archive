import json
import os
import re
import time
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 가상 브라우저 실행 (보안 우회 설정)
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print("KBS 게시판 접속 시도...")
            # 게시판 목록 페이지 접속
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="networkidle", timeout=60000)
            
            # 자바스크립트가 목록을 그릴 시간을 충분히 줌
            time.sleep(7) 
            
            # 페이지 내의 모든 링크 추출 (태그 속성까지 검사)
            elements = page.query_selector_all("a")
            targets = []
            
            for el in elements:
                href = el.get_attribute("href") or ""
                text = el.inner_text().strip()
                
                # 링크 주소에 'view'나 'bbs_loc'이 포함되어 있고, 텍스트에 날짜(숫자)가 보이면 후보로 등록
                if ("view" in href or "bbs_loc" in href) and re.search(r'\d+', text):
                    full_url = href if href.startswith("http") else "https://program.kbs.co.kr" + href
                    targets.append({"title": text, "url": full_url})

            # 중복 링크 제거 및 로그 출력
            seen_urls = set()
            unique_targets = []
            for t in targets:
                if t['url'] not in seen_urls:
                    seen_urls.add(t['url'])
                    unique_targets.append(t)

            print(f"발견된 전체 링크 수: {len(unique_targets)}개")

            # 상위 10개 게시글을 순회하며 진짜 선곡표 찾기
            for target in unique_targets[:10]:
                # 제목에서 날짜 추출 시도
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                
                # 날짜 키 생성 (YYYY-MM-DD)
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 페이지 접속 중: {target['url']}")
                page.goto(target['url'], wait_until="networkidle", timeout=60000)
                time.sleep(4) # 본문 로딩 대기
                
                # 본문 영역을 여러 선택자로 시도
                content_el = page.query_selector(".board_content") or page.query_selector("#content") or page.query_selector(".view_con")
                if not content_el: 
                    print(f"[{date_key}] 본문을 찾을 수 없음")
                    continue
                
                raw_text = content_el.inner_text()
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    # 숫자로 시작하는 곡 정보 패턴 찾기
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
                    print(f"-> {date_key} 수집 성공 ({len(songs)}곡)")

        except Exception as e:
            print(f"진행 중 오류 발생: {e}")
        finally:
            browser.close()
            
    return new_data

# --- 데이터 통합 및 저장 ---
data_file = 'data.json'
total_data = {}

if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            total_data = json.load(f)
        except:
            total_data = {}

new_records = get_kbs_data()
if new_records:
    total_data.update(new_records)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(total_data, f, ensure_ascii=False, indent=4)
    print("최종 업데이트 완료!")
else:
    print("수집된 데이터가 최종적으로 0개입니다. 수동 점검이 필요할 수 있습니다.")
