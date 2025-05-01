# YouTube RAG 기반 카카오톡 챗봇 API

## 프로젝트 개요
이 프로젝트는 FastAPI를 사용하여 RAG(Retrieval-Augmented Generation) 기반의 챗봇 API를 구현한 것입니다. 한국경제 뉴스 기사에서 정보를 추출하여 사용자 질문에 답변하며, 카카오톡 스마트 챗봇과 연동할 수 있습니다.

## 주요 기능
- 웹 페이지(한국경제 기사)에서 콘텐츠를 로드하여 벡터 데이터베이스 구축
- OpenAI 임베딩과 ChatGPT를 활용한 질의응답 시스템
- 카카오톡 챗봇 API 연동(비동기 콜백 지원)
- 직접 API 호출을 통한 질의응답 기능

## 기술 스택
- **FastAPI**: 웹 API 프레임워크
- **LangChain**: LLM 애플리케이션 구축 프레임워크
- **ChromaDB**: 벡터 데이터베이스
- **OpenAI API**: 임베딩 및 질의응답 생성
- **Mangum**: AWS Lambda 배포 지원
- **aiohttp**: 비동기 HTTP 요청 처리

## UBUNTU 셋팅 명령어
// 기본 설치
sudo apt-get update
sudo apt install -y python3-pip nginx

// nginx 셋팅
sudo vim /etc/nginx/sites-enabled/fastapi_nginx

// nginx 문구 설정
server{
	listen 80;
    server_name {public ip};
    location / {
    	proxy_pass http://127.0.0.1:8000;
    }
}

//재시작
sudo service nginx restart

//라이브러리설치
pip install fastapi==0.104.1 uvicorn==0.24.0 langchain==0.0.350 langchain-community==0.0.10 langchain-openai==0.0.2 beautifulsoup4==4.12.2 requests==2.31.0 python-dotenv==1.0.0 chromadb==0.4.18 aiohttp==3.8.6 mangum==0.17.0

//서버 온
nohup python3 -m uvicorn main:app &

//서버 확인
ps aux | grep uvicorn

## 설치 방법

### 필수 요구사항
- Python 3.8 이상
- OpenAI API 키

### 설치 단계
1. 저장소 클론
```bash
git clone https://github.com/your-username/youtube-rag.git
cd youtube-rag
```

2. 가상 환경 설정 (선택사항)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
`.env` 파일을 프로젝트 루트 디렉토리에 생성하고 다음 내용을 추가합니다:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## 사용 방법

### 로컬에서 실행
```bash
uvicorn main:app --reload
```
서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

### API 엔드포인트

1. **GET /** - API 상태 확인
   ```
   http://localhost:8000/
   ```

2. **POST /ask** - 직접 질문 API
   ```
   http://localhost:8000/ask?question=원하는_질문
   ```

3. **POST /kakao** - 카카오톡 챗봇 연동 API
   ```
   http://localhost:8000/kakao
   ```
   - 카카오톡 스킬 서버로 등록하여 사용합니다.

## AWS Lambda 배포
이 프로젝트는 Mangum을 통해 AWS Lambda 배포를 지원합니다. 다음은 배포 과정입니다:

1. 프로젝트 패키징
```bash
pip install -r requirements.txt --target ./package
cp main.py .env ./package/
cd package
zip -r ../deployment.zip .
```

2. AWS Lambda 함수 생성
   - 런타임: Python 3.8+
   - 핸들러: `main.handler`
   - 배포 패키지: 위에서 생성한 zip 파일 업로드

3. API Gateway 설정
   - HTTP API 또는 REST API 생성
   - Lambda 함수와 통합
   - 필요한 경로 및 메서드 설정

## 작동 방식
1. 서버 시작 시 지정된 웹 페이지에서 데이터를 크롤링하여 ChromaDB에 벡터화된 데이터를 저장합니다.
2. 사용자가 질문을 보내면 벡터 데이터베이스에서 관련 정보를 검색합니다.
3. 검색된 정보를 기반으로 OpenAI의 ChatGPT가 응답을 생성합니다.
4. 카카오톡 챗봇을 통한 질문은 비동기 처리되어 콜백 URL로 결과를 전송합니다.

## 라이센스
MIT License

## 주의사항
- OpenAI API 사용에는 비용이 발생할 수 있습니다.
- 뉴스 기사 크롤링 시 해당 사이트의 이용약관을 확인하세요. 
