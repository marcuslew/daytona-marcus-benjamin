"""Hardcoded demo exam questions."""

QUESTIONS = [
    {
        "id": 1,
        "type": "mcq",
        "text": "What is the time complexity of binary search on a sorted array of n elements?",
        "choices": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
    },
    {
        "id": 2,
        "type": "mcq",
        "text": "Which HTTP method is idempotent?",
        "choices": ["POST", "PUT", "PATCH", "CONNECT"],
    },
    {
        "id": 3,
        "type": "mcq",
        "text": "In relational databases, what does ACID stand for?",
        "choices": [
            "Atomicity, Consistency, Isolation, Durability",
            "Availability, Concurrency, Integrity, Durability",
            "Atomicity, Concurrency, Isolation, Dependency",
            "Availability, Consistency, Isolation, Dependency",
        ],
    },
    {
        "id": 4,
        "type": "mcq",
        "text": "Which data structure uses LIFO ordering?",
        "choices": ["Queue", "Stack", "Heap", "Linked List"],
    },
    {
        "id": 5,
        "type": "mcq",
        "text": "What does 'sandboxing' primarily provide in a computing environment?",
        "choices": [
            "Faster CPU execution",
            "Isolation from the host system and other processes",
            "Automatic code formatting",
            "Increased screen resolution",
        ],
    },
    {
        "id": 6,
        "type": "short",
        "text": "In 2-3 sentences, explain why running untrusted code inside an isolated "
        "sandbox is safer than running it directly on a shared server.",
    },
    {
        "id": 7,
        "type": "code",
        "text": "Write a Python function reverse_string(s) that returns s reversed. Your code "
        "runs inside your own Daytona sandbox with ALL outbound network access blocked "
        "-- it cannot call an AI API, search the web, or fetch anything external.",
        "starter_code": (
            "def reverse_string(s):\n"
            "    # your code here\n"
            "    pass\n\n"
            'print(reverse_string("hello"))\n\n'
            "# Try uncommenting these two lines and hitting Run --\n"
            "# the sandbox will block the request, proving isolation is real:\n"
            "# import urllib.request\n"
            "# urllib.request.urlopen('https://api.openai.com', timeout=5)\n"
        ),
    },
]
