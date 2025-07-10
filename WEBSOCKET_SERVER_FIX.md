# WebSocket Server UTF-8 Decoding Fix

## Problem
The WebSocket server was experiencing UTF-8 decoding errors:
```
'utf-8' codec can't decode byte 0xff in position 0: invalid start byte
```

This error occurred because the server was receiving binary data (likely image/video frames) but trying to process it as UTF-8 text.

## Root Cause
The issue was in the `handle_client` method in `sign_classifier_websocket_server.py`. The server was designed to handle JSON text messages but was receiving binary data from clients.

## Solution
1. **Added binary message detection**: The server now checks if incoming messages are binary data and handles them appropriately.

2. **Improved error handling**: Added specific handling for `UnicodeDecodeError` and better error messages.

3. **Enhanced logging**: Added more detailed logging to help debug connection issues.

4. **Fixed host binding**: Changed the server to bind to `0.0.0.0` instead of `localhost` for external access.

## Changes Made

### 1. Binary Message Handling
```python
# 메시지 타입 확인 (텍스트 또는 바이너리)
if isinstance(message, bytes):
    # 바이너리 메시지 처리
    logger.warning(f"[{client_id}] 바이너리 메시지 수신됨 (길이: {len(message)} bytes) - 벡터 처리 모드에서는 지원하지 않음")
    # 클라이언트에게 바이너리 메시지가 지원되지 않음을 알림
    try:
        await websocket.send(json.dumps({
            "type": "error",
            "message": "바이너리 메시지는 지원되지 않습니다. JSON 형식의 랜드마크 데이터를 전송해주세요."
        }))
    except:
        pass
    continue
```

### 2. Enhanced Error Handling
```python
except UnicodeDecodeError as e:
    logger.warning(f"UTF-8 디코딩 오류 [{client_id}]: {e} - 바이너리 데이터가 텍스트로 전송됨")
```

### 3. Host Configuration
```python
# In model_server_manager.py
"--host", "0.0.0.0",  # 외부에서 접근 가능하게 바인딩
```

## Testing

### 1. Run the Test Script
```bash
cd team5-waterandfish-BE
python test_websocket_server.py
```

### 2. Manual Testing
You can also test manually using a WebSocket client:

1. Start the model server
2. Connect to `ws://localhost:9001/ws`
3. Send a ping message:
   ```json
   {"type": "ping"}
   ```
4. Send a landmarks message:
   ```json
   {
     "type": "landmarks",
     "data": [/* 675 landmark values */]
   }
   ```

### 3. Expected Behavior
- ✅ Ping messages should receive pong responses
- ✅ Valid landmarks messages should receive classification results
- ✅ Binary messages should be rejected with an error message
- ✅ Malformed JSON should be handled gracefully
- ✅ No more UTF-8 decoding errors

## Server Modes

### Vector Processing Mode (Current)
- Expects JSON messages with landmark vector data
- Processes pre-computed MediaPipe landmarks
- Optimized for performance
- Does NOT handle raw video/image data

### WebRTC Mode (Alternative)
- Handles raw video frames
- Processes MediaPipe landmarks internally
- More resource intensive
- Currently commented out in the manager

## Troubleshooting

### If you still see UTF-8 errors:
1. Check if the correct server is running (vector processing vs WebRTC)
2. Verify the client is sending JSON, not binary data
3. Check the server logs for detailed error information

### If the server won't start:
1. Check if the port is already in use
2. Verify the model files exist
3. Check the model_info.json file path

### If clients can't connect:
1. Verify the server is binding to the correct host (`0.0.0.0`)
2. Check firewall settings
3. Verify the WebSocket URL format

## Log Messages

The server now provides clear logging:
- 🟢 Vector processing client connected
- 📋 Expected message format information
- ⚠️ Binary message warnings
- ❌ Error details with stack traces
- 🔴 Connection closure information 