import json
import os
import time
from playwright.sync_api import sync_playwright

def trace_kbs_content():
    with sync_playwright() as p:
        # 브라우저 실행
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            print("--- [1단계] 게시판 메인 접속 ---")
            url = "https://program.kbs.co.kr/1fm/radio/startfm/pc/board.html?smenu=0cc198&bbs_loc=R2002-0282-03-537648,list,none,1,0"
            page.goto(url, wait_until="networkidle")
            time.sleep(10) # 데이터 로딩을 위해 충분히 대기

            # 현재 페이지의 모든 텍스트 출력
            all_text = page.evaluate("() => document.body.innerText")
            print("\n[현재 페이지에서 인식된 전체 텍스트 요약]:")
            print(all_text[:1000]) # 상위 1000자 출력

            # 모든 링크 추출 및 출력
            links = page.query_selector_all("a")
            print(f"\n[발견된 전체 링크 개수]: {len(links)}개")
            
            targets = []
            for a in links:
                href = a.get_attribute("href") or ""
                text = a.inner_text().strip()
                if text:
                    print(f"- 링크텍스트: {text} | 주소: {href[:50]}...")
                    # 'view'가 포함된 실제 게시글 링크 후보 수집
                    if "view" in href or "bbs_loc" in href:
                        targets.append({"title": text, "url": href})

            if targets:
                print(f"\n--- [2단계] 첫 번째 후보 게시글 접속 시도: {targets[0]['title']} ---")
                full_url = targets[0]['url'] if targets[0]['url'].startswith("http") else "https://program.kbs.co.kr" + targets[0]['url']
                page.goto(full_url, wait_until="networkidle")
                time.sleep(5)
                
                # 게시글 본문의 모든 내용 가져오기
                post_content = page.evaluate("() => document.body.innerText")
                print("\n[게시글 본문 전체 내용]:")
                print("-" * 30)
                print(post_content)
                print("-" * 30)
            else:
                print("\n[경고] 게시글 링크를 하나도 찾지 못했습니다.")

        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    trace_kbs_content()
