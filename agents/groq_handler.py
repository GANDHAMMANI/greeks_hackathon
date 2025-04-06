import time
import re
import random
import json
import os
from datetime import datetime

class GroqLimitHandler:
    def __init__(self, groq_client, cache_dir="./.cache"):
        self.groq_client = groq_client
        self.cache_dir = cache_dir
        self.api_available = True
        self.daily_limit_reached = False
        self.daily_reset_time = None
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # Load any cached results
        self.in_memory_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load previously cached results from disk"""
        cache_file = os.path.join(self.cache_dir, "groq_responses.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    self.in_memory_cache = json.load(f)
                print(f"Loaded {len(self.in_memory_cache)} cached API responses")
            except Exception as e:
                print(f"Error loading cache: {str(e)}")
    
    def _save_cache(self):
        """Save the current cache to disk"""
        cache_file = os.path.join(self.cache_dir, "groq_responses.json")
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.in_memory_cache, f)
        except Exception as e:
            print(f"Error saving cache: {str(e)}")
    
    def _get_cache_key(self, messages, temperature, max_tokens):
        """Generate a cache key from request parameters"""
        # We exclude 'stream' from the key since we always want non-streaming for caching
        key_parts = []
        for message in messages:
            key_parts.append(f"{message['role']}:{message['content']}")
        
        key_str = "|||".join(key_parts) + f"|||temp:{temperature}|||tokens:{max_tokens}"
        
        # Use a hash of the string as the key to keep it manageable
        import hashlib
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def is_api_available(self):
        """Check if the API is available or if we're in a daily limit cooldown"""
        if not self.daily_limit_reached:
            return True
            
        # Check if we've passed the reset time
        if self.daily_reset_time:
            current_time = time.time()
            if current_time > self.daily_reset_time:
                print("Daily limit cooldown period has ended, resetting API availability")
                self.daily_limit_reached = False
                self.daily_reset_time = None
                return True
        
        return False
    
    def generate_completion(self, messages, temperature=1, max_tokens=1024, stream=False, max_retries=5, force_cache=False):
        """
        Generate a completion using Groq LLM with rate limit handling and caching
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Controls randomness (0 to 1)
            max_tokens: Maximum tokens in completion
            stream: Whether to stream the response
            max_retries: Maximum number of retries on rate limit
            force_cache: Force use of cache even if API is available
            
        Returns:
            dict: Response from Groq API or cache
        """
        # Check if we're in daily limit cooldown and need to use cache
        if not self.is_api_available() or force_cache:
            # If streaming is requested but we're using cache, we can't stream
            if stream:
                print("Warning: Streaming requested but using cache instead due to API limits")
                stream = False
            
            # Generate cache key
            cache_key = self._get_cache_key(messages, temperature, max_tokens)
            
            # Check if we have this in cache
            if cache_key in self.in_memory_cache:
                print("Using cached response due to daily API limit")
                return {
                    "success": True,
                    "content": self.in_memory_cache[cache_key],
                    "cached": True
                }
            else:
                # We're out of tokens and don't have a cached response
                return {
                    "success": False,
                    "error": "Daily API limit reached and no cached response available",
                    "cached": False
                }
        
        # Check cache before making API call
        cache_key = self._get_cache_key(messages, temperature, max_tokens)
        if cache_key in self.in_memory_cache:
            print("Using cached response")
            return {
                "success": True,
                "content": self.in_memory_cache[cache_key],
                "cached": True
            }
        
        # If we get here, we need to call the API
        retries = 0
        backoff = 1  # Initial backoff in seconds
        
        while retries <= max_retries:
            try:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=temperature,
                    max_completion_tokens=max_tokens,
                    top_p=1,
                    stream=stream,
                    stop=None,
                )
                
                if stream:
                    return {"success": True, "stream": completion}
                else:
                    # Cache the successful response
                    content = completion.choices[0].message.content
                    self.in_memory_cache[cache_key] = content
                    self._save_cache()
                    
                    return {
                        "success": True,
                        "content": content,
                        "cached": False
                    }
                    
            except Exception as e:
                error_str = str(e)
                print(f"Error calling Groq API: {error_str}")
                
                # Check if it's a daily limit error
                if "tokens per day (TPD)" in error_str:
                    print("Daily token limit reached")
                    self.daily_limit_reached = True
                    
                    # Try to extract the wait time
                    wait_time_match = re.search(r"try again in (\d+)m(\d+\.\d+)s", error_str)
                    if wait_time_match:
                        minutes = int(wait_time_match.group(1))
                        seconds = float(wait_time_match.group(2))
                        total_seconds = (minutes * 60) + seconds
                        self.daily_reset_time = time.time() + total_seconds
                        reset_time_str = datetime.fromtimestamp(self.daily_reset_time).strftime('%H:%M:%S')
                        print(f"API will be available again at approximately: {reset_time_str}")
                    
                    # Switch to cache mode
                    if cache_key in self.in_memory_cache:
                        print("Using cached response due to daily API limit")
                        return {
                            "success": True,
                            "content": self.in_memory_cache[cache_key],
                            "cached": True
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Daily API limit reached and no cached response available",
                            "cached": False
                        }
                        
                # Check if it's a rate limit error
                elif "rate_limit_exceeded" in error_str:
                    if retries < max_retries:
                        # Extract wait time if available (per-minute rate limit)
                        wait_time_match = re.search(r"try again in (\d+\.\d+)s", error_str)
                        
                        if wait_time_match:
                            wait_time = float(wait_time_match.group(1))
                            # Add a small random jitter (0-1 seconds) to avoid thundering herd
                            wait_time += random.uniform(0, 1)
                        else:
                            wait_time = backoff
                            
                        print(f"Rate limit exceeded. Waiting {wait_time:.2f} seconds before retry {retries + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        
                        # Exponential backoff for next attempt
                        backoff = min(backoff * 2, 30)  # Cap at 30 seconds
                        retries += 1
                        continue
                
                # For non-rate limit errors or if max retries exceeded
                return {
                    "success": False,
                    "error": error_str,
                    "cached": False
                }
        
        # If we've exhausted retries
        return {
            "success": False,
            "error": "Maximum retries exceeded for rate limit",
            "cached": False
        }