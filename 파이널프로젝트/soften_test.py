"""화난 목소리 녹음을 두 단계로 누그러뜨려, 보정 전후를 귀로 비교하기 위한 시험 스크립트.

사용법:  python soften_test.py 녹음.wav
출력:    녹음_soft1.wav  크기 압축 + 거친 고음 깎기 (실시간 처리가 쉬운 방식)
         녹음_soft2.wav  soft1 + 억양 평탄화 + 음높이 살짝 낮추기

실시간 버전이 아니라 파일 단위 시험용이다. 목적은 "이 방식으로 차분하게 들리는가"를 먼저 확인하는 것.
"""
import sys
from pathlib import Path

import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

FRAME = 0.02            # 크기 측정 단위 20ms
RATIO = 4.0             # 기준보다 큰 소리는 4분의 1 기울기로 눌러 준다
HARSH_BAND = (2000, 5000)  # 고함에서 거칠게 긁히는 성분이 몰리는 대역
HARSH_CUT = 0.5         # 그 대역을 절반으로
PITCH_SPREAD = 0.5      # 억양 폭을 절반으로 (치솟는 음을 평평하게)
PITCH_SHIFT = 0.92      # 전체 음높이를 8% 낮춤 (약 1.4반음)


def frame_rms(x, fs):
    n = int(FRAME * fs)
    frames = x[: len(x) // n * n].reshape(-1, n)
    return np.sqrt((frames ** 2).mean(axis=1) + 1e-12), n


def soften_level1(x, fs):
    band = sosfiltfilt(butter(4, HARSH_BAND, "bandpass", fs=fs, output="sos"), x)
    x = x - HARSH_CUT * band

    rms, n = frame_rms(x, fs)
    # 기준 크기를 고정값 대신 "이 사람의 평소 말소리"로 잡아야 녹음 음량과 상관없이 동작한다
    threshold = np.median(rms[rms > rms.max() * 0.05])
    gain = np.where(rms > threshold, (rms / threshold) ** (1 / RATIO - 1), 1.0)
    # 프레임 경계에서 툭툭 끊기지 않도록 이득을 샘플 단위로 부드럽게 잇는다
    centers = np.arange(len(gain)) * n + n / 2
    gain = np.interp(np.arange(len(x)), centers, gain)
    return x * gain


def soften_level2(x, fs):
    f0, sp, ap = pw.wav2world(x.astype(np.float64), fs)
    voiced = f0 > 0
    log_f0 = np.log(f0[voiced])
    center = log_f0.mean()
    f0[voiced] = np.exp(center + (log_f0 - center) * PITCH_SPREAD) * PITCH_SHIFT
    y = pw.synthesize(f0, sp, ap, fs)[: len(x)]
    return soften_level1(y, fs)


def describe(name, x, fs):
    rms, _ = frame_rms(x, fs)
    loud = 20 * np.log10(np.percentile(rms, 90))
    f0, _ = pw.harvest(x.astype(np.float64), fs)
    semitones = 12 * np.log2(f0[f0 > 0])
    print(f"{name:8s}  큰 구간 크기 {loud:6.1f} dB   "
          f"평균 음높이 {np.exp2(semitones.mean() / 12):6.1f} Hz   "
          f"억양 폭 {semitones.std():4.1f} 반음")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    x, fs = sf.read(src, always_2d=True)
    x = x.mean(axis=1)  # 스테레오면 모노로

    outputs = {"원본": x, "soft1": soften_level1(x, fs), "soft2": soften_level2(x, fs)}
    for name, y in outputs.items():
        describe(name, y, fs)
        if name != "원본":
            peak = np.abs(y).max()
            sf.write(src.with_name(f"{src.stem}_{name}.wav"), y / peak * 0.9 if peak > 1 else y, fs)
    print(f"저장 위치: {src.parent}")


if __name__ == "__main__":
    main()
