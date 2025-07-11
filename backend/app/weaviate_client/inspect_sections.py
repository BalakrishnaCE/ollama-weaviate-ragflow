import weaviate

WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8080
WEAVIATE_GRPC_PORT = 50051

# v4.x API
client = weaviate.connect_to_local(host=WEAVIATE_HOST, port=WEAVIATE_PORT, grpc_port=WEAVIATE_GRPC_PORT)

section_collection = client.collections.get("Section")

print("Sample Section objects from Weaviate:")
result = section_collection.query.fetch_objects(limit=5, return_properties=["title", "content", "sop", "embedding"])
for obj in result.objects:
    print("- Title:", obj.properties.get("title"))
    print("  SOP:", obj.properties.get("sop"))
    print("  Content:", obj.properties.get("content"))
    embedding = obj.properties.get("embedding")
    if embedding is not None:
        print(f"  Embedding: [len={len(embedding)}] {embedding[:5]}...{embedding[-5:] if len(embedding) > 10 else ''}")
    else:
        print("  Embedding: None")
    print() 