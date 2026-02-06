import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# 사용법:
# python scraper.py          # 일반 크롤링 실행
# python scraper.py --test   # 이메일 설정 테스트

def send_notification_email(change_summary=None, route_name=None):
    """변경 사항 알림 이메일 전송

    Args:
        change_summary (str|None): 변경 사항 요약 문자열. None이면 간단한 알림만 전송.
        route_name (str|None): 라우트 이름 (예: "EAST ASIA"). Subject에 포함.
    """
    try:
        # 이메일 설정 (아래 값들을 실제 값으로 변경하세요)
        sender_email = "jiworld.kim@gmail.com"  # 발신자 Gmail 주소
        receiver_emails = ["jiworld.kim@gmail.com", "ateam.marko@gmail.com"]  # 여러 수신자 이메일
        password = "lcia yurn ifks eqdi"  # Gmail 앱 비밀번호 (일반 비밀번호 아님!)

        # Gmail 앱 비밀번호 설정 방법:
        # 1. Google 계정 설정 → 보안 → 2단계 인증 켜기
        # 2. 보안 → 앱 비밀번호 생성 (선택: 메일, 기기: Windows 컴퓨터)
        # 3. 생성된 16자리 비밀번호를 password에 입력

        # 이메일 내용 구성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receiver_emails)  # 여러 수신자 표시
        subject_prefix = f"[{route_name}] " if route_name else ""
        msg['Subject'] = f"{subject_prefix}선박 운송 일정 변경 알림 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 이메일 본문에 변경 요약 포함 (있을 경우)
        now_text = datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')
        body_lines = [
            "안녕하세요,",
            "",
            "선박 운송 일정에 변경 사항이 감지되었습니다.",
            "",
            f"변경 시간: {now_text}",
            "",
        ]

        if change_summary:
            # 너무 길면 자르기
            max_len = 4000
            summary = change_summary
            if len(summary) > max_len:
                summary = summary[:max_len] + "\n... (생략)"
            body_lines.append("변경 요약:")
            body_lines.append(summary)
            body_lines.append("")
            body_lines.append("전체 데이터는 shipping_update.json을 확인하세요.")
        else:
            body_lines.append("새로운 데이터를 확인하려면 shipping_update.json 파일을 확인해주세요.")

        body_lines.append("")
        body_lines.append("자동화 시스템")

        body = "\n".join(body_lines)

        msg.attach(MIMEText(body, 'plain'))

        # SMTP 서버 연결 및 이메일 전송 (여러 수신자)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)  # receiver_emails 리스트 전달
        server.quit()

        print("이메일 알림이 성공적으로 전송되었습니다.")

    except Exception as e:
        print(f"이메일 전송 실패: {e}")
def send_test_email():
    """테스트 이메일 전송"""
    try:
        # 이메일 설정 (아래 값들을 실제 값으로 변경하세요)
        sender_email = "jiworld.kim@gmail.com"  # 발신자 Gmail 주소
        receiver_emails = ["jiworld.kim@gmail.com", "rokgy85@gmail.com"]  # 여러 수신자 이메일
        password = "lcia yurn ifks eqdi"  # Gmail 앱 비밀번호 (일반 비밀번호 아님!)

        # 이메일 내용 구성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receiver_emails)  # 여러 수신자 표시
        msg['Subject'] = f"선박 운송 일정 알림 시스템 테스트 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = f"""
테스트 이메일입니다.

선박 운송 일정 알림 시스템이 정상적으로 작동하고 있습니다.

테스트 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}

이 메일이 정상적으로 수신되었다면 시스템 설정이 완료된 것입니다.

자동화 시스템
        """.strip()

        msg.attach(MIMEText(body, 'plain'))

        # SMTP 서버 연결 및 이메일 전송 (여러 수신자)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)  # receiver_emails 리스트 전달
        server.quit()

        print("테스트 이메일이 성공적으로 전송되었습니다!")

    except Exception as e:
        print(f"테스트 이메일 전송 실패: {e}")
        print("\n※ Gmail 설정을 확인해주세요:")
        print("  1. sender_email과 password를 실제 Gmail 계정 정보로 변경")
        print("  2. Gmail 앱 비밀번호 생성 방법:")
        print("    - Google 계정 → 보안 → 2단계 인증 켜기")
        print("    - 보안 → 앱 비밀번호 생성 (메일/Windows 컴퓨터)")
        print("    - 생성된 16자리 비밀번호를 password에 입력")

def summarize_changes(old_data, new_data):
    """두 데이터 리스트를 비교하여 사람 읽기 좋은 변경 요약 문자열 반환."""
    if old_data is None:
        return f"초기 저장: 총 {len(new_data)}개의 선박 정보가 저장되었습니다."

    def key(item):
        return f"{item.get('Company','')}|{item.get('Ship Name','')}|{item.get('Voyage','')}"

    old_map = {key(item): item for item in old_data}
    new_map = {key(item): item for item in new_data}

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    added = new_keys - old_keys
    removed = old_keys - new_keys
    common = old_keys & new_keys

    lines = []
    if added:
        lines.append(f"추가된 선박: {len(added)}개")
        for k in sorted(added):
            parts = k.split('|')
            lines.append(f"  + {parts[0]} - {parts[1]} ({parts[2]})")

    if removed:
        lines.append(f"삭제된 선박: {len(removed)}개")
        for k in sorted(removed):
            parts = k.split('|')
            lines.append(f"  - {parts[0]} - {parts[1]} ({parts[2]})")

    # 변경된 항목 검사
    for k in sorted(common):
        o = old_map[k]
        n = new_map[k]
        sub_lines = []
        # 출발항 비교
        for port, old_val in o.get('Departure Ports', {}).items():
            new_val = n.get('Departure Ports', {}).get(port)
            if old_val != new_val:
                sub_lines.append(f"    출발 - {port}: '{old_val}' -> '{new_val}'")
        # 도착항 비교
        for port, old_val in o.get('Arrival Ports', {}).items():
            new_val = n.get('Arrival Ports', {}).get(port)
            if old_val != new_val:
                sub_lines.append(f"    도착 - {port}: '{old_val}' -> '{new_val}'")

        if sub_lines:
            parts = k.split('|')
            lines.append(f"변경: {parts[0]} - {parts[1]} ({parts[2]})")
            lines.extend(sub_lines)

    if not lines:
        return "변경 사항이 감지되었으나 요약할 차이점이 없습니다. 전체 파일을 확인하세요."

    return "\n".join(lines)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 크롤링 설정 정의
SCRAPE_CONFIGS = [
    {
        "name": "EAST ASIA",
        "url": "https://autocj.co.jp/japan_shipping?dest=8",
        "history_file": "shipping_update_east_asia.json",
        "departure_ports": ["Yokohama", "Kawasaki", "Kisarazu", "Nagoya", "Kobe", "Osaka", "Hakata", "Hibikinada", "Kanda", "Hitachinaka"],
        "arrival_ports": ["Hong Kong", "Laem Chabang", "Hambantota", "Chittagong", "Mongla", "Subic"]
    },
    {
        "name": "ASIA,AFRICA",
        "url": "https://autocj.co.jp/japan_shipping?dest=2",
        "history_file": "shipping_update_asia_africa.json",
        "departure_ports": ["Yokohama", "Kawasaki", "Kisarazu", "Nagoya", "Kobe", "Osaka", "Hakata", "Hibikinada", "Kanda", "Nakanoseki", "Hitachinaka"],
        "arrival_ports": ["Jebel Ali", "Karachi", "Port Louis", "Durban", "Dar", "Mombasa", "Maput"]
    }
]

def scrape_page(config):
    """단일 페이지 크롤링 및 업데이트.

    Args:
        config (dict): 크롤링 설정 (url, history_file, departure_ports, arrival_ports, name)

    Returns:
        bool: 변경 사항이 있었으면 True, 없으면 False
    """
    url = config["url"]
    history_file = config["history_file"]
    departure_ports = config["departure_ports"]
    arrival_ports = config["arrival_ports"]
    route_name = config["name"]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    print(f"\n[{datetime.now()}] {route_name} 크롤링을 시작합니다...")
    print(f"URL: {url}")

    try:
        # 1. 웹사이트 데이터 가져오기
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("1. 웹사이트 접속 성공")

        # 2. BeautifulSoup으로 HTML 파싱 (html5lib로 내결함성 강화)
        soup = BeautifulSoup(response.text, 'html5lib')

        # 3. 데이터 테이블 찾기: div.ship_c > table.main
        ship_div = soup.find('div', class_='ship_c')
        if not ship_div:
            print("에러: div.ship_c를 찾을 수 없습니다.")
            return

        data_table = ship_div.find('table', class_='main')
        if not data_table:
            print("에러: table.main을 찾을 수 없습니다.")
            return

        print("2. 데이터 테이블을 찾았습니다.")

        # 4. 모든 행 추출 (tbody 하위 tr.row 우선, 없으면 tr 전체)
        rows = data_table.select('tbody > tr.row')
        if not rows:
            rows = data_table.select('tbody > tr')
        print(f"3. {len(rows)}개의 행을 찾았습니다.")

        # 5. 데이터 파싱
        current_data = []

        for row in rows:
            # td 셀 추출 (html5lib 파서로 정확한 셀 분리)
            cells = row.find_all('td')

            # 최소 셀 개수 확인 (3 + 출발항 + 도착항)
            min_cells = 3 + len(departure_ports) + len(arrival_ports)
            if len(cells) < min_cells:
                continue

            # 기본 정보 추출 (인덱스 0, 1, 2) - 첫 td만 회사명
            company = cells[0].get_text(strip=True)
            ship_name = cells[1].get_text(strip=True)
            voyage = cells[2].get_text(strip=True)

            # 출발항 정보 추출
            departure_dict = {}
            for i, port_name in enumerate(departure_ports):
                cell_index = 3 + i
                cell_value = cells[cell_index].get_text(strip=True).replace('\n', '').replace(' ', '')
                departure_dict[port_name] = cell_value if cell_value else "-"

            # 도착항 정보 추출
            arrival_dict = {}
            for i, port_name in enumerate(arrival_ports):
                cell_index = 3 + len(departure_ports) + i
                cell_value = cells[cell_index].get_text(strip=True).replace('\n', '').replace(' ', '')
                arrival_dict[port_name] = cell_value if cell_value else "-"

            ship_data = {
                "Company": company,
                "Ship Name": ship_name,
                "Voyage": voyage,
                "Departure Ports": departure_dict,
                "Arrival Ports": arrival_dict
            }

            current_data.append(ship_data)

        print(f"4. 데이터 추출 완료 ({len(current_data)}개 선박 정보)")

        # 5. 기존 데이터 불러오기
        existing_data = None
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"5. 기존 파일 '{history_file}'을 불러왔습니다.")
        else:
            print("5. 기존 파일이 없습니다. 새로 생성합니다.")

        # 6. 변경 사항 비교
        if existing_data is not None and existing_data == current_data:
            print("결과: 기존 데이터와 동일합니다. 변경 사항이 없어 저장하지 않습니다.")
            return

        # 변경 요약 생성
        if existing_data is not None:
            change_summary = summarize_changes(existing_data, current_data)
        else:
            change_summary = summarize_changes(None, current_data)

        # 7. 데이터 저장 (덮어쓰기)
        print("6. 변경 사항 확인! 새 데이터를 저장합니다.")
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        # 8. 변경 알림 이메일 전송 (요약 포함)
        print("7. 변경 알림 이메일을 전송합니다...")
        send_notification_email(f"[{route_name}] 변경 알림\n\n" + change_summary)

        full_path = os.path.abspath(history_file)
        print(f"최종 결과: 파일 저장 완료! 위치: {full_path}")
        print("변경 알림 이메일이 전송되었습니다.")
        return True

    except Exception as e:
        print(f"실행 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def scrape_and_update():
    """모든 설정된 페이지를 크롤링하고 업데이트."""
    print(f"====== 크롤링 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ======")

    results = []
    for config in SCRAPE_CONFIGS:
        changed = scrape_page(config)
        results.append({"route": config["name"], "changed": changed})

    print(f"\n====== 크롤링 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ======")
    print("\n결과 요약:")
    for result in results:
        status = "변경됨" if result["changed"] else "변경 없음"
        print(f"  - {result['route']}: {status}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("테스트 모드로 실행합니다...")
        send_test_email()
    else:
        scrape_and_update()
