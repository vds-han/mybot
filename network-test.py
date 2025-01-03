# network_test.py
import requests
import socket

def test_connection():
    try:
        # Test general internet connectivity
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        print("Network is accessible")
        
        # Test Telegram API specifically
        response = requests.get('https://api.telegram.org', timeout=5)
        print(f"Telegram API is accessible, status code: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
