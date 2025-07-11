import os
from pathlib import Path
from app.weaviate_client.client import get_client
from app.ingestion.docx_ingest import ingest_docx

def clear_section_collection():
    client = get_client()
    if "Section" in client.collections.list_all().keys():
        print("Dropping Section collection...")
        client.collections.delete("Section")
        print("Section collection dropped.")
    else:
        print("Section collection does not exist.")

def batch_ingest_all():
    base_dirs = ["Docs/BDM", "Docs/PreSales"]
    for base_dir in base_dirs:
        for fname in os.listdir(base_dir):
            if fname.endswith(".docx"):
                fpath = os.path.join(base_dir, fname)
                print(f"Ingesting {fpath} ...")
                ingest_docx(fpath)
    print("Batch ingestion complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_section_collection()
    batch_ingest_all() 