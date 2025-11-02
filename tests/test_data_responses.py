"""Test data corpus for ResponseValidator testing.

Contains realistic examples of valid and invalid responses
for comprehensive testing of validation logic.
"""


# Valid Responses

VALID_COMPLETE_RESPONSE = """
# Implementation Complete

I've successfully implemented the requested feature. Here's the complete solution:

## Code Implementation

```python
def calculate_sum(numbers: list) -> int:
    \"\"\"Calculate sum of numbers in list.

    Args:
        numbers: List of integers to sum

    Returns:
        Sum of all numbers
    \"\"\"
    return sum(numbers)


def calculate_average(numbers: list) -> float:
    \"\"\"Calculate average of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Average value

    Raises:
        ValueError: If list is empty
    \"\"\"
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    return sum(numbers) / len(numbers)
```

## Tests

```python
def test_calculate_sum():
    assert calculate_sum([1, 2, 3]) == 6
    assert calculate_sum([]) == 0
    assert calculate_sum([-1, 1]) == 0


def test_calculate_average():
    assert calculate_average([1, 2, 3]) == 2.0
    with pytest.raises(ValueError):
        calculate_average([])
```

## Usage Example

```python
numbers = [10, 20, 30, 40, 50]
total = calculate_sum(numbers)
avg = calculate_average(numbers)
print(f"Total: {total}, Average: {avg}")
```

The implementation handles all edge cases including empty lists and negative numbers.
"""


VALID_MULTICODE_RESPONSE = """
# Full Stack Implementation

Here's the complete implementation across backend and frontend:

## Backend API

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def get_users():
    users = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # Fetch from database
    user = {'id': user_id, 'name': f'User {user_id}'}
    return jsonify(user)
```

## Frontend Component

```javascript
async function fetchUsers() {
    const response = await fetch('/api/users');
    const users = await response.json();
    return users;
}

async function displayUsers() {
    const users = await fetchUsers();
    const userList = document.getElementById('user-list');
    users.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user.name;
        userList.appendChild(li);
    });
}
```

## Configuration

```json
{
  "api": {
    "baseUrl": "http://localhost:5000",
    "timeout": 30000,
    "retries": 3
  },
  "features": {
    "caching": true,
    "logging": true
  }
}
```

This provides a complete full-stack solution with proper error handling.
"""


VALID_EXPLANATION_ONLY = """
# Explanation of the Architecture

The system follows a microservices architecture pattern with the following components:

## Core Components

1. API Gateway: Routes requests to appropriate services
2. Authentication Service: Handles user authentication via JWT tokens
3. Data Service: Manages database operations and caching
4. Message Queue: Enables asynchronous communication between services
5. Logging Service: Centralized logging and monitoring

## Data Flow

When a user makes a request:
1. Request hits the API Gateway
2. Gateway validates authentication token
3. Request is routed to appropriate service
4. Service processes request and returns response
5. Response flows back through gateway to client

## Key Benefits

- Scalability: Each service can scale independently
- Resilience: Failure of one service doesn't bring down the system
- Flexibility: Services can use different technologies
- Maintainability: Clear separation of concerns

The architecture supports high availability and can handle thousands of concurrent requests.
"""


# Invalid Responses - Incomplete

INVALID_TRUNCATED_RESPONSE = """
# Implementation Started

I'll help you implement this feature. Here's what we need to do:

```python
def process_data(data):
    result = []
    for item in data:
        if item.is_valid():
            result.append(item[truncated]
"""


INVALID_TOO_SHORT = "OK, done."


INVALID_REFUSAL_RESPONSE = """
I cannot help with that request. As an AI assistant, I don't have access
to your local filesystem and I'm unable to make changes to production systems.
I apologize but I cannot proceed with this task.
"""


INVALID_UNCLOSED_CODE_BLOCK = """
Here's the implementation:

```python
def hello():
    print("Hello")
    return True

And here's how to use it...
"""


# Invalid Responses - Quality Issues

INVALID_VAGUE_RESPONSE = """
Maybe you could try doing something like that. Perhaps it might work,
or possibly not. Generally speaking, these things usually work out,
but you never know. It could be that the approach might be good,
or maybe you should try something else. Typically, people often
find that these solutions possibly help, but it depends.
""" * 10


INVALID_NO_CODE_WHEN_REQUIRED = """
# Solution

The solution is to use a function that processes the data and returns
the result. You should create a proper implementation with error handling
and validation. Make sure to test it thoroughly before deployment.
"""


INVALID_SYNTAX_ERROR_CODE = """
# Implementation

Here's the code:

```python
def broken_function()
    print("Missing colon")
    if True
        return False
```

This should work fine.
"""


INVALID_CONTRADICTORY_RESPONSE = """
# Analysis

The solution is definitely yes, you should proceed with this approach.
It's the best option available.

However, the answer is no, you should not proceed with this approach.
It's not a good option.

So to be clear: yes, go ahead. But also no, don't do it.
"""


# Edge Cases

EDGE_CASE_MINIMAL_VALID = """
Here is a simple solution that addresses the requirement completely:

```python
def solution():
    return True
```

This implementation is straightforward and meets all specified requirements.
"""


EDGE_CASE_VERY_LONG_CODE = """
# Complete Implementation

Here's the full implementation:

```python
""" + "\n".join([f"def function_{i}():\n    return {i}" for i in range(500)]) + """
```

All functions are implemented as specified.
"""


EDGE_CASE_UNICODE_RESPONSE = """
# Solution with Unicode

Here's an internationalized solution:

```python
def greet(name: str, language: str = 'en'):
    greetings = {
        'en': 'Hello',
        'es': 'Hola',
        'fr': 'Bonjour',
        'de': 'Guten Tag',
        'zh': '你好',
        'ja': 'こんにちは',
        'ar': 'مرحبا',
        'ru': 'Привет'
    }
    return f"{greetings.get(language, 'Hello')} {name}! 🌍"
```

This handles multiple languages with proper Unicode support.
"""


EDGE_CASE_NO_LANGUAGE_SPECIFIED = """
# Generic Code Block

Here's the implementation:

```
function process() {
    return data.map(x => x * 2)
}
```

This works in JavaScript.
"""


# Real-world examples

REALISTIC_BUG_FIX = """
# Bug Fix: Null Pointer Exception

I've identified and fixed the issue. The problem was in the data validation logic.

## Root Cause

The code was accessing properties on potentially null objects without checking:

```python
# Before (broken)
def process_user(user):
    return user.name.upper()  # Fails if user is None
```

## Fix

Added proper null checking:

```python
# After (fixed)
def process_user(user):
    if user is None:
        raise ValueError("User cannot be None")
    if not hasattr(user, 'name'):
        raise AttributeError("User must have a name attribute")
    return user.name.upper()
```

## Test

```python
def test_process_user_null():
    with pytest.raises(ValueError):
        process_user(None)

def test_process_user_valid():
    user = User(name="alice")
    assert process_user(user) == "ALICE"
```

The fix ensures proper error handling and prevents runtime exceptions.
"""


REALISTIC_FEATURE_IMPLEMENTATION = """
# Feature: User Authentication

I've implemented the complete authentication system with JWT tokens.

## Backend Implementation

```python
import jwt
from datetime import datetime, timedelta
from flask import request, jsonify

SECRET_KEY = "your-secret-key"

def generate_token(user_id: int) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return {'valid': True, 'user_id': payload['user_id']}
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    # Validate credentials (simplified)
    if authenticate_user(data['username'], data['password']):
        token = generate_token(data['user_id'])
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401
```

## Security Considerations

1. Tokens expire after 24 hours
2. Passwords are hashed (not shown for brevity)
3. HTTPS required in production
4. Rate limiting recommended

## Testing

```python
def test_generate_token():
    token = generate_token(123)
    assert token is not None
    result = verify_token(token)
    assert result['valid']
    assert result['user_id'] == 123

def test_expired_token():
    # Create token that expires immediately
    payload = {'user_id': 123, 'exp': datetime.utcnow() - timedelta(hours=1)}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    result = verify_token(token)
    assert not result['valid']
```

The implementation is production-ready with proper error handling and security measures.
"""


# Collection for easy access
ALL_VALID_RESPONSES = [
    VALID_COMPLETE_RESPONSE,
    VALID_MULTICODE_RESPONSE,
    VALID_EXPLANATION_ONLY,
    EDGE_CASE_MINIMAL_VALID,
    EDGE_CASE_UNICODE_RESPONSE,
    REALISTIC_BUG_FIX,
    REALISTIC_FEATURE_IMPLEMENTATION
]

ALL_INVALID_RESPONSES = [
    INVALID_TRUNCATED_RESPONSE,
    INVALID_TOO_SHORT,
    INVALID_REFUSAL_RESPONSE,
    INVALID_UNCLOSED_CODE_BLOCK,
    INVALID_VAGUE_RESPONSE,
    INVALID_NO_CODE_WHEN_REQUIRED,
    INVALID_SYNTAX_ERROR_CODE,
    INVALID_CONTRADICTORY_RESPONSE
]

ALL_EDGE_CASES = [
    EDGE_CASE_MINIMAL_VALID,
    EDGE_CASE_VERY_LONG_CODE,
    EDGE_CASE_UNICODE_RESPONSE,
    EDGE_CASE_NO_LANGUAGE_SPECIFIED
]
