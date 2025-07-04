import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
import json
import sys
import os
import asyncio
import websockets
import logging
from collections import deque
from PIL import ImageFont, ImageDraw, Image
import base64
import io
from datetime import datetime
import argparse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class SignClassifierWebSocketServer:
    def __init__(self, model_data_url, host, port):
        """수어 분류 WebSocket 서버 초기화"""
        self.host = host
        self.port = port
        self.clients = set()  # 연결된 클라이언트들
        
        # 모델 정보 로드
        self.model_info = self.load_model_info(model_data_url)
        if not self.model_info:
            raise ValueError("모델 정보를 로드할 수 없습니다.")
        
        # 설정값
        self.MAX_SEQ_LENGTH = self.model_info["input_shape"][0]
        
        # 모델 경로 처리 (절대 경로로 변환)
        model_path = self.model_info["model_path"]
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        # 상대 경로인 경우 public 디렉터리를 기준으로 변환
        if not os.path.isabs(model_path):
            if not model_path.startswith("public"):
                model_path = os.path.join("public", model_path)
            self.MODEL_SAVE_PATH = os.path.join(project_root, model_path)
        else:
            self.MODEL_SAVE_PATH = model_path
        
        # 경로 정규화
        self.MODEL_SAVE_PATH = os.path.normpath(self.MODEL_SAVE_PATH)
        
        self.ACTIONS = self.model_info["labels"]
        self.QUIZ_LABELS = [a for a in self.ACTIONS if a != "None"]
        
        logger.info(f"📋 로드된 라벨: {self.ACTIONS}")
        logger.info(f"🎯 퀴즈 라벨: {self.QUIZ_LABELS}")
        logger.info(f"📊 원본 모델 경로: {self.model_info['model_path']}")
        logger.info(f"📊 변환된 모델 경로: {self.MODEL_SAVE_PATH}")
        logger.info(f"⏱️ 시퀀스 길이: {self.MAX_SEQ_LENGTH}")
        
        # 모델 파일 존재 확인
        if not os.path.exists(self.MODEL_SAVE_PATH):
            logger.error(f"❌ 모델 파일을 찾을 수 없습니다: {self.MODEL_SAVE_PATH}")
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {self.MODEL_SAVE_PATH}")
        
        logger.info(f"✅ 모델 파일 존재 확인: {self.MODEL_SAVE_PATH}")
        
        # MediaPipe 초기화
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            min_detection_confidence=0.5,  # 감지 신뢰도 임계값
            min_tracking_confidence=0.5,   # 추적 신뢰도 임계값
            model_complexity=1,            # 모델 복잡도 (0, 1, 2)
            smooth_landmarks=True,         # 랜드마크 스무딩
            enable_segmentation=False,     # 세그멘테이션 비활성화 (성능 향상)
            refine_face_landmarks=True     # 얼굴 랜드마크 정제
        )
        
        # 모델 로드
        try:
            self.model = tf.keras.models.load_model(self.MODEL_SAVE_PATH)
            logger.info(f"✅ 모델 로드 성공: {self.MODEL_SAVE_PATH}")
        except Exception as e:
            logger.error(f"❌ 모델 로딩 실패: {e}")
            raise
        
        # 시퀀스 버퍼 (클라이언트별로 관리)
        self.client_sequences = {}  # {client_id: deque}
        
        # 분류 상태 (클라이언트별로 관리)
        self.client_states = {}  # {client_id: {prediction, confidence, is_processing}}
        
        # 분류 통계
        self.classification_count = 0
        self.last_log_time = 0
        self.log_interval = 1.0  # 1초마다 로그 출력 (너무 빈번한 로그 방지)
        
        # 시퀀스 관리 (클라이언트별로 관리)
        self.client_sequence_managers = {}  # {client_id: {last_prediction, same_count}}
    
    def load_model_info(self, model_data_url):
        """모델 정보 파일을 로드합니다."""
        try:
            # 현재 스크립트 파일의 위치를 기준으로 프로젝트 루트 계산
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # src/services에서 프로젝트 루트로 이동 (2단계 상위)
            project_root = os.path.dirname(os.path.dirname(current_dir))
            
            # 파일명만 전달된 경우 public/model-info/ 디렉터리에서 찾기
            if os.path.basename(model_data_url) == model_data_url:
                # 파일명만 전달된 경우
                model_data_url = os.path.join("public", "model-info", model_data_url)
            
            # 상대 경로인 경우 프로젝트 루트를 기준으로 절대 경로로 변환
            if not os.path.isabs(model_data_url):
                model_data_url = os.path.join(project_root, model_data_url)
            
            # 경로 정규화
            model_data_url = os.path.normpath(model_data_url)
            
            logger.info(f"📁 모델 정보 파일 경로: {model_data_url}")
            
            if not os.path.exists(model_data_url):
                logger.error(f"❌ 모델 정보 파일을 찾을 수 없습니다: {model_data_url}")
                return None
            
            with open(model_data_url, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ 모델 정보 파일 로드 실패: {e}")
            return None
    
    def get_client_id(self, websocket):
        """클라이언트 ID 생성"""
        return f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    
    def initialize_client(self, client_id):
        """클라이언트 초기화"""
        if client_id not in self.client_sequences:
            self.client_sequences[client_id] = deque(maxlen=self.MAX_SEQ_LENGTH)
            self.client_states[client_id] = {
                "prediction": "None",
                "confidence": 0.0,
                "is_processing": False
            }
            self.client_sequence_managers[client_id] = {
                "last_prediction": None,
                "same_count": 0
            }
            logger.info(f"🆕 클라이언트 초기화: {client_id}")
    
    def cleanup_client(self, client_id):
        """클라이언트 정리"""
        if client_id in self.client_sequences:
            del self.client_sequences[client_id]
        if client_id in self.client_states:
            del self.client_states[client_id]
        if client_id in self.client_sequence_managers:
            del self.client_sequence_managers[client_id]
        logger.info(f"🧹 클라이언트 정리: {client_id}")
    
    def bytes_to_frame(self, image_bytes):
        """바이트 데이터를 OpenCV 프레임으로 변환"""
        try:
            # 바이트를 numpy 배열로 변환
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # 이미지 디코딩
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("프레임 디코딩 실패")
                return None
            
            # 프레임 크기 확인
            if frame.size == 0:
                logger.warning("빈 프레임")
                return None
            
            # 검은색 프레임 감지
            if frame.max() == 0:
                logger.error("❌ 검은색 프레임 감지! 이미지 데이터에 문제가 있습니다.")
                return None
            
            return frame
        except Exception as e:
            logger.error(f"프레임 변환 실패: {e}")
            return None
    
    def normalize_sequence_length(self, sequence, target_length=30):
        """시퀀스 길이를 정규화"""
        current_length = len(sequence)
        if current_length == target_length:
            return sequence
        x_old = np.linspace(0, 1, current_length)
        x_new = np.linspace(0, 1, target_length)
        normalized_sequence = []
        for i in range(sequence.shape[1]):
            f = np.interp(x_new, x_old, sequence[:, i])
            normalized_sequence.append(f)
        return np.array(normalized_sequence).T
    
    def extract_dynamic_features(self, sequence):
        """동적 특성 추출"""
        velocity = np.diff(sequence, axis=0, prepend=sequence[0:1])
        acceleration = np.diff(velocity, axis=0, prepend=velocity[0:1])
        dynamic_features = np.concatenate([sequence, velocity, acceleration], axis=1)
        return dynamic_features
    
    def convert_to_relative_coordinates(self, landmarks_list):
        """상대 좌표로 변환"""
        relative_landmarks = []
        for frame in landmarks_list:
            if not frame["pose"]:
                relative_landmarks.append(frame)
                continue
            pose_landmarks = frame["pose"].landmark
            left_shoulder = pose_landmarks[11]
            right_shoulder = pose_landmarks[12]
            shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
            shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
            shoulder_center_z = (left_shoulder.z + right_shoulder.z) / 2
            shoulder_width = abs(right_shoulder.x - left_shoulder.x)
            if shoulder_width == 0:
                shoulder_width = 1.0
            new_frame = {}
            if frame["pose"]:
                relative_pose = []
                for landmark in pose_landmarks:
                    rel_x = (landmark.x - shoulder_center_x) / shoulder_width
                    rel_y = (landmark.y - shoulder_center_y) / shoulder_width
                    rel_z = (landmark.z - shoulder_center_z) / shoulder_width
                    relative_pose.append([rel_x, rel_y, rel_z])
                new_frame["pose"] = relative_pose
            for hand_key in ["left_hand", "right_hand"]:
                if frame[hand_key]:
                    relative_hand = []
                    for landmark in frame[hand_key].landmark:
                        rel_x = (landmark.x - shoulder_center_x) / shoulder_width
                        rel_y = (landmark.y - shoulder_center_y) / shoulder_width
                        rel_z = (landmark.z - shoulder_center_z) / shoulder_width
                        relative_hand.append([rel_x, rel_y, rel_z])
                    new_frame[hand_key] = relative_hand
                else:
                    new_frame[hand_key] = None
            relative_landmarks.append(new_frame)
        return relative_landmarks
    
    def improved_preprocess_landmarks(self, landmarks_list):
        """랜드마크 전처리"""
        if not landmarks_list:
            return np.zeros((self.MAX_SEQ_LENGTH, 675))
        relative_landmarks = self.convert_to_relative_coordinates(landmarks_list)
        processed_frames = []
        for frame in relative_landmarks:
            combined = []
            for key in ["pose", "left_hand", "right_hand"]:
                if frame[key]:
                    if isinstance(frame[key], list):
                        combined.extend(frame[key])
                    else:
                        combined.extend([[l.x, l.y, l.z] for l in frame[key].landmark])
                else:
                    num_points = {"pose": 33, "left_hand": 21, "right_hand": 21}[key]
                    combined.extend([[0, 0, 0]] * num_points)
            if combined:
                processed_frames.append(np.array(combined).flatten())
            else:
                processed_frames.append(np.zeros(75 * 3))
        if not processed_frames:
            return np.zeros((self.MAX_SEQ_LENGTH, 675))
        
        # 시퀀스 길이 정규화
        sequence = np.array(processed_frames)
        if len(sequence) != self.MAX_SEQ_LENGTH:
            sequence = self.normalize_sequence_length(sequence, self.MAX_SEQ_LENGTH)
        
        # 동적 특성 추출
        sequence = self.extract_dynamic_features(sequence)
        
        return sequence
    
    def log_classification_result(self, result, client_id):
        """분류 결과를 로그로 출력"""
        current_time = asyncio.get_event_loop().time()
        
        # 로그 출력 주기 제한 (너무 빈번한 로그 방지)
        if current_time - self.last_log_time >= self.log_interval:
            logger.info(f"🎯 [{client_id}] 예측: {result['prediction']} (신뢰도: {result['confidence']:.3f})")
            self.last_log_time = current_time
        
        # 분류 횟수 증가
        self.classification_count += 1
    
    def process_frame(self, frame, client_id):
        """프레임 처리 및 분류"""
        if self.client_states[client_id]["is_processing"]:
            return None
        
        self.client_states[client_id]["is_processing"] = True
        
        try:
            # BGR을 RGB로 변환
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # MediaPipe로 랜드마크 추출
            results = self.holistic.process(frame_rgb)
            
            # 랜드마크 데이터 수집
            landmarks_list = []
            landmarks_list.append({
                "pose": results.pose_landmarks,
                "left_hand": results.left_hand_landmarks,
                "right_hand": results.right_hand_landmarks
            })
            
            # 시퀀스에 추가
            self.client_sequences[client_id].extend(landmarks_list)
            
            # 충분한 프레임이 쌓였을 때만 예측
            if len(self.client_sequences[client_id]) >= self.MAX_SEQ_LENGTH:
                # 랜드마크 전처리
                sequence = self.improved_preprocess_landmarks(list(self.client_sequences[client_id]))
                
                # 모델 예측
                pred_probs = self.model.predict(sequence.reshape(1, *sequence.shape), verbose=0)
                pred_idx = np.argmax(pred_probs[0])
                pred_label = self.ACTIONS[pred_idx]
                confidence = float(pred_probs[0][pred_idx])
                
                # 결과 생성
                result = {
                    "prediction": pred_label,
                    "confidence": confidence,
                    "probabilities": {label: float(prob) for label, prob in zip(self.ACTIONS, pred_probs[0])}
                }
                
                # 분류 결과를 로그로 출력
                self.log_classification_result(result, client_id)
                
                return result
                
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return None
        finally:
            self.client_states[client_id]["is_processing"] = False
        
        return None
    
    async def handle_client(self, websocket, path):
        """클라이언트 연결 처리"""
        client_id = self.get_client_id(websocket)
        self.clients.add(websocket)
        self.initialize_client(client_id)
        
        logger.info(f"🟢 클라이언트 연결됨: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    # 바이너리 데이터인지 확인
                    if isinstance(message, bytes):
                        # 바이너리 데이터를 직접 처리
                        frame = self.bytes_to_frame(message)
                        
                        if frame is not None:
                            result = self.process_frame(frame, client_id)
                            
                            if result:
                                # 결과를 클라이언트로 전송
                                response = {
                                    "type": "classification_result",
                                    "data": result,
                                    "timestamp": asyncio.get_event_loop().time()
                                }
                                await websocket.send(json.dumps(response))
                    else:
                        # JSON 메시지 처리 (기존 방식 유지)
                        data = json.loads(message)
                        
                        if data.get("type") == "video_chunk":
                            # 비디오 청크 처리
                            chunk_data = base64.b64decode(data["data"])
                            frame = self.bytes_to_frame(chunk_data)
                            
                            if frame is not None:
                                result = self.process_frame(frame, client_id)
                                
                                if result:
                                    # 결과를 클라이언트로 전송
                                    response = {
                                        "type": "classification_result",
                                        "data": result,
                                        "timestamp": asyncio.get_event_loop().time()
                                    }
                                    await websocket.send(json.dumps(response))
                        
                        elif data.get("type") == "ping":
                            # 핑 응답
                            await websocket.send(json.dumps({"type": "pong"}))
                        
                except json.JSONDecodeError:
                    logger.warning(f"잘못된 JSON 메시지: {client_id}")
                except Exception as e:
                    logger.error(f"메시지 처리 실패 [{client_id}]: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔴 클라이언트 연결 종료: {client_id}")
        except Exception as e:
            logger.error(f"클라이언트 처리 중 오류 [{client_id}]: {e}")
        finally:
            self.clients.remove(websocket)
            self.cleanup_client(client_id)
    
    async def run_server(self):
        """WebSocket 서버 실행"""
        server = await websockets.serve(
            self.handle_client, 
            self.host, 
            self.port
        )
        logger.info(f"🚀 수어 분류 WebSocket 서버 시작: ws://{self.host}:{self.port}")
        logger.info(f"📊 서버 정보:")
        logger.info(f"   - 호스트: {self.host}")
        logger.info(f"   - 포트: {self.port}")
        logger.info(f"   - 모델: {self.MODEL_SAVE_PATH}")
        logger.info(f"   - 라벨 수: {len(self.ACTIONS)}")
        logger.info(f"   - 시퀀스 길이: {self.MAX_SEQ_LENGTH}")
        
        await server.wait_closed()

def main():
    """메인 함수"""
    
    # 모델 서버 프로세스 시작
    print(f"🚀 Starting sign classifier WebSocket server...")
    print(f"📁 Model data URL: {os.environ.get('MODEL_DATA_URL', 'Not set')}")
    print(f"🔌 Port: {os.environ.get('PORT', 'Not set')}")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True, help="Port number for the server")
    parser.add_argument("--env", type=str, required=True, help="Environment variable MODEL_DATA_URL")
    args = parser.parse_args()
    
    port = args.port
    model_data_url = args.env
    
    # 현재 스크립트 파일의 위치를 기준으로 프로젝트 루트 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # src/services에서 프로젝트 루트로 이동 (2단계 상위)
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # 파일명만 전달된 경우 public/model-info/ 디렉터리에서 찾기
    model_data_url_processed = model_data_url
    if os.path.basename(model_data_url) == model_data_url:
        # 파일명만 전달된 경우
        model_data_url_processed = os.path.join("public", "model-info", model_data_url)
    
    # 상대 경로인 경우 프로젝트 루트를 기준으로 절대 경로로 변환
    if not os.path.isabs(model_data_url_processed):
        model_data_url_full = os.path.join(project_root, model_data_url_processed)
    else:
        model_data_url_full = model_data_url_processed
    
    # 경로 정규화
    model_data_url_full = os.path.normpath(model_data_url_full)
    
    logger.info(f"📁 원본 모델 데이터 URL: {model_data_url}")
    logger.info(f"📁 처리된 모델 데이터 경로: {model_data_url_processed}")
    logger.info(f"📁 최종 모델 데이터 경로: {model_data_url_full}")
    logger.info(f"🔌 포트: {port}")
    
    if not os.path.exists(model_data_url_full):
        logger.error(f"❌ 모델 정보 파일을 찾을 수 없습니다: {model_data_url_full}")
        sys.exit(1)
    
    logger.info(f"✅ 모델 정보 파일 확인됨: {model_data_url_full}")
    
    # 서버 생성 및 실행
    # localhost should be changed to the server's IP address when deploying to a server
    server = SignClassifierWebSocketServer(model_data_url, host="localhost", port=port)
    asyncio.run(server.run_server())

if __name__ == "__main__":
    main() 