def is_palindrome(s):
    # Remove spaces and convert to lowercase for uniform comparison
    s = s.replace(" ", "").lower()
    return s == s[::-1]

# Example usage:
text = input("Enter a string: ")

if is_palindrome(text):
    print(f"'{text}' is a palindrome!")
else:
    print(f"'{text}' is not a palindrome.")