import weaviate
from weaviate.exceptions import WeaviateBaseError
from weaviate.collections.classes.config import DataType

WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8080
WEAVIATE_GRPC_PORT = 50051

# Initialize Weaviate client (v4.x API)
def get_client():
    return weaviate.connect_to_local(host=WEAVIATE_HOST, port=WEAVIATE_PORT, grpc_port=WEAVIATE_GRPC_PORT)

# Upgraded schema for Department, SOP, Section (2025 best practices)
SCHEMA = [
    ("Department", [
        {"name": "name", "data_type": DataType.TEXT},
    ]),
    ("SOP", [
        {"name": "title", "data_type": DataType.TEXT},
        {"name": "department", "data_type": DataType.TEXT},
        {"name": "version", "data_type": DataType.TEXT},
        {"name": "date", "data_type": DataType.DATE},
    ]),
    ("Section", [
        {"name": "title", "data_type": DataType.TEXT},
        {"name": "section", "data_type": DataType.TEXT},  # e.g., 'Chunk 1', 'Preparation', etc.
        {"name": "content", "data_type": DataType.TEXT},
        {"name": "summary", "data_type": DataType.TEXT},
        {"name": "step_number", "data_type": DataType.INT},
        {"name": "tags", "data_type": DataType.TEXT},
        {"name": "sop", "data_type": DataType.TEXT},
        {"name": "department", "data_type": DataType.TEXT},
        {"name": "embedding", "data_type": DataType.NUMBER_ARRAY},
    ]),
]

def create_schema(client):
    for name, properties in SCHEMA:
        try:
            print(f"[Weaviate] Checking collection: {name}")
            if not client.collections.exists(name):
                print(f"[Weaviate] Creating collection: {name} with properties: {properties}")
                client.collections.create(name, properties=properties)
                print(f"[Weaviate] Created collection: {name}")
            else:
                print(f"[Weaviate] Collection already exists: {name}")
        except Exception as e:
            print(f"[Weaviate] Schema error for {name}: {e}")

# --- Migration helper ---
def migrate_section_schema(client):
    """Upgrade Section schema to include new fields if missing."""
    collection = client.collections.get("Section")
    existing_fields = set([p.name for p in collection.config.properties])
    desired_fields = {p["name"] for p in SCHEMA[2][1]}
    missing = desired_fields - existing_fields
    for field in missing:
        prop = next(p for p in SCHEMA[2][1] if p["name"] == field)
        print(f"[Weaviate] Adding missing field to Section: {field}")
        collection.config.add_property(prop)
    print(f"[Weaviate] Section schema migration complete. Now has: {[p.name for p in collection.config.properties]}")

def recreate_section_collection(client):
    """Drop and re-create the Section collection with the upgraded schema."""
    name = "Section"
    if client.collections.exists(name):
        print(f"[Weaviate] Dropping existing collection: {name}")
        client.collections.delete(name)
    props = [p for p in SCHEMA[2][1]]
    print(f"[Weaviate] Creating collection: {name} with properties: {props}")
    client.collections.create(name, properties=props)
    print(f"[Weaviate] Created collection: {name}")
# Usage: from app.weaviate_client.client import get_client, recreate_section_collection; recreate_section_collection(get_client())

# Example CRUD operation: add a department
def add_department(client, name):
    return client.data_object.create({"name": name}, "Department")

# Add more CRUD functions as needed 