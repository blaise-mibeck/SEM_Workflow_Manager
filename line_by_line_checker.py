import traceback
import re
import os

filename = "coordinate_matching_test.py"

# First try to find any obvious syntax errors
try:
    with open(filename, 'r') as f:
        content = f.read()
    
    # Test compiling the code to check for syntax errors
    compile(content, filename, 'exec')
    print("Initial syntax check passed")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}, column {e.offset}: {e.text}")
    exit(1)

# Now check class structure and methods
print("\nChecking class structure...")

with open(filename, 'r') as f:
    lines = f.readlines()

# Variables to track indentation and structure
in_class = False
current_class = ""
current_method = ""
method_indentation = 0
expected_methods = [
    "extract_and_log_position_info",
    "crop_session_image",
    "run_template_matching"
]
found_methods = set()

# Check for missing methods or unexpected indentation
for i, line in enumerate(lines):
    line_num = i + 1
    
    # Check for class definitions
    class_match = re.match(r'^class\s+(\w+)', line)
    if class_match:
        in_class = True
        current_class = class_match.group(1)
        print(f"Found class: {current_class}")
        continue
    
    # Check for method definitions within class
    if in_class:
        method_match = re.match(r'^(\s+)def\s+(\w+)\(', line)
        if method_match:
            indent = method_match.group(1)
            method_name = method_match.group(2)
            
            # Check first method indentation
            if not current_method:
                method_indentation = len(indent)
                
            current_method = method_name
            found_methods.add(method_name)
            
            # Check if indentation is consistent
            if len(indent) != method_indentation:
                print(f"WARNING: Method {method_name} at line {line_num} has inconsistent indentation")
                
            # Check for expected methods
            if method_name in expected_methods:
                print(f"Found expected method: {method_name}")
            
            continue
    
    # Check for lines with missing indentation
    if current_method and line.strip() and not line.startswith(' '):
        if not (line.startswith('class') or line.startswith('#') or line.startswith('\n')):
            print(f"ERROR: Line {line_num} should be indented but isn't: {line.strip()}")

# Check if we found all expected methods
missing_methods = [m for m in expected_methods if m not in found_methods]
if missing_methods:
    print(f"\nWARNING: Some expected methods are missing: {missing_methods}")
else:
    print("\nAll expected methods were found.")

print("\nChecking for incomplete methods...")
# Check for any incomplete method blocks (missing indentation)
in_def = False
current_def = ""
def_indentation = 0

for i, line in enumerate(lines):
    line_num = i + 1
    line_text = line.rstrip('\n')
    
    # Check for function/method definitions
    def_match = re.match(r'^(\s*)def\s+(\w+)\(', line)
    if def_match:
        indent = def_match.group(1)
        func_name = def_match.group(2)
        in_def = True
        current_def = func_name
        def_indentation = len(indent)
        continue
    
    # Skip empty lines and comments
    if not line_text.strip() or line_text.strip().startswith('#'):
        continue
    
    # Check if we have an unindented line within a function/method
    if in_def and line_text and not line_text.startswith(' ' * (def_indentation + 4)) and not line_text.startswith((' ' * def_indentation) + 'def'):
        # If this isn't the start of a new function at the same level, it's an error
        if not re.match(r'^(\s*)def\s+(\w+)\(', line_text) and len(line_text.strip()) > 0:
            print(f"Potential issue at line {line_num}: Function '{current_def}' may have an unindented line:")
            print(f"  Line {line_num}: {line_text}")
            print(f"  Expected indentation of at least {def_indentation + 4} spaces")
            
            # Examine a few lines around the problem
            context_start = max(0, i - 3)
            context_end = min(len(lines), i + 4)
            print("\nContext:")
            for ctx_i in range(context_start, context_end):
                prefix = ">" if ctx_i == i else " "
                print(f"{prefix} {ctx_i+1}: {lines[ctx_i].rstrip()}")
            
            in_def = False
            
# Try importing the module (without running the main function)
print("\nAttempting to import the module...")
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("coordinate_matching_test", filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print("Module imported successfully!")
except Exception as e:
    print(f"Import error: {e}")
    traceback.print_exc()

print("\nChecking complete.")
