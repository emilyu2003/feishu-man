print("===START===")
import sys
print("Python:", sys.version)
import os
os.environ['PYTHONPATH'] = 'd:/miao/opencode/feishu-man'
sys.path.append('d:/miao/opencode/feishu-man')
print("Path configured")
from src.main import main
print("Import done")
import asyncio
print("Running main...")
asyncio.run(main())
print("===END===")