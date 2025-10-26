# app/ai_service.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, List
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import asyncio
from functools import partial

from .settings import settings

# 서비스 레이어가 기대하는 필드 구조에 맞춘 JSON을 요청합니다.
SYSTEM_PROMPT = """당신은 공감적인 한국어 일기 감정 분석 AI입니다.
일기를 분석하여 JSON으로 답변하세요.

형식:
{"summary":"요약","sentiment":{"label":"긍정/중립/부정","score":0.0~1.0},"emotion_scores":{"행복":0.0~1.0,"슬픔":0.0~1.0,"분노":0.0~1.0,"불안":0.0~1.0,"평온":0.0~1.0,"흥분":0.0~1.0},"primary_emotion":"행복/슬픔/분노/불안/평온/흥분 중 하나","comfort_message":"따뜻한 위로와 공감 메시지 2-3문장","tags":["태그1","태그2"]}

예시:
일기: "시험에 떨어졌어. 속상해."
{"summary":"시험 불합격으로 속상함","sentiment":{"label":"부정","score":0.7},"emotion_scores":{"행복":0.0,"슬픔":0.8,"분노":0.1,"불안":0.6,"평온":0.0,"흥분":0.0},"primary_emotion":"슬픔","comfort_message":"시험 결과가 기대와 달라 많이 속상하시겠어요. 이번 경험이 다음에는 더 나은 결과로 이어질 거예요.","tags":["시험","실망"]}

일기: "친구들이랑 놀이공원 갔다!"
{"summary":"친구들과 놀이공원에서 즐거운 시간","sentiment":{"label":"긍정","score":0.9},"emotion_scores":{"행복":0.9,"슬픔":0.0,"분노":0.0,"불안":0.0,"평온":0.1,"흥분":0.8},"primary_emotion":"행복","comfort_message":"친구들과 함께한 시간이 정말 즐거웠나 봐요! 이런 행복한 순간들이 계속 이어지길 바랍니다.","tags":["놀이공원","친구","행복"]}

중요: JSON만 출력하고 마크다운(```)이나 설명은 쓰지 마세요."""

def _coerce_emotions(d: Dict[str, Any]) -> Dict[str, float]:
    # 한국어 키를 영어 키로 매핑
    mapping = {
        "행복": "happiness",
        "슬픔": "sadness",
        "분노": "anger",
        "불안": "anxiety",
        "평온": "calmness",
        "흥분": "excitement",
    }
    out = {}
    for kr_key, en_key in mapping.items():
        v = float(d.get(kr_key, 0.0) or 0.0)
        if v < 0: v = 0.0
        if v > 1: v = 1.0
        out[en_key] = round(v, 2)
    return out

def _safe_json_loads(text: str) -> Dict[str, Any]:
    """모델 출력에서 JSON 추출 및 파싱"""
    text = text.strip()

    # 1. 첫 번째 { 찾기
    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("No JSON object found in text")

    # 2. 중첩된 괄호를 고려하여 매칭되는 } 찾기
    count = 0
    end_idx = -1
    for i in range(start_idx, len(text)):
        if text[i] == '{':
            count += 1
        elif text[i] == '}':
            count -= 1
            if count == 0:
                end_idx = i + 1
                break

    if end_idx == -1:
        raise ValueError("No matching closing brace found")

    # 3. JSON 문자열 추출 및 파싱
    json_str = text[start_idx:end_idx]
    return json.loads(json_str)

class AIAnalysisService:
    """로컬 모델 기반 일기 분석/생성 서비스"""

    def __init__(self):
        import os
        # HuggingFace 토큰 설정
        if settings.hf_token:
            os.environ["HUGGINGFACE_TOKEN"] = settings.hf_token
            os.environ["HF_TOKEN"] = settings.hf_token

        print(f"Loading model: {settings.hf_model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            settings.hf_model_id,
            token=settings.hf_token
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            settings.hf_model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            token=settings.hf_token
        )
        print("Model loaded successfully!")

    def _generate_text(self, prompt: str) -> str:
        """동기 함수: 실제 모델 실행"""
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

            # temperature가 너무 낮으면 inf/nan 문제 발생 가능
            temperature = max(settings.hf_temperature, 0.1)

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=settings.hf_max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

            # 프롬프트 제거 (입력 토큰 수만큼 제거)
            input_length = inputs['input_ids'].shape[1]
            output_tokens = outputs[0][input_length:]
            result = self.tokenizer.decode(output_tokens, skip_special_tokens=True)

            return result.strip()
        except RuntimeError as e:
            # multinomial 샘플링 오류 발생 시 greedy decoding으로 재시도
            print(f"WARNING: Sampling error ({e}), retrying with greedy decoding...")
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=settings.hf_max_tokens,
                do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )
            input_length = inputs['input_ids'].shape[1]
            output_tokens = outputs[0][input_length:]
            result = self.tokenizer.decode(output_tokens, skip_special_tokens=True)
            return result.strip()

    async def analyze_diary(self, diary_text: str) -> Dict[str, Any]:
        """일기 텍스트를 분석해서 서비스가 기대하는 딕셔너리 구조로 반환
        - 생성 모델이 summary/sentiment/emotion_scores/primary_emotion/comfort_message/tags 를 JSON으로 직접 출력
        """
        # 1) 프롬프트 구성: SYSTEM_PROMPT + 사용자 일기
        prompt = (
            SYSTEM_PROMPT
            + f'\n\n일기: "{diary_text}"\n출력:\n'
        )

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, partial(self._generate_text, prompt))

        # 2) JSON 파싱 (```json .. ``` 방지용)
        try:
            parsed = _safe_json_loads(raw)
        except Exception as e:
            # 파싱 실패 시, 최소한의 폴백 (요약·태그·감정 라벨은 간단 생성)
            print(f"JSON 파싱 실패: {e}")
            print(f"모델 원본 출력: {raw[:200]}")
            parsed = {
                "summary": diary_text[:50] + "..." if len(diary_text) > 50 else diary_text,
                "sentiment": {"label": "중립", "score": 0.5},
                "emotion_scores": {"행복": 0.2, "슬픔": 0.2, "분노": 0.2, "불안": 0.2, "평온": 0.2, "흥분": 0.2},
                "primary_emotion": "평온",
                "comfort_message": "일기를 작성해주셔서 감사합니다. 오늘 하루도 수고하셨어요!",
                "tags": ["일기", "자동분석"],
            }

        # 3) emotion_scores 한-영 키 정리 + 범위 보정
        if isinstance(parsed.get("emotion_scores"), dict):
            parsed["emotion_scores"] = _coerce_emotions(parsed["emotion_scores"])

        # 4) sentiment 기본값 보정
        sent = parsed.get("sentiment") or {}
        # sentiment가 문자열인 경우 처리
        if isinstance(sent, str):
            label = sent.strip()
        elif isinstance(sent, dict):
            label = (sent.get("label") or "중립").strip()
        else:
            label = "중립"

        # 영어 label을 한국어로 변환
        label_mapping = {
            "positive": "긍정",
            "negative": "부정",
            "neutral": "중립",
        }
        label = label_mapping.get(label.lower(), label)

        # 유효하지 않은 label은 중립으로 처리
        if label not in ["긍정", "중립", "부정"]:
            label = "중립"

        score = float(sent.get("score") or 0.5)
        score = max(0.0, min(1.0, round(score, 2)))
        parsed["sentiment"] = {"label": label, "score": score}

        # 5) primary_emotion 보정 - 유효하지 않으면 emotion_scores에서 최댓값 찾기
        primary_emotion = (parsed.get("primary_emotion") or "").strip()
        valid_emotions = ["행복", "슬픔", "분노", "불안", "평온", "흥분"]
        if primary_emotion not in valid_emotions:
            # emotion_scores에서 한국어 키 중 최댓값 찾기
            emotion_scores_kr = {}
            if isinstance(parsed.get("emotion_scores"), dict):
                kr_mapping = {
                    "happiness": "행복",
                    "sadness": "슬픔",
                    "anger": "분노",
                    "anxiety": "불안",
                    "calmness": "평온",
                    "excitement": "흥분",
                }
                for en_key, kr_key in kr_mapping.items():
                    if en_key in parsed["emotion_scores"]:
                        emotion_scores_kr[kr_key] = parsed["emotion_scores"][en_key]

                if emotion_scores_kr:
                    primary_emotion = max(emotion_scores_kr, key=emotion_scores_kr.get)
                else:
                    primary_emotion = "평온"
            else:
                primary_emotion = "평온"

        # 6) comfort_message 보정
        cm = (parsed.get("comfort_message") or "").strip()
        if not cm or len(cm) < 10:  # 너무 짧은 메시지는 기본 메시지 사용
            cm = "일기를 작성해주셔서 감사합니다. 오늘 하루도 수고하셨어요!"
        parsed["comfort_message"] = cm

        # 7) tags 보정
        tags = parsed.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        parsed["tags"] = [str(t) for t in tags][:5]

        return {
            "summary": parsed.get("summary", diary_text[:50] + "..." if len(diary_text) > 50 else diary_text),
            "sentiment": parsed["sentiment"],
            "emotion_scores": parsed.get("emotion_scores", {}),
            "primary_emotion": primary_emotion,
            "comfort_message": parsed["comfort_message"],
            "tags": parsed["tags"],
        }

    async def generate_followup_response(
        self,
        diary_text: str,
        conversation_history: List[Dict[str, str]],
        user_message: str,
    ) -> str:
        """후속 대화 응답: 간결한 한국어 3~5문장"""
        history_txt = "\n".join([f"{h['role']}: {h['message']}" for h in conversation_history])
        prompt = (
            f"일기: {diary_text}\n\n"
            f"대화 기록:\n{history_txt}\n\n"
            f"사용자: {user_message}\n\n"
            "위 대화를 보고 따뜻하고 공감적인 답변을 3-5문장으로 작성해주세요.\n\n답변:"
        )

        # CPU-bound 작업을 별도 스레드에서 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, partial(self._generate_text, prompt))
        return result    
# ---- 싱글톤 인스턴스 & 팩토리 둘 다 노출 ----
_ai_singleton: AIAnalysisService | None = None

def get_ai_service() -> AIAnalysisService:
    global _ai_singleton
    if _ai_singleton is None:
        _ai_singleton = AIAnalysisService()
    return _ai_singleton

ai_service = get_ai_service()

