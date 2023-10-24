#!/usr/bin/env python3
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma
from langchain.llms import GPT4All, LlamaCpp
import chromadb
import os
import argparse
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for

app = Flask(__name__)

if not load_dotenv():
    print("Could not load .env file or it is empty. Please check if it exists and is readable.")
    exit(1)

embeddings_model_name = os.environ.get("EMBEDDINGS_MODEL_NAME")
persist_directory = os.environ.get('PERSIST_DIRECTORY')

model_type = os.environ.get('MODEL_TYPE')
model_path = os.environ.get('MODEL_PATH')
model_n_ctx = os.environ.get('MODEL_N_CTX')
model_n_batch = int(os.environ.get('MODEL_N_BATCH',8))
target_source_chunks = int(os.environ.get('TARGET_SOURCE_CHUNKS',4))

from constants import CHROMA_SETTINGS

async def chatter(query_msg):
    # Parse the command line arguments
    args = parse_arguments()
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)
    chroma_client = chromadb.PersistentClient(settings=CHROMA_SETTINGS , path=persist_directory)
    db = Chroma(persist_directory=persist_directory, embedding_function=embeddings, client_settings=CHROMA_SETTINGS, client=chroma_client)
    retriever = db.as_retriever(search_kwargs={"k": target_source_chunks})
    # activate/deactivate the streaming StdOut callback for LLMs
    callbacks = [] if args.mute_stream else [StreamingStdOutCallbackHandler()]
    # Prepare the LLM
    match model_type:
        case "LlamaCpp":
            llm = LlamaCpp(model_path=model_path, max_tokens=model_n_ctx, n_batch=model_n_batch, callbacks=callbacks, verbose=False)
        case "GPT4All":
            llm = GPT4All(model=model_path, max_tokens=model_n_ctx, backend='gptj', n_batch=model_n_batch, callbacks=callbacks, verbose=False)
        case _default:
            # raise exception if model_type is not supported
            raise Exception(f"Model type {model_type} is not supported. Please choose one of the following: LlamaCpp, GPT4All")

    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents= not args.hide_source)
    # Interactive questions and answers
    # while True:
    #     # query = input("\nEnter a query: ")
    #     query = query_msg
    #     print("Please wait, returning an answer may take up to 5 minutes")
    #     if query == "exit":
    #         break
    #     if query.strip() == "":
    #         continue

    #     # Get the answer from the chain
    #     start = time.time()
    #     res = qa(query)
    #     answer, docs = res['result'], [] if args.hide_source else res['source_documents']
    #     end = time.time()

    #     # Print the result
    #     print("\n\n> Question:")
    #     print(query)
    #     print(f"\n> Answer (took {round(end - start, 2)} s.):")
    #     print(answer)


    # query = input("\nEnter a query: ")
    query = query_msg
    print("Please wait, returning an answer may take up to 5 minutes")
    # if query == "exit":
    #     break
    # if query.strip() == "":
    #     continue

    # Get the answer from the chain
    start = time.time()
    res = qa(query)
    answer, docs = res['result'], [] if args.hide_source else res['source_documents']
    end = time.time()

    # Print the result
    print("\n\n> Question:")
    print(query)
    print(f"\n> Answer (took {round(end - start, 2)} s.):")
    print(answer)
    return str(answer)


        # Print the relevant sources used for the answer
        # for document in docs:
        #     print("\n> " + document.metadata["source"] + ":")
        #     print(document.page_content)

def parse_arguments():
    parser = argparse.ArgumentParser(description='privateGPT: Ask questions to your documents without an internet connection, '
                                                 'using the power of LLMs.')
    parser.add_argument("--hide-source", "-S", action='store_true',
                        help='Use this flag to disable printing of source documents used for answers.')

    parser.add_argument("--mute-stream", "-M",
                        action='store_true',
                        help='Use this flag to disable the streaming StdOut callback for LLMs.')

    return parser.parse_args()

# @app.route('/', methods=['GET'])
# def handle_get_request():
#     return "This is the response to a GET request."

@app.route('/', methods=['POST'])
def handle_post_request():
    return "This is the response to a POST request."

# http://127.0.0.1:5000/get_response?sentence=What+is+the+village+of+Amelia
@app.route('/get_response', methods=['GET'])
async def get_response():

    # Get the 'sentence' query parameter from the request
    sentence = str(request.args.get('sentence', 'No sentence provided.'))
    print("Request: " + sentence)

    try:
        response = await chatter(sentence)
        # return f"Received response: {response}"
        # return jsonify({"response": response})
        return redirect(url_for('index', response=response))
    except Exception as e:
        # return jsonify({"error": str(e)}), 500
        return redirect(url_for('index', response=str(e)))




@app.route('/')
def index():
    response = request.args.get('response')
    return render_template('index.html', response=response)

if __name__ == "__main__":
    # Run on localhoast
    app.run(host='127.0.0.1', port=5000)

    # Run on external IP
    # app.run(host='0.0.0.0', port=5000)    
