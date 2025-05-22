def second_largest(nums):
    unique_nums = list(set(nums))
    if len(unique_nums) < 2:
        return None
    unique_nums.sort()
    return unique_nums[-2]

# Example
print(second_largest([10, 20, 4, 45, 99, 99]))