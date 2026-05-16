"""
Membra Money Protocol — API Routes
(Re-export of routes from main.py for modularity)
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# Routes are defined in main.py to keep this scaffold simple.
# In a larger app, split them here by domain (claims, reserves, audit, etc.).
