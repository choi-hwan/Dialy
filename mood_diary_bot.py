#!/usr/bin/env python3
"""
하루 기분 요약봇
사용자의 일기를 AI가 요약하고 감정을 분석하여 시각화합니다.
"""

import anthropic
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from collections import Counter

# 한글 폰트 설정 (matplotlib)
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


class MoodDiaryBot:
    def __init__(self, api_key=None):
        """
        MoodDiaryBot 초기화

        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 가져옴)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.diary_history = []

    def analyze_diary(self, diary_text):
        """
        일기 텍스트를 분석하여 요약과 감정을 추출합니다.

        Args:
            diary_text: 사용자가 작성한 일기 텍스트

        Returns:
            dict: {
                'summary': 한 줄 요약,
                'emotions': 감정 리스트,
                'emotion_scores': 감정별 점수 (0-10),
                'primary_emotion': 주요 감정
            }
        """
        prompt = f"""다음은 사용자가 작성한 하루 일기입니다. 이 일기를 분석해주세요.

일기 내용:
{diary_text}

다음 형식의 JSON으로 응답해주세요:
{{
    "summary": "일기 내용을 한 줄로 요약 (30자 이내)",
    "emotions": ["감정1", "감정2", "감정3"],
    "emotion_scores": {{
        "행복": 0-10 점수,
        "슬픔": 0-10 점수,
        "분노": 0-10 점수,
        "불안": 0-10 점수,
        "평온": 0-10 점수,
        "흥분": 0-10 점수
    }},
    "primary_emotion": "가장 주된 감정"
}}

감정은 행복, 슬픔, 분노, 불안, 평온, 흥분 중에서 선택하고, 각 감정의 강도를 0-10 점수로 매겨주세요.
"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Claude의 응답에서 JSON 추출
            response_text = message.content[0].text

            # JSON 파싱
            result = json.loads(response_text)

            # 현재 날짜와 함께 저장
            entry = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'diary': diary_text,
                'analysis': result
            }
            self.diary_history.append(entry)

            return result

        except Exception as e:
            print(f"분석 중 오류 발생: {e}")
            return None

    def visualize_emotions(self, analysis_result):
        """
        감정 분석 결과를 시각화합니다.

        Args:
            analysis_result: analyze_diary()의 반환값
        """
        if not analysis_result:
            print("분석 결과가 없습니다.")
            return

        emotion_scores = analysis_result.get('emotion_scores', {})

        # 막대 그래프로 감정 표시
        emotions = list(emotion_scores.keys())
        scores = list(emotion_scores.values())

        plt.figure(figsize=(10, 6))

        # 색상 지정
        colors = {
            '행복': '#FFD700',
            '슬픔': '#4169E1',
            '분노': '#DC143C',
            '불안': '#9370DB',
            '평온': '#98FB98',
            '흥분': '#FF6347'
        }
        bar_colors = [colors.get(e, '#CCCCCC') for e in emotions]

        bars = plt.bar(emotions, scores, color=bar_colors, alpha=0.7, edgecolor='black')

        # 막대 위에 점수 표시
        for i, (emotion, score) in enumerate(zip(emotions, scores)):
            plt.text(i, score + 0.3, str(score), ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.xlabel('Emotions', fontsize=12, fontweight='bold')
        plt.ylabel('Score (0-10)', fontsize=12, fontweight='bold')
        plt.title(f'Emotion Analysis - Primary: {analysis_result.get("primary_emotion", "N/A")}',
                  fontsize=14, fontweight='bold')
        plt.ylim(0, 11)
        plt.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()

        # 파일로 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'emotion_chart_{timestamp}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n감정 차트가 '{filename}'로 저장되었습니다.")

        plt.show()

    def show_history_summary(self):
        """
        지금까지 기록된 일기들의 감정 통계를 보여줍니다.
        """
        if not self.diary_history:
            print("아직 기록된 일기가 없습니다.")
            return

        print(f"\n총 {len(self.diary_history)}개의 일기가 기록되었습니다.\n")

        # 주요 감정 통계
        primary_emotions = [entry['analysis']['primary_emotion'] for entry in self.diary_history]
        emotion_counts = Counter(primary_emotions)

        print("=== 주요 감정 분포 ===")
        for emotion, count in emotion_counts.most_common():
            percentage = (count / len(self.diary_history)) * 100
            print(f"{emotion}: {count}회 ({percentage:.1f}%)")

        print("\n=== 최근 3개 일기 요약 ===")
        for entry in self.diary_history[-3:]:
            print(f"\n[{entry['date']}]")
            print(f"요약: {entry['analysis']['summary']}")
            print(f"주요 감정: {entry['analysis']['primary_emotion']}")

    def save_history(self, filename='diary_history.json'):
        """
        일기 기록을 JSON 파일로 저장합니다.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.diary_history, f, ensure_ascii=False, indent=2)
        print(f"\n일기 기록이 '{filename}'에 저장되었습니다.")

    def load_history(self, filename='diary_history.json'):
        """
        JSON 파일에서 일기 기록을 불러옵니다.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.diary_history = json.load(f)
            print(f"\n'{filename}'에서 {len(self.diary_history)}개의 일기를 불러왔습니다.")
        except FileNotFoundError:
            print(f"'{filename}' 파일을 찾을 수 없습니다.")


def main():
    """
    메인 실행 함수
    """
    print("=" * 50)
    print("        하루 기분 요약봇에 오신 것을 환영합니다!")
    print("=" * 50)
    print()

    # API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY 환경변수를 설정해주세요.")
        print("예: export ANTHROPIC_API_KEY='your-api-key'")
        return

    # 봇 초기화
    bot = MoodDiaryBot()

    # 기존 기록 불러오기 시도
    bot.load_history()

    while True:
        print("\n" + "=" * 50)
        print("메뉴:")
        print("1. 오늘의 일기 작성하기")
        print("2. 감정 통계 보기")
        print("3. 종료")
        print("=" * 50)

        choice = input("\n선택하세요 (1-3): ").strip()

        if choice == '1':
            print("\n오늘 하루는 어땠나요? 자유롭게 작성해주세요.")
            print("(여러 줄 입력 가능, 입력 완료 후 빈 줄에서 Enter를 두 번 누르세요)\n")

            lines = []
            empty_count = 0
            while True:
                line = input()
                if line == '':
                    empty_count += 1
                    if empty_count >= 2:
                        break
                else:
                    empty_count = 0
                    lines.append(line)

            diary_text = '\n'.join(lines).strip()

            if not diary_text:
                print("일기 내용이 비어있습니다.")
                continue

            print("\n분석 중입니다...\n")

            # 일기 분석
            result = bot.analyze_diary(diary_text)

            if result:
                print("=" * 50)
                print("📝 분석 결과")
                print("=" * 50)
                print(f"\n한 줄 요약: {result['summary']}")
                print(f"\n주요 감정: {result['primary_emotion']}")
                print(f"\n감정 분석:")
                for emotion, score in result['emotion_scores'].items():
                    bar = '█' * score + '░' * (10 - score)
                    print(f"  {emotion}: {bar} ({score}/10)")

                # 감정 시각화
                print("\n감정 차트를 생성 중입니다...")
                bot.visualize_emotions(result)

                # 자동 저장
                bot.save_history()

        elif choice == '2':
            bot.show_history_summary()

        elif choice == '3':
            print("\n오늘도 좋은 하루 보내세요! 👋")
            bot.save_history()
            break

        else:
            print("\n잘못된 선택입니다. 1-3 중에서 선택해주세요.")


if __name__ == "__main__":
    main()
