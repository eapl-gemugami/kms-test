# Sample aplication for KMS Dev test

- [x] Use asyncio and aiohttp to make async requests.
- [x] Handle potential exceptions and timeouts gracefully.
- [x] Log errors and performance metrics.
- [x] Implement a rate limiter to avoid overwhelming the APIs.

## Log performance metrics

Example:
```
2025-07-08 13:53:42,909 - __main__ - INFO - Successfully fetched weather for San Francisco in 0.29s
2025-07-08 13:53:42,934 - __main__ - INFO - Successfully fetched weather for Mexico City in 0.34s
2025-07-08 13:53:42,936 - __main__ - INFO - Successfully fetched weather for London in 0.32s
2025-07-08 13:53:42,937 - __main__ - INFO - Fetched weather for 3 cities in 0.34s
```