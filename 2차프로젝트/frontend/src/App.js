// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('benchmark');
  const [backendHealth, setBackendHealth] = useState({ status: 'Connecting...', platens_count: 0 });
  const [leaderboard, setLeaderboard] = useState([]);
  
  // Schedule state
  const [selectedAlgo, setSelectedAlgo] = useState('ortools');
  const [scheduleData, setScheduleData] = useState(null);
  const [loadingSchedule, setLoadingSchedule] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // Recommend state
  const [reqBlockId, setReqBlockId] = useState('B284');
  const [reqShipId, setReqShipId] = useState('H1088');
  const [reqLength, setReqLength] = useState(20.0);
  const [reqWidth, setReqWidth] = useState(18.4);
  const [reqWeight, setReqWeight] = useState(211.0);
  const [reqLeadTime, setReqLeadTime] = useState(72);
  const [reqEstDay, setReqEstDay] = useState(10);
  const [reqDueDay, setReqDueDay] = useState(90);
  const [reqBlockType, setReqBlockType] = useState('FLAT');
  const [recommendResult, setRecommendResult] = useState(null);
  const [loadingRecommend, setLoadingRecommend] = useState(false);

  // 1. Health check & Benchmark Leaderboard
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(data => setBackendHealth(data))
      .catch(() => setBackendHealth({ status: 'Offline', platens_count: 0 }));

    fetch(`${API_BASE}/api/benchmark`)
      .then(res => res.json())
      .then(data => setLeaderboard(data.leaderboard || []))
      .catch(err => console.error('Benchmark fetch error:', err));
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
  }, [selectedAlgo, activeTab]);

  // 3. Handle Real-time Recommendation
  const handleRecommend = async () => {
    setLoadingRecommend(true);
    try {
      const res = await fetch(`${API_BASE}/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          block_id: reqBlockId,
          ship_id: reqShipId,
          length_m: parseFloat(reqLength),
          width_m: parseFloat(reqWidth),
          weight_ton: parseFloat(reqWeight),
          lead_time_days: parseInt(reqLeadTime),
          est_day: parseInt(reqEstDay),
          due_day: parseInt(reqDueDay),
          block_type: reqBlockType
        })
      });
      const data = await res.json();
      setRecommendResult(data);
    } catch (err) {
      alert('Recommendation API error: ' + err.message);
    } finally {
      setLoadingRecommend(false);
    }
  };

  const setPreset = (type) => {
    if (type === 'type_a') {
      setReqBlockId('B101'); setReqLength(16.0); setReqWidth(14.0); setReqWeight(120.0); setReqLeadTime(35); setReqEstDay(20); setReqDueDay(70); setReqBlockType('FLAT');
    } else if (type === 'type_b') {
      setReqBlockId('B836'); setReqLength(6.5); setReqWidth(21.0); setReqWeight(49.0); setReqLeadTime(15); setReqEstDay(5); setReqDueDay(30); setReqBlockType('FLAT');
    } else if (type === 'type_c') {
      setReqBlockId('B284'); setReqLength(20.0); setReqWidth(18.4); setReqWeight(211.0); setReqLeadTime(72); setReqEstDay(10); setReqDueDay(90); setReqBlockType('FLAT');
    } else if (type === 'type_d') {
      setReqBlockId('B412'); setReqLength(24.0); setReqWidth(16.0); setReqWeight(190.0); setReqLeadTime(55); setReqEstDay(0); setReqDueDay(60); setReqBlockType('CURVED');
    }
  };

  const filteredSchedule = scheduleData?.schedule?.filter(item => 
    item.block_id.toString().toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.platen_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.ship_id.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo-badge">SHI MLOps</div>
          <div>
            <h1>Samsung Heavy Industries Smart Shipyard Platen Optimization</h1>
            <p className="subtitle">Reinforcement Learning & Constraint Programming Hybrid Platform</p>
          </div>
        </div>
        <div className="header-right">
          <div className="stat-pill">
            <span className="pill-label">Total Blocks</span>
            <span className="pill-val">872</span>
          </div>
          <div className="stat-pill">
            <span className="pill-label">Total Platens</span>
            <span className="pill-val">66</span>
          </div>
          <div className="stat-pill highlight">
            <span className="pill-label">Best Makespan</span>
            <span className="pill-val">1,216 Days</span>
          </div>
          <div className={`status-indicator ${backendHealth.status === 'healthy' ? 'online' : 'offline'}`}>
            Backend: {backendHealth.status}
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="tab-nav">
        <button className={`tab-btn ${activeTab === 'benchmark' ? 'active' : ''}`} onClick={() => setActiveTab('benchmark')}>
          Benchmark Leaderboard (11 Algorithms)
        </button>
        <button className={`tab-btn ${activeTab === 'schedule' ? 'active' : ''}`} onClick={() => setActiveTab('schedule')}>
          Interactive Gantt Schedule Viewer
        </button>
        <button className={`tab-btn ${activeTab === 'recommend' ? 'active' : ''}`} onClick={() => setActiveTab('recommend')}>
          Real-time AI Platen Recommender
        </button>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {/* TAB 1: Benchmark Leaderboard */}
        {activeTab === 'benchmark' && (
          <div className="section-card">
            <div className="card-header">
              <h2>Algorithm Benchmark Leaderboard</h2>
              <span className="badge">Evaluated on 872 Blocks x 66 Platens</span>
            </div>
            <p className="card-desc">
              Comparison between Google OR-Tools CP-SAT, PPO Actor-Critic, Double DQN, and Research Paper Baselines.
            </p>
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Algorithm</th>
                    <th>Methodology Type</th>
                    <th>Total Makespan</th>
                    <th>Delayed Blocks</th>
                    <th>Compute Time</th>
                    <th>Deployment Role</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((item, idx) => (
                    <tr key={idx} className={item.rank === 1 ? 'rank-gold' : item.rank === 2 ? 'rank-silver' : item.rank === 3 ? 'rank-bronze' : ''}>
                      <td className="rank-cell">#{item.rank}</td>
                      <td className="algo-name">{item.algorithm}</td>
                      <td><span className="type-tag">{item.type}</span></td>
                      <td className="metric-val">{item.makespan_days.toLocaleString()} Days</td>
                      <td>{item.delayed_blocks} / 872 ({((item.delayed_blocks/872)*100).toFixed(1)}%)</td>
                      <td>{item.compute_time_sec} s</td>
                      <td><span className="status-tag">{item.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: Gantt Schedule Viewer */}
        {activeTab === 'schedule' && (
          <div className="section-card">
            <div className="card-header">
              <h2>Interactive Platen Timeline Schedule</h2>
              <div className="algo-selector">
                <button className={`selector-btn ${selectedAlgo === 'ortools' ? 'active' : ''}`} onClick={() => setSelectedAlgo('ortools')}>
                  Google OR-Tools CP-SAT (1,216d)
                </button>
                <button className={`selector-btn ${selectedAlgo === 'ppo' ? 'active' : ''}`} onClick={() => setSelectedAlgo('ppo')}>
                  PPO Actor-Critic (1,398d)
                </button>
                <button className={`selector-btn ${selectedAlgo === 'dqn' ? 'active' : ''}`} onClick={() => setSelectedAlgo('dqn')}>
                  Double DQN (1,533d)
                </button>
              </div>
            </div>

            {loadingSchedule ? (
              <div className="loading-box">Loading 872 block timeline data...</div>
            ) : (
              <>
                <div className="kpi-grid">
                  <div className="kpi-card">
                    <span className="kpi-title">Total Makespan</span>
                    <span className="kpi-number">{scheduleData?.makespan_days} Days</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Delayed Blocks</span>
                    <span className="kpi-number text-danger">{scheduleData?.delayed_blocks} / {scheduleData?.total_blocks}</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">Total Delay Days</span>
                    <span className="kpi-number">{scheduleData?.total_delay_days?.toLocaleString()} Days</span>
                  </div>
                  <div className="kpi-card">
                    <span className="kpi-title">On-time Completion</span>
                    <span className="kpi-number text-success">
                      {scheduleData ? (((scheduleData.total_blocks - scheduleData.delayed_blocks) / scheduleData.total_blocks) * 100).toFixed(1) : 0}%
                    </span>
                  </div>
                </div>

                <div className="search-bar">
                  <input 
                    type="text" 
                    placeholder="Search by Block ID, Ship ID, or Platen Name (e.g. B284, H1088, Bay48)..." 
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
                  {filteredSchedule.length > 100 && (
                    <div className="table-footer-note">Showing first 100 rows of {filteredSchedule.length} filtered items.</div>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 3: Real-time AI Recommender */}
        {activeTab === 'recommend' && (
          <div className="section-card">
            <div className="card-header">
              <h2>Real-time AI Platen Placement Recommender (PPO Inference)</h2>
              <span className="badge">Latency: &lt;10 ms</span>
            </div>
            <p className="card-desc">
              Input new or emergency block specifications to evaluate against 66 platens and receive instant optimal allocation.
            </p>

            <div className="preset-bar">
              <span className="preset-label">Quick Presets:</span>
              <button className="preset-btn" onClick={() => setPreset('type_a')}>Type-A (Standard 120T)</button>
              <button className="preset-btn" onClick={() => setPreset('type_b')}>Type-B (Small 49T)</button>
              <button className="preset-btn" onClick={() => setPreset('type_c')}>Type-C (Heavy 211T)</button>
              <button className="preset-btn" onClick={() => setPreset('type_d')}>Type-D (Curved Urgent)</button>
            </div>

            <div className="form-grid">
              <div className="form-group">
                <label>Block ID</label>
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
                <label>Lead Time (Days)</label>
                <input type="number" value={reqLeadTime} onChange={e => setReqLeadTime(e.target.value)} />
              </div>
              <div className="form-group">
                <label>EST Day (Start Window)</label>
                <input type="number" value={reqEstDay} onChange={e => setReqEstDay(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Due Day (Target)</label>
                <input type="number" value={reqDueDay} onChange={e => setReqDueDay(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Block Type</label>
                <select value={reqBlockType} onChange={e => setReqBlockType(e.target.value)}>
                  <option value="FLAT">FLAT (Flat Block)</option>
                  <option value="CURVED">CURVED (Curved Block)</option>
                </select>
              </div>
            </div>

            <div className="form-action">
              <button className="submit-btn" onClick={handleRecommend} disabled={loadingRecommend}>
                {loadingRecommend ? 'Running Neural Inference...' : 'Execute PPO Optimal Placement'}
              </button>
            </div>

            {recommendResult && (
              <div className="result-box">
                <div className="result-header">
                  <h3>AI Optimal Allocation Result</h3>
                  <span className="speed-tag">{recommendResult.inference_time_ms} ms</span>
                </div>
                <div className="result-grid">
                  <div className="result-item highlight-box">
                    <span className="res-lbl">Recommended Platen</span>
                    <span className="res-val-big">{recommendResult.recommended_platen_name}</span>
                    <span className="res-sub">Platen ID: {recommendResult.recommended_platen_id}</span>
                  </div>
                  <div className="result-item">
                    <span className="res-lbl">Primary Workshop Area</span>
                    <span className="res-val">{recommendResult.primary_area}</span>
                  </div>
                  <div className="result-item">
                    <span className="res-lbl">Platen Dimensions</span>
                    <span className="res-val">{recommendResult.platen_dimensions}</span>
                  </div>
                  <div className="result-item">
                    <span className="res-lbl">Crane Capacity</span>
                    <span className="res-val">{recommendResult.crane_capacity_ton} Ton</span>
                  </div>
                  <div className="result-item">
                    <span className="res-lbl">Area Utilization</span>
                    <span className="res-val">{recommendResult.area_utilization_pct}%</span>
                  </div>
                  <div className="result-item">
                    <span className="res-lbl">Constraint Verification</span>
                    <span className="res-val text-success">
                      Spatial Fit: OK | Crane Safe: OK
                    </span>
                    <span className="res-sub">Candidates Evaluated: {recommendResult.constraints_verified.feasible_candidates_count} platens</span>
                  </div>
                </div>
              </div>
            )}
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
