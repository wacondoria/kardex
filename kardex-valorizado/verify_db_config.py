import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from models.database_model import engine

def verify_engine_config():
    print(f"Pool size: {engine.pool.size()}")
    print(f"Max overflow: {engine.pool._max_overflow}")
    print(f"Pool recycle: {engine.pool._recycle}")
    
    # Note: SQLite default pool might not show these exactly if not using QueuePool, 
    # but we want to verify the arguments were passed. 
    # Actually, create_engine with sqlite usually uses SingletonThreadPool or NullPool unless specified.
    # However, if the user requested these params, they might be using a different setup or expecting QueuePool.
    # Let's check if the pool has these attributes.
    
    try:
        if engine.pool.size() == 20:
            print("SUCCESS: Pool size is 20")
        else:
            print(f"FAILURE: Pool size is {engine.pool.size()}, expected 20")
            
        if engine.pool._max_overflow == 30:
            print("SUCCESS: Max overflow is 30")
        else:
            print(f"FAILURE: Max overflow is {engine.pool._max_overflow}, expected 30")
            
        if engine.pool._recycle == 3600:
             print("SUCCESS: Pool recycle is 3600")
        else:
             print(f"FAILURE: Pool recycle is {engine.pool._recycle}, expected 3600")

    except Exception as e:
        print(f"Error checking pool config: {e}")
        # If it's SingletonThreadPool, it might not have size() in the same way or ignore it.
        print(f"Pool class: {type(engine.pool)}")

if __name__ == "__main__":
    verify_engine_config()
