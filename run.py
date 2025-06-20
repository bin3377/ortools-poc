#!/usr/bin/env python3
"""
Convenience script to run the FastAPI server
"""

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=port, reload=True, log_level="info"
    )
