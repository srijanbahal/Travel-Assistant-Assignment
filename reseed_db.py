"""
Utility script to manually re-seed the database with fresh data.
Run this when you want to reset the database with new mock data.
"""
from data.init_db import init_db

if __name__ == "__main__":
    print("=" * 50)
    print("MANUAL DATABASE RE-SEED")
    print("=" * 50)
    init_db(force_reseed=True)
    print("\nDatabase has been reset with fresh mock data!")
