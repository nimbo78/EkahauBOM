from app.services.batch_service import BatchService
from uuid import UUID
import traceback

bs = BatchService()
batch_id = UUID("1ee76339-61d5-4fed-a482-99aef78eb0bc")

print("Testing create_batch_archive...")
try:
    result = bs.create_batch_archive(batch_id)
    print(f"SUCCESS: {result}")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
