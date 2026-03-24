# Autocom Shipping Tracker

일본 Autocom 선박 운송 스케줄을 자동으로 추적하고 캘린더 형태로 표시하는 웹 애플리케이션입니다.

## 🚀 주요 기능

- **실시간 스케줄 추적**: 일본 Autocom 웹사이트에서 선박 운송 스케줄을 자동으로 크롤링
- **2개 라우트 지원**:
  - EAST ASIA 라우트 (Hong Kong, Laem Chabang, Hambantota, Chittagong, Mongla, Subic)
  - ASIA, AFRICA 라우트 (Jebel Ali, Karachi, Port Louis, Durban, Dar, Mombasa, Maput)
- **캘린더 뷰**: FullCalendar를 사용한 직관적인 스케줄 표시
- **필터링**: 회사별, 출발/도착 포트별 필터링 지원
- **반응형 디자인**: PC와 모바일 모두 지원
- **이메일 알림**: 스케줄 변경 시 자동 이메일 알림
- **데이터 아카이브**: 과거 스케줄 자동 보관

## 📁 프로젝트 구조

```
autocom-shipping-tracker/
├── index.html                          # 메인 웹페이지 (반응형)
├── calendar.html                       # 캘린더 전용 페이지
├── scraper.py                          # 데이터 크롤링 스크립트
├── shipping_update_east_asia.json      # EAST ASIA 라우트 최신 데이터
├── shipping_update_asia_africa.json    # ASIA, AFRICA 라우트 최신 데이터
├── shipping_archive_east_asia.json     # EAST ASIA 라우트 아카이브 데이터
├── shipping_archive_asia_africa.json   # ASIA, AFRICA 라우트 아카이브 데이터
├── requirements.txt                     # Python 패키지 의존성
└── README.md                           # 프로젝트 설명
```

## 🛠️ 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/autocom-shipping-tracker.git
cd autocom-shipping-tracker
```

### 2. Python 환경 설정

Python 3.7 이상이 필요합니다.

```bash
# 가상환경 생성 (선택사항)
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 필요한 패키지 설치
pip install -r requirements.txt
```

또는 개별 패키지 설치:

```bash
pip install requests beautifulsoup4 html5lib
```

### 3. 이메일 설정 (선택사항)

스케줄 변경 시 이메일 알림을 받으려면 `scraper.py`의 이메일 설정을 수정하세요:

```python
# scraper.py 파일의 24-26번째 줄
sender_email = "your-email@gmail.com"      # 발신자 Gmail 주소
receiver_emails = ["recipient@gmail.com"]   # 수신자 이메일 목록
password = "your-app-password"              # Gmail 앱 비밀번호
```

**Gmail 앱 비밀번호 설정 방법:**
1. Google 계정 → 보안 → 2단계 인증 켜기
2. 보안 → 앱 비밀번호 생성 (메일/Windows 컴퓨터 선택)
3. 생성된 16자리 비밀번호를 `password`에 입력

이메일 설정 테스트:
```bash
python scraper.py --test
```

### 4. 데이터 크롤링

```bash
# 수동 크롤링 실행
python scraper.py
```

### 5. 웹페이지 실행

로컬 서버를 실행하여 웹페이지를 확인할 수 있습니다:

```bash
# Python 내장 서버 사용
python -m http.server 8000

# 또는 Node.js가 설치되어 있다면
npx http-server
```

브라우저에서 `http://localhost:8000`으로 접속

## 📋 사용법

### 웹 인터페이스

1. **라우트 선택**: EAST ASIA 또는 ASIA, AFRICA 선택
2. **필터링**: 
   - 회사별 필터링 (체크박스)
   - 출발 포트별 필터링
   - 도착 포트별 필터링
3. **캘린더 조작**:
   - 키보드 화살표로 월 이동
   - 위쪽 화살표로 오늘로 이동
   - 이벤트 클릭/호버로 상세 정보 확인

### 크롤링 옵션

```bash
# 일반 크롤링 실행
python scraper.py

# 이메일 설정 테스트
python scraper.py --test
```

## 🔧 기술 스택

- **프론트엔드**: HTML5, Tailwind CSS, JavaScript, FullCalendar
- **백엔드**: Python, BeautifulSoup, Requests
- **자동화**: GitHub Actions (옵션)
- **호스팅**: GitHub Pages

## 📊 데이터 구조

각 선박 데이터는 다음과 같은 구조를 가집니다:

```json
{
  "Company": "회사명",
  "Ship Name": "선박명",
  "Voyage": "항차",
  "Departure Ports": {
    "Yokohama": "Jan15",
    "Nagoya": "Jan16",
    "...": "..."
  },
  "Arrival Ports": {
    "Hong Kong": "Jan25",
    "Laem Chabang": "Jan28",
    "...": "..."
  }
}
```

## 🔄 자동화 (옵션)

GitHub Actions을 통해 정기적으로 데이터를 업데이트할 수 있습니다. `.github/workflows/` 디렉토리에 워크플로우 파일을 생성하여 자동화를 설정하세요.

## 📝 requirements.txt

```
requests>=2.31.0
beautifulsoup4>=4.12.2
html5lib>=1.1
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## ⚠️ 주의사항

- 이 도구는 교육 및 개인적 용도로만 사용하세요
- 웹 크롤링 시 대상 사이트의 이용약관을 준수하세요
- 과도한 요청으로 서버에 부하를 주지 않도록 주의하세요

## 📞 지원

문제가 발생하거나 기능 요청이 있으시면 Issues에 등록해 주세요.