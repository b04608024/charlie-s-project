import requests

keywords = ["DNA", "methylation"]

def search_articles():
    if not keywords:
        return
    search_query = " OR ".join(keywords)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={search_query}&retmode=json&sort=pub+date&retmax=5"
    response = requests.get(url)
    if response.status_code == 200:
        article_ids = response.json()['esearchresult']['idlist']
        for article_id in article_ids:
            fetch_article(article_id)
    else:
        print("Error fetching articles")

def fetch_article(article_id):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={article_id}&retmode=json"
    response = requests.get(url)
    if response.status_code == 200:
        article = response.json()['result'][article_id]
        title = article['title']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{article_id}/"
        message = f"Title: {title}\nLink: {url}"
        print(message)  # Print the message instead of sending it to Line
    else:
        print(f"Error fetching article {article_id}")

if __name__ == "__main__":
    search_articles()
