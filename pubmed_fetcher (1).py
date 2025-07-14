
import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Optional

PHARMA_KEYWORDS = [
    "pharma", "biotech", "therapeutics", "genomics", "diagnostics",
    "inc", "corp", "ltd", "gmbh", "s.a.", "s.r.l", "pharmaceutical", "biotechnology"
]

def fetch_pubmed_data(
    query: str,
    limit: int = 50,
    year_filter: Optional[List[str]] = None,
    debug: bool = False
) -> List[Dict[str, str]]:

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(limit),
        "retmode": "xml"
    }

    if debug:
        print(f"[Debug] Searching PubMed with query: '{query}' and limit: {limit}")
        if year_filter:
            print(f"[Debug] Filtering by year(s): {year_filter}")


    try:
        search_response = requests.get(base_url, params=search_params)
        search_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        if debug:
            print(f"[Search Error] Request failed: {e}")
        return []

    if search_response.status_code != 200:
        if debug:
            print(f"[Search Error] Status code: {search_response.status_code}")
        return []

    try:
        root = ET.fromstring(search_response.content)
        ids = root.findall(".//Id")
        id_list = [i.text for i in ids]
    except ET.ParseError as e:
        if debug:
            print(f"[Search Error] Failed to parse XML: {e}")
        return []


    if not id_list:
        if debug:
            print("[Search Result] No IDs found.")
        return []

    if debug:
        print(f"[Debug] Found {len(id_list)} paper IDs.")


    fetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml"
    }

    try:
        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        if debug:
            print(f"[Fetch Error] Request failed: {e}")
        return []


    if fetch_response.status_code != 200:
        if debug:
            print(f"[Fetch Error] Status code: {fetch_response.status_code}")
        return []

    try:
        records_root = ET.fromstring(fetch_response.content)
        records = records_root.findall(".//PubmedArticle")
    except ET.ParseError as e:
        if debug:
            print(f"[Fetch Error] Failed to parse XML: {e}")
        return []

    results: List[Dict[str, str]] = []

    if debug:
        print(f"[Debug] Parsing {len(records)} records.")


    for record in records:
        try:
            title = record.findtext(".//ArticleTitle") or "N/A"
            pub_date_element = record.find(".//PubDate")
            pub_year = pub_date_element.findtext("Year") if pub_date_element else "N/A"
            pmid = record.findtext(".//PMID") or "N/A"

            if year_filter and pub_year not in year_filter:
                if debug:
                    print(f"[Debug] Skipping paper {pmid} due to year filter ({pub_year}).")
                continue

            authors_info = record.findall(".//Author")
            non_academic_authors = []
            company_affiliations = []
            corresponding_email = "N/A"

            for author in authors_info:
                affil_info = author.find("AffiliationInfo")
                affil = affil_info.findtext("Affiliation") if affil_info else None

                if affil and any(k.lower() in affil.lower() for k in PHARMA_KEYWORDS):
                    name = f"{author.findtext('ForeName', '')} {author.findtext('LastName', '')}".strip()
                    if name: # Only add if name is not empty after stripping
                        non_academic_authors.append(name)
                    company_affiliations.append(affil)

                    # Check for email within the affiliation string
                    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", affil)
                    if match:
                        corresponding_email = match.group() # Assuming the first found email is the corresponding one for simplicity

            # Also check AuthorList for CorrespondingAuthor element which might contain email
            try:
                corr_author = record.find(".//AuthorList/Author/CorrespondingAuthor")
                if corr_author is not None:
                    email_element = corr_author.find("AffiliationInfo/Affiliation")
                    if email_element is not None:
                         match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email_element.text)
                         if match:
                             corresponding_email = match.group()

            except Exception as e:
                 if debug:
                     print(f"[Debug] Error checking for CorrespondingAuthor element: {e}")
                 pass # Ignore errors during this check


            if non_academic_authors:
                results.append({
                    "PubmedID": pmid,
                    "Title": title,
                    "Publication Date": pub_year,
                    "Non-academic Author(s)": "; ".join(non_academic_authors),
                    "Company Affiliation(s)": "; ".join(sorted(list(set(company_affiliations)))), # Use set to remove duplicates and sort
                    "Corresponding Author Email": corresponding_email
                })
                if debug:
                    print(f"[Debug] Added paper {pmid} with non-academic affiliation.")


        except Exception as e:
            if debug:
                print(f"[Parse Error] Failed to parse record {pmid if 'pmid' in locals() else 'N/A'}: {e}")

    if debug:
        print(f"[Debug] Finished parsing. Found {len(results)} papers with non-academic affiliations.")


    return results
