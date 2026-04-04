import json
import os
import re
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        # 가상 브라우저 실행
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            print("KBS 게시판 접속 중...")
            # 게시글 목록 페이지 접속
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="networkidle")
            
            # 목록 로딩 대기 (최대 20초)
            page.wait_for_selector(".board_list li", timeout=20000)
            posts = page.query_selector_all(".board_list li")
            
            targets = []
            for post in posts:
                title_el = post.query_selector(".title a")
                if title_el:
                    title_text = title_el.inner_text().strip()
                    href = title_el.get_attribute("href")
                    # 제목에 숫자가 2개 이상 포함되면 날짜가 있는 선곡표로 간주
                    if len(re.findall(r'\d+', title_text)) >= 2:
                        targets.append({"title": title_text, "url": "https://program.kbs.co.kr" + href})

            print(f"총 {len(targets)}개의 후보 게시글 발견")

            for target in targets[:5]: # 최신 5개 분석
                # 날짜 키 생성 (YYYY-MM-DD)
                date_nums = re.findall(r'\d+', target['title'])
                # 연도가 없으면 2026으로 가정, 월/일 추출
                if len(date_nums) == 2:
                    date_key = f"2026-{date_nums[0].zfill(2)}-{date_nums[1].zfill(2)}"
                elif len(date_nums) >= 3:
                    date_key = f"{date_nums[0]}-{date_nums[1].zfill(2)}-{date_nums[2].zfill(2)}"
                else:
                    continue

                print(f"[{date_key}] 상세 페이지 읽는 중: {target['url']}")
                page.goto(target['url'], wait_until="networkidle")
                
                # 본문 로딩 대기
                content_el = page.wait_for_selector(".board_content", timeout=15000)
                if not content_el: continue
                
                # 본문 텍스트 전체 추출
                content = content_el.inner_text()
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                songs = []
                # 1. 작곡가 / 2. 제목 / 3. 연주자 구조 파싱
                for i, line in enumerate(lines):
                    # 숫자로 시작하는 줄 (예: "1.", "1 ", "01.")
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        title = lines[i+1] if i+1 < len(lines) else ""
                        artist = ""
                        # 다음 줄이 숫자로 시작하지 않으면 연주자 정보로 간주
                        if i+2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                            artist = lines[i+2].replace('-', '').strip()
                        
                        songs.append({
                            "no": len(songs) + 1,
                            "title": title,
                            "artist": f"{composer} / {artist}".strip(" /")
                        })
                
                if songs:
                    new_data[date_key] = songs
                    print(f"-> {date_key}: {len(songs)}곡 수집 성공")

        except Exception as e:
            print(f"실행 중 에러: {e}")
        finally:
            browser.close()
            
    return new_data

# 저장 및 기존 데이터 병합
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
    print("data.json 업데이트 완료")
else:
    print("수집된 데이터가 없습니다.")
