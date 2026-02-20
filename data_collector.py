import requests
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

def sub_course_helper(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for index, line in enumerate(lines):
        if "prerequisites" in line.lower():
            if index + 1 < len(lines):
                prereq = lines[index + 1]
                return prereq
    return 'No prerequisites found'

def main_course_info():
    dfs = pd.read_html(f'https://www.mccormick.northwestern.edu/computer-science/academics/courses/', extract_links="body") 
    df = dfs[0] # Assuming the table you want is the first one
    df['Extracted_Link'] = df.iloc[:, 0].apply(lambda x: x[1] if isinstance(x, tuple) else None)
    df2 = pd.read_html(f'https://www.mccormick.northwestern.edu/computer-science/academics/courses/')[0]
    new_extracted_links = []
    for elem in df['Extracted_Link']:
        if elem.startswith('descriptions'):
            new_extracted_links.append('https://www.mccormick.northwestern.edu/computer-science/academics/courses/'+elem)
        else:
            new_extracted_links.append(elem)
    df2['Extracted_Link'] = new_extracted_links
    return df2

def main():
    df = main_course_info()
    prerequisites = []
    # num_lst = df['Course'].str.extract(r'(\d+)')[0].tolist()
    with ThreadPoolExecutor(max_workers=10) as exe:
        results = exe.map(sub_course_helper, df['Extracted_Link'].tolist())
    for prereq in results:
        prerequisites.append(prereq)
        # urls.append(url)
    df['Prerequisites'] = prerequisites
    # df['URL'] = urls
    df.to_csv('main_course_info.csv', index=False)

if __name__ == '__main__':
    main()