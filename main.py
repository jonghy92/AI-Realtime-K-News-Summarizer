# ============================================================================= #
#
#                           Libraies
#
# ============================================================================= #
#from langchain.text_splitter import CharacterTextSplitter
#from langchain.embeddings import HuggingFaceBgeEmbeddings
#from langchain_community.vectorstores import FAISS
#from langchain_community import embeddings
#from langchain_community.document_loaders import PyPDFLoader
#from langchain.prompts import ChatPromptTemplate, PromptTemplate
#from langchain.output_parsers import PydanticOutputParser

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

import shutil
import pandas as pd
from datetime import datetime
from tqdm.auto import tqdm
from bs4 import BeautifulSoup
import requests
# import trafilatura
import shutil
import pandas as pd
from datetime import datetime
import time
from defs import extract_data_from_url, df_category_extract



## 1. 대분류 - hard coded
news_categories_list = [
    "https://www.mk.co.kr/news/economy/latest/",    # 경제
    "https://www.mk.co.kr/news/business/latest/",   # 기업
    "https://www.mk.co.kr/news/society/latest/",    # 사회  
    "https://www.mk.co.kr/news/world/latest/",      # 국제
    "https://www.mk.co.kr/news/realestate/latest",  # 부동산
    "https://www.mk.co.kr/news/stock/latest/",      # 증권
    "https://www.mk.co.kr/news/politics/latest/",   # 정치
    "https://www.mk.co.kr/news/it/latest/",         # IT/과학
    "https://www.mk.co.kr/news/culture/latest/",    # 문화
]

# print("# ------------------------------------------------------------------------------------ #")
# print("Top News Categories Numbers", " : ", len(news_categories_list))
# print("# ------------------------------------------------------------------------------------ #")




### Stage 1.
Total_collection = []
## 1. 대분류 (뉴스 케테고리 9개)
for category in tqdm(news_categories_list, "Extracting Info"):
    category_name = category.split("/")[4]
    response = requests.get(category)
    #print(response.status_code)
    html= response.text
    soup = BeautifulSoup(html, 'html.parser')

    ## 2. 중분류 (뉴스 케테고리별 링크들)
    news_lis = soup.find_all("a", class_="news_item")
    href_lis = []
    for i in news_lis:
        href = i.attrs["href"]
        href_lis.append(href)
    #print("Total news url collected:", len(href_lis))

    ## 3. 추출
    for url in href_lis:
        try:
            extraction = list(extract_data_from_url(url))
            extraction.append(category_name)
            extraction.append(url)
            Total_collection.append(extraction)
        except:
            print(f"잘못된 URL 포맷, 내용을 제외합니다 ... {url}")
        #print("Collection Completed :", url)
        time.sleep(0.5)

print(f"News data extracted from each category ---- Total_Num : {len(news_categories_list)} ")




### Stage 2.
## 추출된 데이터 - 데이터 프레임화
df = pd.DataFrame(Total_collection)
df.columns = ["title", "time", "body", "category", "url"]
#category_list = df["category"].unique()
#print(category_list)
#categories = ['economy' 'business' 'society' 'world' 'realestate' 'stock' 'politics', 'it' 'culture']
category_list = ["economy", "business", "world", "stock", "politics", "it"]

# 파일 시간로그
reportgen_time_log = datetime.now().strftime('%Y%m%d-%H%M%S')



### Stage 3.
## 분석|요약 진행
for category in category_list:
    df_category_selected = df_category_extract(df, f"{category}")
    df_top3_category_selected = df_category_selected[:3]
    
    # top 3 url list
    top3_urls = list(df_top3_category_selected["url"].values)
    news_category_nm = df_top3_category_selected["category"].unique()[0]


    #print(top3_urls)
    # print("categroy: ", category)
    # print("Top3 Urls are listed ...!")    
    for url in tqdm(top3_urls, "[ Top3-news ] -- Summarizing from selected news category...  "):
        
        # df_top3_category_selected 에서 Title 명 추출.
        news_title = df_top3_category_selected[df_top3_category_selected["url"] == url]["title"].values[0]
        news_time = df_top3_category_selected[df_top3_category_selected["url"] == url]["time"].values[0]


        doc = WebBaseLoader(url).load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        doc_splits = text_splitter.split_documents(doc)

        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            # collection_name="rag-chroma",
            embedding=OllamaEmbeddings(model="nomic-embed-text", show_progress=False), 
        )
        
        retriever = vectorstore.as_retriever()
        
        ## LLM import
        model_local = ChatOllama(model="wizardlm2")

        after_rag_template = """Always generate answers with number of bullet points.
                            Answer the question based only on the following context:
                            {context}
                            Question: {question}
                            """
        after_rag_prompt = PromptTemplate.from_template(after_rag_template)
        after_rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | after_rag_prompt
            | model_local
            | StrOutputParser()
        )
        
        ## LLM ANS
        ans = after_rag_chain.invoke("2개의 bullet points로 요약해줘.")
        
        # ============================================== Write ================================================= #
        with open(f"./output_files/research_rslt_{reportgen_time_log}.txt", mode="a", encoding='utf-8') as file:
            file.write("\n")                
            file.write(f"News_Category: {news_category_nm} \n")
            file.write(f"News_Time: {news_time} \n")
            file.write(f"News_Title: {news_title} \n")
            file.write(f"Url_Link: {url} \n")
            file.write("Bullet Points Summary: \n")
            file.write(ans)
            file.write("\n\n")
        # ===================================================================================================== #"
        
        ## Delete all collections in the Chroma db
        vectorstore.delete_collection()
        # print("vector_db refreshed  ...!")

## END-결과 확인용 ##
print("# ---------------------------------------------------------------------------------------- #")
print("\n")
print("Finished Job ...!")
print(f"File Name : research_rslt_{reportgen_time_log}.txt  ...... File generated ....!")
print("\n")
print("# ---------------------------------------------------------------------------------------- #")