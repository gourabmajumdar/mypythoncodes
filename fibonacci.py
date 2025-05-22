
# Online Python - IDE, Editor, Compiler, Interpreter
def fibonacci_series(n):
    fib_series = []
    a, b = 0, 1
    for _ in range(n):
        fib_series.append(a)
        a, b = b, a + b
    return fib_series

# Example usage:
num_terms = int(input("Enter the number of terms: "))
series = fibonacci_series(num_terms)
print("Fibonacci series:")
print(series)
