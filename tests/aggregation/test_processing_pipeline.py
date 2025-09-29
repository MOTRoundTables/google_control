#!/usr/bin/env python3
"""
Test the actual aggregation pipeline to identify timestamp parsing issues
"""

import sys
sys.path.append('.')

from components.aggregation.pipeline import run_pipeline
import tempfile
import shutil
import os

def test_aggregation_pipeline():
    """Test the full aggregation pipeline with data_test_small.csv"""
    
    input_file = 'test_data/data_test_small.csv'
    
    # Create a temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = os.path.join(temp_dir, 'output')
        
        # Configuration for aggregation
        config = {
            'input_file_path': input_file,
            'output_dir': output_dir,
            'ts_format': '%Y-%m-%d %H:%M:%S',
            'tz': 'Asia/Jerusalem',
            'chunk_size': 50000,
            'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'hours': list(range(24)),
            'min_valid_per_hour': 1,
            'start_date': None,
            'end_date': None,
            'link_whitelist': [],
            'link_blacklist': []
        }
        
        print("Testing aggregation pipeline with configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        
        print(f"\nProcessing file: {input_file}")
        print(f"Output directory: {output_dir}")
        
        try:
            # Run the aggregation pipeline
            result = run_pipeline(config)
            
            print(f"\nProcessing completed!")
            print(f"Result: {result}")
            
            # Check what files were created
            if os.path.exists(output_dir):
                print(f"\nOutput files created:")
                for file in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, file)
                    size = os.path.getsize(file_path)
                    print(f"  {file}: {size} bytes")
            else:
                print(f"\nNo output directory created!")
                
        except Exception as e:
            print(f"\nProcessing failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_aggregation_pipeline()