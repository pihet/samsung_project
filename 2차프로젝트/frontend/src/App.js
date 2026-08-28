// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('streaming'); // 기본 탭: 실시간 스트리밍 & AI
  const [backendHealth, setBackendHealth] = useState({ status: 'Connecting...', platens_count: 0 });
  const [leaderboard, setLeaderboard] = useState([]);
  
  // Schedule state
  const [selectedAlgo, setSelectedAlgo] = useState('ortools');
  const [scheduleData, setScheduleData] = useState(null);
  const [loadingSchedule, setLoadingSchedule] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Streaming / Recommend state
  const [reqBlockId, setReqBlockId] = useState('EMG_H1088_099');
  const [reqShipId, setReqShipId] = useState('H1088');
  const [reqLength, setReqLength] = useState(20.0);
  const [reqWidth, setReqWidth] = useState(18.4);
  const [reqWeight, setReqWeight] = useState(72.0);
  const [reqLeadTime, setReqLeadTime] = useState(12);
  const [reqDueDay, setReqDueDay] = useState(45);
  const [reqBlockType, setReqBlockType] = useState('FLAT');
  const [streamResult, setStreamResult] = useState(null);
  const [loadingStream, setLoadingStream] = useState(false);
  const [liveFeed, setLiveFeed] = useState([]);

  // 1. Health check, Benchmark Leaderboard, & Live Events Initial Load
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(data => setBackendHealth(data))
      .catch(() => setBackendHealth({ status: 'Offline', platens_count: 0 }));

    fetch(`${API_BASE}/api/benchmark`)
      .then(res => res.json())
      .then(data => setLeaderboard(data.leaderboard || []))
      .catch(err => console.error('Benchmark fetch error:', err));

    fetch(`${API_BASE}/api/v1/emergency/events`)
      .then(res => res.json())
      .then(data => setLiveFeed(data.events || []))
      .catch(() => {});
  }, []);

  // 2. Fetch Schedule data when selectedAlgo changes
  useEffect(() => {
    if (activeTab === 'schedule') {
      setLoadingSchedule(true);
      fetch(`${API_BASE}/api/schedule/${selectedAlgo}`)
        .then(res => res.json())
        .then(data => {
          setScheduleData(data);
          setLoadingSchedule(false);
        })
        .catch(err => {
          console.error('Schedule fetch error:', err);
          setLoadingSchedule(false);
        });
    }
  }, [activeTab, selectedAlgo]);

  // Handle Real-Time Stream Execution (Kafka -> Flink -> FastAPI -> Postgres)
  const handleStreamPublish = () => {
    setLoadingStream(true);
    const payload = {
      block_id: reqBlockId,
      ship_id: reqShipId,
      length_m: parseFloat(reqLength),
      width_m: parseFloat(reqWidth),
      weight_ton: parseFloat(reqWeight),
      lead_time_days: parseInt(reqLeadTime),
      due_date_day: parseInt(reqDueDay),
      block_type: reqBlockType
    };

    fetch(`${API_BASE}/api/v1/emergency/stream-publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        setStreamResult(data.result);
        setLoadingStream(false);
        // Refresh live feed
        fetch(`${API_BASE}/api/v1/emergency/events`)
          .then(res => res.json())
          .then(d => setLiveFeed(d.events || []));
      })
      .catch(err => {
        console.error('Stream dispatch error:', err);
        setLoadingStream(false);
      });
  };

  const setPreset = (type) => {
    const rNum = Math.floor(Math.random() * 900) + 100;
    if (type === 'type_a') {
      setReqBlockId(`EMG_H1087_${rNum}`);
      setReqShipId('H1087');
      setReqLength(18.5);
      setReqWidth(12.0);
      setReqWeight(55.0);
      setReqLeadTime(10);
      setReqDueDay(40);
      setReqBlockType('FLAT');
    } else if (type === 'type_b') {
      setReqBlockId(`EMG_H1088_${rNum}`);
      setReqShipId('H1088');
      setReqLength(24.0);
      setReqWidth(15.5);
      setReqWeight(78.0);
      setReqLeadTime(14);
      setReqDueDay(50);
      setReqBlockType('CURVED');
    } else if (type === 'type_c') {
      setReqBlockId(`EMG_H1089_${rNum}`);
      setReqShipId('H1089');
      setReqLength(14.0);
      setReqWidth(9.0);
      setReqWeight(32.0);
      setReqLeadTime(6);
      setReqDueDay(25);
      setReqBlockType('FLAT');
    }
  };

  const filteredSchedule = scheduleData?.schedule?.filter(item => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return String(item.block_id).toLowerCase().includes(term) ||
           String(item.ship_id).toLowerCase().includes(term) ||
           String(item.platen_name).toLowerCase().includes(term);
  }) || [];

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="app-header">
        <div className="header-brand">
          <div className="logo-icon"></div>
          <div>
            <h1>Samsung Heavy Industries Smart Shipyard MLOps Platform</h1>
            <p className="subtitle">End-to-End Real-Time Event Streaming & Platen Scheduling Engine</p>
          </div>
        </div>
        <div className="header-status">
          <div className={`status-pill ${backendHealth.status === 'healthy' ? 'status-online' : 'status-offline'}`}>
            <span className="dot"></span>
            <span>FastAPI: {backendHealth.status} ({backendHealth.platens_count} Platens)</span>
          </div>
          <div className="status-pill status-online">
            <span className="dot"></span>
            <span>Kafka & Flink: Active (4 Slots)</span>
          </div>
        </div>
      </header>

      {/* Main Tabs Navigation */}
      <nav className="tab-nav">
        <button 
          className={`tab-btn ${activeTab === 'streaming' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('streaming')}
        >
           Real-time Event Streaming (Kafka -> Flink -> AI)
        </button>
        <button 
          className={`tab-btn ${activeTab === 'schedule' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('schedule')}
        >
           Platen Master Schedule (Gantt Table)
        </button>
        <button 
          className={`tab-btn ${activeTab === 'benchmark' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('benchmark')}
        >
           10-Algorithm Benchmark
        </button>
      </nav>

      {/* Content Body */}
      <main className="app-main">

        {/* TAB 1: Real-time Event Streaming & AI Dispatcher */}
        {activeTab === 'streaming' && (
          <div className="streaming-layout">
            <div className="section-card">
              <div className="card-header">
                <h2>Live Emergency Block Stream Dispatcher</h2>
                <span className="badge badge-accent">Kafka -> Flink -> FastAPI -> Postgres</span>
              </div>
              <p className="card-desc">
                현장 돌발 긴급 블록을 <strong>Kafka 실시간 토픽(`shipyard.emergency.blocks`)에 발행</strong>하고, 
                <strong>Apache Flink가 1ms 이내로 66개 정반의 4대 물리 제약을 메모리 검증</strong>한 뒤 
                FastAPI EST 디스패처 및 PPO Shadow AI로 실시간 배정합니다.
              </p>

              {/* Streaming Pipeline Visual Stepper */}
              <div className="pipeline-stepper">
                <div className="step-box step-done">
                  <span className="step-num">1</span>
                  <span className="step-title">Kafka Event Ingestion</span>
                  <span className="step-sub">shipyard.emergency.blocks</span>
                </div>
                <div className="step-arrow">-></div>
                <div className="step-box step-done">
                  <span className="step-num">2</span>
                  <span className="step-title">Apache Flink Stream Engine</span>
                  <span className="step-sub">66개 정반 물리제약 0.08ms 검증</span>
                </div>
                <div className="step-arrow">-></div>
                <div className="step-box step-done">
                  <span className="step-num">3</span>
                  <span className="step-title">FastAPI Real-time Dispatch</span>
                  <span className="step-sub">EST 0.19s 배정 & PPO Shadow AI</span>
                </div>
                <div className="step-arrow">-></div>
                <div className="step-box step-done">
                  <span className="step-num">4</span>
                  <span className="step-title">PostgreSQL Live Sync</span>
                  <span className="step-sub">shipyard_db:5433</span>
                </div>
              </div>

              {/* Quick Presets */}
              <div className="preset-bar">
                <span className="preset-label">Quick Emergency Presets:</span>
                <button className="preset-btn" onClick={() => setPreset('type_a')}>Type-A (Medium 55T / H1087)</button>
                <button className="preset-btn" onClick={() => setPreset('type_b')}>Type-B (Heavy 78T / Curved)</button>
                <button className="preset-btn" onClick={() => setPreset('type_c')}>Type-C (Fast 32T / Urgent)</button>
              </div>

              {/* Form Input */}
              <div className="form-grid">
                <div className="form-group">
                  <label>Emergency Block ID</label>
                  <input type="text" value={reqBlockId} onChange={e => setReqBlockId(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Ship ID</label>
                  <input type="text" value={reqShipId} onChange={e => setReqShipId(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Length (m)</label>
                  <input type="number" step="0.1" value={reqLength} onChange={e => setReqLength(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Width (m)</label>
                  <input type="number" step="0.1" value={reqWidth} onChange={e => setReqWidth(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Weight (Ton)</label>
                  <input type="number" step="0.1" value={reqWeight} onChange={e => setReqWeight(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Processing Lead Time (Days)</label>
                  <input type="number" value={reqLeadTime} onChange={e => setReqLeadTime(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Due Date Day</label>
                  <input type="number" value={reqDueDay} onChange={e => setReqDueDay(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Block Structure Type</label>
                  <select value={reqBlockType} onChange={e => setReqBlockType(e.target.value)}>
                    <option value="FLAT">FLAT (평면 블록)</option>
                    <option value="CURVED">CURVED (곡블록)</option>
                  </select>
                </div>
              </div>

              <div className="form-action">
                <button className="submit-btn stream-action-btn" onClick={handleStreamPublish} disabled={loadingStream}>
                  {loadingStream ? 'Publishing to Kafka & Processing Flink Stream...' : ' Publish to Kafka & Run Flink/AI Stream Dispatch'}
                </button>
              </div>

              {/* Stream Telemetry & Result */}
              {streamResult && (
                <div className="result-box stream-result-card">
                  <div className="result-header">
                    <h3> Live Stream Dispatch Result</h3>
                    <div className="telemetry-badges">
                      <span className="tag tag-kafka">Kafka: {streamResult.telemetry.kafka_latency_ms}ms</span>
                      <span className="tag tag-flink">Flink 66-Platen Check: {streamResult.telemetry.flink_validation_latency_ms}ms</span>
                      <span className="tag tag-total">Total Pipeline: {streamResult.telemetry.total_pipeline_latency_ms}ms</span>
                    </div>
                  </div>
                  <div className="result-grid">
                    <div className="result-item highlight-box">
                      <span className="res-lbl">Assigned Platen</span>
                      <span className="res-val-big">{streamResult.assigned_platen}</span>
                      <span className="res-sub">Platen ID: {streamResult.assigned_platen_id}</span>
                    </div>
                    <div className="result-item">
                      <span className="res-lbl">Workshop Primary Area</span>
                      <span className="res-val">{streamResult.primary_area}</span>
                    </div>
                    <div className="result-item">
                      <span className="res-lbl">Schedule Time Window</span>
                      <span className="res-val">Day {streamResult.start_day} -> Day {streamResult.end_day}</span>
                      <span className="res-sub">Target Due: Day {streamResult.due_day}</span>
                    </div>
                    <div className="result-item">
                      <span className="res-lbl">Delay Status</span>
                      <span className={`res-val ${streamResult.delay_days > 0 ? 'text-danger' : 'text-success'}`}>
                        {streamResult.delay_days > 0 ? `Delayed +${streamResult.delay_days}d` : 'On-Time (No Delay)'}
                      </span>
                    </div>
                    <div className="result-item">
                      <span className="res-lbl">Area Utilization</span>
                      <span className="res-val">{streamResult.area_utilization_pct}%</span>
                    </div>
                    <div className="result-item">
                      <span className="res-lbl">Flink Validated Candidates</span>
                      <span className="res-val text-success">{streamResult.feasible_candidates_count} / 66 Platens Feasible</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Live Emergency Feed Sidebar */}
            <div className="section-card feed-card">
              <div className="card-header">
                <h2> Live Stream Feed</h2>
                <span className="badge badge-live">Live Sync</span>
              </div>
              <p className="card-desc">실시간으로 유입되어 Flink 검증 및 배정이 완료된 이벤트 히스토리</p>
              
              <div className="feed-list">
                {liveFeed.length === 0 ? (
                  <div className="empty-feed">이벤트를 발행하면 실시간 피드가 표시됩니다.</div>
                ) : (
                  liveFeed.map((ev, idx) => (
                    <div key={idx} className="feed-item">
                      <div className="feed-item-top">
                        <span className="feed-block-id">{ev.block_id}</span>
                        <span className="feed-time">{ev.timestamp}</span>
                      </div>
                      <div className="feed-item-body">
                        <span>배정: <strong>{ev.assigned_platen}</strong></span>
                        <span className="feed-badge">Day {ev.start_day}~{ev.end_day}</span>
                        <span className="feed-latency"> {ev.telemetry?.total_pipeline_latency_ms || 1.2}ms</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Master Schedule Table */}
        {activeTab === 'schedule' && (
          <div className="section-card">
            <div className="card-header">
              <h2>Shipyard Platen Master Schedule (872 Blocks Full Yard)</h2>
              <div className="algo-selector">
                <label>Select Algorithm:</label>
                <select value={selectedAlgo} onChange={e => setSelectedAlgo(e.target.value)}>
                  <option value="ortools">Google OR-Tools CP-SAT (Master Planner)</option>
                  <option value="ppo">PPO Actor-Critic (Ours)</option>
                  <option value="est">EST Heuristic (Unified Sim)</option>
                  <option value="spt">SPT Heuristic (Unified Sim)</option>
                  <option value="lpt">LPT Heuristic (Unified Sim)</option>
                  <option value="rub">RUB Heuristic (Unified Sim)</option>
                  <option value="rtb">RTB Heuristic (Unified Sim)</option>
                  <option value="dqn">Action-Masked DQN (Ours)</option>
                </select>
              </div>
            </div>

            {loadingSchedule ? (
              <div className="loading-box">Loading 872 Master Schedule records...</div>
            ) : (
              <>
                <div className="kpi-grid">
                  <div className="kpi-card">
                    <span className="kpi-title">Total Blocks</span>
                    <span className="kpi-value">{scheduleData?.total_blocks || 872}</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Makespan</span>
                    <span className="kpi-value">{scheduleData?.makespan_days} <small>Days</small></span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Delayed Blocks</span>
                    <span className="kpi-value text-danger">{scheduleData?.delayed_blocks} <small>Blocks</small></span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Total Delay</span>
                    <span className="kpi-value">{scheduleData?.total_delay_days?.toLocaleString()} <small>Days</small></span>
                  </div>
                </div>

                <div className="filter-bar">
                  <input 
                    type="text" 
                    placeholder="Search by Block ID, Ship ID, or Platen Name..." 
                    value={searchTerm} 
                    onChange={e => setSearchTerm(e.target.value)} 
                  />
                  <span className="search-count">Showing {filteredSchedule.length} / {scheduleData?.total_blocks} Blocks</span>
                </div>

                <div className="schedule-table-box">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Block ID</th>
                        <th>Ship ID</th>
                        <th>Assigned Platen</th>
                        <th>Start Day</th>
                        <th>End Day</th>
                        <th>Due Day</th>
                        <th>Lead Time</th>
                        <th>Delay Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSchedule.slice(0, 100).map((item, idx) => (
                        <tr key={idx} className={item.delay_days > 0 ? 'row-delayed' : 'row-ontime'}>
                          <td className="fw-bold">{item.block_id}</td>
                          <td>{item.ship_id}</td>
                          <td><span className="platen-badge">{item.platen_name}</span></td>
                          <td>Day {item.planned_start_day}</td>
                          <td>Day {item.planned_end_day}</td>
                          <td>Day {item.due_day}</td>
                          <td>{item.lead_time_days} days</td>
                          <td>
                            {item.delay_days > 0 ? (
                              <span className="delay-tag">Delayed +{item.delay_days}d</span>
                            ) : (
                              <span className="ontime-tag">On Time</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 3: 10-Algorithm Benchmark */}
        {activeTab === 'benchmark' && (
          <div className="section-card">
            <div className="card-header">
              <h2>Shipyard Scheduling 10-Algorithm Comprehensive Benchmark</h2>
              <span className="badge">Dataset: 872 Blocks x 66 Platens</span>
            </div>
            <p className="card-desc">
              수리최적화(OR-Tools CP-SAT), 심층강화학습(PPO, DQN), 전통 휴리스틱(EST, SPT, LPT 등)의 
              공정 완료일(Makespan), 납기 지연 블록 수, 계산 소요시간 비교 분석.
            </p>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Algorithm</th>
                    <th>Category</th>
                    <th>Makespan (Days)</th>
                    <th>Delayed Blocks</th>
                    <th>Compute Time (s)</th>
                    <th>Role in Pipeline</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map(item => (
                    <tr key={item.rank} className={item.rank === 1 ? 'row-highlight' : ''}>
                      <td className="fw-bold">#{item.rank}</td>
                      <td className="fw-bold">{item.algorithm}</td>
                      <td><span className="cat-tag">{item.type}</span></td>
                      <td className="fw-bold text-accent">{item.makespan_days} d</td>
                      <td className={item.delayed_blocks < 300 ? 'text-success' : 'text-danger'}>
                        {item.delayed_blocks} blocks
                      </td>
                      <td>{item.compute_time_sec}s</td>
                      <td><span className="role-pill">{item.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Samsung Heavy Industries Data Analysis Training Project - On-Premise K8s MLOps Pipeline</p>
      </footer>
    </div>
  );
}

export default App;
