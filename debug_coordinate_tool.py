import traceback

try:
    import coordinate_matching_test
    coordinate_matching_test.main()
except Exception as e:
    print("ERROR: Program failed to start!")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nTraceback:")
    traceback.print_exc()
