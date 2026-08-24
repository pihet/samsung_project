import React, { useState, useEffect } from 'react';
import './App.css';

// FastAPI 백엔드 엔드포인트 URL (포트 8000) ⭐
const API_BASE = 'http://localhost:8000';

function App() {
  const [amount, setAmount] = useState(2500000);
  const [hour, setHour] = useState(14);
  const [category, setCategory] = useState(2);
  const [freq, setFreq] = useState(5);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [modelStatus, setModelStatus] = useState({ accuracy: '99.37%', status: 'Active (MinIO)' });

  // 1. 초기 헬스체크 및 모델 정보 로드
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(data => {
        if (data.model_metadata && data.model_metadata.final_accuracy) {
          setModelStatus({
            accuracy: `${(data.model_metadata.final_accuracy * 100).toFixed(2)}%`,
            status: 'Loaded (MinIO)'
          });
        }
      })
      .catch(() => console.log('Serving backend connecting...'));
  }, []);

  // 2. 실시간 딥러닝 추론 실행
  const handlePredict = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(amount),
          hour: parseFloat(hour),
          item_category: parseFloat(category),
          user_frequency: parseFloat(freq)
        })
      });
      const data = await res.json();
      setResult(data);

      // 히스토리 추가
      const newEntry = {
        id: Date.now(),
        time: new Date().toLocaleTimeString(),
        amount: Number(amount).toLocaleString() + ' 원',
        prob: `${(data.vip_probability * 100).toFixed(1)}%`,
        decision: data.decision,
        isVip: data.is_vip,
        latency: `${data.inference_time_ms} ms`
      };
      setHistory(prev => [newEntry, ...prev.slice(0, 4)]);
    } catch (err) {
      alert('추론 요청 실패: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 3. 모델 무중단 핫 리로드
  const handleReload = async () => {
    try {
      const res = await fetch(`${API_BASE}/reload-model`, { method: 'POST' });
      const data = await res.json();
      alert('✅ MinIO로부터 최신 딥러닝 모델이 성공적으로 핫 리로드되었습니다!');
    } catch (err) {
      alert('리로드 실패: ' + err.message);
    }
  };

  return (
    <div className="dashboard-container">
      {/* 헤더 */}
      <div className="header-section">
        <div className="header-title">
          <h1>☸️ MLOps AI Real-Time Inference Platform</h1>
          <p>Kafka ➔ Spark 분산 ETL ➔ MinIO S3 Lake ➔ Keras 딥러닝 ➔ React + FastAPI</p>
        </div>
        <button className="btn-predict" style={{ width: 'auto', padding: '0.6rem 1.2rem', fontSize: '0.9rem' }} onClick={handleReload}>
          🔄 MinIO 모델 핫 리로드
        </button>
      </div>

      {/* 상태 통계 카드 4종 */}
      <div className="status-grid">
        <div className="status-card">
          <span className="label">Cluster Infrastructure</span>
          <span className="value badge-pulse"><span className="pulse-dot"></span> K8s Cluster (K3s)</span>
        </div>
        <div className="status-card">
          <span className="label">Streaming & Storage</span>
          <span className="value">Kafka + MinIO Lake</span>
        </div>
        <div className="status-card">
          <span className="label">Active Model Accuracy</span>
          <span className="value" style={{ color: '#38bdf8' }}>{modelStatus.accuracy}</span>
        </div>
        <div className="status-card">
          <span className="label">Serving Engine</span>
          <span className="value badge-pulse"><span className="pulse-dot"></span> FastAPI Sub-2ms</span>
        </div>
      </div>

      {/* 메인 인터랙티브 패널 */}
      <div className="main-grid">
        {/* 입력 폼 */}
        <div className="glass-panel">
          <div className="panel-header">
            <span>📝 실시간 주문 피처 시뮬레이터</span>
          </div>

          <div className="form-group">
            <label>
              <span>주문 금액 (KRW)</span>
              <strong style={{ color: '#38bdf8' }}>{Number(amount).toLocaleString()} 원</strong>
            </label>
            <input
              type="range"
              min="100000"
              max="5000000"
              step="50000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>
              <span>주문 시간대 (0 ~ 23시)</span>
              <strong>{hour} 시</strong>
            </label>
            <input
              type="range"
              min="0"
              max="23"
              value={hour}
              onChange={(e) => setHour(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label><span>상품 카테고리</span></label>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="1">1. 프리미엄 가전 (MacBook, TV 등)</option>
              <option value="2">2. IT / 모바일 전자기기</option>
              <option value="3">3. 생활 / 패션 잡화</option>
            </select>
          </div>

          <div className="form-group">
            <label>
              <span>과거 구매 횟수</span>
              <strong>{freq} 회</strong>
            </label>
            <input
              type="number"
              min="1"
              max="50"
              value={freq}
              onChange={(e) => setFreq(e.target.value)}
            />
          </div>

          <button className="btn-predict" onClick={handlePredict} disabled={loading}>
            {loading ? '🧠 딥러닝 신경망 추론 연산 중...' : '⚡ 실시간 딥러닝 추론 실행'}
          </button>
        </div>

        {/* 결과 카드 */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="panel-header">
            <span>📊 딥러닝 신경망 판정 결과</span>
          </div>

          <div className="result-card" style={{ flex: 1 }}>
            {result ? (
              <>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>VIP 고객 분류 확률</span>
                <div className="prob-circle">{(result.vip_probability * 100).toFixed(1)}%</div>
                <div className={`decision-tag ${result.is_vip ? 'decision-vip' : 'decision-normal'}`}>
                  {result.decision}
                </div>
                <div className="speed-tag">
                  ⚡ K8s 파드 추론 소요 시간: <strong style={{ color: '#38bdf8' }}>{result.inference_time_ms} ms</strong>
                </div>
              </>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>
                좌측에서 슬라이더를 조절하고<br/><strong>실시간 딥러닝 추론 실행</strong> 버튼을 눌러주세요.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 최근 추론 기록 테이블 */}
      {history.length > 0 && (
        <div className="glass-panel">
          <div className="panel-header">
            <span>🕒 최근 실시간 추론 스트림 이력</span>
          </div>
          <table className="history-table">
            <thead>
              <tr>
                <th>요청 시각</th>
                <th>주문 금액</th>
                <th>VIP 확률</th>
                <th>판정 결과</th>
                <th>소요 시간</th>
              </tr>
            </thead>
            <tbody>
              {history.map(item => (
                <tr key={item.id}>
                  <td>{item.time}</td>
                  <td>{item.amount}</td>
                  <td style={{ fontWeight: 700, color: '#38bdf8' }}>{item.prob}</td>
                  <td>
                    <span className={`decision-tag ${item.isVip ? 'decision-vip' : 'decision-normal'}`} style={{ padding: '0.2rem 0.6rem', fontSize: '0.8rem' }}>
                      {item.decision}
                    </span>
                  </td>
                  <td>{item.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;
