import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "Docs"

class DocxEventHandler(FileSystemEventHandler):
    def __init__(self, ingest_callback):
        super().__init__()
        self.ingest_callback = ingest_callback

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".docx"):
            self.ingest_callback(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".docx"):
            self.ingest_callback(event.src_path)

def start_watcher(ingest_callback):
    event_handler = DocxEventHandler(ingest_callback)
    observer = Observer()
    observer.schedule(event_handler, str(DOCS_DIR), recursive=True)
    observer.start()
    print(f"Watching {DOCS_DIR} for DOCX changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 