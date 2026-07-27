import queue
from PySide6.QtCore import QThread, Signal, Slot
from ai.clip_vector_db import ClipVectorDB

class VectorIndexingWorker(QThread):
    # Signals
    indexing_completed = Signal(int)       # incident_id
    search_results = Signal(list)          # list of matched incidents
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.running = True
        self.db = None

    def run(self):
        print("[VectorIndexingWorker] Starting vector indexing thread...")
        try:
            self.db = ClipVectorDB()
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize Vector DB: {e}")
            return

        while self.running:
            try:
                task = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            task_type = task[0]

            if task_type == "INDEX":
                _, incident_id, snapshot_path, explanation = task
                try:
                    success = self.db.index_incident(incident_id, snapshot_path, explanation)
                    if success:
                        self.indexing_completed.emit(incident_id)
                except Exception as e:
                    print(f"[VectorIndexingWorker] Indexing error: {e}")
                    self.error_occurred.emit(str(e))

            elif task_type == "SEARCH":
                _, query_text = task
                try:
                    results = self.db.query_semantic(query_text)
                    self.search_results.emit(results)
                except Exception as e:
                    print(f"[VectorIndexingWorker] Search error: {e}")
                    self.error_occurred.emit(str(e))

            self.task_queue.task_done()

        print("[VectorIndexingWorker] Thread stopped.")

    @Slot(int, str, str)
    def enqueue_index_task(self, incident_id: int, snapshot_path: str, explanation: str):
        """Pushes an incident's frame and telemetry to the CLIP embedding queue."""
        if not self.running:
            return
        self.task_queue.put(("INDEX", incident_id, snapshot_path, explanation))

    @Slot(str)
    def trigger_search(self, query_text: str):
        """Dispatches a semantic search query command to the vector thread."""
        if not self.running:
            return
        self.task_queue.put(("SEARCH", query_text))

    def stop(self):
        self.running = False
        self.wait()
