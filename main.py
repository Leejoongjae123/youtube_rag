from fastapi import FastAPI, HTTPException, Request
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import os
import json
import asyncio
import aiohttp
from mangum import Mangum

# 환경 변수 로드
load_dotenv()

app = FastAPI()
handler = Mangum(app)

# API 키 확인
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")

# 벡터 저장소 초기화
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
vectorstore = None

@app.on_event("startup")
async def startup_event():
    global vectorstore
    # 기존 벡터 저장소가 없으면 새로 생성
    if not os.path.exists("chroma_db"):
        # 웹 페이지 로드
        loader = WebBaseLoader("https://www.hankyung.com/article/2025043070561")
        documents = loader.load()
        
        # 텍스트 분할
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        
        # 벡터 저장소 생성
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory="chroma_db"
        )
        vectorstore.persist()
    else:
        # 기존 벡터 저장소 로드
        vectorstore = Chroma(
            persist_directory="chroma_db",
            embedding_function=embeddings
        )

async def send_callback_response(callback_url, response_text):
    """
    콜백 URL로 응답을 전송합니다.
    
    Args:
        callback_url (str): 카카오에서 제공한 콜백 URL
        response_text (str): 전송할 응답 텍스트
    """
    try:
        print(f"콜백 응답 전송 시작: {callback_url}")
        
        # 카카오 챗봇 콜백 응답 형식에 맞게 설정
        response_data = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": response_text
                        }
                    }
                ]
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        print("응답 데이터:", json.dumps(response_data, ensure_ascii=False)[:200] + "...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(callback_url, json=response_data, headers=headers) as resp:
                if resp.status == 200:
                    print(f"콜백 응답 전송 성공: {callback_url}")
                    response_text = await resp.text()
                    print(f"콜백 응답: {response_text}")
                else:
                    response_text = await resp.text()
                    print(f"콜백 응답 전송 실패: {resp.status}, {response_text}")
    except Exception as e:
        print(f"콜백 응답 전송 중 오류 발생: {e}")

async def get_rag_answer(question):
    """
    RAG 모델을 사용하여 질문에 대한 답변을 생성합니다.
    
    Args:
        question (str): 사용자의 질문
    
    Returns:
        str: 생성된 답변
    """
    if not vectorstore:
        raise HTTPException(status_code=500, detail="벡터 저장소가 초기화되지 않았습니다.")
    
    # RAG 체인 생성
    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)
    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vectorstore.as_retriever()
    )
    
    # 질문에 대한 답변 생성
    result = qa_chain({"query": question})
    return result["result"]

async def process_rag_response(callback_url, question, delay_seconds=5):
    """
    RAG 모델로 답변을 생성하고 콜백 URL로 전송하는 비동기 함수
    
    Args:
        callback_url (str): 카카오에서 제공한 콜백 URL
        question (str): 사용자의 질문
        delay_seconds (int): 지연 시간(초)
    """
    try:
        # 실제 처리 전 대기 시간 (선택적)
        await asyncio.sleep(1)
        
        # RAG 모델로 답변 생성
        print(f"질문: {question}에 대한 RAG 응답 생성 중...")
        answer = await get_rag_answer(question)
        print(f"생성된 답변: {answer[:100]}...")
        
        # 콜백 URL로 응답 전송
        await send_callback_response(callback_url, answer)
        print(f"RAG 응답 전송 완료")
    except Exception as e:
        error_message = f"RAG 응답 처리 중 오류 발생: {str(e)}"
        print(error_message)
        # 오류 발생 시에도 사용자에게 응답
        await send_callback_response(callback_url, f"죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: {str(e)}")

@app.get("/")
async def root():
    return {"message": "카카오톡 RAG API 서버가 실행 중입니다."}

@app.post("/ask")
async def ask_direct(question: str):
    """
    직접 API를 호출하여 RAG 모델로 답변을 얻는 엔드포인트
    """
    answer = await get_rag_answer(question)
    return {"answer": answer}

@app.post("/kakao")
async def kakao_callback(request: Request):
    """
    카카오톡 챗봇 API 엔드포인트
    """
    # 요청 본문 파싱
    request_data = await request.json()
    
    # 사용자 발화 텍스트 가져오기
    utterance = request_data.get("userRequest", {}).get("utterance", "")
    # 카카오 callback URL 가져오기
    callback_url = request_data.get("userRequest", {}).get("callbackUrl", "")
    
    print(f'사용자 질문: {utterance}')
    print(f'콜백 URL: {callback_url}')
    
    # 콜백 URL이 있는 경우 비동기 처리
    if callback_url:
        # 즉시 응답 반환 (useCallback 필수)
        temp_response = {
            "version": "2.0",
            "useCallback": True,
            "data": {
                "text": "질문에 대한 답변을 준비 중입니다. 잠시만 기다려주세요..."
            }
        }
        
        # 비동기 태스크 생성
        try:
            task = asyncio.create_task(process_rag_response(callback_url, utterance))
            print(f"비동기 RAG 응답 태스크 생성됨")
        except Exception as e:
            print(f"태스크 생성 중 오류 발생: {e}")
        
        return temp_response
    else:
        # 콜백 URL이 없는 경우 동기적으로 처리
        try:
            # 동기적으로 처리하기 위해 run_until_complete 사용
            answer = await get_rag_answer(utterance)
            
            # 카카오 챗봇 응답 형식
            response_body = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": answer
                            }
                        }
                    ]
                }
            }
            return response_body
        except Exception as e:
            # 오류 발생 시 응답
            error_message = f"답변을 생성하는 중 오류가 발생했습니다: {str(e)}"
            response_body = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": error_message
                            }
                        }
                    ]
                }
            }
            return response_body

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
