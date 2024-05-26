# ============================================================================= #
#
#                           defs collection
#
# ============================================================================= #
## URL 데이터 추출
def extract_data_from_url(url:str):
    import requests
    from bs4 import BeautifulSoup
    import trafilatura

    # from bs4 import BeautifulSoup
    # import requests
    # import trafilatura
    response = requests.get(url)
    # print("Response Code:", response.status_code)
    html_news = response.text
    soup_news = BeautifulSoup(html_news, 'html.parser')

    ## 뉴스 타이틀
    title = soup_news.find(class_="news_ttl").text
    title = title.replace("\n", "")
    # print("News-Title:", title)

    ## 뉴스 날짜
    time_content = soup_news.find("div", class_="time_area")
    time = time_content.find("dd").text
    time = time.replace("\n", "")
    # print("News-Time:", time)

    ## 뉴스 내용
    downloaded = trafilatura.fetch_url(url)
    body = trafilatura.extract(downloaded)
    body = body.replace("\n", "")
    # print("News-Body:", body)
    
    return title, time, body



## 분야별 데이터 추출
def df_category_extract(df, category):
    import pandas as pd
    df_category = df[df["category"]==f"{category}"].copy()
    return df_category
