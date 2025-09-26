#!/usr/bin/env python3
"""
Quick Setup Script - Alternative setup for utils/setup directory
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import the main setup script
from setup import main

if __name__ == "__main__":
    main()