#!/usr/bin/env python3
"""Council of Agents - Simple CLI Version."""

import asyncio
import sys
from simple_cli import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)