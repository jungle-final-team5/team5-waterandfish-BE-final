#!/usr/bin/env python3
"""
Test script for the WebSocket server to verify it's working correctly
and to help debug the UTF-8 decoding issue.
"""

import asyncio
import websockets
import json
import numpy as np
import pytest

@pytest.mark.asyncio
async def test_websocket_server():
    """Test the WebSocket server with proper JSON messages"""
    
    # Test server URL (adjust port as needed)
    uri = "ws://localhost:9001/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Test 1: Send a ping message
            print("\n📤 Sending ping message...")
            await websocket.send(json.dumps({"type": "ping"}))
            
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Test 2: Send a landmarks message with dummy data
            print("\n📤 Sending landmarks message...")
            
            # Create dummy landmark data (675 features as expected by the model)
            dummy_landmarks = np.random.rand(675).tolist()
            
            landmarks_message = {
                "type": "landmarks",
                "data": dummy_landmarks
            }
            
            await websocket.send(json.dumps(landmarks_message))
            
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            
            # Test 3: Send an invalid message type
            print("\n📤 Sending invalid message type...")
            await websocket.send(json.dumps({"type": "invalid_type"}))
            
            # Test 4: Send malformed JSON
            print("\n📤 Sending malformed JSON...")
            await websocket.send('{"type": "landmarks", "data": [1, 2, 3')  # Missing closing brace
            
            # Wait a bit for any error responses
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received for malformed JSON (expected)")
            
            print("\n✅ All tests completed successfully!")
            
    except OSError:
        print(f"❌ Could not connect to {uri}")
        print("Make sure the WebSocket server is running on the specified port.")
    except Exception as e:
        print(f"❌ Error during testing: {e}")

@pytest.mark.asyncio
async def test_binary_message():
    """Test sending binary message to see if it causes the UTF-8 error"""
    
    uri = "ws://localhost:9001/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri} for binary test")
            
            # Send binary data
            print("\n📤 Sending binary message...")
            binary_data = b'\xff\xfe\xfd\xfc'  # Some binary data
            await websocket.send(binary_data)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏰ No response received for binary message (expected)")
            
            print("\n✅ Binary test completed!")
            
    except Exception as e:
        print(f"❌ Error during binary testing: {e}")

if __name__ == "__main__":
    print("🧪 WebSocket Server Test")
    print("=" * 50)
    
    # Run the main test
    asyncio.run(test_websocket_server())
    
    print("\n" + "=" * 50)
    print("🧪 Binary Message Test")
    print("=" * 50)
    
    # Run the binary test
    asyncio.run(test_binary_message()) 