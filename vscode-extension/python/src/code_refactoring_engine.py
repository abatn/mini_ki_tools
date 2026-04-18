# ~/mini_ki_tools/src/code_refactoring_engine.py

import ast
import os

class CodeRefactoringEngine:
    def extract_function(self, code, line_start, line_end, new_func_name):
        # Parse the source code into an AST
        tree = ast.parse(code)
        
        # Find the relevant lines
        relevant_lines = code.splitlines()[line_start-1:line_end]
        func_body = '\n'.join(relevant_lines).strip()
        
        # Create a new function definition
        new_func_def = f"def {new_func_name}():\n    {func_body}"
        
        # Add the new function to the AST
        tree.body.append(ast.parse(new_func_def))
        
        # Return the modified source code as a string
        return ast.unparse(tree)

    def rename_symbol(self, code, old_name, new_name, file_paths):
        # Parse the source code into an AST
        tree = ast.parse(code)
        
        # Rename the symbol in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == old_name:
                node.id = new_name
        
        # Return the modified source code as a string
        return ast.unparse(tree)

    def update_imports(self, file_paths):
        for file_path in file_paths:
            with open(file_path, 'r') as file:
                code = file.read()
            
            tree = ast.parse(code)
            
            # Update imports (example: add import statement if not present)
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            updated_code = self._update_imports(tree, module_name)
            
            with open(file_path, 'w') as file:
                file.write(updated_code)

    def _update_imports(self, tree, module_name):
        # Example: Add import statement if not present
        import_added = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                import_added = True
                break
        
        if not import_added:
            import_node = ast.ImportFrom(module=module_name, names=[ast.alias(name='*', asname=None)], level=0)
            tree.body.insert(0, import_node)
        
        return ast.unparse(tree)

# Example usage
if __name__ == "__main__":
    code_refactoring_engine = CodeRefactoringEngine()
    
    # Extract function example
    code = """
def main():
    print("Hello, world!")
    print("This is a test.")
"""
    new_code = code_refactoring_engine.extract_function(code, 2, 3, "greet")
    print(new_code)
    
    # Rename symbol example
    code = """
x = 10
print(x)
"""
    new_code = code_refactoring_engine.rename_symbol(code, 'x', 'y')
    print(new_code)
    
    # Update imports example
    file_paths = ["example.py"]
    code_refactoring_engine.update_imports(file_paths)