import requests
import json
import time
import markdownify
# import pickle
import os
import sys
import logging
logging.basicConfig(level=logging.INFO)
from datetime import datetime, timezone

from google.cloud import firestore
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

# add src for local imports
absolute_path = os.path.dirname(__file__)
relative_path = "../"
full_path = os.path.realpath(os.path.join(absolute_path, relative_path))
sys.path.append(full_path)

from utils.config import Config
from utils.utility import get_default_embedding_func, log_to_bigquery, get_pickle_from_gcs, upload_pkl_file, process_embeddings, upload_json_file_combined_data
from utils.turbopuffer_helpers import TurbopufferHelpers

# Getting Firestore client and setting project, bucket, prefix parameters
project_id = os.getenv("PROJECT_ID")
bucket_name = os.getenv("BUCKET_NAME")
pkl_file_name = os.getenv("PICKLE_FILE")
application_name = os.getenv("APPLICATION_NAME")
job_type = application_name + "_" + os.getenv("JOB_TYPE")
api_env = os.getenv("API_ENV")
alias_name = os.getenv("ALIAS_NAME")
index_name = os.getenv("INDEX_NAME")
log_table_id = os.getenv("LOG_TABLE_ID")
job_name = job_type.replace("_", "-") + f"-{api_env}"
embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
webhook_url = os.getenv("ALERT_WEBHOOK_URL")
# firestore_collection = job_type + "_" + api_env
# firestore_collection_acs = os.getenv("COLLECTION_NAME_ACS") + "_" + api_env

# db = firestore.Client(project=project_id)
firestore_db = firestore.Client(project=project_id)

# Start time of the first task
start_time = time.time()
start_time_string = datetime.utcfromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# Get OAuth2 access token for API request
def get_access_token(client_id, client_secret):
    response = requests.post(
        Config.fetch('koodo-api-token-url'),
        data={"grant_type": "client_credentials", "scope": "read"},
        auth=(client_id, client_secret),
        # proxies={'http': os.getenv('HTTP_PROXY'), 'https': os.getenv('HTTPS_PROXY')}
    )
    return response.json()['access_token']

# make a GET request to get community articles
def get_articles(access_token, url):
    articles = []
    page = 1
    pageSize = 100
    while True:
        response = requests.get(
            url,
            params={"page": page, "pageSize": pageSize},
            headers={"Authorization": f"Bearer {access_token}"},
            # proxies={'http': os.getenv('HTTP_PROXY'), 'https': os.getenv('HTTPS_PROXY')}
        )
        articles.extend(response.json()['result'])
        if response.json()['result'] == []:
            break
        else:
            page += 1
    return articles

#GET request for koodo commerce
def get_koodo_commerce_and_marketing(language, url):
    response = requests.get(
            f"{url}lang={language}",
            auth=(Config.fetch('koodo-commerce-api-username'), Config.fetch('koodo-commerce-api-password')),
        )

    return response.json()['data']

# get all content categories
def get_categories(access_token, url):
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        # proxies={'http': os.getenv('HTTP_PROXY'), 'https': os.getenv('HTTPS_PROXY')}
    )
    return response.json()['result']


try:
    source_server_url = 'https://www.koodomobile.com/static/help/api/articles'
    # get help articles
    response = requests.get(source_server_url)
    koodo = response.json()
    untagged_articles = []
    koodo = [art for art in [article if "articleCategory" in article.keys() else untagged_articles.append(article) for article in koodo['data']] if art is not None]
    print(f"Number of Koodo Articles: {len(koodo)}")
    
    print(f"metadata keys: {koodo[0].keys()}")
    
    if len(untagged_articles) > 0:
        print(f"Number of untagged articles: {len(untagged_articles)}")
        print(f"Untagged articles: {[article['url'] for article in untagged_articles]}")

    # get koodo commerce and marketing data
    urls_to_iterate = [
    "https://staging.www.koodomobile.com/api/commerce-postpaid/gen-ai/phones?",
    "https://staging.www.koodomobile.com/api/commerce-postpaid/gen-ai/marketing?",
    "https://staging.www.koodomobile.com/api/commerce-postpaid/gen-ai/prepaid-phones?",
    "https://staging.www.koodomobile.com/api/commerce-postpaid/gen-ai/watches?"
]
    dict_map = {"en":urls_to_iterate, "fr":urls_to_iterate}
    commerce_and_marketing_data = []
    for lang, urls in dict_map.items():
        for url in urls:
            comm_data = get_koodo_commerce_and_marketing(lang, url)
            print(f"Fetched {len(comm_data)} items from {url} in {lang} language.")
            commerce_and_marketing_data.extend(comm_data)
    print(f"Total commerce and marketing data fetched: {len(commerce_and_marketing_data)}")


    en_token = get_access_token(Config.fetch('en-koodo-client-id'), Config.fetch('en-koodo-client-secret'))
    fr_token = get_access_token(Config.fetch('fr-koodo-client-id'), Config.fetch('fr-koodo-client-secret'))

    # get community articles
    en_articles = get_articles(en_token, Config.fetch('koodo-api-articles-url'))
    fr_articles = get_articles(fr_token, Config.fetch('koodo-api-articles-url'))
    # en_categories = get_categories(en_token, Config.fetch('koodo-api-categories-url'))
    # fr_categories = get_categories(fr_token, Config.fetch('koodo-api-categories-url'))

    # print community articles that don't have moderator tags
    # english
    en_articles_without_mod_tag = [article for article in en_articles if article['moderatorTags'] == [] and article['status'] == 'published' and 'mobile-masters-group' not in article['seoCommunityUrl']]
    print(f"number of community EN articles without a moderator tag: {len(en_articles_without_mod_tag)}")
    print(f"community EN articles without a moderator tag: {[article['title'] for article in en_articles_without_mod_tag]}")
    # french
    fr_articles_without_mod_tag = [article for article in fr_articles if article['moderatorTags'] == [] and article['status'] == 'published']
    print(f"number of community FR articles without a moderator tag: {len(fr_articles_without_mod_tag)}")
    print(f"community FR articles without a moderator tag: {[article['title'] for article in fr_articles_without_mod_tag]}")

    # exclude articles that are not published or are part of the mobile masters group and don't have moderator tags
    en_articles = [article for article in en_articles if article['moderatorTags'] != [] and article['status'] == 'published' and 'mobile-masters-group' not in article['seoCommunityUrl']]
    fr_articles = [article for article in fr_articles if article['moderatorTags'] != [] and article['status'] == 'published']

    print(f"Number of English documents: {len(en_articles)}")
    print(f"Number of French documents: {len(fr_articles)}")

    # Help Articles
    langchain_docs = []
    exclude_content = set(["https://www.koodomobile.com/en/help/motorola-one-5g-ace-gift-with-purchase-faqs","https://www.koodomobile.com/fr/help/motorola-one-5g-ace-gift-with-purchase-faqs",
            "https://www.koodomobile.com/en/help/ccts",
            "https://www.koodomobile.com/fr/help/ccts",
            "https://community.koodomobile.com/online-orders-232909/when-is-my-order-going-to-arrive-7808174",
            "https://community.koodomobile.com/plans-services-232910/set-up-and-tips-for-traveling-with-your-mobile-device-7811368?postid=19916237#post19916237",
            "https://communaute.koodomobile.com/depannage-90128/configuration-et-conseils-pour-voyager-avec-votre-appareil-mobile-7793316",
            "https://community.koodomobile.com/new-to-koodo-232907/how-to-pay-your-koodo-account-7811897",
            "https://communaute.koodomobile.com/gestion-de-compte-90129/comment-regler-votre-compte-koodo-7794424",
            "https://community.koodomobile.com/plans-services-232910/make-a-call-or-send-a-text-when-traveling-7811507",
            "https://communaute.koodomobile.com/depannage-90128/faire-un-appel-ou-envoyer-un-texto-en-voyage-7793356",
            "https://communaute.koodomobile.com/depannage-90128/mon-telephone-est-il-deja-deverrouille-7793122",
            "https://community.koodomobile.com/device-phone-support-232908/is-my-phone-already-unlocked-7808096",
            "https://community.koodomobile.com/plans-services-232910/troubleshoot-mobile-phone-problems-when-traveling-7811427",
            "https://communaute.koodomobile.com/depannage-90128/resoudre-les-problemes-des-telephones-mobiles-en-voyage-7793231",
            "https://community.koodomobile.com/device-phone-support-232908/stir-shaken-feature-for-mobile-devices-7810686",
            "https://communaute.koodomobile.com/confidentialite-securite-et-fraude-90130/fonction-stir-shaken-pour-les-appareils-mobiles-7793067"])
    
    for d in koodo:
        if d['url'] in exclude_content:
            print(f"Skipping article: {d['url']}")
            continue
            
        if "content" not in d  :
            continue
       
        langchain_docs.append(
            Document(
                # removed .replace('\n\n', ' ') as recursive splitter uses that as a seperator
                page_content = markdownify.markdownify(d['content'].replace('_', '').strip(),  heading_style="ATX", strip = ['img'] ),
                metadata = {
                    "page_title": d['title'],
                    "source": d['url'],
                    # "category": d['articleCategory'] if 'articleCategory' in d else ["postpaid","prepaid","internet"],
                    "category": d['articleCategory'],
                    "language": d['language'],
                }
            )
        )

    # Community Articles
    for d in en_articles:
        if "https://community.koodomobile.com" + d['seoCommunityUrl'] in exclude_content:
            print(f"Skipping community article: https://community.koodomobile.com{d['seoCommunityUrl']}")
            continue

        langchain_docs.append(
            Document(
                # removed .replace('\n\n', ' ') as recursive splitter uses that as a seperator
                page_content = markdownify.markdownify(d['content'].replace('_', '').strip(),  heading_style="ATX", strip = ['img'] ),
                metadata = {
                    "page_title": d['title'],
                    "source": "https://community.koodomobile.com" + d['seoCommunityUrl'],
                    "category": list(map(str.lower, d['moderatorTags'])),
                    "language": "en",
                }
            )
        )

    for d in fr_articles:
        if "https://communaute.koodomobile.com" + d['seoCommunityUrl'] in exclude_content:
            print(f"Skipping article: https://communaute.koodomobile.com{d['seoCommunityUrl']}")
            continue

        langchain_docs.append(
            Document(
                # removed .replace('\n\n', ' ') as recursive splitter uses that as a seperator
                page_content = markdownify.markdownify(d['content'].replace('_', '').strip(),  heading_style="ATX", strip = ['img'] ),
                metadata = {
                    "page_title": d['title'],
                    "source": "https://communaute.koodomobile.com" + d['seoCommunityUrl'],
                    "category": list(map(str.lower, d['moderatorTags'])),
                    "language": "fr",
                }
            )
        )

    # Append commerce and Marketing pages
    for comm_data in commerce_and_marketing_data:
        page_content = comm_data['content']
        langchain_docs.append(
                Document(
                    page_content = markdownify.markdownify(page_content).replace("=", ""),
                    metadata = {
                        "page_title": comm_data['title'],
                        "source" : comm_data['url']  ,
                        "language" : comm_data['language'],
                        "category" : comm_data['articleCategory'],
                        }
                    )
                )
    print(f"Number of commerce and marketing documents added to the langchain docs: {len(commerce_and_marketing_data)}")

    # Go through all documents, combine page content and metadata into a single JSON and upload to GCS
    final_json_list = [{ "page_content": doc.page_content, "metadata": doc.metadata } for doc in langchain_docs]
    filepath = f"{api_env}/src_json_combined/{application_name}_source_data_{run_date}.json"
    upload_json_file_combined_data(project_id, bucket_name, final_json_list, filepath)
    logging.info("Uploaded combined source data JSON to GCS")

    # Create source chunks from the documents
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        # ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)
    md_header_splits = markdown_splitter.split_text([(doc.page_content) for doc in  langchain_docs][0])

    markdown_docs = []
    count = 0
    for doc_num in range(len(langchain_docs)):
        md_header_splits = markdown_splitter.split_text(langchain_docs[doc_num].page_content)
        for md_doc in md_header_splits:
            md_doc.metadata = langchain_docs[doc_num].metadata
        count+=1
        markdown_docs+=md_header_splits

    recursive_text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1200,
        chunk_overlap=100,
        encoding_name="cl100k_base"
    )

    # recursive_text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size = 1500,
    #     chunk_overlap  = 50,
    #     length_function = len,
    # )
    print(f"Number of documents: {len(langchain_docs)}")
    print(f"Number of markdown documents: {len(markdown_docs)}")
    md_source_chunks_token = recursive_text_splitter.split_documents(markdown_docs)
    print(f"Number of source chunk tokens: {len(md_source_chunks_token)}")
    md_source_chunks_token_filtered = [d for d in md_source_chunks_token if len(d.page_content) > 10 and len(set(d.page_content)) > 2]
    print(f"Number of source chunk tokens after filtering: {len(md_source_chunks_token_filtered)}")
    loading_time = time.time()

    # Re-create page_content by appending page_title and fields_subTitle to beginning of page_content
    for doc in md_source_chunks_token_filtered:
        doc.page_content = f"# {doc.metadata['page_title']}\n\n{doc.page_content}"

    # Convert source chunks to dictionary format for process embeddings method
    docs = {}
    for chunk in md_source_chunks_token_filtered:
        docs[chunk.page_content] = chunk

    # Get the embedding function
    embedding_func = get_default_embedding_func(model=embedding_model_name, openai_api_key=Config.fetch("litellm-proxy-key-aia-koodo"))

    start_time_embedding = time.time()

    # Load in docs and embeddings from pkl file if it exists:
    pkl_file = get_pickle_from_gcs(project_id, bucket_name, pkl_file_name)

    # if no pkl file found, generate new embeddings for all documents. If the pkl file is found, load the existing embeddings
    if pkl_file is not None:
        logging.info("Pickle file loaded successfully.")
        embedding_dict = {doc.page_content: embedding for doc, embedding in zip(pkl_file['docs'], pkl_file['embeddings'])}
    else:
        embedding_dict = {} # intialize an empty dictionary to hold document and embedding pairs
        logging.info("Failed to load pickle file or file doesn't exist.")

    new_embeddings_dict, new_embed_count = process_embeddings(docs, embedding_func=embedding_func, embedding_dict=embedding_dict)

    logging.info(f"Total embeddings: {len(new_embeddings_dict)}")
    logging.info(f"New embeddings created: {new_embed_count}")

    # get docs ordered according to new embeddings list for turbopuffer upload
    embedded_chunks_list = [docs[key] for key in new_embeddings_dict.keys()]
    embeddings_list = list(new_embeddings_dict.values())

    # Write pickle file to GCS
    source_docs = {
        'docs': embedded_chunks_list,
        'embeddings': embeddings_list
    }

    logging.info("Finished processing chunks.")
    end_time_embedding = time.time()
    logging.info(f"Pickle file processing time: {end_time_embedding - start_time_embedding} seconds")

    upload_pkl_file(project_id, bucket_name, source_docs=source_docs, destination_file_name=pkl_file_name)

    # Clean up memory before turbopuffer upload
    del source_docs
    del pkl_file
    del new_embeddings_dict
    del final_json_list

    embedding_time = time.time()
    embedding_duration = int(embedding_time - loading_time)
    logging.info(f"Embedded docs in {embedding_duration} seconds")

    index_name += f"-{start_time_string}".replace(":", "-").replace(" ", "-")

    aia_client_id = Config.fetch('aia-client-id')
    namepace_name = f"{aia_client_id}-{embedding_model_name}-{index_name}"
    # Upload to turbopuffer
    tpuf_helpers = TurbopufferHelpers()
    tpuf_namespaces = tpuf_helpers.get_namespaces()
    namespace_index_name = os.getenv("INDEX_NAME")
    delete_namespaces = [ns for ns in tpuf_namespaces if ns.startswith(f"{aia_client_id}-{embedding_model_name}-{namespace_index_name}")]
    # Get prev namespace of previous run to delete 
    tpuf_upload, err = tpuf_helpers.from_documents(
                                        namespace = namepace_name,
                                        documents=embedded_chunks_list, 
                                        embeddings_list=embeddings_list,
                                        embedding_model = embedding_model_name
                                    )

    if err:
        logging.error(f"Error uploading to turbopuffer: {err}")
        raise Exception(f"Error uploading to turbopuffer: {err}")
    else:
        logging.info(f"Uploaded to turbopuffer: {tpuf_upload}")
        # Attempt to create or update the alias
        alias_success = False
        
        # Try creating alias first
        try:
            create_alias = tpuf_helpers.create_alias(namespace=namepace_name, alias=alias_name, embedding_model=embedding_model_name)
            if create_alias:
                logging.info(f"Created alias: {alias_name}")
                alias_success = True
            else:
                logging.warning("Failed to create alias, will try updating instead")
        except ValueError as create_err:
            logging.warning(f"Error creating alias: {create_err}, will try updating instead")
        
        # If creation failed, try updating
        if not alias_success:
            try:
                update_alias = tpuf_helpers.update_alias(namespace=namepace_name, alias=alias_name, embedding_model=embedding_model_name)
                if update_alias:
                    logging.info(f"Updated alias: {alias_name}")
                    alias_success = True
                else:
                    logging.error("Failed to update alias")
            except ValueError as update_err:
                logging.error(f"Error updating alias: {update_err}")
        
        # Only raise error if both operations failed
        if not alias_success:
            raise ValueError("Both create and update alias operations failed")

        # Clean up old namespaces after successful alias operation
        logging.info(f"Deleting previous namespaces: {delete_namespaces}")
        for ns in delete_namespaces: # Delete firestore doc in brain-turbopuffer-namespace-client-id
            tpuf_helpers.delete_namespace(ns)
            namespace_doc_ref = firestore_db.collection(Config.fetch("turbopuffer-client-id-firestore-collection")).document(ns)
            namespace_doc_ref.delete()

    # Add to firestore db
    tpuf_firestore_data ={
                            "admin": [aia_client_id],
                            "write": [],
                            "read": [],
                            "user": "AIA", # First user to create the namespace is essentially the owner
                            "email": "AIA",
                            "embedding_model": embedding_model_name
                        }
    tpuf_doc_ref = firestore_db.collection(Config.fetch("turbopuffer-client-id-firestore-collection")).document(namepace_name)
    tpuf_doc_ref.set(tpuf_firestore_data)

    end_time = time.time()
    end_time_string = datetime.utcfromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
    time_taken = int(end_time - start_time)
    log_entry = {
        'application_name': application_name,
        'job_name': job_name,
        'start_timestamp': start_time_string,
        'end_timestamp': end_time_string,
        'duration_in_seconds': time_taken,
        'num_embeddings': len(embeddings_list),
        'num_new_embeddings': new_embed_count,
        'input_file': source_server_url,
        'output': [{'type': 'turbopuffer', 'name': namepace_name}],
        'status': 'success',
        'error': None
    }
    log_to_bigquery(project_id, 'logs', log_table_id, log_entry)
except Exception as e:
    end_time = time.time()
    end_time_string = datetime.utcfromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
    time_taken = int(end_time - start_time)
    log_entry = {
        'application_name': application_name,
        'job_name': job_name,
        'start_timestamp': start_time_string,
        'end_timestamp': end_time_string,
        'duration_in_seconds': time_taken,
        'num_embeddings': None,
        'input_file': None,
        'output': None,
        'status': 'failed',
        'error': str(e)
    }
    log_to_bigquery(project_id, 'logs', log_table_id, log_entry)
    # Send alert to chat
    # send_alert_to_chat(log_entry, webhook_url)
