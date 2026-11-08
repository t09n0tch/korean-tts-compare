# Korean CPU TTS Compare

같은 한국어 문장을 **Supertonic 3, MeloTTS Korean, Piper KSS**로 합성해 브라우저에서 나란히 듣는 로컬 도구입니다. 직접 입력한 문장을 모델 순서대로 재생하고, 발음·자연스러움 점수와 메모를 CSV로 저장할 수 있습니다. 합성에는 GPU나 외부 TTS API가 필요하지 않습니다. 설치할 때만 모델을 내려받습니다.

## 사용 방법

1. 아래에서 운영체제에 맞게 설치하고 서버를 실행합니다.
2. 브라우저에서 **http://127.0.0.1:8766**을 엽니다.
3. **입력 비우기**를 누르고 문장을 입력합니다. 한 줄에 한 문장, 최대 20문장·문장당 500자입니다. **기본 문장 불러오기**로 발음 점검용 8문장을 사용할 수도 있습니다.
4. 모델을 고르고 **비교 음성 만들기**를 누릅니다. 문장별 플레이어나 **모델 순서대로 듣기**로 재생합니다.
5. 점수와 메모를 남긴 뒤 **평가 CSV 저장**을 누릅니다. 개별 WAV도 다운로드할 수 있습니다.

설치 스크립트는 각 모델의 짧은 한국어 합성을 확인합니다. 기본 8문장의 전체 비교 음성은 화면에서 **비교 음성 만들기**를 눌러 생성합니다.

## 상담 대사 음성 예시

제공받은 상담 대사 5개를 각 모델의 기본 음성으로 합성했습니다. **Supertonic 3은 F1, MeloTTS는 KR, Piper는 KSS**를 사용했습니다. MP3 링크를 누르면 브라우저에서 듣거나 파일로 저장할 수 있습니다. 모델마다 화자와 음량이 다르므로 발음과 문장 흐름을 중심으로 비교하세요. 대사 원문은 [data/counseling-samples.json](data/counseling-samples.json)에 있습니다. 저장소의 MIT 라이선스는 이 프로젝트의 코드에 적용됩니다. 음성 예시를 다른 용도로 사용할 때에는 모델별 사용 조건도 확인하세요.

### 1. 공감과 수용

> 그동안 혼자서 많은 걸 감당해 오셨던 것 같아요. 어떤 순간이 가장 힘들게 느껴지셨나요?

[▶ Supertonic 3](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/supertonic/s01.mp3) · [▶ MeloTTS Korean](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/melo/s01.mp3) · [▶ Piper KSS](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/piper/s01.mp3)

### 2. 감정 탐색

> 그 상황에서 화가 나셨다고 말씀하셨는데, 혹시 그 감정 안에 서운함이나 두려움도 있었을까요?

[▶ Supertonic 3](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/supertonic/s02.mp3) · [▶ MeloTTS Korean](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/melo/s02.mp3) · [▶ Piper KSS](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/piper/s02.mp3)

### 3. 자기이해 유도

> 스스로에게 굉장히 높은 기준을 적용하고 계신 것 같아요. 그 기준에 미치지 못했을 때 자신을 어떻게 바라보시나요?

[▶ Supertonic 3](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/supertonic/s03.mp3) · [▶ MeloTTS Korean](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/melo/s03.mp3) · [▶ Piper KSS](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/piper/s03.mp3)

### 4. 관점 전환

> 친한 친구가 똑같은 상황을 겪고 있다면 어떤 말을 해주실 것 같으세요? 그 말을 자신에게도 해줄 수 있을까요?

[▶ Supertonic 3](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/supertonic/s04.mp3) · [▶ MeloTTS Korean](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/melo/s04.mp3) · [▶ Piper KSS](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/piper/s04.mp3)

### 5. 변화와 회복

> 지금 당장 모든 문제를 해결할 필요는 없어요. 오늘 이야기한 것 중에서 가장 먼저 바꿔보고 싶은 부분은 무엇인가요?

[▶ Supertonic 3](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/supertonic/s05.mp3) · [▶ MeloTTS Korean](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/melo/s05.mp3) · [▶ Piper KSS](https://raw.githubusercontent.com/t09n0tch/korean-tts-compare/main/examples/audio/piper/s05.mp3)

## Windows 10/11: WSL2 Ubuntu

세 모델을 함께 쓰는 Windows 경로는 **WSL2 Ubuntu**입니다. PowerShell을 관리자 권한으로 열고 다음을 실행합니다. Windows가 재시작을 요청하면 재시작한 뒤 Ubuntu를 엽니다. 이미 WSL2 Ubuntu가 있다면 건너뜁니다.

```powershell
wsl --install -d Ubuntu
```

이후 명령은 **Ubuntu 터미널 안에서** 실행합니다. 모델 파일은 WSL 홈 디렉터리에 두는 편이 읽기 속도에 유리합니다.

```bash
sudo apt update
sudo apt install -y git curl libsndfile1
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
cd ~
git clone https://github.com/t09n0tch/korean-tts-compare.git
cd korean-tts-compare
bash setup-all.sh
.venvs/piper/bin/python serve.py
```

Ubuntu 터미널을 열어 둔 채 Windows의 Edge 또는 Chrome에서 **http://localhost:8766**을 엽니다. [Microsoft의 WSL localhost 안내](https://learn.microsoft.com/windows/wsl/networking)에 따라 Windows 브라우저에서 WSL의 로컬 서버에 연결합니다. 서버 종료는 Ubuntu 터미널에서 `Ctrl+C`입니다. Linux에서는 PyTorch의 CPU 빌드를 설치합니다.

## macOS / Linux

`git`, `uv`, `curl`이 필요합니다. `uv`는 [공식 설치 안내](https://docs.astral.sh/uv/getting-started/installation/)에 따라 설치합니다. macOS에서는 `brew install git uv`를 사용할 수 있습니다. Ubuntu에서는 `sudo apt install -y git curl libsndfile1`을 먼저 실행합니다.

```bash
git clone https://github.com/t09n0tch/korean-tts-compare.git
cd korean-tts-compare
bash setup-all.sh
.venvs/piper/bin/python serve.py
```

macOS에서는 `start.command`를 더블클릭해 서버와 브라우저를 열 수도 있습니다. 8766번 포트가 사용 중이면 `serve.py --port 8767`로 시작하고 브라우저에서 `http://127.0.0.1:8767`을 엽니다.

## 비교 기준과 파일

세 모델에 **동일한 원문**을 보냅니다. 숫자 읽기와 발음 변환은 각 모델의 전처리를 그대로 사용합니다. 화자·음량·샘플레이트도 다르므로 발음 오류와 목소리 취향을 구분해 평가하세요. **RTF = 합성 시간 ÷ 생성된 음성 길이**이며 1보다 작으면 재생 시간보다 빠르게 합성한 것입니다. 모델 로딩 시간은 별도로 표시합니다. 다른 CPU의 속도 수치로 옮겨 해석할 수 없습니다.

기본 문장은 [data/samples.json](data/samples.json)에 있습니다. 받침·연음·겹받침, 숫자·날짜의 원문과 한글 표기, 영문 약어, 질문 억양이 포함됩니다.

| 위치 | 내용 |
|---|---|
| `outputs/<작업 ID>/job.json` | 문장, 실행 컴퓨터, 모델별 결과·오류 |
| `outputs/<작업 ID>/<모델>/*.wav` | 문장별 음성 |
| `outputs/<작업 ID>/<모델>/result.json` | 음성 길이·합성 시간·RTF |
| `outputs/<작업 ID>/<모델>/run.log` | 오류 확인용 실행 로그 |
| `data/<모델>.ready.json` | 설치와 짧은 합성 확인 표시 |

점수와 메모는 브라우저의 저장 공간에 보관됩니다. 다른 기기로 옮기거나 오래 보관하려면 **평가 CSV 저장**을 사용하세요. 모델, 생성 음성, 캐시, 개인별 실행 기록은 Git 저장소에 포함되지 않습니다. 설치된 전체 크기는 macOS 테스트 환경에서 약 2.6GB였으며 운영체제에 따라 달라집니다.

CLI에서도 합성할 수 있습니다.

```bash
.venvs/piper/bin/python compare.py --text "책을 읽고 밥을 먹은 뒤, 밖으로 나갔습니다." --models supertonic melo piper --threads 4
```

## 모델 출처와 검증 범위

| 모델 | 출처·사용 조건 |
|---|---|
| Supertonic 3 | [소스](https://github.com/supertone-oss-archive/supertonic), [모델](https://huggingface.co/supertone-oss-archive/supertonic-3). 소스 MIT, 모델 OpenRAIL-M. 공식 개발·지원은 2026년 9월 종료되었습니다. |
| MeloTTS Korean | [소스](https://github.com/myshell-ai/MeloTTS), [한국어 모델](https://huggingface.co/myshell-ai/MeloTTS-Korean). MIT. CPU 실행과 한국어 전처리를 위해 `setup/melo_prepare.py`의 호환 패치를 적용합니다. |
| Piper KSS | [엔진](https://github.com/OHF-Voice/piper1-gpl), [한국어 모델](https://huggingface.co/rhasspy/piper-voices/blob/main/ko/ko_KR/kss/medium/MODEL_CARD). 엔진 GPL-3.0. 모델카드의 학습 데이터셋은 CC BY-NC-SA 4.0으로 표기되어 있어 상업용 이용 시 조건 확인이 필요합니다. |

개발 중 **Apple M6 macOS에서 CPU만 사용해 세 모델의 기본 8문장, 총 24개 WAV**를 생성하고 파일·서버 응답을 확인했습니다. Windows/WSL2 실기기 합성은 아직 검증하지 않았습니다. 플랫폼별 설치 문제는 실행 로그와 함께 GitHub 이슈로 알려 주세요.

휴대폰 접속에는 별도의 HTTPS 터널이 필요합니다. `mobile_gateway.py`는 개인 접속 키를 확인하고 로컬 서버로 요청을 전달하는 선택 기능입니다. 임시 접속 키와 터널 주소는 공개 저장소에 포함되지 않습니다.
