import json
import os
import re
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            print("KBS 게시판 접속 시도...")
            page.goto("https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0", wait_until="networkidle")
            
            # 목록이 뜰 때까지 대기
            page.wait_for_selector(".board_list", timeout=20000)
            
            # 모든 게시글 링크 가져오기
            links = page.query_selector_all(".board_list li .title a")
            targets = []
            for a in links:
                t = a.inner_text().strip()
                h = a.get_attribute("href")
                # 날짜 형식이 포함된 제목만 필터링
                if re.search(r'\d+월\s*\d+일', t):
                    targets.append({"title": t, "url": "https://program.kbs.co.kr" + h})

            print(f"분석 대상 게시글: {len(targets)}개 발견")

            for target in targets[:5]: # 최신 5개 분석
                # 날짜 추출 (2026-MM-DD 형식)
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                
                # 연도가 없으면 2026으로 보정
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 상세 페이지 읽기 시작...")
                page.goto(target['url'], wait_until="networkidle")
                
                # 본문 영역 텍스트 추출 (가장 확실한 방식)
                content_el = page.wait_for_selector(".board_content", timeout=15000)
                if not content_el: continue
                
                # 모든 텍스트를 가져와서 줄바꿈 정리
                raw_text = content_el.evaluate("el => el.innerText")
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                
                songs = []
                # 1. 작곡가 / 2. 제목 / 3. 연주자 구조 파싱
                for i, line in enumerate(lines):
                    # 숫자로 시작하는 라인 (예: 1. 또는 1 )
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        
                        # 다음 줄은 제목, 그 다음 줄은 연주자로 추측
                        song_title = lines[i+1] if i+1 < len(lines) else "정보 없음"
                        artist = ""
                        
                        # 연주자 정보는 보통 다음 줄이 숫자로 시작하지 않을 때 유효
                        if i+2 < len(lines) and not re.match(r'^\d+[\.\s\)]', lines[i+2]):
                            artist = lines[i+2].replace('-', '').strip()
                        
                        songs.append({
                            "no": len(songs) + 1,
                            "title": song_title,
                            "artist": f"{composer} / {artist}".strip(" /")
                        })
                
                if songs:
                    new_data[date_key] = songs
                    print(f"-> {date_key} 수집 완료 ({len(songs)}곡)")

        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            browser.close()
            
    return new_data

# 기존 데이터 로드 및 병합
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
    print("수집된 데이터가 없습니다. 로그를 확인하세요.")
