def find_duplicates(nums):
    seen = set()
    duplicates = set()
    
    for num in nums:
        if num in seen:
            duplicates.add(num)
        else:
            seen.add(num)
    
    return list(duplicates)

# Example usage
input_list = [4, 3, 2, 7, 8, 2, 3, 1]
output = find_duplicates(input_list)
print("Duplicates:", output)
