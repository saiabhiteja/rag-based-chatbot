from langchain_community.document_loaders.pdf import PyPDFDirectoryLoader
import streamlit as st
import hashlib
from langchain.embeddings.openai import OpenAIEmbeddings
from pinecone import Pinecone
from openai import OpenAI



def read_doc(directory: str) -> list[str]:
    # Initialize a PyPDFDirectoryLoader object with the given directory
    file_loader = PyPDFDirectoryLoader(directory)

    # Load PDF documents from the directory
    documents = file_loader.load()

    # Extract only the page content from each document
    page_contents = [doc.page_content for doc in documents]

    return page_contents

def chunk_text_for_list(docs: list[str], max_chunk_size: int = 1000) -> list[list[str]]:
    def chunk_text(text: str, max_chunk_size: int) -> list[str]:
        # Ensure each text ends with a double newline to correctly split paragraphs
        if not text.endswith("\n\n"):
            text += "\n\n"
        # Split text into paragraphs
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        # Iterate over paragraphs and assemble chunks
        for paragraph in paragraphs:
            # Check if adding the current paragraph exceeds the maximum chunk size
            if (
                len(current_chunk) + len(paragraph) + 2 > max_chunk_size
                and current_chunk
            ):
                # If so, add the current chunk to the list and start a new chunk
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # Add the current paragraph to the current chunk
            current_chunk += paragraph.strip() + "\n\n"
        # Add any remaining text as the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    # Apply the chunk_text function to each document in the list
    return [chunk_text(doc, max_chunk_size) for doc in docs]


# You can use my API key
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
EMBEDDINGS = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

def generate_embeddings(documents: list[any]) -> list[list[float]]:
    embedded = [EMBEDDINGS.embed_documents(doc) for doc in documents]
    return embedded



def generate_short_id(content: str) -> str:
    hash_obj = hashlib.sha256()
    hash_obj.update(content.encode("utf-8"))
    return hash_obj.hexdigest()


def combine_vector_and_text(
    documents: list[any], doc_embeddings: list[list[float]]
) -> list[dict[str, any]]:
    data_with_metadata = []

    for doc_text, embedding in zip(documents, doc_embeddings):
        # Convert doc_text to string if it's not already a string
        if not isinstance(doc_text, str):
            doc_text = str(doc_text)

        # Generate a unique ID based on the text content
        doc_id = generate_short_id(doc_text)

        # Create a data item dictionary
        data_item = {
            "id": doc_id,
            "values": embedding[0],
            "metadata": {"text": doc_text},  # Include the text as metadata
        }

        # Append the data item to the list
        data_with_metadata.append(data_item)

    return data_with_metadata


# Obtain your own pinecone key
PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
pc = Pinecone(api_key=PINECONE_API_KEY)
# Place the own index we created earlier
index = pc.Index("ghw-rag-aiml")

def upsert_data_to_pinecone(data_with_metadata: list[dict[str, any]]) -> None:
    index.upsert(vectors=data_with_metadata)

#Call the function
#upsert_data_to_pinecone(data_with_metadata= data_with_meta_data)

def get_query_embeddings(query: str) -> list[float]:
    query_embeddings = EMBEDDINGS.embed_query(query)
    return query_embeddings

# Call the function

def query_pinecone_index(
    query_embeddings: list, top_k: int = 2, include_metadata: bool = True
) -> dict[str, any]:
    query_response = index.query(
        vector=query_embeddings, top_k=top_k, include_metadata=include_metadata
    )
    return query_response

# Call the function

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
def generate_answer(answers: dict[str, any], prompt) -> str:
  client = OpenAI(api_key=OPENAI_API_KEY)
  text_content = answers['matches'][0]['metadata']['text']

  completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
          {"role": "developer", "content": text_content},
          {
              "role": "user",
              "content": "With the given context provide a better answer to the question: " + prompt,

          }
      ]
  )

  st.write(completion.choices[0].message)