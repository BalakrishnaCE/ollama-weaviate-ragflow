import sys
from app.weaviate_client.client import get_client

def inspect_sections(limit=5):
    client = get_client()
    section_collection = client.collections.get("Section")
    print(f"Listing first {limit} objects in Section collection:")
    objs = section_collection.query.fetch_objects(limit=limit)
    for i, obj in enumerate(objs.objects):
        print(f"--- Section {i+1} ---")
        # Print all available attributes
        for attr in dir(obj):
            if not attr.startswith("_") and not callable(getattr(obj, attr)):
                try:
                    print(f"{attr}: {getattr(obj, attr)}")
                except Exception:
                    pass
        print("Properties:")
        for k, v in getattr(obj, "properties", {}).items():
            if k == "embedding" and v is not None:
                print(f"  {k}: [vector, len={len(v)}]")
            else:
                print(f"  {k}: {v}")
        print("Metadata:")
        meta = getattr(obj, "metadata", None)
        if meta:
            for k, v in meta.items():
                print(f"  {k}: {v}")
        print()

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    inspect_sections(limit) 