# API Example Usage

## Query Endpoint

### cURL
```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What should be prepared before a client office tour?", "top_k": 10}'
```

### Python
```python
import requests
resp = requests.post("http://localhost:8000/rag/query", json={"question": "What should be prepared before a client office tour?", "top_k": 10})
print(resp.json())
```

---

## Feedback Endpoint

### cURL
```bash
curl -X POST "http://localhost:8000/rag/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What should be prepared before a client office tour?",
    "answer": "...answer text...",
    "context": ["...context chunk 1...", "...context chunk 2..."],
    "rating": 3,
    "comments": "Very helpful!"
  }'
```

### Python
```python
import requests
payload = {
    "question": "What should be prepared before a client office tour?",
    "answer": "...answer text...",
    "context": ["...context chunk 1...", "...context chunk 2..."],
    "rating": 3,
    "comments": "Very helpful!"
}
resp = requests.post("http://localhost:8000/rag/feedback", json=payload)
print(resp.json())
```

---

## Admin: View Feedback Logs

### cURL
```bash
curl "http://localhost:8000/rag/admin/feedback"
```

### Python
```python
import requests
resp = requests.get("http://localhost:8000/rag/admin/feedback")
print(resp.json())
```

---

## Admin: View Evaluation Logs

### cURL
```bash
curl "http://localhost:8000/rag/admin/evaluation"
```

### Python
```python
import requests
resp = requests.get("http://localhost:8000/rag/admin/evaluation")
print(resp.json())
```

---

## Admin: Download Feedback as CSV

### cURL
```bash
curl -o feedback.csv "http://localhost:8000/rag/admin/feedback/csv"
```

---

## Admin: Download Evaluation as CSV

### cURL
```bash
curl -o evaluation.csv "http://localhost:8000/rag/admin/evaluation/csv"
``` 

---

## Agentic/Multi-hop/Personalized Query Endpoint

### cURL
```bash
curl -X POST "http://localhost:8000/rag/agentic_query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the process for onboarding and who is responsible for approvals?",
    "user_id": "alice123",
    "profile": {"role": "BDM", "location": "Bangalore"},
    "top_k": 5,
    "max_steps": 4
  }'
```

### Python
```python
import requests
payload = {
    "question": "What is the process for onboarding and who is responsible for approvals?",
    "user_id": "alice123",
    "profile": {"role": "BDM", "location": "Bangalore"},
    "top_k": 5,
    "max_steps": 4
}
resp = requests.post("http://localhost:8000/rag/agentic_query", json=payload)
print(resp.json())
``` 