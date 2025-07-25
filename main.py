#!/usr/bin/env python3
"""
Main script for GeoDataReader package.
Example usage of the BroReader functionality.
"""

from BroReader import read_BRO
import pickle
from datetime import date
import argparse
import sys


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Download and read CPTs from BRO')
    parser.add_argument('--x', type=float, default=117769, help='X coordinate (default: 117769)')
    parser.add_argument('--y', type=float, default=439304, help='Y coordinate (default: 439304)')
    parser.add_argument('--radius', type=float, default=1, help='Radius in km (default: 1)')
    parser.add_argument('--output-dir', default='cpts', help='Output directory (default: cpts)')
    parser.add_argument('--start-date', default='2015-01-01', help='Start date (YYYY-MM-DD, default: 2015-01-01)')
    
    args = parser.parse_args()
    
    location = [args.x, args.y]
    radius_distance = args.radius
    start_date = date.fromisoformat(args.start_date) if args.start_date else date(2015, 1, 1)
    
    print(f"Searching for CPTs at location {location} within {radius_distance} km radius")
    print(f"Start date: {start_date}")
    print(f"Output directory: {args.output_dir}")
    
    try:
        c = read_BRO.read_cpts(location, radius_distance, start_date=start_date, output_dir=args.output_dir)
        
        # Save results as pickle
        pickle_file = f'{args.output_dir}/cpts.pickle'
        with open(pickle_file, 'wb') as file:
            pickle.dump(c, file)
        
        print(f"Successfully downloaded {len(c)} CPTs")
        print(f"Results saved to {pickle_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
