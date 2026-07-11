import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.agents.middleware import ModelRequest, dynamic_prompt

print("ModelRequest attributes:", dir(ModelRequest))
print("dynamic_prompt details:", type(dynamic_prompt))
