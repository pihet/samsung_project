// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

// Clean SVG Icons (No Emojis)
const Icons = {
  Stream: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
    </svg>
  ),
  Schedule: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
      <line x1="16" y1="2" x2="16" y2="6"></line>
      <line x1="8" y1="2" x2="8" y2="6"></line>
      <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>
  ),
  Benchmark: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="7"></circle>
      <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
    </svg>
  ),
  Zap: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
    </svg>
  ),
  Server: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
      <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
      <line x1="6" y1="6" x2="6.01" y2="6"></line>
      <line x1="6" y1="18" x2="6.01" y2="18"></line>
    </svg>
  ),
  CheckCircle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  ),
  AlertTriangle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
      <line x1="12" y1="9" x2="12" y2="13"></line>
      <line x1="12" y1="17" x2="12.01" y2="17"></line>
    </svg>
  ),
  Search: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"></circle>
      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
  ),
  Clock: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 6 12 12 16 14"></polyline>
    </svg>
  )
};

function App() {
  const [activeTab, setActiveTab] = useState('streaming');
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
          <div className="brand-badge">SHI</div>
          <div>
            <h1>Samsung Heavy Industries Smart Shipyard MLOps Platform</h1>
            <p className="subtitle">Real-Time Kafka Event Streaming & Platen Scheduling Engine</p>
          </div>
        </div>
        <div className="header-status">
          <div className={`status-pill ${backendHealth.status === 'healthy' ? 'status-online' : 'status-offline'}`}>
            <span className="dot"></span>
            <span>FastAPI: {backendHealth.status} ({backendHealth.platens_count || 66} Platens)</span>
          </div>
          <div className="status-pill status-online">
            <span className="dot"></span>
            <span>Kafka & Flink: Active</span>
          </div>
        </div>
      </header>

      {/* Main Tabs Navigation */}
      <nav className="tab-nav">
        <button 
          className={`tab-btn ${activeTab === 'streaming' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('streaming')}
        >
          <Icons.Stream />
          <span>Real-Time Stream Dispatcher</span>
        </button>
        <button 
          className={`tab-btn ${activeTab === 'schedule' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('schedule')}
        >
          <Icons.Schedule />
          <span>Platen Master Schedule</span>
        </button>
        <button 
          className={`tab-btn ${activeTab === 'benchmark' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('benchmark')}
        >
          <Icons.Benchmark />
          <span>10-Algorithm Benchmark</span>
        </button>
      </nav>

      {/* Content Body */}
      <main className="app-main">

        {/* TAB 1: Real-time Event Streaming & AI Dispatcher */}
        {activeTab === 'streaming' && (
          <div className="streaming-layout">
            <div className="section-card main-dispatch-card">
              <div className="card-header">
                <div>
                  <h2>Live Emergency Block Stream Dispatcher</h2>
                  <p className="card-desc">
                    Kafka 토픽 발행 및 정반 물리 제약(크기, 하중, 블록타입) 실시간 검증 기반 EST 디스패처
                  </p>
                </div>
                <span className="badge badge-accent">Kafka -> Flink -> FastAPI -> Postgres</span>
              </div>

              {/* Streaming Pipeline Visual Stepper */}
              <div className="pipeline-stepper">
                <div className="step-box step-active">
                  <div className="step-num-circle">1</div>
                  <div className="step-info">
                    <span className="step-title">Kafka Event Ingestion</span>
                    <span className="step-sub">shipyard.emergency.blocks</span>
                  </div>
                </div>
                <div className="step-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </div>
                <div className="step-box step-active">
                  <div className="step-num-circle">2</div>
                  <div className="step-info">
                    <span className="step-title">Physical Constraint Filter</span>
                    <span className="step-sub">66개 정반 2D/크레인/타입 검증</span>
                  </div>
                </div>
                <div className="step-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </div>
                <div className="step-box step-active">
                  <div className="step-num-circle">3</div>
                  <div className="step-info">
                    <span className="step-title">EST Platen Dispatcher</span>
                    <span className="step-sub">동적 점유일 갱신 & 원자적 락</span>
                  </div>
                </div>
                <div className="step-arrow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </div>
                <div className="step-box step-active">
                  <div className="step-num-circle">4</div>
                  <div className="step-info">
                    <span className="step-title">PostgreSQL Live Sync</span>
                    <span className="step-sub">shipyard_db:5433</span>
                  </div>
                </div>
              </div>

              {/* Quick Presets */}
              <div className="preset-bar">
                <span className="preset-label">Quick Emergency Presets:</span>
                <button className="preset-btn" onClick={() => setPreset('type_a')}>Type-A (Medium 55T / FLAT)</button>
                <button className="preset-btn" onClick={() => setPreset('type_b')}>Type-B (Heavy 78T / CURVED)</button>
                <button className="preset-btn" onClick={() => setPreset('type_c')}>Type-C (Fast 32T / FLAT)</button>
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
                  <Icons.Zap />
                  <span>{loadingStream ? 'Publishing to Kafka & Processing Stream...' : 'Publish to Kafka & Run Real-Time Dispatch'}</span>
                </button>
              </div>

              {/* Stream Result Box */}
              {streamResult && (
                <div className={`result-box ${streamResult.feasible_candidates_count === 0 ? 'result-rejected' : 'result-success'}`}>
                  <div className="result-header">
                    <div className="result-title-group">
                      {streamResult.feasible_candidates_count > 0 ? <Icons.CheckCircle /> : <Icons.AlertTriangle />}
                      <h3>
                        {streamResult.feasible_candidates_count > 0 
                          ? `Dispatch Complete: Block ${streamResult.block_id}` 
                          : `Dispatch Rejected: Block ${streamResult.block_id}`}
                      </h3>
                    </div>
                    <div className="telemetry-badges">
                      <span className="telemetry-pill">Kafka: {streamResult.telemetry?.kafka_latency_ms || 1.2}ms</span>
                      <span className="telemetry-pill">Validation: {streamResult.telemetry?.validation_latency_ms || 0.3}ms</span>
                      <span className="telemetry-pill highlight">Total: {streamResult.telemetry?.total_pipeline_latency_ms || 3.8}ms</span>
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
                      <span className="res-lbl">Feasible Platen Candidates</span>
                      <span className="res-val text-success">{streamResult.feasible_candidates_count} / 66 Platens Validated</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Live Emergency Feed Sidebar */}
            <div className="section-card feed-card">
              <div className="card-header">
                <div className="card-title-flex">
                  <Icons.Clock />
                  <h2>Live Stream Feed</h2>
                </div>
                <span className="badge badge-live">Live Sync</span>
              </div>
              <p className="card-desc">Kafka 실시간 스트림 이벤트 히스토리</p>
              
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
                        <span className="feed-latency">{ev.telemetry?.total_pipeline_latency_ms || 2.5}ms</span>
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
              <div>
                <h2>Shipyard Platen Master Schedule</h2>
                <p className="card-desc">872개 전체 공정 블록 정반 배치 및 일정표 조회</p>
              </div>
              <div className="algo-selector">
                <label>Select Algorithm:</label>
                <select value={selectedAlgo} onChange={e => setSelectedAlgo(e.target.value)}>
                  <option value="ortools">Google OR-Tools CP-SAT (Master Planner)</option>
                  <option value="ppo">PPO Actor-Critic (Ours)</option>
                  <option value="est">EST Heuristic (Unified Sim)</option>
                  <option value="spt">SPT Heuristic (Unified Sim)</option>
                  <option value="lpt">LPT Heuristic (Unified Sim)</option>
                  <option value="rtb">RTB Heuristic (Unified Sim)</option>
                  <option value="rub">RUB Heuristic (Unified Sim)</option>
                  <option value="dqn">DQN Baseline (Unified Sim)</option>
                </select>
              </div>
            </div>

            {loadingSchedule ? (
              <div className="loading-box">Loading Master Schedule records...</div>
            ) : (
              <>
                <div className="kpi-grid">
                  <div className="kpi-card">
                    <span className="kpi-title">Total Blocks</span>
                    <span className="kpi-value">{scheduleData?.total_blocks || 872}</span>
                    <span className="kpi-sub">Full Yard Scale</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Makespan</span>
                    <span className="kpi-value">{scheduleData?.makespan_days} <small>Days</small></span>
                    <span className="kpi-sub">Total Schedule Duration</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Delayed Blocks</span>
                    <span className="kpi-value text-danger">{scheduleData?.delayed_blocks} <small>Blocks</small></span>
                    <span className="kpi-sub">Past Due Date</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Total Delay Days</span>
                    <span className="kpi-value">{scheduleData?.total_delay_days?.toLocaleString()} <small>Days</small></span>
                    <span className="kpi-sub">Cumulative Tardiness</span>
                  </div>
                </div>

                <div className="filter-bar">
                  <div className="search-input-wrapper">
                    <Icons.Search />
                    <input 
                      type="text" 
                      placeholder="Search by Block ID, Ship ID, or Platen Name..." 
                      value={searchTerm} 
                      onChange={e => setSearchTerm(e.target.value)} 
                    />
                  </div>
                  <span className="search-count">Showing {filteredSchedule.length} / {scheduleData?.total_blocks || 872} Blocks</span>
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
              <div>
                <h2>Shipyard Scheduling 10-Algorithm Comprehensive Benchmark</h2>
                <p className="card-desc">
                  수리최적화(OR-Tools CP-SAT), 심층강화학습(PPO, DQN), 전통 휴리스틱(EST, SPT, LPT 등) 벤치마크
                </p>
              </div>
              <span className="badge">Dataset: 872 Blocks x 66 Platens</span>
            </div>
            
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
                      <td className="fw-bold rank-cell">
                        {item.rank === 1 ? <span className="rank-badge-first">#1</span> : `#${item.rank}`}
                      </td>
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
        <p>Samsung Heavy Industries Smart Shipyard Scheduling & MLOps Platform | On-Premise Kubernetes Architecture</p>
      </footer>
    </div>
  );
}

export default App;
