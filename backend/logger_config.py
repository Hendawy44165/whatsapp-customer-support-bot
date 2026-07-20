import os
import sqlite3
import logging
import threading
import time
import queue
import sys
import structlog
from typing import Optional

class SQLiteBatchLogHandler(logging.Handler):
    """
    A production-grade logging handler that buffers log records in a thread-safe queue
    and writes them in batches to the system_logs table in SQLite in the background.
    """
    def __init__(self, db_path: Optional[str] = None, batch_size: int = 50, flush_interval: float = 2.0):
        super().__init__()
        if db_path:
            self.db_path = db_path
        else:
            db_env = os.getenv("SQLITE_SIM_DB")
            if db_env:
                self.db_path = db_env
            else:
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                self.db_path = os.path.join(backend_dir, "local_supabase_sim.db")
                
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Start background flush thread
        self.worker = threading.Thread(target=self._flush_loop, name="sqlite-logger-worker", daemon=True)
        self.worker.start()

    def emit(self, record):
        try:
            # Store structured details in queue
            log_data = {
                "source": record.name,
                "level": record.levelname,
                "message": self.format(record),
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(record.created))
            }
            self.queue.put(log_data)
        except Exception:
            self.handleError(record)

    def _flush_loop(self):
        while not self.stop_event.is_set():
            time.sleep(self.flush_interval)
            self.flush()

    def flush(self):
        logs = []
        while not self.queue.empty():
            try:
                logs.append(self.queue.get_nowait())
            except queue.Empty:
                break
        
        if not logs:
            return

        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            # Ensure the table is created
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                level TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Bulk insert in a single transaction
            cursor.executemany(
                "INSERT INTO system_logs (source, level, message, created_at) VALUES (?, ?, ?, ?)",
                [(log["source"], log["level"], log["message"], log["created_at"]) for log in logs]
            )
            conn.commit()
        except Exception as e:
            sys.stderr.write(f"SQLiteBatchLogHandler Error: failed to flush logs to SQLite: {e}\n")
        finally:
            if conn:
                conn.close()

    def close(self):
        self.stop_event.set()
        self.flush()
        super().close()


def setup_logging():
    """
    Sets up structlog to output structured JSON logs to standard output (stdio)
    and configures standard Python logging to route all logs to both stdout
    and the SQLiteBatchLogHandler.
    """
    # Configure structlog processors for JSON output
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the standard library root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(logging.INFO)
    
    # Handler 1: StreamHandler to write to stdio (sys.stdout)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(stdout_handler)
    
    # Handler 2: SQLite Batching Handler to write to system_logs in background batches
    sqlite_handler = SQLiteBatchLogHandler()
    sqlite_handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(sqlite_handler)
