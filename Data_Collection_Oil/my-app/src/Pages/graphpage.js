import React, { useEffect, useState, useMemo } from "react";
import {
  ComposedChart, Bar, Line, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

const COLORS = [
  "#4F46E5","#06B6D4","#10B981","#F59E0B","#EF4444",
  "#8B5CF6","#EC4899","#14B8A6","#F97316","#3B82F6",
];

const API_BASE = "http://127.0.0.1:8000/api";

// ── helpers ──────────────────────────────────────────────

function groupBy5Days(data) {
  if (!data || data.length === 0) return [];
  const sorted = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
  const grouped = [];
  for (let i = 0; i < sorted.length; i += 5) {
    const chunk   = sorted.slice(i, i + 5);
    const validOil = chunk.map(d => Number(d.oil_price)).filter(v => !Number.isNaN(v));
    grouped.push({
      date:        chunk[0].date,
      tweet_count: chunk.reduce((s, d) => s + (Number(d.tweet_count) || 0), 0),
      oil_price:   validOil.length > 0
        ? Number((validOil.reduce((s, v) => s + v, 0) / validOil.length).toFixed(2))
        : null,
    });
  }
  return grouped;
}

function groupByMonth(data) {
  if (!data || data.length === 0) return [];
  const map = {};
  data.forEach(item => {
    const d = new Date(item.date);
    if (Number.isNaN(d.getTime())) return;
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    if (!map[key]) map[key] = { date: key, tweet_count: 0, oil_prices: [] };
    map[key].tweet_count += Number(item.tweet_count) || 0;
    const oil = Number(item.oil_price);
    if (!Number.isNaN(oil)) map[key].oil_prices.push(oil);
  });
  return Object.values(map).map(item => ({
    date:        item.date,
    tweet_count: item.tweet_count,
    oil_price:   item.oil_prices.length > 0
      ? Number((item.oil_prices.reduce((s, v) => s + v, 0) / item.oil_prices.length).toFixed(2))
      : null,
  })).sort((a, b) => new Date(a.date + "-01") - new Date(b.date + "-01"));
}

// ── shared components ─────────────────────────────────────

function Card({ title, children }) {
  return (
    <div style={{
      background: "white", borderRadius: 24, padding: 20,
      boxShadow: "0 10px 25px rgba(0,0,0,0.08)", marginBottom: 28,
    }}>
      <h2 style={{ marginBottom: 18, color: "#1e3a8a" }}>{title}</h2>
      {children}
    </div>
  );
}

function WordCloudLike({ data }) {
  if (!data || data.length === 0) return <div>No word data available.</div>;
  const maxCount = Math.max(...data.map(d => d.count), 1);
  return (
    <div style={{
      minHeight: 260, padding: 20, borderRadius: 20,
      background: "linear-gradient(135deg, #f8fbff 0%, #eef6ff 100%)",
      border: "1px solid #dbeafe",
      display: "flex", flexWrap: "wrap", gap: "12px 18px",
      alignItems: "center", justifyContent: "center",
    }}>
      {data.map((item, index) => (
        <span key={item.word} style={{
          fontSize: `${14 + (item.count / maxCount) * 30}px`,
          fontWeight: 600, color: COLORS[index % COLORS.length],
          padding: "4px 8px", borderRadius: "999px",
          background: "rgba(255,255,255,0.7)",
          transform: `rotate(${(index % 5 - 2) * 6}deg)`,
        }}>{item.word}</span>
      ))}
    </div>
  );
}

// ── date range selector ───────────────────────────────────

function DateRangeSelector({ allDates, startDate, endDate, onChange }) {
  const months = useMemo(() => {
    const set = new Set();
    allDates.forEach(d => {
      if (d) set.add(d.slice(0, 7)); // "YYYY-MM"
    });
    return [...set].sort();
  }, [allDates]);

  if (months.length === 0) return null;

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12,
      flexWrap: "wrap", marginBottom: 16,
      background: "#f8fafc", padding: "12px 16px",
      borderRadius: 12, border: "1px solid #e2e8f0",
    }}>
      <span style={{ fontWeight: 600, color: "#374151", fontSize: 14 }}>
        Date range:
      </span>

      <select
        value={startDate}
        onChange={e => onChange(e.target.value, endDate)}
        style={selectStyle}
      >
        {months.map(m => <option key={m} value={m}>{m}</option>)}
      </select>

      <span style={{ color: "#9ca3af" }}>→</span>

      <select
        value={endDate}
        onChange={e => onChange(startDate, e.target.value)}
        style={selectStyle}
      >
        {months.map(m => <option key={m} value={m}>{m}</option>)}
      </select>

      <button
        onClick={() => onChange(months[0], months[months.length - 1])}
        style={{
          padding: "5px 12px", borderRadius: 8,
          border: "1px solid #d1d5db", background: "white",
          cursor: "pointer", fontSize: 13, color: "#6b7280",
        }}
      >Reset</button>
    </div>
  );
}

const selectStyle = {
  padding: "5px 10px", borderRadius: 8,
  border: "1px solid #d1d5db", background: "white",
  fontSize: 13, color: "#374151", cursor: "pointer",
};

// ── prediction card ───────────────────────────────────────

function PredictionCard({ prediction }) {
  if (!prediction || prediction.error) {
    return <Card title="Latest Oil Prediction"><p>No prediction available yet.</p></Card>;
  }
  const hasActual = prediction.actual_price !== null && prediction.actual_price !== undefined;
  return (
    <Card title="Latest Oil Prediction">
      <div style={{
        background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
        borderRadius: 18, padding: 20, border: "1px solid #bfdbfe",
      }}>
        <h1 style={{ color: "#1d4ed8", marginBottom: 10 }}>
          Predicted Price Range: {prediction.predicted_range || "Unknown"}
        </h1>
        <p><b>Prediction Date:</b> {prediction.prediction_date || "Unknown"}</p>
        <p><b>Target Date:</b>     {prediction.target_date    || "Unknown"}</p>
        <p><b>Latest Data Date:</b>{prediction.latest_data_date || "Unknown"}</p>
        {prediction.last3_dates?.length > 0 && (
          <>
            <p><b>Last 3 Days Used:</b></p>
            <ul>{prediction.last3_dates.map((d, i) => <li key={i}>{d}</li>)}</ul>
          </>
        )}
        <hr />
        {hasActual ? (
          <>
            <p><b>Actual Price:</b> {prediction.actual_price}</p>
            <p><b>Actual Range:</b> {prediction.actual_range || "Unknown"}</p>
            <p><b>Correct:</b> {prediction.is_correct ? "✅ Yes" : "❌ No"}</p>
          </>
        ) : (
          <p><b>Actual Result:</b> Not known yet — updates when the target date appears in oil data.</p>
        )}
      </div>
    </Card>
  );
}

// ── prediction accuracy chart ─────────────────────────────

function PredictionAccuracyChart({ data }) {
  const [startDate, setStartDate] = useState(null);
  const [endDate,   setEndDate]   = useState(null);

  const chartData = useMemo(() => (data || [])
    .map(item => ({
      target_date:     item.target_date,
      actual_price:    Number(item.actual_price),
      predicted_range: item.predicted_range,
      actual_range:    item.actual_range,
      is_correct:      item.is_correct === true || item.is_correct === 1 ? 1 : 0,
    }))
    .filter(item => item.target_date && !Number.isNaN(item.actual_price) && item.actual_price !== null)
    .sort((a, b) => new Date(a.target_date) - new Date(b.target_date)),
  [data]);

  const allMonths = useMemo(() =>
    [...new Set(chartData.map(d => d.target_date?.slice(0, 7)))].filter(Boolean).sort(),
  [chartData]);

  // Initialise range once data arrives
  useEffect(() => {
    if (allMonths.length > 0 && !startDate) {
      setStartDate(allMonths[0]);
      setEndDate(allMonths[allMonths.length - 1]);
    }
  }, [allMonths]);

  const handleRange = (s, e) => {
    if (s <= e) { setStartDate(s); setEndDate(e); }
  };

  const filtered = useMemo(() => {
    if (!startDate || !endDate) return chartData;
    return chartData.filter(d => {
      const m = d.target_date?.slice(0, 7);
      return m >= startDate && m <= endDate;
    });
  }, [chartData, startDate, endDate]);

  if (chartData.length === 0) {
    return (
      <Card title="Prediction Accuracy">
        <p>No completed prediction accuracy data available yet.</p>
      </Card>
    );
  }

  const correctCount = filtered.filter(d => d.is_correct === 1).length;
  const accuracy     = filtered.length > 0
    ? ((correctCount / filtered.length) * 100).toFixed(1) : "0.0";

  return (
    <Card title="Prediction Accuracy">
      <DateRangeSelector
        allDates={chartData.map(d => d.target_date)}
        startDate={startDate || ""}
        endDate={endDate || ""}
        onChange={handleRange}
      />

      <div style={{
        marginBottom: 18, background: "#f8fafc", padding: 14,
        borderRadius: 14, border: "1px solid #e2e8f0",
      }}>
        <h3 style={{ margin: 0, color: "#1e3a8a" }}>Accuracy: {accuracy}%</h3>
        <p style={{ margin: "6px 0 0 0" }}>
          Correct: {correctCount} / {filtered.length}
        </p>
      </div>

      <div style={{ overflowX: "auto" }}>
      <div style={{ minWidth: Math.max(600, filtered.length * 28), height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="target_date" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" domain={[0, 1]} ticks={[0, 1]} />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="actual_price"
              stroke="#2563EB" strokeWidth={3} name="Actual Oil Price" />
            <Scatter yAxisId="right" dataKey="is_correct"
              fill="#10B981" name="Correct Prediction" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      </div>

      {/* details table */}
      <div style={{ marginTop: 16 }}>
        <h3 style={{ color: "#1e3a8a" }}>Prediction Details</h3>
        <div style={{ overflowX: "auto", maxHeight: 400, overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: 10 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", background: "white" }}>
            <thead>
              <tr style={{ background: "#eff6ff" }}>
                {["Date","Predicted Range","Actual Price","Actual Range","Correct"].map(h => (
                  <th key={h} style={cellStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={i}>
                  <td style={cellStyle}>{row.target_date}</td>
                  <td style={cellStyle}>{row.predicted_range || "-"}</td>
                  <td style={cellStyle}>{row.actual_price}</td>
                  <td style={cellStyle}>{row.actual_range || "-"}</td>
                  <td style={cellStyle}>{row.is_correct === 1 ? "✅ Yes" : "❌ No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}

const cellStyle = { border: "1px solid #e5e7eb", padding: "10px", textAlign: "left" };

// ── tweets vs oil chart ───────────────────────────────────

function TweetsVsOilChart({ rawData }) {
  const grouped  = useMemo(() => groupBy5Days(rawData), [rawData]);
  const allMonths = useMemo(() =>
    [...new Set(grouped.map(d => d.date?.slice(0, 7)))].filter(Boolean).sort(),
  [grouped]);

  const [startDate, setStartDate] = useState(null);
  const [endDate,   setEndDate]   = useState(null);

  useEffect(() => {
    if (allMonths.length > 0 && !startDate) {
      setStartDate(allMonths[0]);
      setEndDate(allMonths[allMonths.length - 1]);
    }
  }, [allMonths]);

  const handleRange = (s, e) => { if (s <= e) { setStartDate(s); setEndDate(e); } };

  const filtered = useMemo(() => {
    if (!startDate || !endDate) return grouped;
    return grouped.filter(d => {
      const m = d.date?.slice(0, 7);
      return m >= startDate && m <= endDate;
    });
  }, [grouped, startDate, endDate]);

  return (
    <Card title="Tweets vs Oil Price (Grouped by 5 Days)">
      <DateRangeSelector
        allDates={grouped.map(d => d.date)}
        startDate={startDate || ""}
        endDate={endDate || ""}
        onChange={handleRange}
      />
      <div style={{ overflowX: "auto" }}>
      <div style={{ minWidth: Math.max(600, filtered.length * 28), height: 350 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={filtered}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Bar   yAxisId="left"  dataKey="tweet_count" fill="#06B6D4" name="Tweets" />
            <Line  yAxisId="right" type="monotone" dataKey="oil_price"
              stroke="#EF4444" strokeWidth={3} name="Oil Price" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      </div>
    </Card>
  );
}

// ── main page ─────────────────────────────────────────────

export default function GraphPage() {
  const [commonWords,       setCommonWords]       = useState([]);
  const [tweetsVsOil,       setTweetsVsOil]       = useState([]);
  const [byPublisher,       setByPublisher]       = useState({});
  const [prediction,        setPrediction]        = useState(null);
  const [predictionAccuracy,setPredictionAccuracy] = useState([]);
  const [loading,           setLoading]           = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/graph/common-words/`).then(r => r.json()),
      fetch(`${API_BASE}/graph/tweets-vs-oil/`).then(r => r.json()),
      fetch(`${API_BASE}/graph/tweets-vs-oil-by-publisher/`).then(r => r.json()),
      fetch(`${API_BASE}/prediction/`).then(r => r.json()),
      fetch(`${API_BASE}/prediction/accuracy/`).then(r => r.json()),
    ])
    .then(([wordsData, tweetsOilData, byPublisherData, predictionData, accuracyData]) => {
      setCommonWords(Array.isArray(wordsData) ? wordsData : []);
      setTweetsVsOil(Array.isArray(tweetsOilData) ? tweetsOilData : []);
      setPrediction(predictionData);
      setPredictionAccuracy(Array.isArray(accuracyData) ? accuracyData : []);

      const groupedPublishers = {};
      if (byPublisherData && typeof byPublisherData === "object") {
        for (const key in byPublisherData) {
          groupedPublishers[key] = groupByMonth(byPublisherData[key]);
        }
      }
      setByPublisher(groupedPublishers);
    })
    .catch(err => console.error("Error loading dashboard:", err))
    .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 30, background: "#f1f5f9", minHeight: "100vh", fontSize: 20 }}>
        Loading dashboard...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, background: "#f1f5f9", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <h1 style={{ marginBottom: 20, color: "#0f172a" }}>Oil + Tweets Dashboard</h1>

        <PredictionCard prediction={prediction} />

        <PredictionAccuracyChart data={predictionAccuracy} />

        <Card title="Most Common Words">
          <WordCloudLike data={commonWords} />
        </Card>

        <TweetsVsOilChart rawData={tweetsVsOil} />

        <Card title="By Publisher (Monthly)">
          {Object.keys(byPublisher).length === 0 ? (
            <p>No publisher data available.</p>
          ) : (
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              gap: 20,
            }}>
              {Object.keys(byPublisher).map((publisher, i) => (
                <div key={publisher} style={{
                  background: "white", padding: 12,
                  borderRadius: 16, border: "1px solid #e5e7eb",
                }}>
                  <h3 style={{ color: "#1e3a8a" }}>{publisher}</h3>
                  <div style={{ height: 250 }}>
                    <ResponsiveContainer>
                      <ComposedChart data={byPublisher[publisher]}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis yAxisId="left" />
                        <YAxis yAxisId="right" orientation="right" />
                        <Tooltip />
                        <Legend />
                        <Bar  yAxisId="left"  dataKey="tweet_count"
                          fill={COLORS[i % COLORS.length]} name="Tweets" />
                        <Line yAxisId="right" type="monotone" dataKey="oil_price"
                          stroke="#EF4444" strokeWidth={2} name="Oil Price" />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}