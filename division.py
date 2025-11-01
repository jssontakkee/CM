def division_algorithm(num1, num2):
    """
    Performs division using bit shift operations (binary division algorithm)
    Returns the quotient of num1 / num2
    """
    if num2 == 0:
        raise ValueError("Division by zero is not allowed")
    
    temp = 1
    result = 0
    
    # Scale up num2 and temp until num2 > num1
    while num2 <= num1:
        num2 <<= 1  # Left shift (multiply by 2)
        temp <<= 1
    
    # Scale down and subtract
    while temp > 1:
        num2 >>= 1  # Right shift (divide by 2)
        temp >>= 1
        
        if num1 >= num2:
            num1 -= num2
            result += temp
    
    return result


def main():
    print("Enter two numbers:")
    try:
        num1 = int(input("First number (dividend): "))
        num2 = int(input("Second number (divisor): "))
        
        result = division_algorithm(num1, num2)
        print(f"Division of {num1} by {num2} is: {result}")
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
