def fib(n):
    """Calculate nth Fibonacci number"""
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

# Test: Print first 10 Fibonacci numbers
if __name__ == "__main__":
    for i in range(10):
        print(f"fib({i}) = {fib(i)}")