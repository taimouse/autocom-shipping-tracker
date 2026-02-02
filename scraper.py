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

def send_notification_email():
    """변경 사항 알림 이메일 전송"""
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
        msg['Subject'] = f"선박 운송 일정 변경 알림 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body = f"""
안녕하세요,

선박 운송 일정에 변경 사항이 감지되었습니다.

변경 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}

새로운 데이터를 확인하려면 shipping_history.json 파일을 확인해주세요.

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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def scrape_and_update():
    url = "https://autocj.co.jp/japan_shipping?dest=8"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    history_file = "shipping_history.json"

    print(f"[{datetime.now()}] 크롤링을 시작합니다...")

    # 고정 헤더 정의
    departure_ports = ["Yokohama", "Kawasaki", "Kisarazu", "Nagoya", "Kobe", "Osaka", "Hakata", "Hibikinada", "Kanda", "Hitachinaka"]
    arrival_ports = ["Hong Kong", "Laem Chabang", "Hambantota", "Chittagong", "Mongla", "Subic"]

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

            # 최소 19개의 셀이 있어야 함 (3 + 10 + 6)
            if len(cells) < 19:
                continue

            # 기본 정보 추출 (인덱스 0, 1, 2) - 첫 td만 회사명
            company = cells[0].get_text(strip=True)
            ship_name = cells[1].get_text(strip=True)
            voyage = cells[2].get_text(strip=True)

            # 출발항 정보 추출 (인덱스 3~12, 총 10개)
            departure_dict = {}
            for i, port_name in enumerate(departure_ports):
                cell_index = 3 + i
                cell_value = cells[cell_index].get_text(strip=True).replace('\n', '').replace(' ', '')
                departure_dict[port_name] = cell_value if cell_value else "-"

            # 도착항 정보 추출 (인덱스 13~18, 총 6개)
            arrival_dict = {}
            for i, port_name in enumerate(arrival_ports):
                cell_index = 13 + i
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

        # 7. 데이터 저장 (덮어쓰기)
        print("6. 변경 사항 확인! 새 데이터를 저장합니다.")
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        # 8. 변경 알림 이메일 전송
        print("7. 변경 알림 이메일을 전송합니다...")
        send_notification_email()

        full_path = os.path.abspath(history_file)
        print(f"최종 결과: 파일 저장 완료! 위치: {full_path}")
        print("변경 알림 이메일이 전송되었습니다.")

    except Exception as e:
        print(f"실행 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("테스트 모드로 실행합니다...")
        send_test_email()
    else:
        scrape_and_update()
