import json
import os
import re
import time
from playwright.sync_api import sync_playwright

def get_kbs_data():
    new_data = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 실제 브라우저와 동일한 환경 설정
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            print("KBS 출발 FM 게시판 접속...")
            # 선곡표 메뉴가 포함된 메인 주소
            url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0"
            page.goto(url, wait_until="networkidle")
            time.sleep(5)

            # 핵심: iframe 내부로 프레임 전환
            # KBS 게시판은 보통 'ifrm_view' 또는 특정 ID의 iframe 안에 목록이 있습니다.
            main_frame = None
            for frame in page.frames:
                if "board.html" in frame.url and "smenu=0cc198" in frame.url:
                    main_frame = frame
                    break
            
            # 프레임을 찾지 못했다면 현재 페이지에서 직접 찾기
            target_page = main_frame if main_frame else page
            
            print("게시글 목록 추출 중...")
            # 날짜가 포함된 링크들 찾기
            links = target_page.query_selector_all("a")
            targets = []
            for a in links:
                text = a.inner_text().strip()
                href = a.get_attribute("href") or ""
                if re.search(r'\d+월\s*\d+일', text):
                    # 주소 보정 (슬래시 누락 방지)
                    if href.startswith("board.html"):
                        href = "/1fm/radio/startfm/pc/" + href
                    full_url = "https://program.kbs.co.kr" + href if href.startswith("/") else href
                    targets.append({"title": text, "url": full_url})

            print(f"발견된 선곡표 게시글: {len(targets)}개")

            for target in targets[:5]:
                nums = re.findall(r'\d+', target['title'])
                if len(nums) < 2: continue
                y = nums[0] if len(nums) >= 3 else "2026"
                m = nums[1] if len(nums) >= 3 else nums[0]
                d = nums[2] if len(nums) >= 3 else nums[1]
                date_key = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

                print(f"[{date_key}] 상세 내용 읽기 시도...")
                page.goto(target['url'], wait_until="networkidle")
                time.sleep(3)
                
                # 본문 추출 (iframe 내부일 수 있으므로 다시 체크)
                content = page.evaluate("() => document.body.innerText")
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                
                songs = []
                for i, line in enumerate(lines):
                    # 사용자님의 데이터 패턴: 1. 작곡가 / 제목 / 연주자
                    if re.match(r'^\d+[\.\s\)]', line):
                        composer = re.sub(r'^\d+[\.\s\)]*', '', line).strip()
                        title = lines[i+1] if i+1 < len(lines) else "정보없음"
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
                    print(f"-> {date_key} 업데이트 성공!")

        except Exception as e:
            print(f"실행 오류: {e}")
        finally:
            browser.close()
            
    return new_data

# --- 기존 데이터 병합 및 저장 ---
data_file = 'data.json'
total_data = {}
if os.path.exists(data_file) and os.path.getsize(data_file) > 0:
    with open(data_file, 'r', encoding='utf-8') as f:
        try: total_data = json.load(f)
        except: total_data = {}

new_records = get_kbs_data()
total_data.update(new_records)

with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(total_data, f, ensure_ascii=False, indent=4)
print("작업 완료.")
